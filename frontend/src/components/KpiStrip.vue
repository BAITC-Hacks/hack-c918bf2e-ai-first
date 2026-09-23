<template>
  <div class="kpi-grid">
    <div class="kpi panel">
      <div class="kpi-label">Функций до → после</div>
      <div class="kpi-value tabular">
        {{ summary.before_functions }} <span class="muted kpi-arrow">→</span> {{ summary.after_functions }}
      </div>
      <div class="text-caption muted tabular">
        {{ delta >= 0 ? '+' : '' }}{{ delta }} · без изменений {{ summary.unchanged }}
      </div>
    </div>
    <button
      v-for="card in cards"
      :key="card.key"
      type="button"
      class="kpi panel kpi--action"
      :class="[{ 'kpi--active': active === card.type }, `border-${card.color}`]"
      :aria-pressed="active === card.type"
      @click="$emit('select', active === card.type ? null : card.type)"
    >
      <div class="kpi-label row items-center no-wrap">
        <span class="sev-dot q-mr-xs" :class="`bg-${card.color}`" />{{ card.label }}
      </div>
      <div class="kpi-value tabular" :class="card.value > 0 ? `text-${card.color}` : ''">{{ card.value }}</div>
      <div class="text-caption muted">{{ card.hint }}</div>
    </button>
    <div class="kpi panel kpi--risk">
      <div class="kpi-label row items-center no-wrap">
        <q-icon name="warning" size="16px" class="q-mr-xs" />Высокий риск
      </div>
      <div class="kpi-value tabular">{{ summary.high_risk }}</div>
      <div class="text-caption">требуют решения до утверждения</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisSummary, FindingType } from '@/api/types'
import { TYPE_META } from '@/utils/labels'

const props = defineProps<{ summary: AnalysisSummary; active: FindingType | null }>()
defineEmits<{ select: [type: FindingType | null] }>()

const delta = computed(() => props.summary.after_functions - props.summary.before_functions)

const cards = computed(() => {
  const s = props.summary
  const rows: Array<{ key: string; type: FindingType; value: number; hint: string }> = [
    { key: 'lost', type: 'lost', value: s.lost, hint: 'не закреплены' },
    { key: 'duplicates', type: 'duplicate', value: s.duplicates, hint: 'закреплены дважды' },
    { key: 'changed', type: 'changed', value: s.changed, hint: 'по содержанию' },
    { key: 'moved', type: 'moved', value: s.moved, hint: 'в другое подразделение' },
    { key: 'added', type: 'added', value: s.added, hint: 'новые функции' },
  ]
  return rows.map((r) => ({ ...r, label: TYPE_META[r.type].label, color: TYPE_META[r.type].color }))
})
</script>

<style scoped lang="scss">
.kpi-grid { display: grid; gap: 12px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
@media (min-width: 600px) { .kpi-grid { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
@media (min-width: 1280px) { .kpi-grid { grid-template-columns: 1.3fr repeat(5, minmax(0, 1fr)) 1.2fr; } }
.kpi { padding: 14px 16px; text-align: left; font: inherit; color: inherit; }
.kpi-label { font-size: 13px; color: var(--c-muted); font-weight: 500; }
.kpi-value { font-size: 28px; font-weight: 600; line-height: 1.2; margin: 4px 0 2px; }
.kpi-arrow { font-size: 20px; }
.kpi--action {
  cursor: pointer; border-top-width: 3px; transition: box-shadow .15s, background .15s;
  &:hover { box-shadow: 0 2px 8px rgba(15, 42, 68, .08); }
  &:focus-visible { outline: 2px solid $primary; outline-offset: 2px; }
}
.kpi--active { background: #eef4fb; box-shadow: inset 0 0 0 1px $primary; }
@media (max-width: 599px) { .kpi--risk { grid-column: span 2; } }
.kpi--risk { background: #fdecec; border-color: #f2c4c4; color: #8e1c1c; .kpi-label { color: #8e1c1c; } }
</style>
