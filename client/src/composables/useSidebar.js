import { ref } from 'vue'

const STORAGE_KEY = 'sidebar-collapsed'
// 1024px matches the width already manually verified during the redesign's
// responsiveness check - this is the app's first JS-driven breakpoint.
const COLLAPSE_BREAKPOINT = 1024

const storedValue = localStorage.getItem(STORAGE_KEY)
const hasStoredPreference = ref(storedValue !== null)

const mediaQuery = window.matchMedia(`(max-width: ${COLLAPSE_BREAKPOINT}px)`)

const isSidebarCollapsed = ref(
  hasStoredPreference.value ? storedValue === 'true' : mediaQuery.matches
)

// Keep following the viewport default on resize only until the user makes an
// explicit choice - once they toggle, their choice wins permanently (mirrors
// useI18n.js: read once on init, only written on explicit user action).
mediaQuery.addEventListener('change', (event) => {
  if (!hasStoredPreference.value) {
    isSidebarCollapsed.value = event.matches
  }
})

export function useSidebar() {
  const toggleSidebar = () => {
    isSidebarCollapsed.value = !isSidebarCollapsed.value
    hasStoredPreference.value = true
    localStorage.setItem(STORAGE_KEY, String(isSidebarCollapsed.value))
  }

  return { isSidebarCollapsed, toggleSidebar }
}
