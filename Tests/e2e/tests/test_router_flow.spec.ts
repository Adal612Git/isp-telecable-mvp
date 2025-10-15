import { expect, test } from '@playwright/test';

function randomRFC() {
  const base = Math.random().toString(36).slice(2, 8).toUpperCase();
  return `AAA${base}`.padEnd(13, 'X');
}

test.describe('Flujo de router simulado', () => {
  test('permite registrar cliente y controlar router', async ({ page }) => {
    await page.goto('/cliente');

    // Prellenar datos demo para acelerar la captura.
    await page.getByRole('button', { name: 'Autocompletar demo' }).click();

    const clienteNombre = `QA Demo ${Date.now()}`;
    await page.getByPlaceholder('Nombre del titular').fill(clienteNombre);
    await page.getByPlaceholder('RFC').fill(randomRFC());
    await page.getByPlaceholder('correo@ejemplo.com').fill(`qa+${Date.now()}@demo.test`);

    await page.getByRole('button', { name: 'Registrar cliente' }).click();

    await expect(page.getByText(clienteNombre, { exact: false })).toBeVisible({ timeout: 5000 });
    await expect(page.getByText('Estado en tiempo real')).toBeVisible();
    await expect(page.getByText('Encendido')).toBeVisible();

    // Apagar router.
    await page.getByRole('button', { name: 'Apagar' }).click();
    await expect(page.getByText('Apagado')).toBeVisible({ timeout: 4000 });

    // Volver a encender.
    await page.getByRole('button', { name: 'Encender' }).click();
    await expect(page.getByText('Encendido')).toBeVisible({ timeout: 4000 });

    // Verifica que exista bitácora
    await expect(page.getByText('Bitácora')).toBeVisible();
  });
});
