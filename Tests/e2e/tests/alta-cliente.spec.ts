import { test, expect } from '@playwright/test';

test('Flujo Nuevo Cliente: alta→contrato→facturación', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  await page.fill('#nombre', 'E2E Cliente');
  await page.fill('#rfc', 'AAA010101AAA');
  await page.fill('#email', 'e2e@example.com');
  await page.fill('#telefono', '5555555555');
  await page.fill('#calle', 'Calle');
  await page.fill('#numero', '1');
  await page.fill('#colonia', 'Centro');
  await page.fill('#cp', '01000');
  await page.fill('#ciudad', 'CDMX');
  await page.fill('#estado', 'CDMX');
  // <option> elements are not "visible" for Playwright; wait for attachment
  await page.waitForSelector('#zona option', { state: 'attached', timeout: 30000 });
  await page.selectOption('#zona', { label: 'NORTE' });
  // plan is populated dynamically; wait and choose first option
  await page.waitForSelector('#plan option', { state: 'attached', timeout: 30000 });
  const firstPlan = await page.locator('#plan option').first().getAttribute('value');
  if (firstPlan) await page.selectOption('#plan', firstPlan);
  await page.click('button[type="submit"]');
  await expect(page.locator('#result')).toContainText('cliente');
  await page.screenshot({ path: '/reports/screenshots/portal_alta.png' });
});
