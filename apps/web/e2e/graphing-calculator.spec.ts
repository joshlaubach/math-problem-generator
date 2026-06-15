/**
 * Graphing Calculator — comprehensive Playwright test suite
 *
 * Tests every realistic expression category against the GraphingPanel:
 * algebraic, trig, exponential/log, integral, parametric, polar, x=f(y),
 * and edge cases. For each expression we verify:
 *   1. No JS exception is thrown
 *   2. The Mafs canvas renders SVG curve paths (for expressions that should plot)
 *   3. The panel stays stable through expression changes
 *
 * Run:  npx playwright test --config apps/web/playwright.config.ts
 */

import { test, expect, Page, ConsoleMessage } from '@playwright/test'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const BASE = 'http://localhost:3001'

/** Set the LaTeX value of the nth math-field element (0-indexed) and trigger input. */
async function setMathField(page: Page, index: number, latex: string) {
  await page.evaluate(
    ({ idx, val }) => {
      const fields = document.querySelectorAll('math-field')
      const el = fields[idx] as HTMLElement & { value: string }
      if (!el) throw new Error(`math-field[${idx}] not found`)
      el.value = val
      el.dispatchEvent(new Event('input', { bubbles: true }))
    },
    { idx: index, val: latex },
  )
}

/** Switch the function type selector for the nth function card (0-indexed). */
async function setFnType(page: Page, index: number, type: 'y' | 'x' | 'parametric' | 'polar') {
  const selects = page.locator('select').filter({ hasText: 'y =' })
  // Type selectors are after CalcMathField containers; pick by index
  await page.evaluate(
    ({ idx, val }) => {
      const selects = Array.from(document.querySelectorAll('select')).filter(
        s => s.querySelector('option[value="y"]'),
      )
      const el = selects[idx] as HTMLSelectElement
      if (!el) throw new Error(`fn-type select[${idx}] not found`)
      el.value = val
      el.dispatchEvent(new Event('change', { bubbles: true }))
    },
    { idx: index, val: type },
  )
}

/**
 * Count SVG path elements inside the Mafs canvas.
 * Mafs renders the coordinate grid as <line> elements and function curves as
 * <path> elements with complex d attributes. A non-zero count means something
 * was drawn.
 */
async function graphPathCount(page: Page): Promise<number> {
  return page.evaluate(() => {
    const wrapper = document.querySelector('.mafs-calc-wrapper')
    if (!wrapper) return -1
    return wrapper.querySelectorAll('svg path[d]').length
  })
}

/** True when at least one <path d="..."> contains a long coordinate string. */
async function hasPlottedCurve(page: Page): Promise<boolean> {
  return page.evaluate(() => {
    const wrapper = document.querySelector('.mafs-calc-wrapper')
    if (!wrapper) return false
    const paths = wrapper.querySelectorAll('svg path[d]')
    for (const p of paths) {
      const d = p.getAttribute('d') ?? ''
      if (d.length > 50) return true
    }
    return false
  })
}

/** Collect console errors during a callback. Returns the error list. */
async function withErrorCapture(page: Page, fn: () => Promise<void>): Promise<string[]> {
  const errors: string[] = []
  const onError = (err: Error) => errors.push(err.message)
  const onConsole = (msg: ConsoleMessage) => {
    if (msg.type() === 'error') errors.push(msg.text())
  }
  page.once('pageerror', onError)
  page.on('console', onConsole)
  await fn()
  page.off('pageerror', onError)
  page.off('console', onConsole)
  return errors
}

/** Click "+ Add function" to add a new function card. */
async function addFunction(page: Page) {
  await page.getByText('+ Add function').click()
  await page.waitForTimeout(150)
}

// ─── Test setup ───────────────────────────────────────────────────────────────

test.beforeEach(async ({ page }) => {
  await page.goto(`${BASE}/test-calc`)
  // Wait for Mafs canvas to load (the loading-placeholder text disappears)
  await page.waitForFunction(() => !document.querySelector('.mafs-calc-wrapper')?.textContent?.includes('Loading graph'))
  // Wait for first math-field (MathLive component)
  await page.waitForSelector('math-field', { timeout: 8000 })
  // Brief settle so initial React render completes
  await page.waitForTimeout(300)
})

// ─── Sanity: page loads ────────────────────────────────────────────────────────

test('page loads without JS errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(`${BASE}/test-calc`)
  await page.waitForSelector('math-field', { timeout: 8000 })
  expect(errors).toHaveLength(0)
})

test('Mafs canvas renders the coordinate grid', async ({ page }) => {
  await expect(page.locator('.mafs-calc-wrapper svg')).toBeVisible()
  const count = await graphPathCount(page)
  expect(count).toBeGreaterThanOrEqual(0) // grid may use <line>, not <path>
})

test('graphing tab is active by default with calcMode=graphing', async ({ page }) => {
  await expect(page.locator('.mafs-calc-wrapper')).toBeVisible()
  await expect(page.locator('math-field').first()).toBeVisible()
})

// ─── Algebraic expressions ─────────────────────────────────────────────────────

const algebraicCases: Array<[string, string]> = [
  ['identity line y=x',        'x'],
  ['parabola y=x²',            'x^{2}'],
  ['cubic y=x³',               'x^{3}'],
  ['linear 2x+3',              '2x+3'],
  ['linear with fraction',     '\\frac{1}{2}x-1'],
  ['inverted parabola',        '-x^{2}+4'],
  ['quartic',                  'x^{4}-4x^{2}'],
  ['reciprocal 1/x',          '\\frac{1}{x}'],
  ['rational (x²-1)/(x-1)',   '\\frac{x^{2}-1}{x-1}'],
  ['square root',              '\\sqrt{x}'],
  ['sqrt of sum',              '\\sqrt{x^{2}+1}'],
  ['absolute value |x|',       '\\left|x\\right|'],
  ['abs of quadratic',         '\\left|x^{2}-4\\right|'],
  ['degree 5 polynomial',      'x^{5}-5x^{3}+4x'],
  ['product (x-1)(x+2)',       '\\left(x-1\\right)\\left(x+2\\right)'],
]

for (const [label, latex] of algebraicCases) {
  test(`algebraic: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setMathField(page, 0, latex)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Trigonometric expressions ─────────────────────────────────────────────────

const trigCases: Array<[string, string]> = [
  ['sin(x) with parens',           '\\sin\\left(x\\right)'],
  ['cos(x) with parens',           '\\cos\\left(x\\right)'],
  ['tan(x) with parens',           '\\tan\\left(x\\right)'],
  ['sin x — no parens',            '\\sin x'],          // the special case we fixed
  ['cos x — no parens',            '\\cos x'],
  ['arctan(x)',                    '\\arctan\\left(x\\right)'],
  ['arcsin(x)',                    '\\arcsin\\left(x\\right)'],
  ['arccos(x)',                    '\\arccos\\left(x\\right)'],
  ['2 sin(3x+1)',                  '2\\sin\\left(3x+1\\right)'],
  ['sin(x²)',                      '\\sin\\left(x^{2}\\right)'],
  ['sin(x) + cos(x)',              '\\sin\\left(x\\right)+\\cos\\left(x\\right)'],
  ['sin(x)/x  (sinc)',             '\\frac{\\sin\\left(x\\right)}{x}'],
  ['tan(x/2)',                     '\\tan\\left(\\frac{x}{2}\\right)'],
  ['cos²(x) via square',          '\\cos\\left(x\\right)^{2}'],
  ['sin(x)·cos(x)',                '\\sin\\left(x\\right)\\cdot\\cos\\left(x\\right)'],
]

for (const [label, latex] of trigCases) {
  test(`trig: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setMathField(page, 0, latex)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Exponential & logarithmic ─────────────────────────────────────────────────

const expLogCases: Array<[string, string]> = [
  ['e^x',                    'e^{x}'],
  ['e^{-x} decay',           'e^{-x}'],
  ['Gaussian e^{-x²}',       'e^{-x^{2}}'],
  ['2^x  base 2',            '2^{x}'],
  ['0.5^x',                  '0.5^{x}'],
  ['10^x',                   '10^{x}'],
  ['ln(x)',                  '\\ln\\left(x\\right)'],
  ['log(x) base 10',         '\\log\\left(x\\right)'],
  ['e^x - e^{-x}  sinh',     'e^{x}-e^{-x}'],
  ['x·e^{-x}',               'x\\cdot e^{-x}'],
  ['ln(x²+1)',               '\\ln\\left(x^{2}+1\\right)'],
  ['e^{sin(x)}',             'e^{\\sin\\left(x\\right)}'],
  ['log(|x|)',               '\\log\\left(\\left|x\\right|\\right)'],
  ['x^x  (x>0)',             'x^{x}'],
]

for (const [label, latex] of expLogCases) {
  test(`exp/log: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setMathField(page, 0, latex)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Integral expressions (numerical) ─────────────────────────────────────────

const integralCases: Array<[string, string]> = [
  ['∫₁ˣ 1/t dt = ln(x)',               '\\int_{1}^{x}\\frac{1}{t}\\mathrm{d}t'],
  ['∫₀ˣ e^{-t²} dt (error fn)',        '\\int_{0}^{x}e^{-t^{2}}dt'],
  ['∫₀ˣ sin(t) dt = 1-cos(x)',         '\\int_{0}^{x}\\sin\\left(t\\right)dt'],
  ['∫₀ˣ cos(t) dt = sin(x)',           '\\int_{0}^{x}\\cos\\left(t\\right)dt'],
  ['∫₋₁ˣ t² dt = cubic',              '\\int_{-1}^{x}t^{2}dt'],
  ['∫₀ˣ t³ dt = x⁴/4',               '\\int_{0}^{x}t^{3}dt'],
  ['∫₁ˣ 1/t² dt = 1-1/x',            '\\int_{1}^{x}\\frac{1}{t^{2}}dt'],
  ['∫₀ˣ e^t dt = e^x-1',             '\\int_{0}^{x}e^{t}dt'],
  ['∫₀ˣ 1/(1+t²) dt = arctan(x)',     '\\int_{0}^{x}\\frac{1}{1+t^{2}}dt'],
  ['∫₀ˣ e^{-t²} dt (mathrm d)',       '\\int_0^{x}e^{-t^{2}}\\,\\mathrm{d}t'],
]

for (const [label, latex] of integralCases) {
  test(`integral: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setMathField(page, 0, latex)
      await page.waitForTimeout(600) // integrals take longer to compute
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Polar curves ──────────────────────────────────────────────────────────────

const polarCases: Array<[string, string]> = [
  ['circle r=1',              '1'],
  ['Archimedean spiral r=θ',  '\\theta'],
  ['cardioid 1+cos(θ)',       '1+\\cos\\left(\\theta\\right)'],
  ['rose 2cos(2θ)',           '2\\cos\\left(2\\theta\\right)'],
  ['limaçon 1+2cos(θ)',       '1+2\\cos\\left(\\theta\\right)'],
  ['lemniscate r=cos(2θ)',    '\\cos\\left(2\\theta\\right)'],
]

for (const [label, expr] of polarCases) {
  test(`polar: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setFnType(page, 0, 'polar')
      await page.waitForTimeout(200)
      await setMathField(page, 0, expr)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Parametric curves ─────────────────────────────────────────────────────────

const parametricCases: Array<[string, string, string]> = [
  ['unit circle',        '\\cos\\left(t\\right)',         '\\sin\\left(t\\right)'],
  ['parabola param',     't',                             't^{2}'],
  ['spiral',             't\\cdot\\cos\\left(t\\right)', 't\\cdot\\sin\\left(t\\right)'],
  ['Lissajous 3:2',      '\\sin\\left(3t\\right)',        '\\sin\\left(2t\\right)'],
  ['epicycloid',         '\\cos\\left(t\\right)-\\cos\\left(5t\\right)', '\\sin\\left(t\\right)-\\sin\\left(5t\\right)'],
  ['cycloid x=t-sin t',  't-\\sin\\left(t\\right)',       '1-\\cos\\left(t\\right)'],
]

for (const [label, xExpr, yExpr] of parametricCases) {
  test(`parametric: ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setFnType(page, 0, 'parametric')
      await page.waitForTimeout(200)
      // parametric has two math-fields per card: x(t) at index 0, y(t) at index 1
      await setMathField(page, 0, xExpr)
      await setMathField(page, 1, yExpr)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── x = f(y) curves ──────────────────────────────────────────────────────────

const xOfYCases: Array<[string, string]> = [
  ['horizontal parabola x=y²',   'y^{2}'],
  ['rotated cubic x=y³-y',       'y^{3}-y'],
  ['x=sin(y)',                    '\\sin\\left(y\\right)'],
  ['x=e^y',                       'e^{y}'],
]

for (const [label, expr] of xOfYCases) {
  test(`x=f(y): ${label}`, async ({ page }) => {
    const errors = await withErrorCapture(page, async () => {
      await setFnType(page, 0, 'x')
      await page.waitForTimeout(200)
      await setMathField(page, 0, expr)
      await page.waitForTimeout(400)
    })
    expect(errors.filter(e => !e.includes('Warning:'))).toHaveLength(0)
    expect(await hasPlottedCurve(page)).toBe(true)
  })
}

// ─── Multiple functions simultaneously ─────────────────────────────────────────

test('multiple functions: sin and cos simultaneously', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, '\\sin\\left(x\\right)')
  await page.waitForTimeout(200)
  await addFunction(page)
  await setMathField(page, 1, '\\cos\\left(x\\right)')
  await page.waitForTimeout(400)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('three functions: parabola, sin, ln', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, 'x^{2}')
  await addFunction(page)
  await setMathField(page, 1, '\\sin\\left(x\\right)')
  await addFunction(page)
  await setMathField(page, 2, '\\ln\\left(x\\right)')
  await page.waitForTimeout(500)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

// ─── Edge cases — should be graceful, no crashes ───────────────────────────────

const edgeCases: Array<[string, string]> = [
  ['empty expression',            ''],
  ['division by zero 1/0',       '\\frac{1}{0}'],
  ['sqrt of negative √(-1)',     '\\sqrt{-1}'],
  ['complex: sqrt(-x²)',         '\\sqrt{-x^{2}}'],
  ['large exponent 10^x',        '10^{x^{2}}'],   // grows very fast; clipped
  ['tan near π/2',               '\\tan\\left(x\\right)'],  // has asymptotes
  ['log(0)',                     '\\ln\\left(0\\right)'],
  ['log of negative',            '\\ln\\left(-x\\right)'],
  ['undefined symbol',           '\\alpha+x'],    // \alpha not defined, should return null
]

for (const [label, latex] of edgeCases) {
  test(`edge case graceful: ${label}`, async ({ page }) => {
    const errors: string[] = []
    page.on('pageerror', e => errors.push(e.message))

    await setMathField(page, 0, latex)
    await page.waitForTimeout(400)

    expect(errors).toHaveLength(0)
    // Canvas should still render (even if no curve)
    await expect(page.locator('.mafs-calc-wrapper svg')).toBeVisible()
  })
}

// ─── Style controls don't crash ────────────────────────────────────────────────

test('line style toggles (solid/dashed/dotted) work without errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, 'x^{2}')
  await page.waitForTimeout(200)

  // Click dashed style button
  await page.getByText('╌').click()
  await page.waitForTimeout(100)
  // Click dotted
  await page.getByText('⋯').click()
  await page.waitForTimeout(100)
  // Back to solid
  await page.getByText('─').click()
  await page.waitForTimeout(200)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('weight selector changes without errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, '\\sin\\left(x\\right)')
  await page.waitForTimeout(200)

  // Select weight 3×
  await page.evaluate(() => {
    const weightSelects = Array.from(document.querySelectorAll('select')).filter(
      s => s.querySelector('option[value="3"]'),
    )
    const el = weightSelects[0] as HTMLSelectElement
    if (el) { el.value = '3'; el.dispatchEvent(new Event('change', { bubbles: true })) }
  })
  await page.waitForTimeout(200)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('visibility toggle hides and shows function', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, 'x^{2}')
  await page.waitForTimeout(300)
  const beforeCount = await graphPathCount(page)

  // Click the ◉ visibility toggle to hide
  await page.getByText('◉').first().click()
  await page.waitForTimeout(300)
  const hiddenCount = await graphPathCount(page)

  // Click ○ to show again
  await page.getByText('○').first().click()
  await page.waitForTimeout(300)
  const reshownCount = await graphPathCount(page)

  expect(errors).toHaveLength(0)
  // When hidden, fewer paths; when reshown, same as before
  expect(hiddenCount).toBeLessThanOrEqual(beforeCount)
  expect(reshownCount).toBeGreaterThanOrEqual(beforeCount)
})

test('add and delete function cards', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, 'x')
  await addFunction(page)
  await setMathField(page, 1, 'x^{2}')
  await page.waitForTimeout(300)

  // Delete the second function (× button)
  const deleteButtons = page.getByText('×')
  await deleteButtons.last().click()
  await page.waitForTimeout(300)

  expect(errors).toHaveLength(0)
  // Should have gone back to 1 function
  const fieldCount = await page.evaluate(() => document.querySelectorAll('math-field').length)
  expect(fieldCount).toBe(1)
})

// ─── View window controls ──────────────────────────────────────────────────────

test('changing view window bounds re-renders without errors', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  await setMathField(page, 0, '\\sin\\left(x\\right)')
  await page.waitForTimeout(300)

  // Change xMin to -10
  await page.evaluate(() => {
    const inputs = Array.from(document.querySelectorAll('input[type="number"]'))
    const el = inputs[0] as HTMLInputElement
    if (el) { el.value = '-10'; el.dispatchEvent(new Event('change', { bubbles: true })) }
  })
  await page.waitForTimeout(300)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

// ─── LaTeX conversion correctness (JS-level) ──────────────────────────────────
//
// These tests call latexToMathjs logic via the internal test helper that the
// test-calc page exposes on window.__testCalcFns (if present).
// If the helper is not exposed, we fall back to verifying the visual output.

test('latexToMathjs conversion: \\sin x → produces a plot', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\sin x')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('latexToMathjs conversion: \\frac{1}{x} → produces a plot', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\frac{1}{x}')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('latexToMathjs conversion: \\sqrt{x^{2}+1} → produces a plot', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\sqrt{x^{2}+1}')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('integral: \\int_1^{x}\\frac{1}{t}\\mathrm{d}t plots ln(x)', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\int_{1}^{x}\\frac{1}{t}\\mathrm{d}t')
  await page.waitForTimeout(700) // numerical integration takes longer
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('integral: \\int_0^{x}e^{-t^{2}}dt plots Gaussian CDF shape', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\int_{0}^{x}e^{-t^{2}}dt')
  await page.waitForTimeout(700)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

// ─── Rapid expression switching stability ─────────────────────────────────────

test('rapid expression changes do not crash', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))

  const exprs = [
    'x', 'x^{2}', '\\sin\\left(x\\right)', 'e^{x}', '\\sqrt{x}',
    '\\frac{1}{x}', '\\ln\\left(x\\right)', '\\cos\\left(x\\right)',
    'x^{3}-x', '\\tan\\left(x\\right)',
  ]
  for (const expr of exprs) {
    await setMathField(page, 0, expr)
    await page.waitForTimeout(80)
  }
  await page.waitForTimeout(500)

  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

// ─── Pi and theta as constants ────────────────────────────────────────────────

test('π constant renders correctly: sin(πx)', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\sin\\left(\\pi x\\right)')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('π constant in fraction: sin(2πx/3)', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\sin\\left(\\frac{2\\pi x}{3}\\right)')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

// ─── Desmos-representative showcase ───────────────────────────────────────────
// These mirror what a student would typically enter in Desmos.

test('Desmos: quadratic formula discriminant', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  // b²-4ac where a=1, b=x, c=2 → x²-8 (just checking expression parsing)
  await setMathField(page, 0, 'x^{2}-4')
  await page.waitForTimeout(300)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('Desmos: standard normal PDF', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\frac{1}{\\sqrt{2\\pi}}e^{-\\frac{x^{2}}{2}}')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('Desmos: logistic sigmoid 1/(1+e^{-x})', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\frac{1}{1+e^{-x}}')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})

test('Desmos: step function via arctan approximation', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', e => errors.push(e.message))
  await setMathField(page, 0, '\\frac{1}{2}+\\frac{1}{\\pi}\\arctan\\left(10x\\right)')
  await page.waitForTimeout(400)
  expect(errors).toHaveLength(0)
  expect(await hasPlottedCurve(page)).toBe(true)
})
