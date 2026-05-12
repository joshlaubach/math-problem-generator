'use client'

import { useState, useCallback } from 'react'
import { useAuth } from '@clerk/nextjs'
import { MathInput } from './MathInput'

interface ScratchpadProps {
  sessionId: string
  /** Called when any valid entry is submitted (so the parent can unlock hints) */
  onWorkSubmitted: () => void
  /** Which box the tutor is currently requesting */
  requestedBox?: 'reasoning' | 'expression' | null
  disabled?: boolean
}

interface Entry {
  box: 'reasoning' | 'expression'
  content: string
  result: 'valid' | 'invalid' | 'unknown' | 'reasoning' | 'pending'
}

export function Scratchpad({ sessionId, onWorkSubmitted, requestedBox, disabled }: ScratchpadProps) {
  const { getToken } = useAuth()
  const [reasoningText, setReasoningText] = useState('')
  const [expressionLatex, setExpressionLatex] = useState('')
  const [entries, setEntries] = useState<Entry[]>([])
  const [loading, setLoading] = useState<'reasoning' | 'expression' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastInvalidExpression, setLastInvalidExpression] = useState<string | null>(null)
  const [disputeLoading, setDisputeLoading] = useState(false)
  const [disputeResult, setDisputeResult] = useState<string | null>(null)

  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  const submitBox = useCallback(async (box: 'reasoning' | 'expression') => {
    const content = box === 'reasoning' ? reasoningText.trim() : expressionLatex.trim()
    if (!content) return

    setLoading(box)
    setError(null)

    // Optimistically add entry
    const optimisticEntry: Entry = { box, content, result: 'pending' }
    setEntries(prev => [...prev, optimisticEntry])

    try {
      const token = await getToken()
      const resp = await fetch(`${apiBase}/tutor/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ session_id: sessionId, box, content }),
      })
      const data = await resp.json() as { valid: boolean; sympy_result: string; feedback?: string }

      setEntries(prev =>
        prev.map((e, i) =>
          i === prev.length - 1 && e.result === 'pending'
            ? { ...e, result: data.sympy_result as Entry['result'] }
            : e
        )
      )

      if (data.valid) {
        if (box === 'reasoning') setReasoningText('')
        else setExpressionLatex('')
        onWorkSubmitted()
      } else if (data.feedback) {
        setError(data.feedback)
        // Keep entry in history but mark invalid — show dispute option for expression box
        if (box === 'expression') {
          setLastInvalidExpression(content)
        } else {
          setEntries(prev => prev.slice(0, -1))
        }
      }
    } catch {
      setEntries(prev => prev.slice(0, -1))
      setError('Could not validate — please try again.')
    } finally {
      setLoading(null)
    }
  }, [reasoningText, expressionLatex, sessionId, apiBase, onWorkSubmitted, getToken])

  const handleDispute = useCallback(async () => {
    if (!lastInvalidExpression) return
    setDisputeLoading(true)
    setDisputeResult(null)
    try {
      const token = await getToken()
      const resp = await fetch(`${apiBase}/tutor/dispute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ session_id: sessionId, expression: lastInvalidExpression }),
      })
      const data = await resp.json() as { accepted: boolean; message: string }
      setDisputeResult(data.message)
      if (data.accepted) {
        setError(null)
        setLastInvalidExpression(null)
        onWorkSubmitted()
      }
    } catch {
      setDisputeResult('Could not process dispute. Please try again.')
    } finally {
      setDisputeLoading(false)
    }
  }, [lastInvalidExpression, sessionId, apiBase, getToken, onWorkSubmitted])

  const isRequested = (box: 'reasoning' | 'expression') =>
    requestedBox === box || requestedBox == null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{
        fontSize: 12, fontWeight: 600, color: 'var(--text-dim)',
        letterSpacing: '0.05em', textTransform: 'uppercase',
      }}>
        Scratchpad
      </div>

      {/* Entry history */}
      {entries.length > 0 && (
        <div style={{
          maxHeight: 140, overflowY: 'auto',
          display: 'flex', flexDirection: 'column', gap: 6,
        }}>
          {entries.map((e, i) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'flex-start', gap: 8,
              padding: '6px 10px', borderRadius: 8,
              background: e.result === 'invalid' ? 'var(--terra-dim)'
                : e.result === 'pending' ? 'var(--surface2)'
                : 'var(--sage-dim, rgba(100,150,100,0.1))',
              border: `1px solid ${
                e.result === 'invalid' ? 'rgba(193,68,14,0.2)'
                : e.result === 'pending' ? 'var(--border)'
                : 'rgba(100,150,100,0.2)'
              }`,
            }}>
              <span style={{
                fontSize: 10, fontWeight: 600,
                color: e.box === 'expression' ? 'var(--caramel)' : 'var(--text-dim)',
                flexShrink: 0, marginTop: 1,
              }}>
                {e.box === 'expression' ? 'EXP' : 'NOTE'}
              </span>
              <span style={{ fontSize: 13, color: 'var(--text)', fontFamily: 'monospace', flex: 1 }}>
                {e.content}
              </span>
              <span style={{ fontSize: 10, color: 'var(--text-muted)', flexShrink: 0 }}>
                {e.result === 'pending' ? '…'
                  : e.result === 'invalid' ? '✗'
                  : e.result === 'unknown' ? '?'
                  : '✓'}
              </span>
            </div>
          ))}
        </div>
      )}

      {error && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{
            padding: '8px 12px', borderRadius: 8, fontSize: 12,
            color: 'var(--terracotta)', background: 'var(--terra-dim)',
            border: '1px solid rgba(193,68,14,0.2)',
          }}>
            {error}
          </div>
          {lastInvalidExpression && !disputeResult && (
            <button
              onClick={handleDispute}
              disabled={disputeLoading}
              style={{
                padding: '6px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600,
                background: 'none', border: '1px solid var(--border)', cursor: 'pointer',
                color: 'var(--text-dim)', textAlign: 'center',
                opacity: disputeLoading ? 0.6 : 1,
              }}
            >
              {disputeLoading ? 'Checking…' : 'I think I\'m right →'}
            </button>
          )}
          {disputeResult && (
            <div style={{
              padding: '8px 12px', borderRadius: 8, fontSize: 12,
              color: 'var(--text-dim)', background: 'var(--surface2)',
              border: '1px solid var(--border)',
            }}>
              {disputeResult}
            </div>
          )}
        </div>
      )}

      {/* Reasoning box */}
      {isRequested('reasoning') && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 500 }}>
            Reasoning / Setup
          </label>
          <div style={{ display: 'flex', gap: 6 }}>
            <textarea
              value={reasoningText}
              onChange={e => setReasoningText(e.target.value)}
              disabled={disabled || loading !== null}
              placeholder="e.g. Let x = the unknown value…"
              rows={2}
              style={{
                flex: 1, padding: '8px 10px', borderRadius: 8, resize: 'none',
                border: '1px solid var(--border)', background: 'var(--surface2)',
                fontSize: 13, color: 'var(--text)', fontFamily: 'inherit',
                outline: 'none',
              }}
            />
            <button
              onClick={() => submitBox('reasoning')}
              disabled={!reasoningText.trim() || disabled || loading !== null}
              style={{
                padding: '0 12px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: 'var(--caramel)', color: '#fff', fontSize: 13, fontWeight: 600,
                opacity: reasoningText.trim() && !disabled ? 1 : 0.4,
                flexShrink: 0,
              }}
            >
              {loading === 'reasoning' ? '…' : '↑'}
            </button>
          </div>
        </div>
      )}

      {/* Expression box */}
      {isRequested('expression') && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <label style={{ fontSize: 12, color: 'var(--text-dim)', fontWeight: 500 }}>
            Math Expression
            <span style={{ marginLeft: 6, fontSize: 10, color: 'var(--caramel)' }}>
              verified
            </span>
          </label>
          <div style={{ display: 'flex', gap: 6, alignItems: 'flex-start' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <MathInput
                value={expressionLatex}
                onChange={setExpressionLatex}
                placeholder="e.g. 2x + 5 = 13"
              />
            </div>
            <button
              onClick={() => submitBox('expression')}
              disabled={!expressionLatex.trim() || disabled || loading !== null}
              style={{
                padding: '8px 12px', borderRadius: 8, border: 'none', cursor: 'pointer',
                background: 'var(--caramel)', color: '#fff', fontSize: 13, fontWeight: 600,
                opacity: expressionLatex.trim() && !disabled ? 1 : 0.4,
                flexShrink: 0,
                marginTop: 2,
              }}
            >
              {loading === 'expression' ? '…' : '↑'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
