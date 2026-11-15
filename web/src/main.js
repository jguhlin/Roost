import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

// Dark mode: the .dark class drives Tailwind's dark: variants (see
// app.css @custom-variant). Synced from the system preference so behaviour
// matches the old media-query variant — and stays deterministic for
// tooling (axe resolves class-based dark backgrounds correctly).
const darkMq = window.matchMedia('(prefers-color-scheme: dark)')
const applyColorScheme = () =>
  document.documentElement.classList.toggle('dark', darkMq.matches)
applyColorScheme()
darkMq.addEventListener('change', applyColorScheme)

const app = mount(App, {
  target: document.getElementById('app'),
})

export default app

// Matomo — production-only (gated by hostname + env vars inside)
import { initMatomo } from './lib/analytics.js'
initMatomo()
