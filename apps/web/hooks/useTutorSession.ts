'use client'

import { useCallback, useEffect, useRef, useState } from 'react'

// ── Types ─────────────────────────────────────────────────────────────────────

export type SessionType = '1hr' | '2hr'

export type TutorSessionState =
  | 'idle'
  | 'connecting'
  | 'loading'      // building problem queue
  | 'discovering'  // legacy open-ended topic detection
  | 'ready'
  | 'thinking'
  | 'in_lesson'    // tutor is narrating a lesson
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
  topics_covered?: string[]
  per_topic_performance?: Record<string, string>
  practice_problems?: string[]
  problems_solved?: number
  queue_total?: number
}

export interface TopicOption {
  topic_id: string
  topic_name: string
  course_name: string
}

export interface WhiteboardWsMessage {
  type: 'whiteboard' | 'wb_write' | 'wb_clear' | 'wb_new_section' | 'wb_zoom' | 'wb_annotate_student'
  action?: 'write' | 'plot' | 'clear'
  latex?: string
  label?: string
  fn?: string
  domain?: [number, number]
  region?: string
  snapshot?: boolean
  x?: number
  y?: number
  // wb_annotate_student fields
  x_hint?: 'left' | 'center' | 'right'
  color?: 'correction' | 'confirmation' | 'neutral'
}

export interface RagMatch {
  statement_latex: string
  similarity: number
  session_id: string
  problem_number: number
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
  // Progress
  currentIndex: number
  totalProblems: number
  // Discovery (legacy)
  pendingTopicConfirm: { topic_id: string; topic_name: string; mode: string; message: string } | null
  topicPicklist: TopicOption[] | null
  // Exam mode
  examModeProposed: boolean
  examModeActive: boolean
  // Whiteboard
  whiteboardMessages: WhiteboardWsMessage[]
  // RAG
  ragMatch: RagMatch | null
  // Student work
  defaultInputMode: string   // "latex" | "drawing" | "mixed"
  // Actions
  /** Phase 4: connect to a pre-created session by session_id */
  connectToSession: (sessionId: string, token: string) => void
  /** Legacy: connect by generating a new random session_id */
  connect: (topicId: string | null, difficulty: number, token: string, sessionType: SessionType, tutorName?: string) => void
  sendText: (text: string) => void
  submitAnswer: (answer: string) => void
  requestHint: () => void
  walkMeThrough: () => void
  goingTooFast: () => void
  nextProblem: () => void
  acceptExamMode: () => void
  endSession: () => void
  disconnect: () => void
  // Legacy discovery
  acceptTopic: (topicId: string, mode: string) => void
  rejectTopic: () => void
  // Scratchpad
  scratchpadHasWork: boolean
  setScratchpadHasWork: (v: boolean) => void
  // Drawing recognition + drops
  sendCanvasSnapshot: (imageB64: string, source?: 'whiteboard' | 'scratchpad') => void
  sendImageDrop: (imageB64: string, mediaType: string) => void
  sendRagSearch: () => void
  sendStudentWork: (stepsLatex: string) => void
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
    tutorName?: string
    // Phase 4: pre-created session
    preSessionId?: string
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
  const [currentIndex, setCurrentIndex] = useState(0)
  const [totalProblems, setTotalProblems] = useState(0)
  const [pendingTopicConfirm, setPendingTopicConfirm] = useState<{
    topic_id: string; topic_name: string; mode: string; message: string
  } | null>(null)
  const [topicPicklist, setTopicPicklist] = useState<TopicOption[] | null>(null)
  const [examModeProposed, setExamModeProposed] = useState(false)
  const [examModeActive, setExamModeActive] = useState(false)
  const [scratchpadHasWork, setScratchpadHasWork] = useState(false)
  const [whiteboardMessages, setWhiteboardMessages] = useState<WhiteboardWsMessage[]>([])
  const [ragMatch, setRagMatch] = useState<RagMatch | null>(null)
  const [defaultInputMode, setDefaultInputMode] = useState('latex')

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

    // ── Loading ─────────────────────────────────────────────────────────────
    if (type === 'session_loading') {
      setState('loading')
    }

    // ── Session ready ────────────────────────────────────────────────────────
    else if (type === 'session_ready') {
      setPendingTopicConfirm(null)
      setTopicPicklist(null)
      const p = msg.problem as TutorProblem | null
      if (p) {
        setProblem(p)
        setMaxHints(p.hint_ladder_length)
      }
      if (msg.default_input_mode) setDefaultInputMode(msg.default_input_mode as string)
      setState('ready')
      const maxDur = (msg.max_duration_seconds as number) ?? 3600
      const graceDur = (msg.grace_period_seconds as number) ?? GRACE_PERIOD_SECONDS
      startCountdown(maxDur, graceDur)
      setCurrentIndex((msg.index as number) ?? 0)
      setTotalProblems((msg.total as number) ?? 1)

      // Legacy: narrate worked_example steps
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

      const dq = msg.diagnostic_question as string | undefined
      if (dq) {
        setMessages(prev => [
          ...prev,
          { role: 'tutor', content: dq, timestamp: Date.now() },
        ])
      }
    }

    // ── Next problem (queue advance) ─────────────────────────────────────────
    else if (type === 'next_problem') {
      const p = msg.problem as TutorProblem
      setProblem(p)
      setMaxHints(p.hint_ladder_length)
      setHintLevel(0)
      setIsCorrect(false)
      setState('ready')
      setCurrentIndex((msg.index as number) ?? 0)
      setTotalProblems((msg.total as number) ?? 1)
    }

    // ── Queue complete ───────────────────────────────────────────────────────
    else if (type === 'queue_complete') {
      setMessages(prev => [
        ...prev,
        { role: 'system', content: msg.message as string, timestamp: Date.now() },
      ])
    }

    // ── Agent text ───────────────────────────────────────────────────────────
    else if (type === 'agent_text') {
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.text as string, timestamp: Date.now() },
      ])
      setState(prev => prev === 'in_lesson' ? 'in_lesson' : 'ready')
    }

    // ── Lesson mode ──────────────────────────────────────────────────────────
    else if (type === 'lesson_start') {
      setState('in_lesson')
      setMessages(prev => [
        ...prev,
        { role: 'system', content: '— Lesson mode —', timestamp: Date.now() },
      ])
    }
    else if (type === 'lesson_end') {
      setState('ready')
    }

    // ── Answer result ────────────────────────────────────────────────────────
    else if (type === 'answer_result') {
      if (msg.correct as boolean) {
        setIsCorrect(true)
        setState('solved')
        stopCountdown()
      } else {
        setState('ready')
      }
    }

    // ── Hint ─────────────────────────────────────────────────────────────────
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

    // ── Exam mode ────────────────────────────────────────────────────────────
    else if (type === 'exam_mode_propose') {
      setExamModeProposed(true)
      setMessages(prev => [
        ...prev,
        { role: 'tutor', content: msg.message as string, timestamp: Date.now() },
      ])
    }
    else if (type === 'exam_mode_active') {
      setExamModeProposed(false)
      setExamModeActive(true)
      setMessages(prev => [
        ...prev,
        { role: 'system', content: '— Exam mode active —', timestamp: Date.now() },
      ])
    }

    // ── Whiteboard ───────────────────────────────────────────────────────────
    else if (type === 'whiteboard' || type === 'wb_write' || type === 'wb_clear'
             || type === 'wb_new_section' || type === 'wb_zoom'
             || type === 'wb_annotate_student') {
      setWhiteboardMessages(prev => [...prev, msg as unknown as WhiteboardWsMessage])
    }

    // ── RAG match ────────────────────────────────────────────────────────────
    else if (type === 'rag_match') {
      const match = (msg as any).match
      if (match) {
        setRagMatch({
          statement_latex: match.statement_latex ?? '',
          similarity: match.similarity ?? 0,
          session_id: match.session_id ?? '',
          problem_number: match.problem_number ?? 1,
        })
      }
    }

    // ── Time warning ─────────────────────────────────────────────────────────
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

    // ── Session end ──────────────────────────────────────────────────────────
    else if (type === 'session_end' || type === 'session_timeout') {
      stopCountdown()
      setSummary(msg.summary as SessionSummary)
      setState(type === 'session_timeout' ? 'timeout' : 'ended')
    }

    // ── Discovery (legacy) ───────────────────────────────────────────────────
    else if (type === 'discovery_start') {
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

    // ── Error ────────────────────────────────────────────────────────────────
    else if (type === 'error') {
      setLastError(msg.message as string)
    }
  }, [startCountdown, stopCountdown])

  // ── WS open ─────────────────────────────────────────────────────────────────

  const openWs = useCallback((url: string) => {
    const ws = new WebSocket(url)
    wsRef.current = ws
    ws.onmessage = (event) => handleMessage(event.data as string)

    ws.onclose = (event) => {
      const params = connectParamsRef.current
      const shouldReconnect =
        !NO_RECONNECT_CODES.has(event.code) &&
        reconnectCountRef.current < MAX_RECONNECT_ATTEMPTS &&
        params !== null

      if (shouldReconnect) {
        reconnectCountRef.current++
        const delay = 1000 * Math.pow(2, reconnectCountRef.current - 1)
        setTimeout(() => {
          if (!connectParamsRef.current) return
          const p = connectParamsRef.current
          if (p.preSessionId) {
            // Phase 4: reconnect to known session
            openWs(`${API_WS_BASE}/ws/tutor/${p.preSessionId}?token=${encodeURIComponent(p.token)}`)
          } else {
            openWs(
              `${API_WS_BASE}/ws/tutor/${crypto.randomUUID()}` +
              `?token=${encodeURIComponent(p.token)}` +
              `&difficulty=${p.difficulty}` +
              `&session_type=${p.sessionType}` +
              (p.topicId ? `&topic_id=${encodeURIComponent(p.topicId)}` : '') +
              (p.tutorName ? `&tutor_name=${encodeURIComponent(p.tutorName)}` : '')
            )
          }
        }, delay)
      } else {
        const s = wsRef.current ? 'idle' : state
        if (s !== 'solved' && s !== 'ended' && s !== 'timeout') {
          setState(NO_RECONNECT_CODES.has(event.code) ? 'error' : 'ended')
        }
        stopCountdown()
      }
    }

    ws.onerror = () => setLastError('Connection error. Retrying…')
  }, [handleMessage, state, stopCountdown]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Reset state ──────────────────────────────────────────────────────────────

  const resetState = useCallback(() => {
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
    setWhiteboardMessages([])
    setDefaultInputMode('latex')
    setExamModeProposed(false)
    setExamModeActive(false)
    setCurrentIndex(0)
    setTotalProblems(0)
  }, [])

  // ── Public API ──────────────────────────────────────────────────────────────

  /** Phase 4: connect to a pre-created session (session_id from /tutor/session/create). */
  const connectToSession = useCallback((sessionId: string, token: string) => {
    reconnectCountRef.current = 0
    connectParamsRef.current = {
      topicId: null, difficulty: 3, token,
      sessionType: '1hr', preSessionId: sessionId,
    }
    setState('connecting')
    resetState()
    openWs(`${API_WS_BASE}/ws/tutor/${sessionId}?token=${encodeURIComponent(token)}`)
  }, [openWs, resetState])

  /** Legacy: connect without a pre-created session. */
  const connect = useCallback((
    topicId: string | null,
    difficulty: number,
    token: string,
    sessionType: SessionType,
    tutorName?: string,
  ) => {
    reconnectCountRef.current = 0
    connectParamsRef.current = { topicId, difficulty, token, sessionType, tutorName }
    setState('connecting')
    resetState()
    const url =
      `${API_WS_BASE}/ws/tutor/${crypto.randomUUID()}` +
      `?token=${encodeURIComponent(token)}` +
      `&difficulty=${difficulty}` +
      `&session_type=${sessionType}` +
      (topicId ? `&topic_id=${encodeURIComponent(topicId)}` : '') +
      (tutorName ? `&tutor_name=${encodeURIComponent(tutorName)}` : '')
    openWs(url)
  }, [openWs, resetState])

  const _send = useCallback((payload: object) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify(payload))
  }, [])

  const sendText = useCallback((text: string) => {
    _send({ type: 'student_text', text })
    setMessages(prev => [...prev, { role: 'student', content: text, timestamp: Date.now() }])
    setState(prev => prev === 'discovering' ? 'discovering' : 'thinking')
  }, [_send])

  const submitAnswer = useCallback((answer: string) => {
    _send({ type: 'answer_submit', answer })
    setMessages(prev => [
      ...prev,
      { role: 'student', content: `Submitted: ${answer}`, timestamp: Date.now() },
    ])
    setState('thinking')
  }, [_send])

  const requestHint = useCallback(() => _send({ type: 'hint_request' }), [_send])
  const walkMeThrough = useCallback(() => _send({ type: 'walk_me_through' }), [_send])
  const goingTooFast = useCallback(() => _send({ type: 'going_too_fast' }), [_send])
  const nextProblem = useCallback(() => _send({ type: 'next_problem' }), [_send])
  const acceptExamMode = useCallback(() => {
    setExamModeProposed(false)
    _send({ type: 'exam_mode_accept' })
  }, [_send])
  const endSession = useCallback(() => _send({ type: 'session_end' }), [_send])

  const disconnect = useCallback(() => {
    reconnectCountRef.current = MAX_RECONNECT_ATTEMPTS
    connectParamsRef.current = null
    stopCountdown()
    wsRef.current?.close(1000)
    setState('idle')
  }, [stopCountdown])

  const acceptTopic = useCallback((topicId: string, mode: string) => {
    _send({ type: 'topic_accept', topic_id: topicId, mode })
    setPendingTopicConfirm(null)
    setTopicPicklist(null)
    setState('connecting')
  }, [_send])

  const rejectTopic = useCallback(() => {
    _send({ type: 'topic_reject' })
    setPendingTopicConfirm(null)
    setTopicPicklist(null)
  }, [_send])

  const sendCanvasSnapshot = useCallback((imageB64: string, source: 'whiteboard' | 'scratchpad' = 'whiteboard') => {
    _send({ type: 'student_canvas_snapshot', image_b64: imageB64, source })
  }, [_send])

  const sendImageDrop = useCallback((imageB64: string, mediaType: string) => {
    _send({ type: 'image_drop', image_b64: imageB64, media_type: mediaType })
  }, [_send])

  const sendRagSearch = useCallback(() => {
    _send({ type: 'rag_search' })
  }, [_send])

  const sendStudentWork = useCallback((stepsLatex: string) => {
    _send({ type: 'wb_student_work', latex: stepsLatex })
    setMessages(prev => [
      ...prev,
      { role: 'student', content: `My work: ${stepsLatex}`, timestamp: Date.now() },
    ])
    setState(prev => prev === 'in_lesson' ? 'in_lesson' : 'thinking')
  }, [_send])

  useEffect(() => {
    return () => {
      stopCountdown()
      wsRef.current?.close(1000)
    }
  }, [stopCountdown])

  return {
    state, problem, messages, hintLevel, maxHints, secondsRemaining, inGracePeriod,
    isCorrect, summary, lastError, currentIndex, totalProblems,
    pendingTopicConfirm, topicPicklist,
    examModeProposed, examModeActive,
    whiteboardMessages, ragMatch,
    connectToSession, connect, sendText, submitAnswer, requestHint,
    walkMeThrough, goingTooFast, nextProblem, acceptExamMode,
    endSession, disconnect, acceptTopic, rejectTopic,
    scratchpadHasWork, setScratchpadHasWork,
    sendCanvasSnapshot, sendImageDrop, sendRagSearch, sendStudentWork,
    defaultInputMode,
  }
}
