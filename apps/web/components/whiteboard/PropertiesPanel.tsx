'use client'
import React, { useEffect, useState } from 'react'

interface Props {
  selectedObj: any | null
  canvas: any | null
  theme: 'light' | 'dark'
  onClose?: () => void
}

export function PropertiesPanel({ selectedObj, canvas, theme }: Props) {
  const d = theme === 'dark'
  const bg      = d ? '#1c2128' : '#f6f7fb'
  const border  = d ? '#30363d' : '#dce0ee'
  const text    = d ? '#e6edf3' : '#0f1623'
  const muted   = d ? '#8b949e' : '#4a5472'
  const surface = d ? '#0d1117' : '#ffffff'

  // Local mirror of obj properties so inputs stay responsive
  const [, forceRender] = useState(0)

  useEffect(() => { forceRender(n => n + 1) }, [selectedObj])

  if (!selectedObj) {
    return (
      <div style={{ width: 240, background: bg, borderLeft: `1px solid ${border}`, padding: 16, color: muted, fontSize: 12 }}>
        Select an object to edit its properties.
      </div>
    )
  }

  const set = (props: Record<string, any>) => {
    if (!canvas || !selectedObj) return
    selectedObj.set(props)
    canvas.requestRenderAll()
    forceRender(n => n + 1)
  }

  // Fabric v7 lowercases the static type (e.g. 'FabricAxes' → 'fabricaxes')
  // Normalise to lowercase for all comparisons; display name strips the 'fabric' prefix.
  const typeRaw: string = selectedObj.type ?? ''
  const type = typeRaw.toLowerCase()

  // ── Section helpers ───────────────────────────────────────────────────────

  const Label = ({ children }: { children: React.ReactNode }) => (
    <div style={{ fontSize: 10, fontWeight: 600, color: muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 4 }}>
      {children}
    </div>
  )

  const Row = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div style={{ marginBottom: 10 }}>
      <Label>{label}</Label>
      {children}
    </div>
  )

  const ColorInput = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
      <input type="color" value={value || '#4a9eff'}
        onChange={e => onChange(e.target.value)}
        style={{ width: 32, height: 24, border: 'none', padding: 0, cursor: 'pointer', background: 'transparent' }} />
      <input type="text" value={value || ''} onChange={e => onChange(e.target.value)}
        style={{ flex: 1, fontSize: 12, padding: '3px 6px', borderRadius: 4, border: `1px solid ${border}`, background: surface, color: text }} />
    </div>
  )

  const NumInput = ({ value, min, max, step = 1, onChange }: {
    value: number; min?: number; max?: number; step?: number; onChange: (v: number) => void
  }) => (
    <input type="number" value={value} min={min} max={max} step={step}
      onChange={e => onChange(Number(e.target.value))}
      style={{ width: '100%', fontSize: 12, padding: '3px 6px', borderRadius: 4, border: `1px solid ${border}`, background: surface, color: text }} />
  )

  const TextInput = ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <input type="text" value={value}
      onChange={e => onChange(e.target.value)}
      style={{ width: '100%', fontSize: 12, padding: '3px 6px', borderRadius: 4, border: `1px solid ${border}`, background: surface, color: text }} />
  )

  const Checkbox = ({ value, onChange, label }: { value: boolean; onChange: (v: boolean) => void; label: string }) => (
    <label style={{ display: 'flex', gap: 6, alignItems: 'center', cursor: 'pointer', color: text, fontSize: 12 }}>
      <input type="checkbox" checked={value} onChange={e => onChange(e.target.checked)} />
      {label}
    </label>
  )

  // ── Common properties (all objects) ───────────────────────────────────────

  const commonProps = (
    <>
      <Row label="Stroke colour">
        <ColorInput value={String(selectedObj.stroke || '#4a9eff')}
          onChange={v => set({ stroke: v })} />
      </Row>
      <Row label="Stroke width">
        <NumInput value={selectedObj.strokeWidth ?? 2} min={0.5} max={20} step={0.5}
          onChange={v => set({ strokeWidth: v })} />
      </Row>
      <Row label="Opacity">
        <input type="range" min={0} max={1} step={0.01} value={selectedObj.opacity ?? 1}
          onChange={e => set({ opacity: Number(e.target.value) })}
          style={{ width: '100%' }} />
      </Row>
    </>
  )

  const fillProp = (
    <Row label="Fill colour">
      <ColorInput value={String(selectedObj.fill || 'transparent')}
        onChange={v => set({ fill: v })} />
    </Row>
  )

  // ── Type-specific properties ───────────────────────────────────────────────

  const specific = () => {
    if (type === 'fabricregularpolygon') {
      return (
        <Row label="Sides">
          <NumInput value={selectedObj.sides ?? 6} min={3} max={20}
            onChange={v => { selectedObj.sides = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
        </Row>
      )
    }

    if (type === 'fabricanglemarker') {
      return (
        <>
          <Row label="Angle (°)">
            <NumInput value={selectedObj.angleDeg ?? 60} min={1} max={359}
              onChange={v => { selectedObj.angleDeg = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
          </Row>
          <Row label="Arc count">
            {([1,2,3] as const).map(n => (
              <label key={n} style={{ marginRight: 10, fontSize: 12, color: text, cursor: 'pointer' }}>
                <input type="radio" name="arcCount" value={n} checked={selectedObj.arcCount === n}
                  onChange={() => { selectedObj.arcCount = n; canvas.requestRenderAll(); forceRender(f=>f+1) }} />
                {' '}{n}
              </label>
            ))}
          </Row>
          <Row label="">
            <Checkbox value={selectedObj.showLabel ?? true}
              onChange={v => { selectedObj.showLabel = v; canvas.requestRenderAll(); forceRender(n=>n+1) }}
              label="Show degree label" />
          </Row>
        </>
      )
    }

    if (type === 'fabriclinesegment') {
      return (
        <Row label="Tick marks">
          {([0,1,2,3] as const).map(n => (
            <label key={n} style={{ marginRight: 10, fontSize: 12, color: text, cursor: 'pointer' }}>
              <input type="radio" name="tickCount" value={n} checked={selectedObj.tickCount === n}
                onChange={() => { selectedObj.tickCount = n; canvas.requestRenderAll(); forceRender(f=>f+1) }} />
              {' '}{n}
            </label>
          ))}
        </Row>
      )
    }

    if (type === 'fabricnumberline') {
      return (
        <>
          <Row label="Start"><NumInput value={selectedObj.numStart ?? -5} step={1} onChange={v => { selectedObj.numStart = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="End"><NumInput value={selectedObj.numEnd ?? 5} step={1} onChange={v => { selectedObj.numEnd = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Step"><NumInput value={selectedObj.step ?? 1} min={0.1} step={0.5} onChange={v => { selectedObj.step = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label=""><Checkbox value={selectedObj.showLabels ?? true} label="Show labels" onChange={v => { selectedObj.showLabels = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
        </>
      )
    }

    if (type === 'fabricbrace') {
      return (
        <Row label="Label">
          <TextInput value={selectedObj.label ?? ''} onChange={v => { selectedObj.label = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
        </Row>
      )
    }

    if (type === 'fabricdot') {
      return (
        <>
          <Row label="Label"><TextInput value={selectedObj.label ?? ''} onChange={v => { selectedObj.label = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Radius"><NumInput value={selectedObj.dotRadius ?? 6} min={2} max={30} onChange={v => { selectedObj.dotRadius = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
        </>
      )
    }

    if (type === 'fabricvenn') {
      return (
        <>
          <Row label="Circles">
            {([2,3] as const).map(n => (
              <label key={n} style={{ marginRight: 10, fontSize: 12, color: text, cursor: 'pointer' }}>
                <input type="radio" name="vennCount" value={n} checked={selectedObj.count === n}
                  onChange={() => {
                    selectedObj.count = n
                    selectedObj.vennLabels = Array.from({length: n}, (_,i) => String.fromCharCode(65+i))
                    canvas.requestRenderAll(); forceRender(f=>f+1)
                  }} />
                {' '}{n}
              </label>
            ))}
          </Row>
          {(selectedObj.vennLabels ?? ['A','B']).map((lbl: string, i: number) => (
            <Row key={i} label={`Label ${i+1}`}>
              <TextInput value={lbl} onChange={v => {
                const a = [...(selectedObj.vennLabels ?? [])]
                a[i] = v; selectedObj.vennLabels = a; canvas.requestRenderAll(); forceRender(n=>n+1)
              }} />
            </Row>
          ))}
        </>
      )
    }

    if (type === 'fabricmatrix') {
      return (
        <>
          <Row label="Rows"><NumInput value={selectedObj.rows ?? 3} min={1} max={10} onChange={v => { selectedObj.rows = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Columns"><NumInput value={selectedObj.cols ?? 3} min={1} max={10} onChange={v => { selectedObj.cols = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
        </>
      )
    }

    if (type === 'fabricarc' || type === 'fabricsector') {
      return (
        <>
          <Row label="Start angle (°)"><NumInput value={selectedObj.startAngleDeg ?? 0} min={0} max={360} onChange={v => { selectedObj.startAngleDeg = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="End angle (°)"><NumInput value={selectedObj.endAngleDeg ?? 90} min={0} max={360} onChange={v => { selectedObj.endAngleDeg = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
        </>
      )
    }

    if (type === 'fabricannulus') {
      return (
        <Row label="Inner radius (0–1)">
          <input type="range" min={0.05} max={0.95} step={0.05} value={selectedObj.innerRatio ?? 0.5}
            onChange={e => { selectedObj.innerRatio = Number(e.target.value); canvas.requestRenderAll(); forceRender(n=>n+1) }}
            style={{ width: '100%' }} />
          <span style={{ fontSize: 11, color: muted }}>{((selectedObj.innerRatio ?? 0.5) * 100).toFixed(0)}%</span>
        </Row>
      )
    }

    if (type === 'fabricparallelogram') {
      return (
        <Row label="Skew (0–0.6)">
          <input type="range" min={0} max={0.6} step={0.05} value={selectedObj.skew ?? 0.3}
            onChange={e => { selectedObj.skew = Number(e.target.value); canvas.requestRenderAll(); forceRender(n=>n+1) }}
            style={{ width: '100%' }} />
        </Row>
      )
    }

    if (type === 'fabrictrapezoid') {
      return (
        <Row label="Top ratio (0–1)">
          <input type="range" min={0.1} max={1} step={0.05} value={selectedObj.topRatio ?? 0.6}
            onChange={e => { selectedObj.topRatio = Number(e.target.value); canvas.requestRenderAll(); forceRender(n=>n+1) }}
            style={{ width: '100%' }} />
        </Row>
      )
    }

    if (type === 'fabricslider') {
      return (
        <>
          <Row label="Variable name"><TextInput value={selectedObj.varName ?? 'a'} onChange={v => { selectedObj.varName = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Minimum"><NumInput value={selectedObj.sliderMin ?? 0} step={1} onChange={v => { selectedObj.sliderMin = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Maximum"><NumInput value={selectedObj.sliderMax ?? 10} step={1} onChange={v => { selectedObj.sliderMax = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Step"><NumInput value={selectedObj.sliderStep ?? 0.1} min={0.001} step={0.05} onChange={v => { selectedObj.sliderStep = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Current value">
            <span style={{ fontSize: 13, color: text, fontWeight: 600 }}>{(selectedObj.sliderValue ?? 5).toFixed(3)}</span>
          </Row>
        </>
      )
    }

    if (type === 'fabricaxes') {
      return (
        <>
          <Row label="x range">
            <div style={{ display: 'flex', gap: 6 }}>
              <NumInput value={selectedObj.xMin ?? -10} step={1} onChange={v => { selectedObj.xMin = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
              <NumInput value={selectedObj.xMax ?? 10} step={1} onChange={v => { selectedObj.xMax = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
            </div>
          </Row>
          <Row label="y range">
            <div style={{ display: 'flex', gap: 6 }}>
              <NumInput value={selectedObj.yMin ?? -10} step={1} onChange={v => { selectedObj.yMin = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
              <NumInput value={selectedObj.yMax ?? 10} step={1} onChange={v => { selectedObj.yMax = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
            </div>
          </Row>
          <Row label="Tick spacing">
            <NumInput value={selectedObj.tickSpacing ?? 1} min={0.1} step={0.5} onChange={v => { selectedObj.tickSpacing = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} />
          </Row>
          <Row label="Variant">
            <select value={selectedObj.variant ?? 'cartesian'}
              onChange={e => { selectedObj.variant = e.target.value; canvas.requestRenderAll(); forceRender(n=>n+1) }}
              style={{ fontSize: 12, padding: '3px 6px', borderRadius: 4, border: `1px solid ${border}`, background: surface, color: text, width: '100%' }}>
              <option value="cartesian">Cartesian</option>
              <option value="polar">Polar</option>
              <option value="complex">Complex Plane</option>
              <option value="numberplane">Number Plane</option>
            </select>
          </Row>
          <Row label="x label"><TextInput value={selectedObj.labelX ?? 'x'} onChange={v => { selectedObj.labelX = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="y label"><TextInput value={selectedObj.labelY ?? 'y'} onChange={v => { selectedObj.labelY = v; canvas.requestRenderAll(); forceRender(n=>n+1) }} /></Row>
          <Row label="Functions">
            {(selectedObj.axisFunctions ?? []).map((fn: any, i: number) => (
              <div key={i} style={{ display: 'flex', gap: 4, marginBottom: 4 }}>
                <input type="text" placeholder="y = sin(x)" value={fn.expr}
                  onChange={e => {
                    const a = [...selectedObj.axisFunctions]; a[i] = {...a[i], expr: e.target.value}
                    selectedObj.axisFunctions = a; canvas.requestRenderAll(); forceRender(n=>n+1)
                  }}
                  style={{ flex: 1, fontSize: 11, padding: '2px 4px', borderRadius: 4, border: `1px solid ${border}`, background: surface, color: text }} />
                <input type="color" value={fn.color || '#4a9eff'}
                  onChange={e => {
                    const a = [...selectedObj.axisFunctions]; a[i] = {...a[i], color: e.target.value}
                    selectedObj.axisFunctions = a; canvas.requestRenderAll(); forceRender(n=>n+1)
                  }}
                  style={{ width: 24, height: 24, border: 'none', padding: 0, cursor: 'pointer' }} />
                <button onClick={() => {
                  const a = selectedObj.axisFunctions.filter((_: any, j: number) => j !== i)
                  selectedObj.axisFunctions = a; canvas.requestRenderAll(); forceRender(n=>n+1)
                }} style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4, border: `1px solid ${border}`, background: 'transparent', color: '#f87171', cursor: 'pointer' }}>×</button>
              </div>
            ))}
            <button onClick={() => {
              selectedObj.axisFunctions = [...(selectedObj.axisFunctions ?? []), { expr: '', color: '#4a9eff', label: '' }]
              canvas.requestRenderAll(); forceRender(n=>n+1)
            }} style={{ fontSize: 12, padding: '4px 8px', borderRadius: 4, border: `1px solid ${border}`, background: 'transparent', color: text, cursor: 'pointer', width: '100%' }}>
              + Add function
            </button>
          </Row>
        </>
      )
    }

    return null
  }

  const hasFill = !['fabricarc', 'fabriclinesegment', 'fabricvector',
    'fabricnumberline', 'fabricanglemarker', 'fabricrightanglemarker',
    'fabricslider', 'fabricprotractor', 'fabricaxes'].includes(type)

  // Build a clean display name: strip leading 'fabric' prefix and capitalise
  const rawName = typeRaw.replace(/^fabric/i, '') || typeRaw || 'Object'
  const typeName = rawName.charAt(0).toUpperCase() + rawName.slice(1)

  return (
    <div style={{ width: 240, background: bg, borderLeft: `1px solid ${border}`, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      {/* Header */}
      <div style={{ padding: '12px 16px 8px', borderBottom: `1px solid ${border}`, fontSize: 12, fontWeight: 700, color: text }}>
        {typeName}
      </div>
      {/* Content (scrollable) */}
      <div style={{ flex: 1, overflowY: 'auto', padding: 16 }}>
        {specific()}
        {hasFill && fillProp}
        {commonProps}
        {/* Transform controls */}
        <div style={{ marginTop: 12, borderTop: `1px solid ${border}`, paddingTop: 12 }}>
          <Label>Transform</Label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            <button onClick={() => {
              const o = selectedObj; const cl = o.clone().then((c: any) => { c.left += 20; c.top += 20; canvas.add(c); canvas.setActiveObject(c); canvas.requestRenderAll() })
            }} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, border: `1px solid ${border}`, background: 'transparent', color: text, cursor: 'pointer' }}>
              Duplicate
            </button>
            <button onClick={() => {
              selectedObj.bringObjectForward?.() ?? selectedObj.bringForward?.()
              canvas.requestRenderAll()
            }} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, border: `1px solid ${border}`, background: 'transparent', color: text, cursor: 'pointer' }}>
              Forward
            </button>
            <button onClick={() => {
              selectedObj.sendObjectBackwards?.() ?? selectedObj.sendBackwards?.()
              canvas.requestRenderAll()
            }} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, border: `1px solid ${border}`, background: 'transparent', color: text, cursor: 'pointer' }}>
              Backward
            </button>
            <button onClick={() => {
              canvas.remove(selectedObj)
              canvas.discardActiveObject()
              canvas.requestRenderAll()
            }} style={{ fontSize: 11, padding: '4px 8px', borderRadius: 4, border: `1px solid #f87171`, background: 'transparent', color: '#f87171', cursor: 'pointer' }}>
              Delete
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
