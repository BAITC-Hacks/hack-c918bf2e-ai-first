<template>
  <span
    class="type-label"
    :class="{ 'sv-chip': filled }"
    :style="{ color: meta.fg, background: filled ? meta.bg : undefined }"
  >
    <q-icon :name="meta.icon" :size="filled ? '15px' : '18px'" />{{ meta.label }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { FindingType } from '@/api/types'
import { TYPE_META } from '@/utils/labels'

const props = defineProps<{ type: FindingType; filled?: boolean }>()
const meta = computed(() => TYPE_META[props.type])
</script>

<style scoped>
.type-label { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 500; white-space: nowrap; }
</style>
