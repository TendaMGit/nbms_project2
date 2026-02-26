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
    try {
      await page.goto(targetPath);
      await page.waitForLoadState('networkidle');
      if (pattern.test(page.url())) {
        return;
      }
    } catch {
      // Transient connection resets can occur in containerized CI startup windows.
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
  await expect(page.getByRole('heading', { name: 'NBMS' })).toBeVisible();
  await expect(page).toHaveURL(/indicators/);

  await expect(page.getByRole('link', { name: 'Indicators' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Dashboard' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Reporting' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Template Packs' })).toHaveCount(0);

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/account\/login/);
});

test('authenticated system admin can access core workspaces', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  await expect(page.getByRole('button', { name: 'User menu' })).toBeVisible();

  await navigateWithRetry(page, '/dashboard', /dashboard/);
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();

  await navigateWithRetry(page, '/indicators', /indicators/);

  await navigateWithRetry(page, '/spatial/map', /spatial\/map|\/map/);

  await navigateWithRetry(page, '/programmes', /programmes/);

  await expect(page.getByRole('link', { name: 'Reporting' })).toBeVisible();

  await navigateWithRetry(page, '/template-packs', /template-packs/);

  await page.getByRole('link', { name: 'Preferences' }).click();
  await expect(page).toHaveURL(/account\/preferences/);
  await expect(page.getByText('Profile & Preferences', { exact: true })).toBeVisible();
});

test('role visibility matrix is enforced in UI navigation', async ({ browser }) => {
  const contributorContext = await browser.newContext({ baseURL: BASE_URL });
  const contributorPage = await contributorContext.newPage();
  await loginAsSeededUser(contributorPage, CONTRIBUTOR_USERNAME, 'can_view_dashboard');
  await expect(contributorPage.getByRole('link', { name: 'Dashboard' })).toBeVisible();
  await expect(contributorPage.getByRole('link', { name: 'Indicators' })).toBeVisible();
  await expect(contributorPage.getByRole('link', { name: 'Reporting' })).toHaveCount(0);
  await expect(contributorPage.getByRole('link', { name: 'Template Packs' })).toHaveCount(0);
  await contributorContext.close();

  const reviewerContext = await browser.newContext({ baseURL: BASE_URL });
  const reviewerPage = await reviewerContext.newPage();
  await loginAsSeededUser(reviewerPage, REVIEWER_USERNAME, 'can_view_programmes');
  await expect(reviewerPage.getByRole('link', { name: 'Dashboard' })).toBeVisible();
  await expect(reviewerPage.getByRole('link', { name: 'Programmes' })).toBeVisible();
  await reviewerContext.close();

  const publicContext = await browser.newContext({ baseURL: BASE_URL });
  const publicPage = await publicContext.newPage();
  await loginAsSeededUser(publicPage, PUBLIC_USERNAME, 'can_view_dashboard');
  await expect(publicPage.getByRole('link', { name: 'Indicators' })).toBeVisible();
  await expect(publicPage.getByRole('link', { name: 'Programmes' })).toHaveCount(0);
  await expect(publicPage.getByRole('link', { name: 'Reporting' })).toHaveCount(0);
  await expect(publicPage.getByRole('link', { name: 'Template Packs' })).toHaveCount(0);
  await publicContext.close();
});

test('indicator explorer saves views and watchlist state', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  await navigateWithRetry(page, '/indicators', /indicators/);

  const filterRail = page.locator('nbms-filter-rail');
  await filterRail.getByLabel('Search').fill('forest');
  await page.getByLabel('GBF Target').fill('3');
  await page.getByLabel('Geography type').click();
  await page.getByRole('option', { name: 'Municipality' }).click();
  await page.getByLabel('Geography code').fill('ZA-GP-TSH');

  const savedViewName = `E2E Saved View ${Date.now()}`;
  await page.evaluate(async (viewName) => {
    const csrfResponse = await fetch('/api/auth/csrf', { credentials: 'include' });
    const csrfPayload = await csrfResponse.json();
    const csrfToken = csrfPayload?.csrfToken || csrfPayload?.csrf_token;
    const response = await fetch('/api/me/preferences/saved-filters', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
      },
      body: JSON.stringify({
        namespace: 'indicators',
        name: viewName,
        pinned: true,
        params: {
          q: 'forest',
          gbf_target: '3',
          geography_type: 'municipality',
          geography_code: 'ZA-GP-TSH',
          sort: 'last_updated_desc',
          mode: 'table'
        }
      })
    });
    if (!response.ok) {
      throw new Error(`saved filter create failed: ${response.status}`);
    }
  }, savedViewName);

  const indicatorUuid = await page.evaluate(async () => {
    const response = await fetch('/api/indicators?page=1&page_size=1', { credentials: 'include' });
    if (!response.ok) {
      return null;
    }
    const payload = await response.json();
    return payload?.results?.[0]?.uuid ?? null;
  });
  if (indicatorUuid) {
    await page.evaluate(async (uuid) => {
      const csrfResponse = await fetch('/api/auth/csrf', { credentials: 'include' });
      const csrfPayload = await csrfResponse.json();
      const csrfToken = csrfPayload?.csrfToken || csrfPayload?.csrf_token;
      await fetch('/api/me/preferences/watchlist/add', {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
        },
        body: JSON.stringify({ namespace: 'indicators', item_id: uuid })
      });
    }, indicatorUuid);
  }

  await page.goto('/work');
  await page.waitForLoadState('networkidle');
  await expect(page.getByText('My Work Queue')).toBeVisible();
  await expect(page.getByText('Watched indicators')).toBeVisible();

  await page.goto('/indicators');
  await page.waitForLoadState('networkidle');
  await filterRail.getByLabel('Saved views').click();
  await page.getByRole('option', { name: savedViewName }).click();
  await expect(filterRail.getByLabel('Search')).toHaveValue(/forest/i);
});

test('downloads landing page shows citation for created record', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  const created = await page.evaluate(async () => {
    const csrfResponse = await fetch('/api/auth/csrf', { credentials: 'include' });
    if (!csrfResponse.ok) {
      throw new Error(`csrf failed: ${csrfResponse.status}`);
    }
    const payload = await csrfResponse.json();
    const csrfToken = payload?.csrfToken || payload?.csrf_token;
    const response = await fetch('/api/downloads/records', {
      method: 'POST',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
        ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {})
      },
      body: JSON.stringify({
        record_type: 'registry_export',
        object_type: 'registry_taxa',
        query_snapshot: {
          registry_kind: 'taxa'
        }
      })
    });
    if (!response.ok) {
      const detail = await response.text();
      throw new Error(`create failed: ${response.status} ${detail}`);
    }
    return response.json();
  });
  await page.goto(`/downloads/${created.uuid}`);
  await expect(page).toHaveURL(/downloads\/[0-9a-f-]+/);
  await expect(page.locator('mat-card-title', { hasText: 'Citation' }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: 'Copy citation' })).toBeVisible();
});
