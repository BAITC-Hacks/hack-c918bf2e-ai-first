<template>
  <section aria-label="Сводка" class="sv-card summary">
    <div class="cell risk-cell" :class="{ 'risk-cell--hot': s.high_risk > 0 }">
      <span class="sv-overline sv-overline--muted">Высокий риск</span>
      <div class="row items-center no-wrap" style="gap: 10px">
        <q-icon :name="s.high_risk ? 'error' : 'check_circle'" size="30px" :style="{ color: riskFg }" />
        <span class="kpi-xl tabular" :style="{ color: riskFg }">{{ s.high_risk }}</span>
      </div>
      <span class="note">{{ s.high_risk ? 'отклонения требуют проверки до утверждения структуры' : 'Отклонений высокого риска не выявлено' }}</span>
      <q-btn
        v-if="s.high_risk"
        flat
        no-caps
        class="sv-btn sv-btn--ghost self-start show-high no-print"
        icon-right="arrow_downward"
        label="Показать в таблице"
        @click="$emit('showHigh')"
      />
    </div>

    <div class="cell">
      <span class="sv-overline sv-overline--muted">Баланс функций</span>
      <div class="row items-end no-wrap tabular" style="gap: 14px">
        <div class="sv-col"><span class="sv-meta">до</span><span class="kpi-l">{{ s.before_functions }}</span></div>
        <q-icon name="arrow_forward" size="24px" style="color: var(--sv-icon-muted); margin-bottom: 6px" />
        <div class="sv-col"><span class="sv-meta">после</span><span class="kpi-l">{{ s.after_functions }}</span></div>
      </div>
      <span class="note">{{ s.unchanged }} из {{ s.before_functions }} сохранены без изменений</span>
    </div>

    <div class="cell breakdown-cell">
      <div class="row items-baseline" style="gap: 8px">
        <span class="sv-overline sv-overline--muted">Функциональные отклонения</span>
        <span class="sv-small sv-muted tabular">{{ total }} {{ pluralize(total, FINDINGS_WORD) }}</span>
      </div>
      <div class="breakdown" role="group" aria-label="Фильтр по типу отклонения">
        <button
          v-for="k in cells"
          :key="k.type"
          type="button"
          class="bd-cell"
          :aria-pressed="active === k.type"
          @click="$emit('toggleType', k.type)"
        >
          <span class="bd-label" :style="{ color: TYPE_META[k.type].fg }">
            <q-icon :name="TYPE_META[k.type].icon" size="16px" />{{ TYPE_META[k.type].label }}
          </span>
          <span class="kpi-m tabular">{{ k.count }}</span>
        </button>
      </div>
      <div class="bar" aria-hidden="true">
        <span v-for="k in cells" v-show="k.count" :key="k.type" :style="{ flex: k.count, background: TYPE_META[k.type].fg }" :title="`${TYPE_META[k.type].label}: ${k.count}`" />
        <span v-show="s.unchanged" :style="{ flex: s.unchanged, background: 'var(--sv-border)' }" :title="`Без изменений: ${s.unchanged}`" />
      </div>
      <span class="sv-meta">Серым — {{ s.unchanged }} {{ pluralize(s.unchanged, FUNCS_WORD) }} без изменений.</span>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisSummary, FindingType } from '@/api/types'
import { FINDINGS_WORD, FUNCS_WORD, TYPE_META, pluralize } from '@/utils/labels'

const props = defineProps<{ summary: AnalysisSummary; active: FindingType | null }>()
defineEmits<{ showHigh: []; toggleType: [type: FindingType] }>()

const s = computed(() => props.summary)
const riskFg = computed(() => (s.value.high_risk ? 'var(--sv-high)' : 'var(--sv-low)'))
const cells = computed(() => [
  { type: 'lost' as const, count: s.value.lost },
  { type: 'duplicate' as const, count: s.value.duplicates },
  { type: 'changed' as const, count: s.value.changed },
  { type: 'moved' as const, count: s.value.moved },
  { type: 'added' as const, count: s.value.added },
])
const total = computed(() => cells.value.reduce((sum, k) => sum + k.count, 0))
</script>

<style scoped lang="scss">
.summary { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); overflow: hidden; }
@media (min-width: 1440px) { .summary { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(0, 2fr); } }
.cell { padding: 18px 20px; display: flex; flex-direction: column; gap: 6px; border-right: 1px solid var(--sv-divider); min-width: 0; }
.breakdown-cell { gap: 12px; border-right: 0; grid-column: span 2; border-top: 1px solid var(--sv-divider); }
@media (min-width: 1440px) { .breakdown-cell { grid-column: auto; border-top: 0; } }
.risk-cell--hot { background: var(--sv-high-row); }
.kpi-xl { font-size: 48px; line-height: 1; font-weight: 500; }
.kpi-l { font-size: 40px; line-height: 1; font-weight: 500; }
.kpi-m { font-size: 24px; line-height: 1; font-weight: 500; }
.note { font-size: 13px; line-height: 1.45; color: var(--sv-text-2); }
.show-high.q-btn { color: var(--sv-high); padding-left: 0; }
.breakdown { display: grid; grid-template-columns: repeat(auto-fit, minmax(104px, 1fr)); gap: 6px; }
.bd-cell {
  text-align: left; background: var(--sv-surface); border: 1px solid var(--sv-divider); border-radius: 8px; padding: 8px 10px;
  cursor: pointer; display: flex; flex-direction: column; gap: 4px; font: inherit; color: var(--sv-text);
  transition: border-color .12s ease-out;
  &:hover { border-color: var(--sv-accent-line); }
  &[aria-pressed='true'] { border-color: var(--sv-accent); background: var(--sv-accent-tint); }
}
.bd-label { display: flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 500; white-space: nowrap; }
.bar { display: flex; height: 6px; border-radius: 3px; overflow: hidden; gap: 2px; }
@media (max-width: 599px) {
  .summary { grid-template-columns: 1fr 1fr; }
  .cell { padding: 14px; }
  .kpi-xl { font-size: 40px; }
  .kpi-l { font-size: 30px; }
  .breakdown { display: flex; overflow-x: auto; padding-bottom: 2px; }
  .bd-cell { flex: none; flex-direction: row; align-items: center; gap: 8px; border-radius: 16px; padding: 6px 12px; min-height: 44px; }
  .kpi-m { font-size: 16px; }
}
</style>
