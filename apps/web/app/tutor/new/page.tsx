'use client'

/**
 * /tutor/new — Pre-session intake form
 *
 * Collects: class, unit(s), topic(s), reason, notes, session length.
 * Pre-fills from ?topic=<id> and ?name=<name> query params (from practice page or sidebar).
 * Submits to POST /tutor/session/create → redirects to /tutor/session/:sessionId.
 */

import React, { useCallback, useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'

// ── Types ─────────────────────────────────────────────────────────────────────

interface TopicItem  { id: string; name: string }
interface UnitItem   { id: string; name: string; is_honors: boolean; topics: TopicItem[] }
interface CourseItem { id: string; name: string; units: UnitItem[] }

// ── Constants ─────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

const WHY_OPTIONS = [
  { value: 'learn_concept',      label: 'Learn a Concept',     desc: 'I want to understand something new' },
  { value: 'homework',           label: 'Homework Help',        desc: "I'm stuck on an assignment" },
  { value: 'test_prep',          label: 'Test / Exam Prep',     desc: 'I have a test coming up' },
  { value: 'grade_improvement',  label: 'Grade Improvement',    desc: 'I want to catch up or recover my grade' },
  { value: 'get_ahead',          label: 'Get Ahead',            desc: 'I want to preview upcoming material' },
  { value: 'other',              label: 'Other',                desc: '' },
]

// ── Helpers ───────────────────────────────────────────────────────────────────

function toggle<T>(arr: T[], value: T): T[] {
  return arr.includes(value) ? arr.filter(v => v !== value) : [...arr, value]
}

// ── Sub-components ────────────────────────────────────────────────────────────

function FieldLabel({ children, optional }: { children: React.ReactNode; optional?: boolean }) {
  return (
    <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 8 }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>{children}</span>
      {optional && (
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 400 }}>optional</span>
      )}
    </div>
  )
}

function Section({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', marginBottom: 24, ...style }}>
      {children}
    </div>
  )
}

function MultiCheckbox({
  items,
  selected,
  onChange,
  showAll = false,
}: {
  items: { id: string; name: string; honors?: boolean }[]
  selected: string[]
  onChange: (ids: string[]) => void
  showAll?: boolean
}) {
  const allSelected = selected.includes('__all__')

  function handleAll() {
    onChange(allSelected ? [] : ['__all__'])
  }

  function handleItem(id: string) {
    const next = selected.filter(s => s !== '__all__')
    onChange(toggle(next, id))
  }

  return (
    <div style={{
      border: '1px solid var(--border)',
      borderRadius: 8,
      maxHeight: 200,
      overflowY: 'auto',
      background: 'var(--surface)',
    }}>
      {showAll && (
        <label style={checkboxRowStyle(allSelected)}>
          <input
            type="checkbox"
            checked={allSelected}
            onChange={handleAll}
            style={{ accentColor: 'var(--caramel)', flexShrink: 0 }}
          />
          <span style={{ fontWeight: 600, color: 'var(--caramel)' }}>All</span>
        </label>
      )}
      {items.map((item, i) => {
        const isChecked = allSelected || selected.includes(item.id)
        return (
          <label
            key={item.id}
            style={{
              ...checkboxRowStyle(isChecked),
              borderTop: i === 0 && showAll ? '1px solid var(--border)' : undefined,
            }}
          >
            <input
              type="checkbox"
              checked={isChecked}
              onChange={() => handleItem(item.id)}
              style={{ accentColor: 'var(--caramel)', flexShrink: 0 }}
            />
            <span style={{ color: item.honors ? 'var(--caramel)' : 'var(--text)' }}>
              {item.name}
              {item.honors && (
                <span style={{ fontSize: 10, marginLeft: 5, opacity: 0.6 }}>H</span>
              )}
            </span>
          </label>
        )
      })}
    </div>
  )
}

function checkboxRowStyle(active: boolean): React.CSSProperties {
  return {
    display: 'flex', alignItems: 'center', gap: 10,
    padding: '8px 12px', cursor: 'pointer',
    background: active ? 'var(--caramel-dim)' : 'transparent',
    transition: 'background 0.12s',
    fontSize: 13,
    userSelect: 'none',
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function TutorNewPage() {
  const router        = useRouter()
  const searchParams  = useSearchParams()
  const { getToken }  = useAuth()

  // ── Data state ──────────────────────────────────────────────────────────
  const [taxonomy, setTaxonomy] = useState<CourseItem[]>([])
  const [loading,  setLoading]  = useState(true)

  // ── Form state ──────────────────────────────────────────────────────────
  const [classId,      setClassId]      = useState<string>('')
  const [unitIds,      setUnitIds]      = useState<string[]>([])
  const [topicIds,     setTopicIds]     = useState<string[]>([])
  const [why,          setWhy]          = useState<string>('')
  const [notes,        setNotes]        = useState('')
  const [freeformDesc, setFreeformDesc] = useState('')
  const [sessionType,  setSessionType]  = useState<'1hr' | '2hr'>('1hr')

  // ── Submission state ─────────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false)
  const [error,      setError]      = useState<string | null>(null)

  // ── Derived ──────────────────────────────────────────────────────────────
  const isOther       = classId === 'other'
  const selectedCourse = taxonomy.find(c => c.id === classId)
  const allUnits       = selectedCourse?.units ?? []

  // Units available for topic selection
  const relevantUnits = unitIds.includes('__all__')
    ? allUnits
    : allUnits.filter(u => unitIds.includes(u.id))

  const allTopics = relevantUnits.flatMap(u => u.topics)

  // ── Load taxonomy ─────────────────────────────────────────────────────────
  useEffect(() => {
    fetch(`${API_BASE}/tutor/taxonomy`)
      .then(r => r.ok ? r.json() : Promise.reject(r.statusText))
      .then((data: CourseItem[]) => {
        setTaxonomy(data)
        // Pre-fill from ?topic=<id>
        const prefillTopicId = searchParams.get('topic')
        if (prefillTopicId) {
          for (const course of data) {
            for (const unit of course.units) {
              const found = unit.topics.find(t => t.id === prefillTopicId)
              if (found) {
                setClassId(course.id)
                setUnitIds([unit.id])
                setTopicIds([prefillTopicId])
                break
              }
            }
          }
        }
      })
      .catch(() => { /* show form anyway; taxonomy load is best-effort */ })
      .finally(() => setLoading(false))
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Cascading resets are handled inline in the onChange handlers below.
  // Do NOT use effects for this — effects fire after render and would
  // overwrite the pre-fill state set by the taxonomy useEffect.

  // ── Submit ────────────────────────────────────────────────────────────────
  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    if (!classId) { setError('Please select a class.'); return }
    setError(null)
    setSubmitting(true)

    try {
      const token = await getToken()
      if (!token) throw new Error('Not signed in. Please refresh and try again.')

      // Resolve effective topic IDs
      const effectiveTopicIds = topicIds.includes('__all__')
        ? allTopics.map(t => t.id)
        : topicIds

      // Resolve effective unit names
      const effectiveUnitIds = unitIds.includes('__all__')
        ? allUnits.map(u => u.id)
        : unitIds
      const effectiveUnitNames = allUnits
        .filter(u => effectiveUnitIds.includes(u.id))
        .map(u => u.name)

      const body = {
        class_name: isOther ? 'Other' : (selectedCourse?.name ?? classId),
        unit_names: effectiveUnitNames,
        topic_ids: isOther ? [] : effectiveTopicIds,
        freeform_topics: isOther && freeformDesc ? [freeformDesc] : [],
        why: why || undefined,
        notes: [notes, isOther ? freeformDesc : ''].filter(Boolean).join('\n\n').trim(),
        session_type: sessionType,
      }

      const res = await fetch(`${API_BASE}/tutor/session/create`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error((data as { detail?: string }).detail ?? `Error ${res.status}`)
      }

      const { session_id } = await res.json() as { session_id: string }
      router.push(`/tutor/session/${session_id}`)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
      setSubmitting(false)
    }
  }, [
    classId, unitIds, topicIds, why, notes, freeformDesc,
    sessionType, isOther, selectedCourse, allUnits, allTopics,
    getToken, router,
  ])

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      color: 'var(--text)',
      fontFamily: 'system-ui',
    }}>
      <div style={{
        maxWidth: 620,
        margin: '0 auto',
        padding: '48px 24px 80px',
      }}>
        {/* Header */}
        <div style={{ marginBottom: 36 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
            <div style={{
              width: 36, height: 36, borderRadius: 8,
              background: 'var(--caramel)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 18, flexShrink: 0,
            }}>
              ✦
            </div>
            <h1 style={{
              fontSize: 22, fontWeight: 700, margin: 0,
              fontFamily: 'var(--font-fraunces), Georgia, serif',
              letterSpacing: '-0.02em',
            }}>
              Book a Tutoring Session
            </h1>
          </div>
          <p style={{ fontSize: 14, color: 'var(--text-dim)', lineHeight: 1.6, margin: 0 }}>
            Tell your tutor what you're working on and they'll meet you right there.
          </p>
        </div>

        {loading ? (
          <div style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', paddingTop: 40 }}>
            Loading courses…
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column' }}>

            {/* ── Class ─────────────────────────────────────────────────── */}
            <Section>
              <FieldLabel>Class</FieldLabel>
              <select
                value={classId}
                onChange={e => { setClassId(e.target.value); setUnitIds([]); setTopicIds([]) }}
                required
                style={selectStyle}
              >
                <option value="">— Select a class —</option>
                {taxonomy.map(course => (
                  <option key={course.id} value={course.id}>{course.name}</option>
                ))}
                <option value="other">Other / Out of curriculum</option>
              </select>
            </Section>

            {/* ── Freeform (Other) ──────────────────────────────────────── */}
            {isOther && (
              <Section>
                <FieldLabel>What do you need help with?</FieldLabel>
                <textarea
                  value={freeformDesc}
                  onChange={e => setFreeformDesc(e.target.value)}
                  placeholder="Describe the topic or paste your problem here…"
                  rows={4}
                  style={textareaStyle}
                />
              </Section>
            )}

            {/* ── Units ────────────────────────────────────────────────── */}
            {!isOther && classId && allUnits.length > 0 && (
              <Section>
                <FieldLabel optional>Units</FieldLabel>
                <MultiCheckbox
                  items={allUnits.map(u => ({ id: u.id, name: u.name, honors: u.is_honors }))}
                  selected={unitIds}
                  onChange={ids => { setUnitIds(ids); setTopicIds([]) }}
                  showAll
                />
              </Section>
            )}

            {/* ── Topics ───────────────────────────────────────────────── */}
            {!isOther && unitIds.length > 0 && allTopics.length > 0 && (
              <Section>
                <FieldLabel optional>Topics</FieldLabel>
                <MultiCheckbox
                  items={allTopics.map(t => ({ id: t.id, name: t.name }))}
                  selected={topicIds}
                  onChange={setTopicIds}
                  showAll
                />
              </Section>
            )}

            {/* ── Why ──────────────────────────────────────────────────── */}
            <Section>
              <FieldLabel optional>Why are you coming in?</FieldLabel>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {WHY_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setWhy(why === opt.value ? '' : opt.value)}
                    title={opt.desc}
                    style={{
                      padding: '7px 14px',
                      borderRadius: 20,
                      fontSize: 12, fontWeight: 500,
                      cursor: 'pointer',
                      border: `1px solid ${why === opt.value ? 'var(--caramel)' : 'var(--border)'}`,
                      background: why === opt.value ? 'var(--caramel-dim)' : 'transparent',
                      color: why === opt.value ? 'var(--caramel)' : 'var(--text-dim)',
                      transition: 'all 0.15s',
                    }}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </Section>

            {/* ── Notes ────────────────────────────────────────────────── */}
            <Section>
              <FieldLabel optional>Notes for your tutor</FieldLabel>
              <textarea
                value={notes}
                onChange={e => setNotes(e.target.value)}
                placeholder={'e.g. "I have my final on Friday — please focus on integration by parts and sequences."'}
                rows={3}
                maxLength={2000}
                style={textareaStyle}
              />
              {notes.length > 1600 && (
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4, textAlign: 'right' }}>
                  {notes.length}/2000
                </div>
              )}
            </Section>

            {/* ── File upload placeholder ───────────────────────────────── */}
            <Section style={{ marginBottom: 28 }}>
              <FieldLabel optional>Upload problem set or photo</FieldLabel>
              <div style={{
                border: '1px dashed var(--border)',
                borderRadius: 8,
                padding: '20px 16px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 12,
                background: 'var(--surface)',
              }}>
                📎 File upload coming in Phase 3
              </div>
            </Section>

            {/* ── Session length ────────────────────────────────────────── */}
            <Section>
              <FieldLabel>Session length</FieldLabel>
              <div style={{ display: 'flex', gap: 10 }}>
                {(['1hr', '2hr'] as const).map(type => (
                  <button
                    key={type}
                    type="button"
                    onClick={() => setSessionType(type)}
                    style={{
                      flex: 1, padding: '10px 16px',
                      borderRadius: 8, cursor: 'pointer',
                      border: `1px solid ${sessionType === type ? 'var(--caramel)' : 'var(--border)'}`,
                      background: sessionType === type ? 'var(--caramel-dim)' : 'transparent',
                      color: sessionType === type ? 'var(--caramel)' : 'var(--text-dim)',
                      fontSize: 13, fontWeight: sessionType === type ? 600 : 400,
                      transition: 'all 0.15s',
                    }}
                  >
                    {type === '1hr' ? '1 hour' : '2 hours'}
                  </button>
                ))}
              </div>
            </Section>

            {/* ── Error ─────────────────────────────────────────────────── */}
            {error && (
              <div style={{
                padding: '12px 16px', borderRadius: 8, marginBottom: 16,
                background: 'rgba(220,38,38,0.08)', border: '1px solid rgba(220,38,38,0.25)',
                fontSize: 13, color: '#ef4444',
              }}>
                {error}
              </div>
            )}

            {/* ── Submit ────────────────────────────────────────────────── */}
            <button
              type="submit"
              disabled={submitting || !classId}
              className="btn-caramel"
              style={{
                width: '100%', padding: '13px 20px',
                fontSize: 14, fontWeight: 600,
                justifyContent: 'center',
                opacity: submitting || !classId ? 0.55 : 1,
                cursor: submitting || !classId ? 'not-allowed' : 'pointer',
              }}
            >
              {submitting ? 'Creating session…' : 'Start Session →'}
            </button>

          </form>
        )}
      </div>
    </div>
  )
}

// ── Shared styles ─────────────────────────────────────────────────────────────

const selectStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  background: 'var(--surface)',
  color: 'var(--text)',
  fontSize: 13,
  appearance: 'auto',
  cursor: 'pointer',
}

const textareaStyle: React.CSSProperties = {
  width: '100%',
  padding: '10px 12px',
  borderRadius: 8,
  border: '1px solid var(--border)',
  background: 'var(--surface)',
  color: 'var(--text)',
  fontSize: 13,
  lineHeight: 1.6,
  resize: 'vertical',
  fontFamily: 'inherit',
  boxSizing: 'border-box',
}
