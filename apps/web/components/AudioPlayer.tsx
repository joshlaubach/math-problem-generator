'use client'

import { useEffect, useRef, useCallback, useState } from 'react'
import { useAuth } from '@clerk/nextjs'

interface AudioPlayerProps {
  /** Text to synthesize and play. Pass null to stop. */
  text: string | null
  voiceMode: boolean
  onComplete?: () => void
}

export function AudioPlayer({ text, voiceMode, onComplete }: AudioPlayerProps) {
  const { getToken } = useAuth()
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
  const prevTextRef = useRef<string | null>(null)

  const synthesizeAndPlay = useCallback(async (textToSpeak: string) => {
    setError(null)
    try {
      const token = await getToken()
      const resp = await fetch(`${apiBase}/tutor/synthesize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text: textToSpeak }),
      })

      if (!resp.ok) {
        throw new Error(`TTS error: ${resp.status}`)
      }

      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)

      // Stop any currently playing audio
      if (audioRef.current) {
        audioRef.current.pause()
        URL.revokeObjectURL(audioRef.current.src)
      }

      const audio = new Audio(url)
      audioRef.current = audio
      audio.onended = () => {
        setIsPlaying(false)
        URL.revokeObjectURL(url)
        onComplete?.()
      }
      audio.onerror = () => {
        setIsPlaying(false)
        setError('Audio playback failed.')
      }
      await audio.play()
      setIsPlaying(true)
    } catch (err) {
      setError('Voice synthesis unavailable.')
      onComplete?.()
    }
  }, [getToken, apiBase, onComplete])

  const stopPlayback = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current = null
    }
    setIsPlaying(false)
  }, [])

  // Auto-play when text changes and voice mode is on
  useEffect(() => {
    if (!voiceMode || !text || text === prevTextRef.current) return
    prevTextRef.current = text
    synthesizeAndPlay(text)
  }, [text, voiceMode, synthesizeAndPlay])

  // Cleanup on unmount
  useEffect(() => {
    return () => stopPlayback()
  }, [stopPlayback])

  if (!voiceMode) return null

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      {isPlaying && (
        <>
          <div style={{
            display: 'flex', gap: 2, alignItems: 'flex-end', height: 16,
          }}>
            {[4, 8, 6, 10, 5].map((h, i) => (
              <div key={i} style={{
                width: 3, height: h, borderRadius: 2,
                background: 'var(--caramel)',
                animation: `soundbar 0.6s ${i * 0.1}s ease-in-out infinite alternate`,
              }} />
            ))}
          </div>
          <button
            onClick={stopPlayback}
            style={{
              fontSize: 11, padding: '2px 8px', borderRadius: 6,
              border: '1px solid var(--border)', background: 'none',
              cursor: 'pointer', color: 'var(--text-dim)',
            }}
          >
            Skip
          </button>
        </>
      )}
      {error && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{error}</span>}
    </div>
  )
}
