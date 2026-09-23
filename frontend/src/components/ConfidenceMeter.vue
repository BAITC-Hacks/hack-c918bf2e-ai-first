<template>
  <span class="sv-col meter">
    <span class="tabular value">{{ percent(value) }} <span class="level">{{ confidenceLevel(value) }}</span></span>
    <span class="track"><span :style="{ width: `${Math.round(value * 100)}%` }" /></span>
    <q-tooltip :delay="400">Уверенность ИИ-агента в выводе: ≥ 85% — высокая, 70–84% — средняя, ниже 70% — низкая</q-tooltip>
  </span>
</template>

<script setup lang="ts">
import { confidenceLevel, percent } from '@/utils/labels'

defineProps<{ value: number }>()
</script>

<style scoped>
.meter { gap: 4px; }
.value { font-size: 13px; color: var(--sv-text); white-space: nowrap; }
.level { font-size: 11px; color: var(--sv-muted); }
.track { height: 4px; width: 72px; background: var(--sv-divider); border-radius: 2px; overflow: hidden; }
.track span { display: block; height: 100%; background: var(--sv-muted); }
</style>
