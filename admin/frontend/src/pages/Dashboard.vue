<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { Badge, Card, LoadingText, ErrorMessage, Progress, AxisChart, Button } from 'frappe-ui'

const router = useRouter()

const data = ref(null)
const loading = ref(true)
const error = ref('')

async function load() {
  try {
    const res = await fetch('/api/dashboard')
    if (!res.ok) throw new Error(`${res.status}`)
    data.value = await res.json()
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

const MAX_HISTORY = 60
const stats = ref(null)
const history = ref([])

async function loadStats() {
  try {
    const res = await fetch('/api/stats')
    if (!res.ok) return
    const s = await res.json()
    stats.value = s
    history.value = [
      ...history.value.slice(-(MAX_HISTORY - 1)),
      { time: new Date(), CPU: s.cpu_percent, Memory: s.memory_percent },
    ]
  } catch {}
}

function formatBytes(bytes) {
  if (bytes < 1024 ** 2) return (bytes / 1024).toFixed(0) + ' KB'
  if (bytes < 1024 ** 3) return (bytes / 1024 ** 2).toFixed(1) + ' MB'
  return (bytes / 1024 ** 3).toFixed(1) + ' GB'
}

function datasetLabel(name) {
  return name.split('/').pop()
}

function datasetPercent(dataset) {
  return dataset.quota_bytes ? (dataset.used_bytes / dataset.quota_bytes) * 100 : 0
}

const POOL_HEALTH_THEME = { ONLINE: 'green', DEGRADED: 'yellow' }

function poolHealthTheme(health) {
  return POOL_HEALTH_THEME[health] ?? 'red'
}

const chartConfig = computed(() => ({
  title: 'CPU & Memory',
  data: history.value,
  xAxis: { key: 'time', type: 'time', timeGrain: 'second' },
  yAxis: { yMin: 0, yMax: 100, echartOptions: { name: '' } },
  series: [
    { name: 'CPU', type: 'area' },
    { name: 'Memory', type: 'area' },
  ],
}))

const taskLoading = ref('')
const taskError = ref('')

async function runTask(command) {
  try {
    const res = await fetch('/api/tasks/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ command }),
    })
    const d = await res.json()
    if (d.ok) router.push(`/tasks/${d.task_id}`)
    else taskError.value = d.error
  } catch (e) {
    taskError.value = e.message
  } finally {
    taskLoading.value = ''
  }
}

async function runUpdate() {
  taskError.value = ''
  taskLoading.value = 'update'
  await runTask('update')
}

async function setupNginx() {
  taskError.value = ''
  taskLoading.value = 'setup-nginx'
  await runTask('setup-nginx')
}

async function setupProduction() {
  taskError.value = ''
  taskLoading.value = 'setup-production'
  await runTask('setup-production')
}

let dashTimer, statsTimer

onMounted(() => {
  load()
  loadStats()
  dashTimer = setInterval(load, 10000)
  statsTimer = setInterval(loadStats, 3000)
})
onUnmounted(() => {
  clearInterval(dashTimer)
  clearInterval(statsTimer)
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <LoadingText v-if="loading" />
    <ErrorMessage v-else-if="error" :message="error" />

    <template v-else-if="data">
      <div class="flex items-center justify-between">
        <h2 class="text-base font-medium text-ink-gray-7">{{ data.summary?.name ?? 'Bench' }}</h2>
        <div class="flex items-center gap-2">
          <ErrorMessage :message="taskError" />
          <Button variant="outline" :loading="taskLoading === 'setup-nginx'" @click="setupNginx">Setup Nginx</Button>
          <Button variant="outline" :loading="taskLoading === 'setup-production'" @click="setupProduction">Setup Production</Button>
          <Button variant="outline" :loading="taskLoading === 'update'" @click="runUpdate">Update Bench</Button>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4 md:grid-cols-4">
        <button class="text-left" @click="router.push('/apps')">
          <Card :title="`${data.cloned_count} / ${data.apps.length}`" subtitle="Apps cloned" />
        </button>
        <button class="text-left" @click="router.push('/sites')">
          <Card :title="`${data.online_count} / ${data.sites.length}`" subtitle="Sites online" />
        </button>
        <button class="text-left" @click="router.push('/processes')">
          <Card :title="`${data.running_count} / ${data.processes.length}`" subtitle="Processes running" />
        </button>
        <button class="text-left" @click="router.push('/tasks')">
          <Card :title="String(data.recent_tasks.length)" subtitle="Recent tasks" />
        </button>
      </div>

      <Card v-if="stats" title="Server Stats">
        <template #actions>
          <span class="flex items-center gap-1.5 text-xs text-ink-gray-4">
            <span class="h-2 w-2 animate-pulse rounded-full bg-green-500" />
            Live
          </span>
        </template>

        <div class="flex flex-col gap-6">
          <div class="grid grid-cols-3 gap-6">
            <div>
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium text-ink-gray-7">CPU</span>
                <span class="text-sm font-semibold text-ink-gray-9">{{ stats.cpu_percent.toFixed(1) }}%</span>
              </div>
              <Progress :value="stats.cpu_percent" size="md" />
            </div>

            <div>
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium text-ink-gray-7">Memory</span>
                <span class="text-sm text-ink-gray-5">{{ formatBytes(stats.memory_used) }} / {{ formatBytes(stats.memory_total) }}</span>
              </div>
              <Progress :value="stats.memory_percent" size="md" />
            </div>

            <div v-if="stats.volume?.enabled">
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium text-ink-gray-7">ZFS Pool</span>
                <Badge :label="stats.volume.pool_health" :theme="poolHealthTheme(stats.volume.pool_health)" />
              </div>
              <p class="font-mono text-xs text-ink-gray-4">{{ stats.volume.pool }}</p>
            </div>
            <div v-else>
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium text-ink-gray-7">Disk</span>
                <span class="text-sm text-ink-gray-5">{{ formatBytes(stats.disk_used) }} / {{ formatBytes(stats.disk_total) }}</span>
              </div>
              <Progress :value="stats.disk_percent" size="md" />
            </div>
          </div>

          <div v-if="stats.volume?.enabled" class="grid grid-cols-3 gap-6">
            <div v-for="dataset in stats.volume.datasets" :key="dataset.name">
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium capitalize text-ink-gray-7">{{ datasetLabel(dataset.name) }}</span>
                <span class="text-sm text-ink-gray-5">{{ formatBytes(dataset.used_bytes) }} / {{ formatBytes(dataset.quota_bytes) }}</span>
              </div>
              <Progress :value="datasetPercent(dataset)" size="md" />
              <p class="mt-1 text-xs text-ink-gray-4">
                {{ formatBytes(dataset.available_bytes) }} available · {{ formatBytes(dataset.reservation_bytes) }} reserved
              </p>
            </div>
            <div>
              <div class="mb-2 flex items-baseline justify-between">
                <span class="text-sm font-medium text-ink-gray-7">Root Disk</span>
                <span class="text-sm text-ink-gray-5">{{ formatBytes(stats.disk_used) }} / {{ formatBytes(stats.disk_total) }}</span>
              </div>
              <Progress :value="stats.disk_percent" size="md" />
            </div>
          </div>

          <AxisChart v-if="history.length > 1" :config="chartConfig" />
        </div>
      </Card>
    </template>
  </div>
</template>
