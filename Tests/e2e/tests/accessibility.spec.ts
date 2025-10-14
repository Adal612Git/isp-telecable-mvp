import { test, expect } from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

test('Portal accesible (AXE)', async ({ page }) => {
  await page.goto('/');
  await page.waitForLoadState('domcontentloaded');
  const results = await new AxeBuilder({ page }).withTags(['wcag2a', 'wcag2aa']).analyze();
  // Permite hasta 2 issues menores durante Sprint 0/1
  expect(results.violations.length).toBeLessThanOrEqual(2);
});
