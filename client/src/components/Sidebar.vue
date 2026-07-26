<template>
  <aside class="sidebar" :class="{ collapsed: isSidebarCollapsed }">
    <div class="brand" v-if="!isSidebarCollapsed">
      <h1>{{ t('nav.companyName') }}</h1>
      <span class="subtitle">{{ t('nav.subtitle') }}</span>
    </div>
    <div class="brand" v-else>
      <div class="brand-mark" :title="t('nav.companyName')">{{ companyInitial }}</div>
    </div>

    <nav class="nav-list">
      <router-link
        to="/"
        class="nav-item"
        :class="{ active: $route.path === '/' }"
        :title="t('nav.overview')"
        :aria-label="t('nav.overview')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="6" height="6" rx="1" />
          <rect x="11" y="3" width="6" height="6" rx="1" />
          <rect x="3" y="11" width="6" height="6" rx="1" />
          <rect x="11" y="11" width="6" height="6" rx="1" />
        </svg>
        <span>{{ t('nav.overview') }}</span>
      </router-link>

      <router-link
        to="/inventory"
        class="nav-item"
        :class="{ active: $route.path === '/inventory' }"
        :title="t('nav.inventory')"
        :aria-label="t('nav.inventory')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 2.5L17 6v8l-7 3.5L3 14V6z" />
          <path d="M3 6l7 3.5L17 6" />
          <path d="M10 9.5v7" />
        </svg>
        <span>{{ t('nav.inventory') }}</span>
      </router-link>

      <router-link
        to="/orders"
        class="nav-item"
        :class="{ active: $route.path === '/orders' }"
        :title="t('nav.orders')"
        :aria-label="t('nav.orders')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2.5 3h2l1.6 9.6a1.5 1.5 0 0 0 1.5 1.4h6.8a1.5 1.5 0 0 0 1.5-1.2l1.1-6.3H5.2" />
          <circle cx="8" cy="16.5" r="1.1" />
          <circle cx="14" cy="16.5" r="1.1" />
        </svg>
        <span>{{ t('nav.orders') }}</span>
      </router-link>

      <router-link
        to="/spending"
        class="nav-item"
        :class="{ active: $route.path === '/spending' }"
        :title="t('nav.finance')"
        :aria-label="t('nav.finance')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2.5" y="6" width="15" height="10" rx="1.5" />
          <path d="M2.5 9.5h15" />
          <rect x="12" y="11.25" width="4" height="2.5" rx="0.5" />
        </svg>
        <span>{{ t('nav.finance') }}</span>
      </router-link>

      <router-link
        to="/demand"
        class="nav-item"
        :class="{ active: $route.path === '/demand' }"
        :title="t('nav.demandForecast')"
        :aria-label="t('nav.demandForecast')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 14l4.5-5 3 3L17 5" />
          <path d="M13 5h4v4" />
        </svg>
        <span>{{ t('nav.demandForecast') }}</span>
      </router-link>

      <router-link
        to="/restocking"
        class="nav-item"
        :class="{ active: $route.path === '/restocking' }"
        :title="t('nav.restocking')"
        :aria-label="t('nav.restocking')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 10a6 6 0 0 1-10.5 4" />
          <path d="M4 10a6 6 0 0 1 10.5-4" />
          <path d="M5.5 17v-3.5H2" />
          <path d="M14.5 3v3.5H18" />
        </svg>
        <span>{{ t('nav.restocking') }}</span>
      </router-link>

      <router-link
        to="/reports"
        class="nav-item"
        :class="{ active: $route.path === '/reports' }"
        :title="t('nav.reports')"
        :aria-label="t('nav.reports')"
      >
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
          <path d="M5 2.5h6l4 4v10a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1v-13a1 1 0 0 1 1-1z" />
          <path d="M11 2.5v4h4" />
          <path d="M6.5 10.5h7" />
          <path d="M6.5 13h7" />
          <path d="M6.5 15.5h4" />
        </svg>
        <span>{{ t('nav.reports') }}</span>
      </router-link>
    </nav>

    <button
      class="sidebar-toggle"
      type="button"
      :title="toggleLabel"
      :aria-label="toggleLabel"
      @click="toggleSidebar"
    >
      <svg
        class="sidebar-toggle-icon"
        :class="{ rotated: isSidebarCollapsed }"
        width="20"
        height="20"
        viewBox="0 0 20 20"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <path d="M12.5 4.5L7 10l5.5 5.5" />
      </svg>
    </button>
  </aside>
</template>

<script>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n'
import { useSidebar } from '../composables/useSidebar'

export default {
  name: 'Sidebar',
  setup() {
    const { t } = useI18n()
    const { isSidebarCollapsed, toggleSidebar } = useSidebar()

    const companyInitial = computed(() => t('nav.companyName').charAt(0))
    const toggleLabel = computed(() =>
      isSidebarCollapsed.value ? t('nav.expandSidebar') : t('nav.collapseSidebar')
    )

    return {
      t,
      isSidebarCollapsed,
      toggleSidebar,
      companyInitial,
      toggleLabel
    }
  }
}
</script>

<style scoped>
/* Fixed positioning (rather than a flex-stretch column) keeps the sidebar
   pinned full-height on the left while the content column scrolls independently */
.sidebar {
  position: fixed;
  top: 0;
  left: 0;
  width: var(--sidebar-width);
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  background: #ffffff;
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.sidebar.collapsed {
  width: var(--sidebar-width-collapsed);
}

.brand {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-6) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.brand h1 {
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.subtitle {
  font-size: 0.813rem;
  color: var(--color-text-secondary);
  font-weight: 400;
}

/* Collapsed brand: single-letter "mark" replaces the name + subtitle so the
   header stays legible at icon-only width, without a separate logo asset */
.sidebar.collapsed .brand {
  align-items: center;
  padding: var(--space-5) var(--space-3);
}

.brand-mark {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: var(--color-accent-tint);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.125rem;
  font-weight: 700;
}

.nav-list {
  display: flex;
  flex-direction: column;
  padding: var(--space-3);
  gap: var(--space-1);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.938rem;
  border-radius: 8px;
  position: relative;
  transition: all 0.2s ease;
}

.nav-item svg {
  flex-shrink: 0;
}

.nav-item:hover {
  color: var(--color-text);
  background: #f1f5f9;
}

.nav-item.active {
  color: var(--color-accent);
  background: var(--color-accent-tint);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--color-accent);
}

/* Collapsed nav: hide labels and center the icons - :title/aria-label on the
   router-link (bound above, next to each visible <span>) keep these
   accessible/discoverable once the <span> text is display:none'd */
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: var(--space-3);
}

.sidebar.collapsed .nav-item span {
  display: none;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  margin: var(--space-3);
  margin-top: auto;
  padding: var(--space-3);
  background: none;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s ease;
}

.sidebar-toggle:hover {
  color: var(--color-text);
  background: #f1f5f9;
  border-color: #cbd5e1;
}

.sidebar-toggle-icon {
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.sidebar-toggle-icon.rotated {
  transform: rotate(180deg);
}
</style>
