'use client'

/**
 * useVoicePipeline — open-mic voice pipeline for the tutor session.
 *
 * Architecture:
 *   Mic → AudioContext(16kHz) → AnalyserNode → AudioWorkletNode → silent gain → destination
 *                                     ↓ VAD (energy RMS)
 *   AudioWorklet postMessage → main thread → WebSocket → backend → Deepgram → transcript
 *
 * States returned (map directly to VoiceIndicatorState):
 *   idle        — pipeline ready, no speech detected
 *   recording   — student speaking (energy VAD threshold crossed)
 *   transcribing — speech_final received from Deepgram, waiting for Claude
 *
 * The page layer overlays 'thinking' and 'speaking' on top of these based on its own
 * knowledge of Claude generation and TTS playback.
 *
 * Barge-in: when energy VAD fires during TTS, onBargeIn() is called immediately so
 * the page can stop the current audio element and clear the queue.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import type { VoiceIndicatorState } from '@/components/VoiceIndicator'

// ── Energy VAD config ──────────────────────────────────────────────────────────

// RMS threshold above which audio is considered speech.
// Calibrated for a typical indoor tutoring environment.
const VAD_SPEECH_THRESHOLD = 0.015

// Student must sustain speech for this many ms before barge-in fires.
// Prevents "hmm" or a cough from cutting the tutor off.
const BARGE_IN_SUSTAIN_MS = 500

// After the last speech frame, wait this long before resetting to idle.
// Deepgram's endpointing handles the actual utterance boundary — this is just
// for local state cleanup after the server confirms speech_final.
const POST_SPEECH_IDLE_MS = 1500

export interface UseVoicePipelineOptions {
  sessionId: string
  token: string
  apiBase: string
  /** Pipeline is active only when true. Teardown runs when it flips to false. */
  enabled: boolean
  /** Called when Deepgram returns a speech_final transcript. */
  onTranscript: (text: string) => void
  /** Called when the energy VAD detects sustained student speech (barge-in). */
  onBargeIn: () => void
}

export interface VoicePipelineHandle {
  /** Current voice indicator state (idle | recording | transcribing). */
  voiceState: VoiceIndicatorState
  /** Whether filler clips have been pre-synthesized and are ready to play. */
  fillerReady: boolean
  /** Play a random filler clip ("Hmm.", "Okay.", etc.) */
  playFiller: () => void
}

const FILLER_TEXTS = ['Hmm.', 'Okay.', 'Interesting.', 'I see.', 'Let me think.']

export function useVoicePipeline({
  sessionId,
  token,
  apiBase,
  enabled,
  onTranscript,
  onBargeIn,
}: UseVoicePipelineOptions): VoicePipelineHandle {
  const [voiceState, setVoiceState] = useState<VoiceIndicatorState>('idle')
  const [fillerReady, setFillerReady] = useState(false)

  // Persistent refs survive re-renders and don't cause re-renders themselves
  const wsRef = useRef<WebSocket | null>(null)
  const audioCtxRef = useRef<AudioContext | null>(null)
  const fillerBuffersRef = useRef<AudioBuffer[]>([])
  const cleanupRef = useRef<(() => void) | null>(null)
  const onTranscriptRef = useRef(onTranscript)
  const onBargeInRef = useRef(onBargeIn)

  // Keep callback refs fresh without re-running the pipeline effect
  useEffect(() => { onTranscriptRef.current = onTranscript }, [onTranscript])
  useEffect(() => { onBargeInRef.current = onBargeIn }, [onBargeIn])

  // ── Pre-synthesize filler clips ─────────────────────────────────────────────
  useEffect(() => {
    if (!enabled || !token || fillerBuffersRef.current.length > 0) return
    let cancelled = false

    async function prefetch() {
      const ctx = new AudioContext()
      audioCtxRef.current ??= ctx
      const buffers: AudioBuffer[] = []

      for (const text of FILLER_TEXTS) {
        if (cancelled) break
        try {
          const resp = await fetch(`${apiBase}/tutor/synthesize`, {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`,
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text }),
          })
          if (!resp.ok) continue
          const arr = await resp.arrayBuffer()
          const decoded = await (audioCtxRef.current ?? ctx).decodeAudioData(arr)
          buffers.push(decoded)
        } catch {
          // Skip this filler — not fatal
        }
      }

      if (!cancelled && buffers.length > 0) {
        fillerBuffersRef.current = buffers
        setFillerReady(true)
      }
    }

    prefetch()
    return () => { cancelled = true }
  }, [enabled, token, apiBase])

  // ── Main pipeline ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!enabled || !sessionId || !token) {
      setVoiceState('idle')
      return
    }

    let cancelled = false
    let ws: WebSocket | null = null
    let audioCtx: AudioContext | null = null
    let stream: MediaStream | null = null
    let workletNode: AudioWorkletNode | null = null
    let analyser: AnalyserNode | null = null
    let vadTimer: ReturnType<typeof setTimeout> | null = null
    let bargeInTimer: ReturnType<typeof setTimeout> | null = null
    let speechActive = false
    let deepgramReady = false
    let animFrameId: number | null = null

    function teardown() {
      cancelled = true
      if (animFrameId !== null) cancelAnimationFrame(animFrameId)
      if (vadTimer) clearTimeout(vadTimer)
      if (bargeInTimer) clearTimeout(bargeInTimer)
      if (workletNode) { try { workletNode.disconnect() } catch { } }
      if (analyser) { try { analyser.disconnect() } catch { } }
      if (stream) stream.getTracks().forEach(t => t.stop())
      if (audioCtx && audioCtx.state !== 'closed') audioCtx.close().catch(() => {})
      if (ws && ws.readyState !== WebSocket.CLOSED) {
        try { ws.send(JSON.stringify({ type: 'close' })) } catch { }
        ws.close(1000)
      }
      stream = null; audioCtx = null; workletNode = null
      analyser = null; ws = null
      setVoiceState('idle')
    }

    cleanupRef.current = teardown

    async function startPipeline() {
      // 1. Microphone
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        })
      } catch {
        return
      }
      if (cancelled) { stream.getTracks().forEach(t => t.stop()); return }

      // 2. AudioContext at 16 kHz — browser resamples mic input automatically
      try {
        audioCtx = new AudioContext({ sampleRate: 16000 })
        audioCtxRef.current = audioCtx
      } catch {
        // Fallback: let browser choose rate; Deepgram handles most rates with
        // appropriate query param update — acceptable degradation
        audioCtx = new AudioContext()
        audioCtxRef.current = audioCtx
      }
      const source = audioCtx.createMediaStreamSource(stream)

      // 3. Load AudioWorklet processor
      try {
        await audioCtx.audioWorklet.addModule('/audio-processor.js')
      } catch (e) {
        console.error('[VoicePipeline] AudioWorklet load failed:', e)
        teardown()
        return
      }
      if (cancelled) { teardown(); return }

      workletNode = new AudioWorkletNode(audioCtx, 'pcm-processor')

      // 4. VAD AnalyserNode — monitors RMS for barge-in detection
      analyser = audioCtx.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.4

      // Silent output chain: source → analyser → worklet → silentGain → destination
      // The chain must reach destination for Web Audio to pull (and run) the nodes.
      const silentGain = audioCtx.createGain()
      silentGain.gain.value = 0
      silentGain.connect(audioCtx.destination)

      source.connect(analyser)
      analyser.connect(workletNode)
      workletNode.connect(silentGain)

      // 5. Open Voice WebSocket
      const wsBase = apiBase.replace(/^http(s?)/, 'ws$1')
      ws = new WebSocket(`${wsBase}/ws/voice/${sessionId}`, ['bearer', token])
      wsRef.current = ws

      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        if (cancelled) { ws?.close(); return }
        // WS open but Deepgram may not be connected yet — wait for 'ready'
      }

      ws.onmessage = (ev: MessageEvent) => {
        if (cancelled) return
        try {
          const msg = JSON.parse(ev.data as string)

          if (msg.type === 'ready') {
            deepgramReady = true
            // Start forwarding PCM frames to Deepgram via the backend WS
            workletNode!.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
              if (ws?.readyState === WebSocket.OPEN && deepgramReady) {
                ws.send(e.data)
              }
            }
            setVoiceState('idle')
            startVAD()
          } else if (msg.type === 'speech_final' && msg.text) {
            if (vadTimer) clearTimeout(vadTimer)
            if (bargeInTimer) clearTimeout(bargeInTimer)
            speechActive = false
            setVoiceState('transcribing')
            onTranscriptRef.current(msg.text)
          } else if (msg.type === 'interim' && msg.text) {
            if (!speechActive) {
              // Deepgram detected speech before local VAD fired
              setVoiceState('recording')
            }
          }
        } catch { /* malformed message — ignore */ }
      }

      ws.onerror = (e) => {
        console.error('[VoicePipeline] WS error:', e)
      }

      ws.onclose = () => {
        if (!cancelled) setVoiceState('idle')
      }
    }

    function startVAD() {
      if (!analyser || cancelled) return
      const timeDomain = new Float32Array(analyser.frequencyBinCount)

      function tick() {
        if (cancelled || !analyser) return
        analyser.getFloatTimeDomainData(timeDomain)

        let sum = 0
        for (let i = 0; i < timeDomain.length; i++) {
          sum += timeDomain[i] * timeDomain[i]
        }
        const rms = Math.sqrt(sum / timeDomain.length)

        if (rms > VAD_SPEECH_THRESHOLD) {
          if (vadTimer) { clearTimeout(vadTimer); vadTimer = null }

          if (!speechActive) {
            // Sustained speech check: fire barge-in after BARGE_IN_SUSTAIN_MS
            if (!bargeInTimer) {
              bargeInTimer = setTimeout(() => {
                bargeInTimer = null
                if (!cancelled) {
                  speechActive = true
                  setVoiceState('recording')
                  onBargeInRef.current()
                }
              }, BARGE_IN_SUSTAIN_MS)
            }
          }
        } else {
          // Silence — cancel pending barge-in if not yet fired
          if (bargeInTimer && !speechActive) {
            clearTimeout(bargeInTimer)
            bargeInTimer = null
          }

          if (speechActive && !vadTimer) {
            vadTimer = setTimeout(() => {
              speechActive = false
              vadTimer = null
              // Don't reset voiceState here — wait for speech_final from Deepgram
            }, POST_SPEECH_IDLE_MS)
          }
        }

        animFrameId = requestAnimationFrame(tick)
      }

      animFrameId = requestAnimationFrame(tick)
    }

    startPipeline()

    return teardown
  }, [enabled, sessionId, token, apiBase]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Filler playback ─────────────────────────────────────────────────────────
  const playFiller = useCallback(() => {
    const bufs = fillerBuffersRef.current
    const ctx = audioCtxRef.current
    if (!bufs.length || !ctx) return
    try {
      const buf = bufs[Math.floor(Math.random() * bufs.length)]
      const src = ctx.createBufferSource()
      src.buffer = buf
      src.connect(ctx.destination)
      src.start()
    } catch { /* AudioContext may have been closed */ }
  }, [])

  return { voiceState, fillerReady, playFiller }
}
