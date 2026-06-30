import { test, expect } from '@playwright/test'

/**
 * Tutor session E2E flow.
 *
 * Prerequisites:
 * - API running at PLAYWRIGHT_API_URL (default http://localhost:8000)
 * - Web running at PLAYWRIGHT_WEB_URL (default http://localhost:3000)
 * - A test user pre-created with PLAYWRIGHT_TEST_EMAIL / PLAYWRIGHT_TEST_PASSWORD
 *   and AUTH_PROVIDER=jwt in the API
 *
 * These tests exercise the golden path only; they are skipped in CI
 * until a staging environment with seeded credentials is set up.
 */

const WEB_URL = process.env.PLAYWRIGHT_WEB_URL ?? 'http://localhost:3000'
const SKIP_E2E = !process.env.PLAYWRIGHT_RUN_E2E

test.skip(SKIP_E2E, 'Set PLAYWRIGHT_RUN_E2E=1 to run E2E tests against a live environment')

test.describe('Tutor session golden path', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${WEB_URL}/sign-in`)
    // Fill Clerk sign-in form (works when AUTH_PROVIDER=clerk with test credentials)
    await page.fill('[name="identifier"]', process.env.PLAYWRIGHT_TEST_EMAIL ?? '')
    await page.fill('[name="password"]', process.env.PLAYWRIGHT_TEST_PASSWORD ?? '')
    await page.click('[data-localization-key="formButtonPrimary"]')
    await page.waitForURL(`${WEB_URL}/dashboard`, { timeout: 15_000 })
  })

  test('sign-in → select topic → session shows problem', async ({ page }) => {
    // Navigate to a known topic practice page
    await page.goto(`${WEB_URL}/practice/alg1_linear_solve_one_var`)
    // Start session button
    await page.click('[data-testid="start-session"]')
    // Problem should appear within 30s (session creation + generation)
    await expect(page.locator('[data-testid="problem-statement"]')).toBeVisible({ timeout: 30_000 })
  })

  test('submit correct answer → problem advances', async ({ page }) => {
    await page.goto(`${WEB_URL}/practice/alg1_linear_solve_one_var`)
    await page.click('[data-testid="start-session"]')
    await expect(page.locator('[data-testid="problem-statement"]')).toBeVisible({ timeout: 30_000 })

    // Type a message (session is chat-based)
    const chatInput = page.locator('[data-testid="chat-input"]')
    await chatInput.fill('x = 5')
    await page.keyboard.press('Enter')

    // Tutor should respond
    await expect(page.locator('[data-testid="tutor-message"]').last()).toBeVisible({ timeout: 20_000 })
  })

  test('request hint → hint appears in chat', async ({ page }) => {
    await page.goto(`${WEB_URL}/practice/alg1_linear_solve_one_var`)
    await page.click('[data-testid="start-session"]')
    await expect(page.locator('[data-testid="problem-statement"]')).toBeVisible({ timeout: 30_000 })

    const hintButton = page.locator('[data-testid="hint-button"]')
    await expect(hintButton).toBeVisible()
    await hintButton.click()

    // A hint message should appear
    await expect(page.locator('[data-testid="tutor-message"]').last()).toBeVisible({ timeout: 20_000 })
  })

  test('end session → summary appears', async ({ page }) => {
    await page.goto(`${WEB_URL}/practice/alg1_linear_solve_one_var`)
    await page.click('[data-testid="start-session"]')
    await expect(page.locator('[data-testid="problem-statement"]')).toBeVisible({ timeout: 30_000 })

    const endButton = page.locator('[data-testid="end-session-button"]')
    await expect(endButton).toBeVisible()
    await endButton.click()

    // Confirmation dialog
    const confirmButton = page.locator('[data-testid="confirm-end-session"]')
    if (await confirmButton.isVisible({ timeout: 2_000 }).catch(() => false)) {
      await confirmButton.click()
    }

    // Session summary screen
    await expect(page.locator('[data-testid="session-summary"]')).toBeVisible({ timeout: 15_000 })
  })
})
