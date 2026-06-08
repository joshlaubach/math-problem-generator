import type { GridType } from './types'

export const MINOR_GRID = 40   // canvas units between minor lines
export const MAJOR_GRID = 200  // canvas units between major lines

interface GridColors {
  bg: string
  minor: string
  major: string
}

function getColors(theme: 'light' | 'dark'): GridColors {
  return theme === 'dark'
    ? { bg: '#0d1117', minor: 'rgba(255,255,255,0.055)', major: 'rgba(255,255,255,0.14)' }
    : { bg: '#ffffff',  minor: 'rgba(0,0,0,0.065)',      major: 'rgba(0,0,0,0.15)' }
}

/**
 * Draw the background grid onto a 2-D canvas context.
 * vpt = Fabric viewportTransform [a,b,c,d,e,f] (a=d=zoom, e=panX, f=panY)
 */
export function drawGrid(
  ctx: CanvasRenderingContext2D,
  vpt: number[],
  W: number,
  H: number,
  type: GridType,
  theme: 'light' | 'dark',
) {
  const colors = getColors(theme)
  // Fill background
  ctx.fillStyle = colors.bg
  ctx.fillRect(0, 0, W, H)

  if (type === 'blank') return

  const zoom = vpt[0]           // = vpt[3]; no rotation in this tool
  const panX = vpt[4]
  const panY = vpt[5]

  if (type === 'square') drawSquare(ctx, zoom, panX, panY, W, H, colors)
  else if (type === 'dotted') drawDotted(ctx, zoom, panX, panY, W, H, colors)
  else if (type === 'isometric') drawIsometric(ctx, zoom, panX, panY, W, H, colors)
}

// ── Square grid ───────────────────────────────────────────────────────────────

function drawSquare(
  ctx: CanvasRenderingContext2D,
  zoom: number, panX: number, panY: number,
  W: number, H: number,
  colors: GridColors,
) {
  const minorPx = MINOR_GRID * zoom
  const majorPx = MAJOR_GRID * zoom
  const showMinor = minorPx >= 5

  ctx.save()

  // Minor lines
  if (showMinor) {
    ctx.strokeStyle = colors.minor
    ctx.lineWidth = 0.5
    const ox = ((panX % minorPx) + minorPx) % minorPx
    const oy = ((panY % minorPx) + minorPx) % minorPx
    ctx.beginPath()
    for (let x = ox; x < W; x += minorPx) { ctx.moveTo(x, 0); ctx.lineTo(x, H) }
    for (let y = oy; y < H; y += minorPx) { ctx.moveTo(0, y); ctx.lineTo(W, y) }
    ctx.stroke()
  }

  // Major lines
  ctx.strokeStyle = colors.major
  ctx.lineWidth = showMinor ? 1 : 0.5
  const mx = ((panX % majorPx) + majorPx) % majorPx
  const my = ((panY % majorPx) + majorPx) % majorPx
  ctx.beginPath()
  for (let x = mx; x < W; x += majorPx) { ctx.moveTo(x, 0); ctx.lineTo(x, H) }
  for (let y = my; y < H; y += majorPx) { ctx.moveTo(0, y); ctx.lineTo(W, y) }
  ctx.stroke()

  ctx.restore()
}

// ── Dotted grid ───────────────────────────────────────────────────────────────

function drawDotted(
  ctx: CanvasRenderingContext2D,
  zoom: number, panX: number, panY: number,
  W: number, H: number,
  colors: GridColors,
) {
  const minorPx = MINOR_GRID * zoom
  const majorPx = MAJOR_GRID * zoom
  const showMinor = minorPx >= 8
  const spacing = showMinor ? minorPx : majorPx

  const ox = ((panX % spacing) + spacing) % spacing
  const oy = ((panY % spacing) + spacing) % spacing

  ctx.save()
  for (let x = ox; x < W + 0.5; x += spacing) {
    for (let y = oy; y < H + 0.5; y += spacing) {
      const worldX = (x - panX) / zoom
      const worldY = (y - panY) / zoom
      const isMajor =
        Math.abs(worldX % MAJOR_GRID) < 1 &&
        Math.abs(worldY % MAJOR_GRID) < 1
      const r = isMajor ? 2 : 1
      ctx.beginPath()
      ctx.arc(x, y, r, 0, Math.PI * 2)
      ctx.fillStyle = isMajor ? colors.major : colors.minor
      ctx.fill()
    }
  }
  ctx.restore()
}

// ── Isometric grid ────────────────────────────────────────────────────────────

function drawIsometric(
  ctx: CanvasRenderingContext2D,
  zoom: number, panX: number, panY: number,
  W: number, H: number,
  colors: GridColors,
) {
  const spacing = MINOR_GRID * zoom
  if (spacing < 4) return

  const sin60 = Math.sqrt(3) / 2
  const vStep = spacing * sin60      // vertical distance between horizontal lines
  const tan60 = Math.sqrt(3)         // tan(60°)

  ctx.save()
  ctx.strokeStyle = colors.minor
  ctx.lineWidth = 0.5
  ctx.beginPath()

  // Horizontal lines
  const oy = ((panY % vStep) + vStep) % vStep
  for (let y = oy - vStep; y < H + vStep; y += vStep) {
    ctx.moveTo(0, y); ctx.lineTo(W, y)
  }

  // +60° diagonals (slope = +tan(60°) → going down-right)
  const ox60 = ((panX % spacing) + spacing) % spacing
  for (let x = ox60 - spacing - H / tan60; x < W + spacing; x += spacing) {
    ctx.moveTo(x, 0); ctx.lineTo(x + H / tan60, H)
  }

  // −60° diagonals (slope = −tan(60°) → going down-left)
  const ox120 = ((panX % spacing) + spacing) % spacing
  for (let x = ox120 - spacing; x < W + H / tan60 + spacing; x += spacing) {
    ctx.moveTo(x, 0); ctx.lineTo(x - H / tan60, H)
  }

  ctx.stroke()
  ctx.restore()
}
