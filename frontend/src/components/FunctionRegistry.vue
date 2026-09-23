<template>
  <section class="registry sv-col" aria-labelledby="registry-heading">
    <div class="row items-baseline" style="gap: 8px 16px">
      <h2 id="registry-heading" class="sv-h2">Реестр функций и охват анализа</h2>
      <span class="sv-small sv-muted tabular">{{ countLabel }}</span>
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

    <div v-if="allRows.length" class="sv-col toolbar no-print">
      <div class="row items-center" style="gap: 10px">
        <q-input
          v-model="query"
          outlined
          dense
          clearable
          :debounce="200"
          class="sv-input search"
          placeholder="Поиск по функции, подразделению, документу или пункту"
          aria-label="Поиск по реестру функций"
          @clear="query = ''"
        >
          <template #prepend><q-icon name="search" size="18px" /></template>
        </q-input>
        <q-btn v-if="filtered" flat no-caps class="sv-btn sv-btn--ghost" icon="filter_alt_off" label="Сбросить фильтры" @click="reset" />
      </div>
      <div role="group" aria-label="Статус сопоставления" class="row chips">
        <button type="button" class="sv-filter-chip" :aria-pressed="!statuses.length" @click="statuses = []">
          <q-icon v-if="!statuses.length" name="check" />Все<span class="tabular sv-muted">{{ allRows.length }}</span>
        </button>
        <button
          v-for="s in chipStatuses"
          :key="s"
          type="button"
          class="sv-filter-chip"
          :class="{ 'chip--review': s === 'needs_review' && counts[s] > 0 }"
          :aria-pressed="statuses.includes(s)"
          @click="toggle(s)"
        >
          <q-icon v-if="statuses.includes(s)" name="check" />{{ MAPPING_LABEL[s] }}<span class="tabular sv-muted">{{ counts[s] }}</span>
        </button>
      </div>
    </div>

    <q-table
      v-if="rows.length"
      v-model:pagination="pagination"
      flat bordered wrap-cells row-key="key" :rows="rows" :columns="columns"
      :rows-per-page-options="[10, 25, 50, 100]"
      rows-per-page-label="Записей на странице"
      :pagination-label="(first: number, last: number, total: number) => `${first}–${last} из ${total}`"
      class="registry-table"
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
            <q-badge :color="props.row.status === 'needs_review' ? 'orange-9' : 'blue-grey-7'">{{ MAPPING_LABEL[props.row.status as MappingStatus] }}</q-badge>
            <p class="sv-small q-mt-sm">{{ props.row.explanation }}</p>
          </q-td>
        </q-tr>
      </template>
    </q-table>

    <div v-else class="sv-card empty sv-col items-center text-center">
      <template v-if="allRows.length">
        <q-icon name="filter_alt_off" size="30px" style="color: var(--sv-icon-muted)" />
        <span class="empty-title">Нет записей по выбранным фильтрам</span>
        <span class="sv-small sv-muted">Измените статус или поисковый запрос.</span>
        <q-btn flat no-caps class="sv-btn sv-btn--secondary q-mt-sm" label="Сбросить фильтры" @click="reset" />
      </template>
      <template v-else>
        <q-icon name="inbox" size="30px" style="color: var(--sv-icon-muted)" />
        <span class="empty-title">В реестре нет сопоставлений</span>
        <span class="sv-small sv-muted">Сервис не выделил функций для сопоставления. Проверьте решения по исходным фрагментам ниже.</span>
      </template>
    </div>

    <details v-if="registry.source_reviews.length" class="source-review" :open="sourcesOpen" @toggle="onToggle">
      <summary>Решения по исходным фрагментам · {{ registry.coverage.unresolved_fragments }} требуют проверки</summary>
      <div class="row items-center source-toolbar no-print">
        <q-select
          v-model="sourceStatus" outlined dense emit-value map-options :options="SOURCE_OPTIONS"
          class="sv-input source-select" aria-label="Решение по фрагменту"
        />
        <span class="sv-meta">{{ sourceRows.length }} из {{ registry.source_reviews.length }}<template v-if="query.trim()"> · учтён поиск «{{ query.trim() }}»</template></span>
      </div>
      <q-table flat dense wrap-cells :rows="sourceRows" :columns="sourceColumns" row-key="source_id"
        :pagination="{ rowsPerPage: 10 }" :rows-per-page-options="[10, 25, 50, 100]"
        rows-per-page-label="Записей на странице" no-data-label="Нет фрагментов по выбранным фильтрам" />
    </details>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QTableColumn } from 'quasar'
import type { FunctionRegistry, MappingStatus, SourceReview } from '@/api/types'
import { MAPPING_LABEL, MAPPING_ORDER, SOURCE_LABEL, filterRows, filterSources, registryRows, statusCounts } from '@/utils/registry'

const props = defineProps<{ registry: FunctionRegistry; reviewRequest?: number }>()

const query = ref('')
const statuses = ref<MappingStatus[]>([])
const pagination = ref({ page: 1, rowsPerPage: 25 })
const sourceStatus = ref<SourceReview['status'] | 'all'>('all')
const sourcesOpen = ref(false)

const allRows = computed(() => registryRows(props.registry))
const counts = computed(() => statusCounts(allRows.value))
// needs_review stays visible even at 0 so reviewers can see there is nothing open.
const chipStatuses = computed(() => MAPPING_ORDER.filter((s) => s === 'needs_review' || counts.value[s] > 0))
const rows = computed(() => filterRows(allRows.value, { query: query.value ?? '', statuses: statuses.value }))
const filtered = computed(() => !!(query.value ?? '').trim() || statuses.value.length > 0 || sourceStatus.value !== 'all')
const countLabel = computed(() =>
  rows.value.length === allRows.value.length ? `${allRows.value.length} записей` : `Показано ${rows.value.length} из ${allRows.value.length}`,
)

function toggle(s: MappingStatus) {
  statuses.value = statuses.value.includes(s) ? statuses.value.filter((x) => x !== s) : [...statuses.value, s]
}
function reset() {
  query.value = ''
  statuses.value = []
  sourceStatus.value = 'all'
}
function onToggle(event: Event) {
  sourcesOpen.value = (event.target as HTMLDetailsElement).open
}

// A filter change must not leave the user on an empty page 7.
watch([query, statuses], () => (pagination.value = { ...pagination.value, page: 1 }))

// «Показать требующие проверки» from the coverage summary.
watch(
  () => props.reviewRequest,
  (n) => {
    if (!n) return
    query.value = ''
    statuses.value = ['needs_review']
    sourceStatus.value = 'needs_review'
    sourcesOpen.value = props.registry.coverage.unresolved_fragments > 0
  },
)

const columns: QTableColumn[] = [
  { name: 'before', label: 'Функция ДО', field: 'before', align: 'left', style: 'width: 35%' },
  { name: 'after', label: 'Функция ПОСЛЕ', field: 'after', align: 'left', style: 'width: 35%' },
  { name: 'status', label: 'Решение / обоснование', field: 'status', align: 'left' },
]

const SOURCE_OPTIONS = [
  { value: 'all', label: 'Все решения' },
  { value: 'needs_review', label: SOURCE_LABEL.needs_review },
  { value: 'functions', label: SOURCE_LABEL.functions },
  { value: 'non_functional', label: SOURCE_LABEL.non_functional },
]
const sourceRows = computed(() =>
  filterSources(props.registry.source_reviews, query.value ?? '', sourceStatus.value).map((row) => ({
    ...row,
    sideLabel: row.side === 'before' ? 'ДО' : 'ПОСЛЕ',
    statusLabel: SOURCE_LABEL[row.status],
  })),
)
const sourceColumns: QTableColumn[] = [
  { name: 'side', label: 'Комплект', field: 'sideLabel', align: 'left' },
  { name: 'document', label: 'Документ', field: 'document', align: 'left' },
  { name: 'clause', label: 'Фрагмент', field: 'clause', align: 'left' },
  { name: 'status', label: 'Решение', field: 'statusLabel', align: 'left' },
  { name: 'reason', label: 'Причина', field: 'reason', align: 'left' },
]
</script>

<style scoped lang="scss">
.registry { gap: 14px; min-width: 0; scroll-margin-top: 72px; }
.registry-metrics { display: flex; gap: 12px 24px; flex-wrap: wrap; font-size: 14px; }
.registry p { margin-bottom: 0; }
.toolbar { gap: 10px; }
.search { flex: 0 1 420px; min-width: 240px; }
.chips { gap: 4px; flex-wrap: wrap; }
.chip--review { border-color: var(--sv-medium-border); }
.registry-table { background: var(--sv-surface); color: var(--sv-text); }
.source { margin-top: 8px; font-size: 12px; overflow-wrap: anywhere; }
summary { cursor: pointer; color: var(--sv-text-2); }
blockquote { margin: 8px 0; padding-left: 12px; border-left: 2px solid var(--sv-border); }
.target + .target { margin-top: 14px; }
.source-review { padding: 12px; border: 1px solid var(--sv-border); border-radius: 8px; }
.source-toolbar { gap: 12px; margin: 10px 0; }
.source-select { width: 220px; }
.empty { padding: 32px 16px; gap: 8px; }
.empty-title { font-size: 16px; font-weight: 500; }
@media (max-width: 599px) {
  .search { flex: 1 1 100%; }
  .chips { flex-wrap: nowrap; overflow-x: auto; width: 100%; padding-bottom: 2px; }
  .sv-filter-chip { min-height: 44px; flex: none; }
}
</style>
