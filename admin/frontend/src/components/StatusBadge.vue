<script setup>
import { computed } from 'vue'
import { Badge } from 'frappe-ui'

const props = defineProps({
  variant: { type: String, default: 'badge-neutral' },
  label: { type: String, default: '' },
})

// semantic variants → frappe-ui Badge theme
const VARIANT_THEME = {
  'badge-success': 'green',
  'badge-warning': 'orange',
  'badge-error':   'red',
  'badge-neutral': 'gray',
  'badge-running': 'blue',
}

const theme = computed(() => VARIANT_THEME[props.variant] ?? 'gray')
</script>

<template>
  <Badge :theme="theme" variant="subtle" size="sm" :label="label">
    <template v-if="variant === 'badge-running'" #prefix>
      <span class="pulse-dot"></span>
    </template>
  </Badge>
</template>
