import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:8081';
const ADMIN_USERNAME = process.env.PLAYWRIGHT_USERNAME || 'SystemAdmin';
const ADMIN_PASSWORD = process.env.PLAYWRIGHT_PASSWORD || 'SystemAdmin';
const CONTRIBUTOR_USERNAME = process.env.PLAYWRIGHT_CONTRIBUTOR_USERNAME || 'Contributor';
const CONTRIBUTOR_PASSWORD = process.env.PLAYWRIGHT_CONTRIBUTOR_PASSWORD || 'Contributor';
const REVIEWER_USERNAME = process.env.PLAYWRIGHT_REVIEWER_USERNAME || 'Reviewer';
const REVIEWER_PASSWORD = process.env.PLAYWRIGHT_REVIEWER_PASSWORD || 'Reviewer';
const PUBLIC_USERNAME = process.env.PLAYWRIGHT_PUBLIC_USERNAME || 'PublicUser';
const PUBLIC_PASSWORD = process.env.PLAYWRIGHT_PUBLIC_PASSWORD || 'PublicUser';

let cachedSessions: Record<string, string> | null = null;

function sessionFilePath() {
  const candidates = [
    path.resolve(process.cwd(), 'e2e', '.session-keys.json'),
    path.resolve(process.cwd(), 'frontend', 'e2e', '.session-keys.json'),
  ];
  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate;
    }
  }
  throw new Error('Session key file not found. Run `npm --prefix frontend run e2e:bootstrap` first.');
}

function loadSessionMap() {
  if (cachedSessions) {
    return cachedSessions;
  }
  const payload = JSON.parse(readFileSync(sessionFilePath(), 'utf-8'));
  if (!payload?.sessions || typeof payload.sessions !== 'object') {
    throw new Error('Invalid e2e session key payload.');
  }
  cachedSessions = payload.sessions as Record<string, string>;
  return cachedSessions;
}

async function navigateWithRetry(page: Page, targetPath: string, pattern: RegExp, retries = 5) {
  for (let attempt = 0; attempt < retries; attempt += 1) {
    await page.goto(targetPath);
    await page.waitForLoadState('networkidle');
    if (pattern.test(page.url())) {
      return;
    }
    await page.waitForTimeout(250);
  }
  throw new Error(`Unable to reach ${targetPath}; current URL: ${page.url()}`);
}

function passwordForUser(username: string) {
  const defaults: Record<string, string> = {
    [ADMIN_USERNAME]: ADMIN_PASSWORD,
    [CONTRIBUTOR_USERNAME]: CONTRIBUTOR_PASSWORD,
    [REVIEWER_USERNAME]: REVIEWER_PASSWORD,
    [PUBLIC_USERNAME]: PUBLIC_PASSWORD,
  };
  return defaults[username] || username;
}

async function loginByForm(page: Page, username: string, password: string) {
  await page.context().clearCookies();
  await page.goto('/account/login/?next=/dashboard');
  await page.waitForLoadState('networkidle');
  await page.fill('input[name="auth-username"]', username);
  await page.fill('input[name="auth-password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForLoadState('networkidle');
}

async function loginAsSeededUser(page: Page, username: string, requiredCapability?: string) {
  const sessionKey = loadSessionMap()[username];
  const loginPassword = passwordForUser(username);
  let lastAuthState: { username: string; capabilities: Record<string, boolean> } | null = null;
  for (let attempt = 0; attempt < 6; attempt += 1) {
    await page.context().clearCookies();
    if (sessionKey) {
      await page.context().addCookies([
        {
          name: 'sessionid',
          value: sessionKey,
          url: BASE_URL,
        },
      ]);
    }
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    const authState = await page.evaluate(async () => {
      const response = await fetch('/api/auth/me', { credentials: 'include' });
      if (!response.ok) {
        return null;
      }
      const payload = await response.json();
      return { username: payload?.username, capabilities: payload?.capabilities || {} };
    });
    lastAuthState = authState;
    if (!authState || authState.username !== username) {
      await page.waitForTimeout(250);
      continue;
    }
    if (!requiredCapability || authState.capabilities?.[requiredCapability]) {
      return;
    }
    await page.waitForTimeout(250);
  }
  // Fallback to explicit login when pre-generated session keys were rotated/invalidated.
  await loginByForm(page, username, loginPassword);
  const fallbackAuthState = await page.evaluate(async () => {
    const response = await fetch('/api/auth/me', { credentials: 'include' });
    if (!response.ok) {
      return null;
    }
    const payload = await response.json();
    return { username: payload?.username, capabilities: payload?.capabilities || {} };
  });
  if (
    fallbackAuthState &&
    fallbackAuthState.username === username &&
    (!requiredCapability || fallbackAuthState.capabilities?.[requiredCapability])
  ) {
    return;
  }
  throw new Error(
    `Unable to establish authenticated session for ${username}. Last auth state: ${JSON.stringify(
      fallbackAuthState || lastAuthState
    )}`
  );
}

test('anonymous user sees public workspace only', async ({ page }) => {
  await page.goto('/indicators');
  await expect(page.getByText('National Biodiversity Monitoring System')).toBeVisible();
  await expect(page).toHaveURL(/indicators/);

  await expect(page.getByRole('link', { name: 'Indicator Explorer' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Dashboard' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'NR7 Builder' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'MEA Packs' })).toHaveCount(0);

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/indicators/);
});

test('authenticated system admin can access core workspaces', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  await expect(page.getByRole('link', { name: 'Logout' })).toBeVisible();

  await navigateWithRetry(page, '/dashboard', /dashboard/);
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();

  await page.getByRole('link', { name: 'Indicator Explorer' }).click();
  await expect(page).toHaveURL(/indicators/);

  await page.getByRole('link', { name: 'Spatial Viewer' }).click();
  await expect(page).toHaveURL(/map/);

  await page.getByRole('link', { name: 'Programme Ops' }).click();
  await expect(page).toHaveURL(/programmes/);

  await page.getByRole('link', { name: 'NR7 Builder' }).click();
  await expect(page).toHaveURL(/nr7-builder/);

  await page.getByRole('link', { name: 'MEA Packs' }).click();
  await expect(page).toHaveURL(/template-packs/);

  await page.getByRole('link', { name: 'Report Products' }).click();
  await expect(page).toHaveURL(/report-products/);
});

test('role visibility matrix is enforced in UI navigation', async ({ browser }) => {
  const contributorContext = await browser.newContext({ baseURL: BASE_URL });
  const contributorPage = await contributorContext.newPage();
  await loginAsSeededUser(contributorPage, CONTRIBUTOR_USERNAME, 'can_view_dashboard');
  await expect(contributorPage.getByRole('link', { name: 'Dashboard' })).toBeVisible();
  await expect(contributorPage.getByRole('link', { name: 'Indicator Explorer' })).toBeVisible();
  await expect(contributorPage.getByRole('link', { name: 'NR7 Builder' })).toHaveCount(0);
  await expect(contributorPage.getByRole('link', { name: 'MEA Packs' })).toHaveCount(0);
  await contributorContext.close();

  const reviewerContext = await browser.newContext({ baseURL: BASE_URL });
  const reviewerPage = await reviewerContext.newPage();
  await loginAsSeededUser(reviewerPage, REVIEWER_USERNAME, 'can_view_programmes');
  await expect(reviewerPage.getByRole('link', { name: 'Dashboard' })).toBeVisible();
  await expect(reviewerPage.getByRole('link', { name: 'Programme Ops' })).toBeVisible();
  await expect(reviewerPage.getByRole('link', { name: 'NR7 Builder' })).toBeVisible();
  await expect(reviewerPage.getByRole('link', { name: 'MEA Packs' })).toBeVisible();
  await reviewerContext.close();

  const publicContext = await browser.newContext({ baseURL: BASE_URL });
  const publicPage = await publicContext.newPage();
  await loginAsSeededUser(publicPage, PUBLIC_USERNAME, 'can_view_dashboard');
  await expect(publicPage.getByRole('link', { name: 'Indicator Explorer' })).toBeVisible();
  await expect(publicPage.getByRole('link', { name: 'Programme Ops' })).toHaveCount(0);
  await expect(publicPage.getByRole('link', { name: 'NR7 Builder' })).toHaveCount(0);
  await expect(publicPage.getByRole('link', { name: 'MEA Packs' })).toHaveCount(0);
  await publicContext.close();
});
