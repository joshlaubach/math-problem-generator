'use client'

import { useState, useRef, useCallback } from 'react'
import { useAuth } from '@clerk/nextjs'

interface VoiceInputProps {
  onTranscript: (text: string) => void
  onLowConfidence: () => void
  disabled?: boolean
}

type RecordingState = 'idle' | 'recording' | 'transcribing' | 'error'

export function VoiceInput({ onTranscript, onLowConfidence, disabled }: VoiceInputProps) {
  const { getToken } = useAuth()
  const [state, setState] = useState<RecordingState>('idle')
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  const startRecording = useCallback(async () => {
    setErrorMsg(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' })
      mediaRecorderRef.current = mediaRecorder
      chunksRef.current = []

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop())
        setState('transcribing')
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        await transcribeBlob(blob)
      }

      mediaRecorder.start()
      setState('recording')
    } catch (err) {
      setErrorMsg('Microphone access denied. Please allow microphone access.')
      setState('error')
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop()
    }
  }, [])

  const transcribeBlob = useCallback(async (blob: Blob) => {
    try {
      const token = await getToken()
      const formData = new FormData()
      formData.append('file', blob, 'audio.webm')

      const resp = await fetch(`${apiBase}/tutor/transcribe`, {
        method: 'POST',
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
        body: formData,
      })

      if (!resp.ok) {
        throw new Error(`Transcription failed (${resp.status})`)
      }

      const data = await resp.json() as { text: string | null; confidence: number; low_confidence: boolean }

      if (data.low_confidence || !data.text) {
        onLowConfidence()
      } else {
        onTranscript(data.text)
      }
      setState('idle')
    } catch (err) {
      setErrorMsg('Could not transcribe audio. Please try again.')
      setState('error')
    }
  }, [getToken, apiBase, onTranscript, onLowConfidence])

  const isRecording = state === 'recording'
  const isTranscribing = state === 'transcribing'
  const isDisabled = disabled || isTranscribing

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 6 }}>
      <button
        onMouseDown={startRecording}
        onMouseUp={stopRecording}
        onTouchStart={startRecording}
        onTouchEnd={stopRecording}
        disabled={isDisabled}
        aria-label={isRecording ? 'Release to stop recording' : 'Hold to record'}
        style={{
          width: 52, height: 52, borderRadius: '50%', border: 'none', cursor: isDisabled ? 'not-allowed' : 'pointer',
          background: isRecording ? 'var(--terracotta)' : isTranscribing ? 'var(--caramel)' : 'var(--surface2)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 22,
          boxShadow: isRecording ? '0 0 0 6px rgba(193,68,14,0.2)' : 'none',
          transition: 'all 0.15s', flexShrink: 0,
          opacity: isDisabled && !isTranscribing ? 0.5 : 1,
        }}
      >
        {isTranscribing ? '⟳' : isRecording ? '⏹' : '🎤'}
      </button>
      <span style={{ fontSize: 10, color: 'var(--text-muted)', textAlign: 'center' }}>
        {isRecording ? 'Recording… release to stop'
          : isTranscribing ? 'Transcribing…'
          : 'Hold to speak'}
      </span>
      {errorMsg && (
        <div style={{ fontSize: 11, color: 'var(--terracotta)', textAlign: 'center', maxWidth: 160 }}>
          {errorMsg}
        </div>
      )}
    </div>
  )
}
