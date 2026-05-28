<script setup>
import { h, ref, computed, onMounted } from 'vue'
import { ListView, TabButtons, LoadingText, ErrorMessage } from 'frappe-ui'
import StatusBadge from '../components/StatusBadge.vue'

const tasks = ref([])
const loading = ref(true)
const error = ref('')
const statusFilter = ref('all')

const filterButtons = ['all', 'running', 'success', 'failed', 'killed'].map(s => ({
  label: s.charAt(0).toUpperCase() + s.slice(1),
  value: s,
}))

const TASK_STATUS_BADGE = {
  running: 'badge-running',
  success: 'badge-success',
  failed:  'badge-error',
  stopped: 'badge-error',
  killed:  'badge-neutral',
}

const columns = [
  { label: 'Command', key: 'command', width: '140px' },
  { label: 'Context', key: '_args' },
  {
    label: 'Status', key: 'status', width: '90px',
    prefix: ({ row }) => h(StatusBadge, {
      label: row.status,
      variant: TASK_STATUS_BADGE[row.status] || 'badge-neutral',
    }),
    getLabel: () => '',
  },
  { label: 'Started', key: '_started', width: '150px' },
  { label: 'Duration', key: '_duration', width: '80px' },
]

function fmtArgs(args) {
  if (!args || !Object.keys(args).length) return ''
  const parts = []
  if (args.site) parts.push(args.site)
  if (args.app) parts.push(args.app)
  if (args.name) parts.push(args.name)
  if (args.repo) parts.push(args.repo)
  return parts.join(' · ') || Object.values(args).join(' · ')
}

const rows = computed(() =>
  tasks.value.map(t => ({
    ...t,
    _args: fmtArgs(t.args),
    _started: fmtDate(t.started_at),
    _duration: fmtDuration(t.duration_seconds),
  }))
)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const params = statusFilter.value !== 'all' ? `?status=${statusFilter.value}` : ''
    const res = await fetch(`/api/tasks/${params}`)
    tasks.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function fmtDuration(s) {
  if (s == null) return '—'
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  return `${Math.round(s / 3600)}h`
}

function onFilterChange(val) {
  statusFilter.value = val
  load()
}

onMounted(load)
</script>

<template>
  <div class="flex flex-col gap-4">
    <TabButtons :buttons="filterButtons" :modelValue="statusFilter" @update:modelValue="onFilterChange" />

    <LoadingText v-if="loading" />
    <ErrorMessage v-else-if="error" :message="error" />

    <div v-else>
      <ListView
        :columns="columns"
        :rows="rows"
        row-key="task_id"
        :options="{
          getRowRoute: (row) => `/tasks/${row.task_id}`,
          selectable: false,
          showTooltip: false,
        }"
      />
    </div>
  </div>
</template>
