'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

export type SessionType = '1hr' | '2hr'

export type TutorSessionState =
  | 'idle'
  | 'connecting'
  | 'discovering'   // open-ended topic detection in progress
  | 'ready'
  | 'thinking'
  | 'solved'
  | 'ended'
  | 'timeout'
  | 'error'

export interface TutorProblem {
  statement: string
  answer_type: string
  hint_ladder_length: number
}

export interface ChatMessage {
  role: 'student' | 'tutor' | 'system'
  content: string
  timestamp: number
}

export interface SessionSummary {
  hints_used: number
  attempts: number
  correct: boolean
  reward: number
  duration_seconds: number
  ai_summary?: string[]
}

export interface TopicOption {
  topic_id: string
  topic_name: string
  course_name: string
}

export interface TutorSessionHook {
  state: TutorSessionState
  problem: TutorProblem | null
  messages: ChatMessage[]
  hintLevel: number
  maxHints: number
  secondsRemaining: number | null
  inGracePeriod: boolean
  isCorrect: boolean
  summary: SessionSummary | null
  lastError: string | null
  // Discovery
  pendingTopicConfirm: { topic_id: string; topic_name: string; mode: string; message: string } | null
  topicPicklist: TopicOption[] | null
  // Actions
  connect: (topicId: string | null, difficulty: number, token: string, sessionType: SessionType) => void
  sendText: (text: string) => void
  submitAnswer: (answer: string) => void
  requestHint: () => void
  endSession: () => void
  disconnect: () => void
  acceptTopic: (topicId: string, mode: string) => void
  rejectTopic: () => void
  // Scratchpad
  scratchpadHasWork: boolean
  setScratchpadHasWork: (v: boolean) => void
}

// ── Constants ─────────────────────────────────────────────────────────────────

const MAX_RECONNECT_ATTEMPTS = 3
const GRACE_PERIOD_SECONDS = 600

const API_WS_BASE = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'
).replace(/^http/, 'ws')

const NO_RECONNECT_CODES = new Set([1000, 4001, 4003, 4004, 4029])

// ── Hook ──────────────────────────────────────────────────────────────────────

export function useTutorSession(): TutorSessionHook {
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectCountRef = useRef(0)
  const connectParamsRef = useRef<{
    topicId: string | null
    difficulty: number
    token: string
    sessionType: SessionType
  } | null>(null)
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [state, setState] = useState<TutorSessionState>('idle')
  const [problem, setProblem] = useState<TutorProblem | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [hintLevel, setHintLevel] = useState(0)
  const [maxHints, setMaxHints] = useState(4)
  const [secondsRemaining, setSecondsRemaining] = useState<number | null>(null)
  const [inGracePeriod, setInGracePeriod] = useState(false)
  const [isCorrect, setIsCorrect] = useState(false)
  const [summary, setSummary] = useState<SessionSummary | null>(null)
  const [lastError, setLastError] = useState<string | null>(null)
  const [pendingTopicConfirm, setPendingTopicConfirm] = useState<{
    topic_id: string; topic_name: string; mode: string; message: string
  } | null>(null)
  const [topicPicklist, setTopicPicklist] = useState<TopicOption[] | null>(null)
  const [scratchpadHasWork, setScratchpadHasWork] = useState(false)

  // ── Countdown ───────────────────────────────────────────────────────────────

  const startCountdown = useCallback((totalSeconds: number, graceSeconds: number) => {
    if (countdownRef.current) clearInterval(countdownRef.current)
    setSecondsRemaining(totalSeconds + graceSeconds)
    countdownRef.current = setInterval(() => {
      setSecondsRemaining(prev => {
        if (prev === null || prev <= 0) return 0
        const next = prev - 1
        setInGracePeriod(next <= graceSeconds && next > 0)
        return next
      })
    }, 1000)
  }, [])

  const stopCountdown = useCallback(() => {
    if (countdownRef.current) {
      clearInterval(countdownRef.current)
      countdownRef.current = null
    }
  }, [])

  // ── Message handler ─────────────────────────────────────────────────────────

  const handleMessage = useCallback((raw: string) => {
    let msg: Record<string, unknown>
    try { msg = JSON.parse(raw) } catch { return }
    const type = msg.type as string

    if (type === 'discovery_start') {
      setState('discovering')
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.prompt as string, timestamp: Date.now() },
      ])
    }

    else if (type === 'topic_confirm') {
      setPendingTopicConfirm({
        topic_id: msg.topic_id as string,
        topic_name: msg.topic_name as string,
        mode: msg.mode as string,
        message: msg.message as string,
      })
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.message as string, timestamp: Date.now() },
      ])
    }

    else if (type === 'topic_picklist') {
      setTopicPicklist(msg.options as TopicOption[])
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.message as string, timestamp: Date.now() },
      ])
    }

    else if (type === 'session_ready') {
      setPendingTopicConfirm(null)
      setTopicPicklist(null)
      const p = msg.problem as TutorProblem
      setProblem(p)
      setMaxHints(p.hint_ladder_length)
      setState('ready')
      const maxDur = (msg.max_duration_seconds as number) ?? 3600
      const graceDur = (msg.grace_period_seconds as number) ?? GRACE_PERIOD_SECONDS
      startCountdown(maxDur, graceDur)

      // If Demonstrate phase, narrate each worked_example step as tutor messages
      const workedExample = msg.worked_example as Array<{expression_latex: string; description_latex: string}> | undefined
      if (workedExample && workedExample.length > 0) {
        const narratedSteps = workedExample
          .map((step, i) => {
            const parts = []
            if (step.description_latex) parts.push(step.description_latex)
            if (step.expression_latex) parts.push(step.expression_latex)
            return `Step ${i + 1}: ${parts.join(' — ')}`
          })
          .join('\n\n')
        setMessages(prev => [
          ...prev,
          { role: 'tutor', content: `Let me walk you through an example:\n\n${narratedSteps}`, timestamp: Date.now() },
        ])
      }

      // Show diagnostic question as first tutor message if present
      const dq = msg.diagnostic_question as string | undefined
      if (dq) {
        setMessages(prev => [
          ...prev,
          { role: 'tutor', content: dq, timestamp: Date.now() },
        ])
      }
    }

    else if (type === 'agent_text') {
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.text as string, timestamp: Date.now() },
      ])
      setState('ready')
    }

    else if (type === 'answer_result') {
      if (msg.correct as boolean) {
        setIsCorrect(true)
        setState('solved')
        stopCountdown()
      } else {
        setState('ready')
      }
    }

    else if (type === 'hint') {
      setHintLevel(msg.level as number)
      setMessages(prev => [
        ...prev,
        {
          role: 'system',
          content: `Hint ${msg.level}/${msg.max_level}: ${msg.text}`,
          timestamp: Date.now(),
        },
      ])
      setState('ready')
    }

    else if (type === 'time_warning') {
      setMessages(prev => [
        ...prev,
        {
          role: 'system',
          content: `Your session ends in ${msg.minutes_remaining} minutes.`,
          timestamp: Date.now(),
        },
      ])
    }

    else if (type === 'session_end' || type === 'session_timeout') {
      stopCountdown()
      setSummary(msg.summary as SessionSummary)
      setState(type === 'session_timeout' ? 'timeout' : 'ended')
    }

    else if (type === 'error') {
      setLastError(msg.message as string)
    }
  }, [startCountdown, stopCountdown])

  // ── WS open ─────────────────────────────────────────────────────────────────

  const openWs = useCallback((
    sessionId: string,
    topicId: string | null,
    difficulty: number,
    token: string,
    sessionType: SessionType,
  ) => {
    let url =
      `${API_WS_BASE}/ws/tutor/${sessionId}` +
      `?token=${encodeURIComponent(token)}` +
      `&difficulty=${difficulty}` +
      `&session_type=${sessionType}`
    if (topicId) url += `&topic_id=${encodeURIComponent(topicId)}`

    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onmessage = (event) => handleMessage(event.data as string)

    ws.onclose = (event) => {
      const shouldReconnect =
        !NO_RECONNECT_CODES.has(event.code) &&
        reconnectCountRef.current < MAX_RECONNECT_ATTEMPTS &&
        connectParamsRef.current !== null

      if (shouldReconnect) {
        reconnectCountRef.current++
        const delay = 1000 * Math.pow(2, reconnectCountRef.current - 1)
        setTimeout(() => {
          if (!connectParamsRef.current) return
          const { topicId: t, difficulty: d, token: tk, sessionType: st } = connectParamsRef.current
          openWs(crypto.randomUUID(), t, d, tk, st)
        }, delay)
      } else {
        if (state !== 'solved' && state !== 'ended' && state !== 'timeout') {
          setState(NO_RECONNECT_CODES.has(event.code) ? 'error' : 'ended')
        }
        stopCountdown()
      }
    }

    ws.onerror = () => setLastError('Connection error. Retrying…')
  }, [handleMessage, state, stopCountdown])

  // ── Public API ──────────────────────────────────────────────────────────────

  const connect = useCallback((
    topicId: string | null,
    difficulty: number,
    token: string,
    sessionType: SessionType,
  ) => {
    reconnectCountRef.current = 0
    connectParamsRef.current = { topicId, difficulty, token, sessionType }
    setState('connecting')
    setMessages([])
    setProblem(null)
    setHintLevel(0)
    setIsCorrect(false)
    setSummary(null)
    setLastError(null)
    setSecondsRemaining(null)
    setInGracePeriod(false)
    setPendingTopicConfirm(null)
    setTopicPicklist(null)
    setScratchpadHasWork(false)
    openWs(crypto.randomUUID(), topicId, difficulty, token, sessionType)
  }, [openWs])

  const sendText = useCallback((text: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'student_text', text }))
    setMessages(prev => [...prev, { role: 'student', content: text, timestamp: Date.now() }])
    setState(prev => prev === 'discovering' ? 'discovering' : 'thinking')
  }, [])

  const submitAnswer = useCallback((answer: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'answer_submit', answer }))
    setMessages(prev => [
      ...prev,
      { role: 'student', content: `Submitted answer: ${answer}`, timestamp: Date.now() },
    ])
    setState('thinking')
  }, [])

  const requestHint = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'hint_request' }))
  }, [])

  const endSession = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'session_end' }))
  }, [])

  const disconnect = useCallback(() => {
    reconnectCountRef.current = MAX_RECONNECT_ATTEMPTS
    connectParamsRef.current = null
    stopCountdown()
    wsRef.current?.close(1000)
    setState('idle')
  }, [stopCountdown])

  const acceptTopic = useCallback((topicId: string, mode: string) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'topic_accept', topic_id: topicId, mode }))
    setPendingTopicConfirm(null)
    setTopicPicklist(null)
    setState('connecting') // wait for session_ready
  }, [])

  const rejectTopic = useCallback(() => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ type: 'topic_reject' }))
    setPendingTopicConfirm(null)
    setTopicPicklist(null)
  }, [])

  useEffect(() => {
    return () => {
      stopCountdown()
      wsRef.current?.close(1000)
    }
  }, [stopCountdown])

  return {
    state, problem, messages, hintLevel, maxHints, secondsRemaining, inGracePeriod,
    isCorrect, summary, lastError, pendingTopicConfirm, topicPicklist,
    connect, sendText, submitAnswer, requestHint, endSession, disconnect,
    acceptTopic, rejectTopic, scratchpadHasWork, setScratchpadHasWork,
  }
}
