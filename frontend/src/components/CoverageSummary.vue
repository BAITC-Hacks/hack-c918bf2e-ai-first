<template>
  <section class="sv-card coverage sv-col" :class="`coverage--${state.kind}`" aria-labelledby="coverage-h">
    <div class="row items-center head">
      <q-icon :name="icon" size="22px" class="head-icon" />
      <h2 id="coverage-h" class="title">Охват обработки</h2>
      <span class="sv-chip kind">{{ kindLabel }}</span>
      <q-space />
      <q-btn
        v-if="state.kind === 'incomplete' && hasRegistry"
        flat
        no-caps
        class="sv-btn sv-btn--secondary no-print"
        icon="filter_list"
        label="Показать требующие проверки"
        @click="$emit('showReview')"
      />
    </div>

    <p class="headline">{{ state.headline }}</p>

    <div v-if="state.kind !== 'missing'" class="metrics">
      <div class="metric">
        <span class="sv-meta">Фрагменты рассмотрены</span>
        <b class="tabular">{{ state.reviewedFragments }} / {{ state.totalFragments }}</b>
      </div>
      <div class="metric" :class="{ 'metric--warn': state.unresolvedFragments > 0 }">
        <span class="sv-meta">Фрагменты без решения</span>
        <b class="tabular">{{ state.unresolvedFragments }}</b>
      </div>
      <div class="metric" :class="{ 'metric--warn': state.needsReviewMappings > 0 }">
        <span class="sv-meta">Сопоставления требуют проверки</span>
        <b class="tabular">{{ state.needsReviewMappings }}</b>
      </div>
      <div class="metric">
        <span class="sv-meta">Функции ДО с найденной парой</span>
        <b class="tabular">{{ state.matchedBeforeFunctions }} / {{ state.beforeFunctions }}</b>
      </div>
    </div>

    <ul class="notes sv-small sv-text-2">
      <li>Статус «Обработка завершена» означает, что pipeline закончил работу, а не что все функции проверены.</li>
      <li>{{ COVERAGE_DISCLAIMER }}</li>
      <li v-if="state.kind === 'missing'">Без реестра нельзя оценить, какие фрагменты документов остались без решения.</li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis } from '@/api/types'
import { COVERAGE_DISCLAIMER, coverageState } from '@/utils/coverage'

const props = defineProps<{ analysis: Analysis }>()
defineEmits<{ showReview: [] }>()

const state = computed(() => coverageState(props.analysis))
const hasRegistry = computed(() => !!props.analysis.function_registry)
const icon = computed(() => ({ complete: 'task_alt', incomplete: 'report_problem', missing: 'help_outline' })[state.value.kind])
const kindLabel = computed(() => ({ complete: 'Все фрагменты рассмотрены', incomplete: 'Неполный', missing: 'Неизвестен' })[state.value.kind])
</script>

<style scoped lang="scss">
.coverage { padding: 16px 20px; gap: 10px; }
.coverage--incomplete { border-color: var(--sv-medium-border); background: var(--sv-medium-bg); }
.head { gap: 8px 10px; flex-wrap: wrap; }
.title { font-size: 16px; line-height: 1.3; font-weight: 500; letter-spacing: normal; }
.head-icon { color: var(--sv-muted); }
.coverage--incomplete .head-icon { color: var(--sv-medium); }
.coverage--complete .head-icon { color: var(--sv-low); }
.kind { border-color: var(--sv-border); background: var(--sv-surface); color: var(--sv-text-2); }
.coverage--incomplete .kind { border-color: var(--sv-medium-border); color: var(--sv-medium); }
.headline { margin: 0; font-size: 15px; font-weight: 500; }
.coverage--incomplete .headline { color: var(--sv-medium-text); }
.metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.metric { display: flex; flex-direction: column; gap: 2px; padding: 8px 12px; border: 1px solid var(--sv-divider); border-radius: 8px; background: var(--sv-surface);
  b { font-size: 20px; font-weight: 500; } }
.metric--warn { border-color: var(--sv-medium-border); b { color: var(--sv-medium); } }
.notes { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 2px; }
</style>
