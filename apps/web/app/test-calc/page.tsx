'use client'

import dynamic from 'next/dynamic'

const CalculatorWidget = dynamic(
  () => import('@/components/CalculatorWidget').then(m => m.CalculatorWidget),
  { ssr: false },
)

export default function TestCalcPage() {
  return (
    <div
      data-testid="test-calc-page"
      style={{
        minHeight: '100vh',
        background: 'var(--bg, #0d1117)',
        color: 'var(--text, #e6edf3)',
        padding: '32px 16px',
      }}
    >
      <div style={{ maxWidth: 480, margin: '0 auto' }}>
        <h1 style={{ fontSize: 20, fontWeight: 700, marginBottom: 24 }}>
          Graphing Calculator — E2E Test Harness
        </h1>
        <CalculatorWidget
          calcMode="graphing"
          difficulty={5}
          userTier="pro"
          getToken={async () => null}
          onSendToAnswer={() => {}}
        />
      </div>
    </div>
  )
}
