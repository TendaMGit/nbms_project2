import { expect, test, type Page } from '@playwright/test';

const E2E_USERNAME = process.env.PLAYWRIGHT_USERNAME || '';
const E2E_PASSWORD = process.env.PLAYWRIGHT_PASSWORD || '';
async function loginThroughDjango(page: Page, username: string, password: string) {
  await page.goto('/account/login/?next=/dashboard');
  await page.fill('input[name="auth-username"]', username);
  await page.fill('input[name="auth-password"]', password);
  await Promise.all([page.waitForURL(/\/dashboard$/), page.click('button[type="submit"]:has-text("Next")')]);
  await page.waitForLoadState('networkidle');
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
  test.skip(!E2E_USERNAME || !E2E_PASSWORD, 'Set PLAYWRIGHT_USERNAME and PLAYWRIGHT_PASSWORD for auth smoke');

  await loginThroughDjango(page, E2E_USERNAME, E2E_PASSWORD);
  await expect(page.getByRole('link', { name: 'Logout' })).toBeVisible();

  await page.goto('/dashboard');
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();

  await page.getByRole('link', { name: 'Indicator Explorer' }).click();
  await expect(page).toHaveURL(/indicators/);

  await page.getByRole('link', { name: 'Spatial Viewer' }).click();
  await expect(page).toHaveURL(/map/);

  await page.getByRole('link', { name: 'NR7 Builder' }).click();
  await expect(page).toHaveURL(/nr7-builder/);

  await page.getByRole('link', { name: 'MEA Packs' }).click();
  await expect(page).toHaveURL(/template-packs/);
});
