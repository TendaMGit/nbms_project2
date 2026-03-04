import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { expect, test, type Locator, type Page } from '@playwright/test';

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

function shellNav(page: Page) {
  return page.locator('mat-sidenav.side-nav');
}

async function isLocatorVisible(locator: Locator) {
  try {
    return await locator.first().isVisible();
  } catch {
    return false;
  }
}

async function waitForThrottleWindow(page: Page, reload = false) {
  const banner = page.getByText(/Request was throttled\./i).first();
  const visible = await banner.isVisible().catch(() => false);
  if (!visible) {
    return;
  }
  const message = (await banner.textContent()) || '';
  const seconds = Number(/(\d+)/.exec(message)?.[1] || '2');
  await page.waitForTimeout((Math.min(seconds, 10) + 1) * 1000);
  if (reload) {
    await page.reload();
    await page.waitForLoadState('networkidle');
  }
}

async function loginByForm(page: Page, username: string, password: string) {
  await page.context().clearCookies();
  await page.goto('/account/login/?next=/dashboard');
  await page.waitForLoadState('networkidle');
  const usernameField = page
    .locator('input[name="auth-username"], input[name="username"], input[autocomplete="username"]')
    .first();
  const passwordField = page
    .locator('input[name="auth-password"], input[name="password"], input[type="password"]')
    .first();
  const submitButton = page.getByRole('button', { name: /next|log in|login|sign in/i }).first();
  await usernameField.fill(username);
  await passwordField.fill(password);
  await submitButton.click();
  await page.waitForURL(/dashboard|account\/login/, { timeout: 15_000 }).catch(() => undefined);
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
  let fallbackAuthState: { username: string; capabilities: Record<string, boolean> } | null = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    await loginByForm(page, username, loginPassword);
    fallbackAuthState = await page.evaluate(async () => {
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
    await page.waitForTimeout(400);
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

  const nav = shellNav(page);
  await expect(nav.getByRole('link', { name: 'Indicators', exact: true })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Dashboard', exact: true })).toHaveCount(0);
  await expect(nav.getByRole('link', { name: 'Programmes', exact: true })).toHaveCount(0);
  await expect(nav.getByRole('link', { name: 'Template Packs', exact: true })).toHaveCount(0);

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/account\/login/);
});

test('authenticated system admin can access core workspaces', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  await expect(page.getByRole('button', { name: 'User menu' })).toBeVisible();
  const nav = shellNav(page);
  await expect(nav.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Frameworks', exact: true })).toBeVisible();
  await expect(nav.getByRole('link', { name: 'Indicators', exact: true })).toBeVisible();

  await navigateWithRetry(page, '/dashboard', /dashboard/);
  await navigateWithRetry(page, '/indicators', /indicators/);
  await navigateWithRetry(page, '/spatial/map', /spatial\/map|\/map/);
  await navigateWithRetry(page, '/programmes', /programmes/);
  await navigateWithRetry(page, '/template-packs', /template-packs/);

  await page.getByRole('button', { name: 'User menu' }).click();
  await page.getByRole('menuitem', { name: 'Preferences' }).click();
  await expect(page).toHaveURL(/account\/preferences/);
  await expect(page.getByText('Profile & Preferences', { exact: true })).toBeVisible();
});

test('role visibility matrix is enforced in UI navigation', async ({ browser }) => {
  const contributorContext = await browser.newContext({ baseURL: BASE_URL });
  const contributorPage = await contributorContext.newPage();
  await loginAsSeededUser(contributorPage, CONTRIBUTOR_USERNAME, 'can_view_dashboard');
  const contributorNav = shellNav(contributorPage);
  await expect(contributorNav.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await expect(contributorNav.getByRole('link', { name: 'Indicators', exact: true })).toBeVisible();
  await expect(contributorNav.getByRole('link', { name: 'Programmes', exact: true })).toHaveCount(0);
  await expect(contributorNav.getByRole('link', { name: 'Template Packs', exact: true })).toHaveCount(0);
  await contributorContext.close();

  const reviewerContext = await browser.newContext({ baseURL: BASE_URL });
  const reviewerPage = await reviewerContext.newPage();
  await loginAsSeededUser(reviewerPage, REVIEWER_USERNAME, 'can_view_programmes');
  const reviewerNav = shellNav(reviewerPage);
  await expect(reviewerNav.getByRole('link', { name: 'Dashboard', exact: true })).toBeVisible();
  await navigateWithRetry(reviewerPage, '/programmes', /programmes/);
  await expect(reviewerPage.getByRole('heading', { name: 'Programme Operations' })).toBeVisible();
  await reviewerContext.close();

  const publicContext = await browser.newContext({ baseURL: BASE_URL });
  const publicPage = await publicContext.newPage();
  await loginAsSeededUser(publicPage, PUBLIC_USERNAME, 'can_view_dashboard');
  const publicNav = shellNav(publicPage);
  await expect(publicNav.getByRole('link', { name: 'Indicators', exact: true })).toBeVisible();
  await expect(publicNav.getByRole('link', { name: 'Programmes', exact: true })).toHaveCount(0);
  await expect(publicNav.getByRole('link', { name: 'Template Packs', exact: true })).toHaveCount(0);
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

async function resolveIndicatorUuid(page: Page, code: string): Promise<string> {
  return page.evaluate(async (indicatorCode) => {
    for (let attempt = 0; attempt < 4; attempt += 1) {
      const response = await fetch('/api/indicators?page=1&page_size=250', { credentials: 'include' });
      if (response.status === 429) {
        await new Promise((resolve) => window.setTimeout(resolve, 1500 * (attempt + 1)));
        continue;
      }
      if (!response.ok) {
        throw new Error(`indicator lookup failed: ${response.status}`);
      }
      const payload = await response.json();
      const match = (payload?.results || []).find(
        (indicator: { code: string; uuid: string }) => indicator.code === indicatorCode
      );
      if (match?.uuid) {
        return match.uuid;
      }
      break;
    }
    throw new Error(`Indicator ${indicatorCode} was not available in the running seed catalogue.`);
  }, code);
}

test('pilot ecosystem RLE indicator defaults to distribution view and filters the slice', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  const indicatorUuid = await resolveIndicatorUuid(page, 'NBA_ECO_RLE_TERR');

  await navigateWithRetry(page, `/indicators/${indicatorUuid}?tab=indicator`, new RegExp(`indicators/${indicatorUuid}`));
  await expect(page).toHaveURL(/view=distribution/);
  await expect(page.getByRole('tab', { name: 'distribution', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.getByLabel('Category dimension')).toBeVisible();
  await expect(page.locator('nbms-data-table .row').first()).toBeVisible();
  await expect(page.locator('nbms-data-table .table-empty')).toHaveCount(0);
  await page.locator('nbms-view-distribution .table-link').first().click();
  await expect(page).toHaveURL(/dim_value=/);
});

test('pilot plant SPI taxonomy pack supports level switching', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  const indicatorUuid = await resolveIndicatorUuid(page, 'NBA_PLANT_SPI');

  await navigateWithRetry(
    page,
    `/indicators/${indicatorUuid}?tab=indicator&view=taxonomy`,
    new RegExp(`indicators/${indicatorUuid}.*view=taxonomy`)
  );
  await waitForThrottleWindow(page);
  await expect(page.getByLabel('Group by level')).toBeVisible();

  await page.getByLabel('Group by level').click();
  await page.getByRole('option', { name: 'Genus' }).click();
  await expect(page).toHaveURL(/tax_level=genus/);
  await waitForThrottleWindow(page);
  await expect(page.getByLabel('Group by level')).toContainText('Genus');
});

test('pilot RLE x EPL matrix indicator supports click-to-filter', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  const indicatorUuid = await resolveIndicatorUuid(page, 'NBA_ECO_RLE_EPL_TERR_MATRIX');

  await navigateWithRetry(
    page,
    `/indicators/${indicatorUuid}?tab=indicator&report_cycle=NR7-2022`,
    new RegExp(`indicators/${indicatorUuid}`)
  );
  await waitForThrottleWindow(page, true);
  const firstCell = page.locator('.matrix .cell').first();
  await expect(firstCell).toBeVisible();
  await firstCell.click();
  await expect(page).toHaveURL(/compare=/);
  await expect(page).toHaveURL(/dim_value=/);
  await expect(page).toHaveURL(/right=/);
});

test('pilot TEPI indicator shows a multi-year timeseries', async ({ page }) => {
  await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');
  const indicatorUuid = await resolveIndicatorUuid(page, 'NBA_TEPI_TERR');

  await navigateWithRetry(
    page,
    `/indicators/${indicatorUuid}?tab=indicator`,
    new RegExp(`indicators/${indicatorUuid}`)
  );
  await waitForThrottleWindow(page, true);
  await expect(page).toHaveURL(/view=timeseries/);
  await expect(page.getByRole('tab', { name: 'timeseries', exact: true })).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('canvas').first()).toBeVisible();
  expect(await page.locator('nbms-data-table .row').count()).toBeGreaterThan(1);

  await page.getByRole('tab', { name: 'distribution', exact: true }).click();
  await waitForThrottleWindow(page);
  await expect(page).toHaveURL(/view=distribution/);
  await expect(page.getByLabel('Category dimension')).toBeVisible();
});

async function openResponsiveSurface(
  page: Page,
  surface: 'dashboard' | 'framework' | 'target' | 'indicators' | 'indicator',
  frameworkId: string
): Promise<boolean> {
  if (surface === 'dashboard') {
    await navigateWithRetry(page, '/dashboard', /dashboard/);
    return true;
  }

  if (surface === 'framework') {
    try {
      await navigateWithRetry(page, '/frameworks', /frameworks/);
    } catch {
      return false;
    }
    const frameworkLink = page.locator(`a[href="/frameworks/${frameworkId}"]`).first();
    if (await frameworkLink.count()) {
      await frameworkLink.click();
      await page.waitForLoadState('networkidle');
    }
    return true;
  }

  if (surface === 'target') {
    const frameworkOpened = await openResponsiveSurface(page, 'framework', frameworkId);
    if (!frameworkOpened) {
      return false;
    }
    const targetLink = page.locator('a[href*="/targets/"]').first();
    if (await targetLink.count()) {
      await targetLink.click();
      await page.waitForLoadState('networkidle');
    }
    return true;
  }

  if (surface === 'indicators') {
    await navigateWithRetry(page, '/indicators', /indicators/);
    return true;
  }

  await openResponsiveSurface(page, 'indicators', frameworkId);
  const indicatorLink = page.locator('a[href^="/indicators/"]:not([href="/indicators"])').first();
  if (await indicatorLink.count()) {
    await indicatorLink.click();
    await page.waitForLoadState('networkidle');
  }
  return true;
}

test.describe('responsive analytics surfaces', () => {
  const viewports = [
    { name: 'desktop', width: 1440, height: 900, mobile: false },
    { name: 'tablet', width: 1024, height: 768, mobile: false },
    { name: 'mobile', width: 390, height: 844, mobile: true },
  ] as const;

  for (const viewport of viewports) {
    test(`${viewport.name} layouts stay navigable across core routes`, async ({ page }) => {
      test.slow();
      await page.setViewportSize({ width: viewport.width, height: viewport.height });
      await loginAsSeededUser(page, ADMIN_USERNAME, 'can_view_dashboard');

      const examples = await page.evaluate(async () => {
        const [summaryResponse, indicatorResponse] = await Promise.all([
          fetch('/api/dashboard/summary', { credentials: 'include' }),
          fetch('/api/indicators?page=1&page_size=1', { credentials: 'include' })
        ]);
        const summary = summaryResponse.ok ? await summaryResponse.json() : null;
        const indicators = indicatorResponse.ok ? await indicatorResponse.json() : null;
        const targetRow = summary?.published_by_framework_target?.[0];
        return {
          frameworkId: targetRow?.framework_indicator__framework_target__framework__code || 'GBF',
          targetId: targetRow?.framework_indicator__framework_target__code || '1',
          indicatorUuid: indicators?.results?.[0]?.uuid || null
        };
      });

      const surfaces = [
        { key: 'dashboard', expectsContextBar: true, expectsHeaderOverflow: true },
        { key: 'framework', expectsContextBar: true, expectsHeaderOverflow: true },
        { key: 'target', expectsContextBar: true, expectsHeaderOverflow: true },
        { key: 'indicators', expectsContextBar: false, expectsHeaderOverflow: false },
        { key: 'indicator', expectsContextBar: true, expectsHeaderOverflow: false }
      ] as const;

      for (const surface of surfaces) {
        const opened = await openResponsiveSurface(page, surface.key, examples.frameworkId);
        if (!opened) {
          continue;
        }
        await expect(page.locator('body')).not.toContainText('Page not found (404)');
        await expect(page.getByRole('heading').first()).toBeVisible();

        if (viewport.mobile) {
          const navToggle = page.getByRole('button', { name: 'Toggle navigation' });
          if (await navToggle.count()) {
            await expect(navToggle).toBeVisible();
            const sideNav = page.locator('mat-sidenav.side-nav');
            const navOpen = await sideNav
              .evaluate((element) => element.classList.contains('mat-drawer-opened'))
              .catch(() => false);
            if (!navOpen) {
              await navToggle.click();
            }
            await expect(sideNav).toContainText('Indicators');
            await page.keyboard.press('Escape');
            await page.waitForTimeout(150);
          }
        }

        if (viewport.mobile && surface.expectsContextBar) {
          const filterToggle = page.locator('button.filter-toggle').first();
          if (await filterToggle.count()) {
            await expect(filterToggle).toBeVisible();
            await filterToggle.click();
            await expect(page.getByLabel('Report cycle').first()).toBeVisible();
          }
        }

        if (viewport.mobile && surface.expectsHeaderOverflow) {
          const overflowTrigger = page.locator('.action-overflow-trigger').first();
          if (await overflowTrigger.count()) {
            await expect(overflowTrigger).toBeVisible();
          }
        }

        const overflow = await page.evaluate(() => {
          const root = document.documentElement;
          return root.scrollWidth - root.clientWidth;
        });
        expect(overflow).toBeLessThanOrEqual(4);
      }
    });
  }
});
