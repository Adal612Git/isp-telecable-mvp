import { defineConfig, devices } from '@playwright/test';

const portalPort = process.env.HOST_PORTAL_CLIENTE_PORT || '5173';

export default defineConfig({
  testDir: './tests',
  timeout: 60000,
  reporter: [['list'], ['junit', { outputFile: '../reports/junit-e2e.xml' }], ['html', { outputFolder: '../reports/html/e2e' }]],
  use: {
    baseURL: `http://localhost:${portalPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
