import { ref } from 'vue'
import { Dark } from 'quasar'

const KEY = 'sverka-theme'
export const theme = ref<'light' | 'dark'>('light')

function apply() {
  document.documentElement.dataset.theme = theme.value
  Dark.set(theme.value === 'dark')
}

export function initTheme() {
  try {
    if (localStorage.getItem(KEY) === 'dark') theme.value = 'dark'
  } catch {
    // Storage blocked: stay on the default light theme.
  }
  apply()
}

export function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
  try {
    localStorage.setItem(KEY, theme.value)
  } catch {
    // Ignore: preference simply will not persist.
  }
  apply()
}
