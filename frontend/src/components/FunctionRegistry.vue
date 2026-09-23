<template>
  <section class="registry sv-col" aria-labelledby="registry-heading">
    <div class="row items-center justify-between" style="gap: 12px">
      <h2 id="registry-heading" class="sv-h2">Реестр функций и охват анализа</h2>
      <q-toggle v-model="onlyUnresolved" label="Только требует проверки" />
    </div>
    <div class="registry-metrics">
      <span>Рассмотрено фрагментов: <b>{{ registry.coverage.reviewed_fragments }} / {{ registry.coverage.total_fragments }}</b></span>
      <span>Сопоставлено функций ДО: <b>{{ registry.coverage.matched_before_functions }} / {{ registry.coverage.before_functions }}</b></span>
      <span>Записей требуют проверки: <b>{{ registry.coverage.needs_review_mappings }}</b></span>
    </div>
    <p class="sv-small sv-text-2">
      Реестр содержит извлечённые ИИ обязанности с проверенными цитатами. Охват фрагментов — не точность
      и не гарантия полноты извлечения. «Потенциальная потеря» требует проверки специалистом.
    </p>
    <q-table
      flat bordered wrap-cells row-key="key" :rows="rows" :columns="columns"
      :rows-per-page-options="[10, 25, 50]" :pagination="{ rowsPerPage: 10 }"
      no-data-label="Нет записей по выбранному фильтру"
    >
      <template #body="props">
        <q-tr :props="props">
          <q-td key="before" :props="props">
            <template v-if="props.row.before">
              <b>{{ props.row.before.action }}</b>
              <div class="sv-small sv-muted">{{ props.row.before.owner || 'Исполнитель не указан' }}</div>
              <details class="source"><summary>{{ props.row.before.evidence.document }} · {{ props.row.before.evidence.clause }}</summary>
                <blockquote>{{ props.row.before.evidence.quote }}</blockquote>
              </details>
            </template>
            <span v-else class="sv-muted">Нет пары ДО</span>
          </q-td>
          <q-td key="after" :props="props">
            <div v-for="fn in props.row.after" :key="fn.id" class="target">
              <b>{{ fn.action }}</b>
              <div class="sv-small sv-muted">{{ fn.owner || 'Исполнитель не указан' }}</div>
              <details class="source"><summary>{{ fn.evidence.document }} · {{ fn.evidence.clause }}</summary>
                <blockquote>{{ fn.evidence.quote }}</blockquote>
              </details>
            </div>
            <span v-if="!props.row.after.length" class="sv-muted">Нет подтверждённой пары ПОСЛЕ</span>
          </q-td>
          <q-td key="status" :props="props">
            <q-badge :color="props.row.status === 'needs_review' ? 'orange-9' : 'blue-grey-7'">{{ labels[props.row.status as MappingStatus] }}</q-badge>
            <p class="sv-small q-mt-sm">{{ props.row.explanation }}</p>
          </q-td>
        </q-tr>
      </template>
    </q-table>
    <details v-if="registry.source_reviews.length" class="source-review">
      <summary>Решения по исходным фрагментам · {{ registry.coverage.unresolved_fragments }} требуют проверки</summary>
      <q-table flat dense wrap-cells :rows="sourceRows" :columns="sourceColumns" row-key="source_id"
        :pagination="{ rowsPerPage: 10 }" :rows-per-page-options="[10, 25, 50]" no-data-label="Нет нерешённых фрагментов" />
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import type { QTableColumn } from 'quasar'
import type { FunctionRegistry, MappingStatus } from '@/api/types'

const props = defineProps<{ registry: FunctionRegistry }>()
const onlyUnresolved = ref(false)
const labels: Record<MappingStatus, string> = {
  unchanged: 'Сохранена', moved: 'Передана', changed: 'Изменена',
  lost: 'Потенциальная потеря', added: 'Новая', needs_review: 'Требует проверки',
}
const functions = computed(() => new Map(props.registry.functions.map(fn => [fn.id, fn])))
const rows = computed(() => props.registry.mappings.map((row, index) => ({
  ...row, key: index,
  before: row.before_id ? functions.value.get(row.before_id) : null,
  after: row.after_ids.map(id => functions.value.get(id)).filter(Boolean),
})).filter(row => !onlyUnresolved.value || row.status === 'needs_review'))
const columns: QTableColumn[] = [
  { name: 'before', label: 'Функция ДО', field: 'before', align: 'left', style: 'width: 35%' },
  { name: 'after', label: 'Функция ПОСЛЕ', field: 'after', align: 'left', style: 'width: 35%' },
  { name: 'status', label: 'Решение / обоснование', field: 'status', align: 'left' },
]
const sourceLabels = { functions: 'Функции извлечены', non_functional: 'Нефункциональный', needs_review: 'Требует проверки' }
const sourceRows = computed(() => props.registry.source_reviews
  .filter(row => !onlyUnresolved.value || row.status === 'needs_review')
  .map(row => ({ ...row, sideLabel: row.side === 'before' ? 'ДО' : 'ПОСЛЕ', statusLabel: sourceLabels[row.status] })))
const sourceColumns: QTableColumn[] = [
  { name: 'side', label: 'Комплект', field: 'sideLabel', align: 'left' },
  { name: 'document', label: 'Документ', field: 'document', align: 'left' },
  { name: 'clause', label: 'Фрагмент', field: 'clause', align: 'left' },
  { name: 'status', label: 'Решение', field: 'statusLabel', align: 'left' },
  { name: 'reason', label: 'Причина', field: 'reason', align: 'left' },
]
</script>

<style scoped lang="scss">
.registry { gap: 14px; min-width: 0; }
.registry-metrics { display: flex; gap: 12px 24px; flex-wrap: wrap; font-size: 14px; }
.registry p { margin-bottom: 0; }
.source { margin-top: 8px; font-size: 12px; overflow-wrap: anywhere; }
summary { cursor: pointer; color: var(--sv-text-2); }
blockquote { margin: 8px 0; padding-left: 12px; border-left: 2px solid var(--sv-border); }
.target + .target { margin-top: 14px; }
.source-review { padding: 12px; border: 1px solid var(--sv-border); border-radius: 8px; }
</style>
