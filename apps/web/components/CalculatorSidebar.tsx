'use client'

import { useEffect, useRef } from 'react'
import { Calculator, X } from '@phosphor-icons/react'
import { CalculatorWidget, CalculatorWidgetProps } from './CalculatorWidget'

interface CalculatorSidebarProps extends CalculatorWidgetProps {
  open: boolean
  onClose: () => void
}

// Tooltip for the disabled toggle button
export function CalculatorToggleButton({
  calcMode,
  open,
  onToggle,
}: {
  calcMode: string
  open: boolean
  onToggle: () => void
}) {
  const disabled = calcMode === 'none'
  const label = open ? 'Close Calculator' : 'Calculator'

  if (disabled) {
    return (
      <div style={{ position: 'relative', display: 'inline-block' }}>
        <button
          type="button"
          disabled
          title="Calculator not available for this topic"
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '6px 14px', borderRadius: 8,
            border: '1px solid var(--border)',
            background: 'var(--surface2)', color: 'var(--text-muted)',
            fontSize: 13, fontWeight: 500,
            cursor: 'not-allowed', opacity: 0.55,
          }}
        >
          <Calculator size={14} /> Calculator
        </button>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={onToggle}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 6,
        padding: '6px 14px', borderRadius: 8,
        border: '1px solid var(--border)',
        background: open ? 'var(--caramel-dim)' : 'var(--surface2)',
        color: open ? 'var(--caramel)' : 'var(--text)',
        fontSize: 13, fontWeight: open ? 700 : 500,
        cursor: 'pointer',
        transition: 'all 0.15s',
      }}
    >
      <Calculator size={14} /> {label}
    </button>
  )
}

// Desktop collapsible sidebar — rendered as a third column
export function CalculatorSidebar({
  open,
  onClose,
  ...widgetProps
}: CalculatorSidebarProps) {
  if (!open) return null

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 0,
        width: 320,
        minWidth: 260,
        maxWidth: 360,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 14,
        overflow: 'hidden',
        animation: 'viewIn 0.25s cubic-bezier(0.16,1,0.3,1) both',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--surface2)',
      }}>
        <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>
          <Calculator size={14} /> Calculator
        </span>
        <button
          type="button"
          onClick={onClose}
          style={{
            background: 'none', border: 'none',
            color: 'var(--text-muted)', display: 'flex',
            cursor: 'pointer', padding: '2px 4px',
            borderRadius: 6,
          }}
          title="Close calculator"
        >
          <X size={16} />
        </button>
      </div>

      {/* Widget body */}
      <div style={{ padding: 16, overflowY: 'auto', flex: 1 }}>
        <CalculatorWidget {...widgetProps} />
      </div>
    </div>
  )
}

// Mobile bottom sheet
export function CalculatorBottomSheet({
  open,
  onClose,
  ...widgetProps
}: CalculatorSidebarProps) {
  const sheetRef = useRef<HTMLDivElement>(null)

  // Close on backdrop click
  useEffect(() => {
    if (!open) return
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, zIndex: 40,
          background: 'rgba(0,0,0,0.35)',
          animation: 'fadeIn 0.2s ease',
        }}
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        style={{
          position: 'fixed', bottom: 0, left: 0, right: 0, zIndex: 50,
          background: 'var(--surface)',
          borderRadius: '18px 18px 0 0',
          boxShadow: '0 -8px 40px rgba(0,0,0,0.18)',
          maxHeight: '70vh',
          display: 'flex', flexDirection: 'column',
          animation: 'slideUp 0.3s cubic-bezier(0.16,1,0.3,1) both',
        }}
      >
        {/* Drag handle */}
        <div style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 4px' }}>
          <div style={{ width: 36, height: 4, borderRadius: 2, background: 'var(--border2)' }} />
        </div>

        {/* Header */}
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '4px 20px 12px',
          borderBottom: '1px solid var(--border)',
        }}>
          <span style={{ fontWeight: 700, fontSize: 14, color: 'var(--text)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Calculator size={14} /> Calculator
          </span>
          <button
            type="button"
            onClick={onClose}
            style={{
              background: 'none', border: 'none',
              color: 'var(--text-muted)', display: 'flex',
              cursor: 'pointer', padding: 2,
            }}
          >
            <X size={20} />
          </button>
        </div>

        {/* Scrollable body */}
        <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
          <CalculatorWidget {...widgetProps} />
        </div>
      </div>

      <style>{`
        @keyframes slideUp {
          from { transform: translateY(100%); }
          to   { transform: translateY(0); }
        }
      `}</style>
    </>
  )
}

// Responsive wrapper — sidebar on lg+, bottom sheet on mobile
export function ResponsiveCalculator(props: CalculatorSidebarProps) {
  return (
    <>
      {/* Desktop sidebar (lg and above) */}
      <div className="hidden lg:block">
        <CalculatorSidebar {...props} />
      </div>

      {/* Mobile bottom sheet (below lg) */}
      <div className="block lg:hidden">
        <CalculatorBottomSheet {...props} />
      </div>
    </>
  )
}
