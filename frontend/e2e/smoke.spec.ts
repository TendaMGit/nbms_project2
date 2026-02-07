import { expect, test } from '@playwright/test';

test('nbms shell loads main workspaces', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('National Biodiversity Monitoring System')).toBeVisible();

  await page.getByRole('link', { name: 'Dashboard' }).click();
  await expect(page).toHaveURL(/dashboard/);

  await page.getByRole('link', { name: 'Indicator Explorer' }).click();
  await expect(page).toHaveURL(/indicators/);

  await page.getByRole('link', { name: 'Spatial Viewer' }).click();
  await expect(page).toHaveURL(/map/);

  await page.getByRole('link', { name: 'NR7 Builder' }).click();
  await expect(page).toHaveURL(/nr7-builder/);

  await page.getByRole('link', { name: 'MEA Packs' }).click();
  await expect(page).toHaveURL(/template-packs/);
});
