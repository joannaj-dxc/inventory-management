<template>
  <div class="app">
    <Sidebar />
    <div class="content-column" :class="{ 'sidebar-collapsed': isSidebarCollapsed }">
      <div class="top-bar">
        <FilterBar />
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import { useSidebar } from './composables/useSidebar'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'
import Sidebar from './components/Sidebar.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher,
    Sidebar
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const { isSidebarCollapsed } = useSidebar()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    return {
      t,
      isSidebarCollapsed,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask
    }
  }
}
</script>

<style>
/* Design tokens: colors + spacing scale shared across global classes below.
   Per-view scoped styles (Dashboard.vue etc.) still use raw literals for now -
   that migration is a later stage of the sidebar redesign. */
:root {
  --color-text: #0f172a;
  --color-text-secondary: #64748b;
  --color-border: #e2e8f0;
  --color-bg: #f8fafc;
  --color-accent: #2563eb;
  --color-accent-tint: #eff6ff;
  --color-success: #059669;
  --color-success-tint: #d1fae5;
  --color-warning: #ea580c;
  --color-warning-tint: #fed7aa;
  --color-danger: #dc2626;
  --color-danger-tint: #fecaca;
  --color-info: #2563eb;
  --color-info-tint: #dbeafe;

  --sidebar-width: 250px;
  --sidebar-width-collapsed: 72px;

  --space-1: 0.25rem;
  --space-2: 0.375rem;
  --space-3: 0.5rem;
  --space-4: 0.75rem;
  --space-5: 1rem;
  --space-6: 1.25rem;
  --space-7: 1.5rem;
  --space-8: 3rem;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  min-height: 100vh;
}

/* content-column's margin-left matches Sidebar's width - the sidebar is position:fixed
   (not a flex sibling that stretches), so the content column has to reserve that space
   itself rather than relying on flexbox to lay them out side by side. Both this and
   Sidebar.vue's .sidebar width read the same isSidebarCollapsed ref and transition in
   sync, so the collapse animation never causes a layout jump. */
.content-column {
  flex: 1;
  min-width: 0;
  margin-left: var(--sidebar-width);
  transition: margin-left 0.2s ease;
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.content-column.sidebar-collapsed {
  margin-left: var(--sidebar-width-collapsed);
}

.top-bar {
  background: #ffffff;
  border-bottom: 1px solid var(--color-border);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: var(--space-5);
  padding: var(--space-4) var(--space-7);
  /* FilterBar + LanguageSwitcher + ProfileMenu used to occupy two separate full-width
     rows before the sidebar redesign. Now that they share one row inside a
     content-column that's already 250px narrower (sidebar width), the combined content
     no longer fits at common laptop widths (~1280px and below). Allow wrapping so
     LanguageSwitcher/ProfileMenu drop to a second line instead of overflowing the
     viewport horizontally. */
  flex-wrap: wrap;
  row-gap: var(--space-4);
}

/* FilterBar's root element (.filters-bar) is untouched/scoped in its own component -
   this rule (from App.vue's global styles) makes it fill the remaining top-bar width
   so LanguageSwitcher/ProfileMenu sit flush right, without editing FilterBar.vue itself */
.top-bar > .filters-bar {
  flex: 1;
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: var(--space-7);
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: var(--color-text);
  margin-bottom: var(--space-2);
  letter-spacing: -0.025em;
}

.page-header p {
  color: var(--color-text-secondary);
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--space-6);
  margin-bottom: var(--space-7);
}

.stat-card {
  background: white;
  padding: var(--space-6);
  border-radius: 10px;
  border: 1px solid var(--color-border);
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: var(--color-text-secondary);
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--space-4);
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: var(--color-warning);
}

.stat-card.success .stat-value {
  color: var(--color-success);
}

.stat-card.danger .stat-value {
  color: var(--color-danger);
}

.stat-card.info .stat-value {
  color: var(--color-info);
}

.card {
  background: white;
  border-radius: 10px;
  padding: var(--space-6);
  border: 1px solid var(--color-border);
  margin-bottom: var(--space-6);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-5);
  padding-bottom: var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: var(--color-bg);
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
}

th {
  text-align: left;
  padding: var(--space-3) var(--space-4);
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: var(--color-bg);
}

.badge {
  display: inline-block;
  padding: 0.313rem var(--space-4);
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: var(--color-success-tint);
  color: #065f46;
}

.badge.warning {
  background: var(--color-warning-tint);
  color: #92400e;
}

.badge.danger {
  background: var(--color-danger-tint);
  color: #991b1b;
}

.badge.info {
  background: var(--color-info-tint);
  color: #1e40af;
}

.badge.increasing {
  background: var(--color-success-tint);
  color: #065f46;
}

.badge.decreasing {
  background: var(--color-danger-tint);
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: var(--color-danger-tint);
  color: #991b1b;
}

.badge.medium {
  background: var(--color-warning-tint);
  color: #92400e;
}

.badge.low {
  background: var(--color-info-tint);
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: var(--space-8);
  color: var(--color-text-secondary);
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid var(--color-danger-tint);
  color: #991b1b;
  padding: var(--space-5);
  border-radius: 8px;
  margin: var(--space-5) 0;
  font-size: 0.938rem;
}
</style>
