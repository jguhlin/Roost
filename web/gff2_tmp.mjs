import { chromium } from '@playwright/test';
import { createServer } from 'vite';
const server = await createServer({ root: process.cwd(), server: { port: 5185 } });
await server.listen();
const browser = await chromium.launch();
const page = await browser.newPage();
const errors = [];
page.on('pageerror', e => errors.push(e.message.slice(0, 200)]);
