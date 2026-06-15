/**
 * QA helper script — runs Playwright against a page and reports:
 *   - Console errors/warnings
 *   - Failed network requests (4xx/5xx)
 *   - Screenshot saved to qa-screenshots/
 *
 * Usage:
 *   node qa-check.mjs <url> [<slug>] [--auth=qa-auth-state.json]
 *
 * After running, inspect reported issues and click-through results.
 */

import { chromium } from '@playwright/test';
import { writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SCREENSHOTS_DIR = resolve(__dirname, 'qa-screenshots');
mkdirSync(SCREENSHOTS_DIR, { recursive: true });

const [,, rawUrl, rawSlug, ...flags] = process.argv;
if (!rawUrl) {
  console.error('Usage: node qa-check.mjs <url> [slug] [--auth=file.json]');
  process.exit(1);
}

const authFlag = flags.find(f => f.startsWith('--auth='));
const authFile = authFlag ? authFlag.replace('--auth=', '') : null;
const slug = rawSlug || rawUrl.replace(/https?:\/\/[^/]+/, '').replace(/\//g, '_').replace(/^_/, '') || 'home';

async function run() {
  const browser = await chromium.launch({ headless: true });
  const contextOpts = { viewport: { width: 1280, height: 900 } };
  if (authFile) {
    contextOpts.storageState = authFile;
  }
  const context = await browser.newContext(contextOpts);
  const page = await context.newPage();

  const consoleErrors = [];
  const consoleWarnings = [];
  const networkFailures = [];

  // Collect console messages
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
    if (msg.type() === 'warning') consoleWarnings.push(msg.text());
  });

  // Collect JS exceptions
  page.on('pageerror', err => {
    consoleErrors.push(`[pageerror] ${err.message}`);
  });

  // Collect failed network requests
  page.on('response', response => {
    const status = response.status();
    if (status >= 400) {
      networkFailures.push(`${status} ${response.request().method()} ${response.url()}`);
    }
  });

  console.log(`\n${'='.repeat(60)}`);
  console.log(`QA CHECK: ${rawUrl}`);
  console.log(`${'='.repeat(60)}`);

  try {
    await page.goto(rawUrl, { waitUntil: 'networkidle', timeout: 30000 });
  } catch (e) {
    console.error(`Navigation failed: ${e.message}`);
    await browser.close();
    process.exit(1);
  }

  // Initial screenshot
  const initShot = resolve(SCREENSHOTS_DIR, `${slug}-initial.png`);
  await page.screenshot({ path: initShot, fullPage: true });
  console.log(`Screenshot: ${initShot}`);

  // Report console errors
  if (consoleErrors.length > 0) {
    console.log(`\nCONSOLE ERRORS (${consoleErrors.length}):`);
    consoleErrors.forEach(e => console.log(`  ✗ ${e}`));
  } else {
    console.log('\nConsole errors: NONE');
  }

  if (consoleWarnings.length > 0) {
    console.log(`\nCONSOLE WARNINGS (${consoleWarnings.length}):`);
    consoleWarnings.forEach(w => console.log(`  ! ${w}`));
  }

  // Report network failures
  if (networkFailures.length > 0) {
    console.log(`\nNETWORK FAILURES (${networkFailures.length}):`);
    networkFailures.forEach(f => console.log(`  ✗ ${f}`));
  } else {
    console.log('Network failures: NONE');
  }

  // Collect all links on page
  const links = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('a[href]')).map(a => ({
      text: a.textContent?.trim().slice(0, 60),
      href: a.getAttribute('href'),
    }));
  });

  if (links.length > 0) {
    console.log(`\nLINKS (${links.length}):`);
    links.forEach(l => console.log(`  ${l.href.padEnd(50)} "${l.text}"`));
  }

  // Collect all buttons
  const buttons = await page.evaluate(() => {
    return Array.from(document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]')).map(b => ({
      text: b.textContent?.trim().slice(0, 60) || b.getAttribute('value') || b.getAttribute('aria-label') || '(no text)',
      type: b.tagName.toLowerCase(),
      disabled: b.disabled || b.getAttribute('aria-disabled') === 'true',
    }));
  });

  if (buttons.length > 0) {
    console.log(`\nBUTTONS (${buttons.length}):`);
    buttons.forEach(b => console.log(`  [${b.disabled ? 'disabled' : 'enabled '}] ${b.text}`));
  }

  // Summary
  const issues = consoleErrors.length + networkFailures.length;
  console.log(`\n${'─'.repeat(60)}`);
  console.log(`RESULT: ${issues === 0 ? 'PASS' : `FAIL (${issues} issue(s))`}`);
  console.log(`${'─'.repeat(60)}\n`);

  await browser.close();
  return { consoleErrors, consoleWarnings, networkFailures, links, buttons };
}

run().catch(err => {
  console.error('Fatal:', err);
  process.exit(1);
});
