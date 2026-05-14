'use client'

import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Mathematics from '@tiptap/extension-mathematics'
import { Extension, InputRule } from '@tiptap/core'
import { useState, useCallback } from 'react'
import { useAuth } from '@clerk/nextjs'

// Fires when the user closes $...$ — converts to an inlineMath node
const SingleDollarMath = Extension.create({
  name: 'singleDollarMathInput',
  addInputRules() {
    return [
      new InputRule({
        find: /(?<!\$)\$([^$\n]+?)\$(?!\$)/,
        handler: ({ state, range, match }) => {
          const latex = match[1]?.trim()
          if (!latex) return null
          const inlineMathType = state.schema.nodes.inlineMath
          if (!inlineMathType) return null
          state.tr.replaceWith(range.from, range.to, inlineMathType.create({ latex }))
        },
      }),
    ]
  },
})

interface MathScratchpadProps {
  onChange?: (hasContent: boolean) => void
  disabled?: boolean
}

/**
 * Parse a $...$-delimited string into a Tiptap JSON document.
 * Math spans become mathInline nodes; prose stays as text nodes.
 */
function buildTiptapDoc(text: string): object {
  const lines = text.split('\n')
  const paragraphs = lines.map(line => {
    const trimmed = line.trim()
    const content: unknown[] = []
    const pattern = /\$([^$\n]+)\$/g
    let lastIndex = 0
    let match: RegExpExecArray | null

    while ((match = pattern.exec(trimmed)) !== null) {
      if (match.index > lastIndex) {
        content.push({ type: 'text', text: trimmed.slice(lastIndex, match.index) })
      }
      content.push({
        type: 'inlineMath',
        attrs: { latex: match[1] },
      })
      lastIndex = match.index + match[0].length
    }
    if (lastIndex < trimmed.length) {
      content.push({ type: 'text', text: trimmed.slice(lastIndex) })
    }

    return {
      type: 'paragraph',
      content: content.length > 0 ? content : [{ type: 'text', text: '' }],
    }
  })

  return { type: 'doc', content: paragraphs }
}

export function MathScratchpad({ onChange, disabled = false }: MathScratchpadProps) {
  const { getToken } = useAuth()
  const [converting, setConverting] = useState(false)
  const [convertError, setConvertError] = useState<string | null>(null)
  const apiBase = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

  const editor = useEditor({
    extensions: [StarterKit, Mathematics, SingleDollarMath],
    onUpdate: ({ editor }) => {
      onChange?.(editor.getText().trim().length > 0)
    },
    editable: !disabled,
    editorProps: {
      attributes: { class: 'math-scratchpad-content', spellcheck: 'false' },
    },
  })

  const handleConvert = useCallback(async () => {
    if (!editor) return
    // getText returns math node content without $, which Claude handles fine
    const rawText = editor.getText({ blockSeparator: '\n' })
    if (!rawText.trim()) return

    setConverting(true)
    setConvertError(null)
    try {
      const token = await getToken()
      const resp = await fetch(`${apiBase}/tutor/convert`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ text: rawText }),
      })
      if (!resp.ok) throw new Error()
      const { converted } = await resp.json() as { converted: string }
      // Build proper Tiptap JSON with mathInline nodes so the extension renders them
      editor.commands.setContent(buildTiptapDoc(converted))
      onChange?.(true)
    } catch {
      setConvertError('Conversion failed — try again')
      setTimeout(() => setConvertError(null), 3000)
    } finally {
      setConverting(false)
    }
  }, [editor, apiBase, getToken, onChange])

  const isEmpty = !editor?.getText().trim()

  return (
    <div>
      <div
        className="math-scratchpad-wrapper"
        onClick={() => editor?.commands.focus()}
      >
        {isEmpty && (
          <div className="math-scratchpad-placeholder">
            Write your reasoning… type $…$ around math, or hit AI → LaTeX
          </div>
        )}
        <EditorContent editor={editor} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 6 }}>
        <button
          onClick={handleConvert}
          disabled={converting || isEmpty || disabled}
          style={{
            fontSize: 12, padding: '5px 12px', borderRadius: 8,
            border: '1px solid rgba(196,151,106,0.4)',
            background: 'var(--caramel-dim)',
            color: (converting || isEmpty) ? 'var(--text-muted)' : 'var(--caramel)',
            cursor: (converting || isEmpty || disabled) ? 'default' : 'pointer',
            fontWeight: 500,
            opacity: (converting || isEmpty) ? 0.55 : 1,
            display: 'flex', alignItems: 'center', gap: 4,
          }}
        >
          {converting ? 'Converting…' : '✦ AI → LaTeX'}
        </button>
        {convertError ? (
          <span style={{ fontSize: 11, color: 'var(--terracotta)' }}>{convertError}</span>
        ) : (
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            or type $…$ around math to render it
          </span>
        )}
      </div>
    </div>
  )
}
