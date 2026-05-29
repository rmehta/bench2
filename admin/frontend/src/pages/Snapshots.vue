<script setup>
import { computed, onMounted, ref } from 'vue'
import { Button, ErrorMessage, ListView, LoadingText, Tabs } from 'frappe-ui'

const tabs = [
  { label: 'Benches', dataset: 'benches' },
  { label: 'MariaDB', dataset: 'mariadb' },
]

const activeTab = ref(0)
const allSnapshots = ref([])
const snapshotsEnabled = ref(true)
const loading = ref(false)
const loadError = ref('')
const createError = ref('')
const deletingTag = ref('')
const createLoading = ref(false)

const currentDataset = computed(() => tabs[activeTab.value].dataset)

const columns = [
  { label: 'Snapshot Tag', key: 'tag' },
  { label: 'Created', key: 'formattedDate', width: '180px' },
  { label: 'Used', key: 'formattedSize', width: '100px' },
  { label: '', key: '_delete', width: '80px' },
]

const rows = computed(() =>
  allSnapshots.value
    .filter(snapshot => snapshot.dataset.endsWith(currentDataset.value))
    .map(snapshot => ({
      ...snapshot,
      formattedDate: formatDate(snapshot.created_at),
      formattedSize: formatBytes(snapshot.used_bytes),
    }))
)

function formatDate(isoString) {
  return new Date(isoString).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' })
}

function formatBytes(bytes) {
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(0)} KB`
  if (bytes < 1024 ** 3) return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  return `${(bytes / 1024 ** 3).toFixed(1)} GB`
}

async function loadSnapshots() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetch('/api/volume/snapshots')
    if (!response.ok) throw new Error(await response.text())
    const data = await response.json()
    allSnapshots.value = data.snapshots
    snapshotsEnabled.value = data.snapshots_enabled
  } catch (error) {
    loadError.value = error.message
  } finally {
    loading.value = false
  }
}

async function createSnapshot() {
  createError.value = ''
  createLoading.value = true
  try {
    const response = await fetch('/api/volume/snapshots', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dataset: currentDataset.value }),
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || response.statusText)
    await loadSnapshots()
  } catch (error) {
    createError.value = error.message
  } finally {
    createLoading.value = false
  }
}

async function deleteSnapshot(row) {
  deletingTag.value = row.tag
  loadError.value = ''
  try {
    const response = await fetch(`/api/volume/snapshots/${currentDataset.value}/${row.tag}`, {
      method: 'DELETE',
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || response.statusText)
    await loadSnapshots()
  } catch (error) {
    loadError.value = error.message
  } finally {
    deletingTag.value = ''
  }
}

onMounted(loadSnapshots)
</script>

<template>
  <Tabs :tabs="tabs" v-model="activeTab" @update:modelValue="loadSnapshots">
    <template #tab-panel>
      <div class="pt-4">

        <div class="mb-3 flex items-center justify-between gap-3">
          <div class="flex-1 text-sm">
            <ErrorMessage v-if="createError" :message="createError" />
            <span v-else-if="!snapshotsEnabled" class="text-ink-gray-4">
              Snapshots are disabled — set <code>volume.snapshots.enabled = true</code> in bench.toml to create snapshots.
            </span>
            <span v-else class="text-ink-gray-5">
              {{ rows.length }} snapshot{{ rows.length !== 1 ? 's' : '' }}
            </span>
          </div>
          <Button variant="subtle" :loading="createLoading" @click="createSnapshot">
            Create Snapshot
          </Button>
        </div>

        <ErrorMessage v-if="loadError" :message="loadError" />
        <LoadingText v-else-if="loading" />
        <ListView
          v-else
          :columns="columns"
          :rows="rows"
          row-key="tag"
          :options="{ selectable: false, showTooltip: false }"
        >
          <template #cell="{ column, row }">
            <Button
              v-if="column.key === '_delete'"
              variant="ghost"
              theme="red"
              size="sm"
              :loading="deletingTag === row.tag"
              @click="deleteSnapshot(row)"
            >
              Delete
            </Button>
            <span v-else class="block truncate">{{ row[column.key] }}</span>
          </template>
        </ListView>

      </div>
    </template>
  </Tabs>
</template>
