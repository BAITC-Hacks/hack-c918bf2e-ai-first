<template>
  <section id="findings" aria-labelledby="f-h" class="sv-col section">
    <div class="row items-baseline section-head">
      <h2 id="f-h" class="sv-h2">Функциональные отклонения</h2>
      <span class="sv-small sv-muted tabular">{{ countLabel }}</span>
    </div>

    <div v-if="findings.length" class="sv-col toolbar no-print">
      <div class="row items-center toolbar-row">
        <q-input
          v-model="filters.query"
          outlined
          dense
          clearable
          :debounce="200"
          class="sv-input search"
          placeholder="Поиск по выводу, подразделению, документу"
          aria-label="Поиск"
          @clear="filters.query = ''"
        >
          <template #prepend><q-icon name="search" size="18px" /></template>
        </q-input>
        <q-space class="gt-xs" />
        <q-select v-model="filters.risk" outlined dense emit-value map-options :options="RISK_OPTIONS" class="sv-input select" aria-label="Риск" />
        <q-select v-model="filters.sort" outlined dense emit-value map-options :options="SORT_OPTIONS" class="sv-input select" aria-label="Сортировка" />
      </div>
      <div role="group" aria-label="Тип отклонения" class="row chips">
        <button type="button" class="sv-filter-chip" :aria-pressed="!filters.types.length" @click="filters.types = []">
          <q-icon v-if="!filters.types.length" name="check" />Все
        </button>
        <button
          v-for="t in chipTypes"
          :key="t.type"
          type="button"
          class="sv-filter-chip"
          :aria-pressed="filters.types.includes(t.type)"
          @click="toggleType(t.type)"
        >
          <q-icon
            :name="filters.types.includes(t.type) ? 'check' : TYPE_META[t.type].icon"
            :style="{ color: filters.types.includes(t.type) ? undefined : TYPE_META[t.type].fg }"
          />
          {{ TYPE_META[t.type].label }}<span class="tabular sv-muted">{{ t.count }}</span>
        </button>
      </div>
    </div>

    <div class="sv-card table-card">
      <q-table
        v-if="visible.length"
        flat
        :rows="visible"
        :columns="columns"
        row-key="id"
        hide-pagination
        :pagination="{ rowsPerPage: 0 }"
        :grid="$q.screen.lt.md"
        :visible-columns="visibleColumns"
        class="table"
        table-header-class="sv-th"
      >
        <template #header="hp">
          <q-tr :props="hp">
            <q-th v-for="col in hp.cols" :key="col.name" :props="hp" class="sv-th" :style="col.headerStyle">{{ col.label }}</q-th>
          </q-tr>
        </template>

        <template #body="{ row, cols }">
          <q-tr
            class="row-click"
            :class="{ 'row--selected': row.id === selectedId, 'row--high': row.severity === 'high' }"
            tabindex="0"
            role="button"
            :aria-label="`${labelOf(row.id)}: ${row.title}`"
            @click="openFinding(row.id)"
            @keydown.enter.prevent="openFinding(row.id)"
          >
            <q-td v-for="col in cols" :key="col.name" :class="`cell-${col.name}`">
              <RiskChip v-if="col.name === 'severity'" :severity="row.severity" />
              <TypeLabel v-else-if="col.name === 'type'" :type="row.type" />
              <div v-else-if="col.name === 'title'" class="sv-col" style="gap: 2px">
                <span class="title">{{ row.title }}</span>
                <span class="id tabular">{{ labelOf(row.id) }}</span>
              </div>
              <span v-else-if="col.name === 'department'" class="dept">{{ department(row) }}</span>
              <div v-else-if="col.name === 'source'" class="sv-col source">
                <span class="row items-center no-wrap" style="gap: 4px">
                  <q-icon name="format_quote" size="15px" class="sv-muted" />{{ clauseLabel(primaryEvidence(row)) }}
                </span>
                <span class="doc ellipsis">{{ primaryEvidence(row)?.document ?? '—' }}</span>
                <q-tooltip v-if="primaryEvidence(row)" :delay="400">{{ primaryEvidence(row)!.document }}</q-tooltip>
              </div>
              <ConfidenceMeter v-else-if="col.name === 'confidence'" :value="row.confidence" />
              <q-icon v-else-if="col.name === 'chevron'" name="chevron_right" size="20px" style="color: var(--sv-icon-muted)" />
            </q-td>
          </q-tr>
        </template>

        <template #item="{ row }">
          <div class="col-12 card-item">
            <div
              class="finding-card sv-col"
              :class="{ 'row--selected': row.id === selectedId }"
              tabindex="0"
              role="button"
              :aria-label="`${labelOf(row.id)}: ${row.title}`"
              @click="openFinding(row.id)"
              @keydown.enter.prevent="openFinding(row.id)"
            >
              <div class="row items-center" style="gap: 8px">
                <RiskChip :severity="row.severity" />
                <TypeLabel :type="row.type" />
                <q-space />
                <span class="id tabular">{{ labelOf(row.id) }}</span>
              </div>
              <span class="title">{{ row.title }}</span>
              <span class="dept">{{ department(row) }}</span>
              <div class="row items-center justify-between" style="gap: 8px">
                <span class="sv-meta row items-center no-wrap" style="gap: 4px; min-width: 0">
                  <q-icon name="format_quote" size="15px" />{{ clauseLabel(primaryEvidence(row)) }}
                </span>
                <ConfidenceMeter :value="row.confidence" />
              </div>
            </div>
          </div>
        </template>
      </q-table>

      <div v-else class="empty sv-col items-center text-center">
        <template v-if="findings.length">
          <q-icon name="filter_alt_off" size="32px" style="color: var(--sv-icon-muted)" />
          <span class="empty-title">Нет отклонений по выбранным фильтрам</span>
          <span class="sv-small sv-muted">Измените тип, риск или поисковый запрос.</span>
          <q-btn flat no-caps class="sv-btn sv-btn--secondary q-mt-sm" label="Сбросить фильтры" @click="resetFilters" />
        </template>
        <template v-else>
          <q-icon name="inbox" size="32px" style="color: var(--sv-icon-muted)" />
          <span class="empty-title">Принятых функциональных отклонений нет</span>
          <span class="sv-small sv-muted" style="max-width: 560px">
            Это не подтверждает, что все {{ beforeCount }} {{ pluralize(beforeCount, FUNCS_WORD) }} комплекта «до» сохранены: проверьте
            охват обработки и записи реестра, требующие проверки.
          </span>
        </template>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useQuasar, type QTableColumn } from 'quasar'
import type { Finding, FindingType } from '@/api/types'
import ConfidenceMeter from './ConfidenceMeter.vue'
import RiskChip from './RiskChip.vue'
import TypeLabel from './TypeLabel.vue'
import { useAnalysisContext } from '@/composables/analysisContext'
import { clauseLabel, department, primaryEvidence } from '@/utils/findings'
import { FINDINGS_WORD, FUNCS_WORD, TYPE_META, TYPE_ORDER, pluralize } from '@/utils/labels'

defineProps<{ beforeCount: number }>()

const $q = useQuasar()
const { findings, filters, visible, resetFilters, openFinding, selectedId, labelOf } = useAnalysisContext()

const RISK_OPTIONS = [
  { value: 'all', label: 'Любой риск' },
  { value: 'high', label: 'Высокий риск' },
  { value: 'medium', label: 'Средний риск' },
  { value: 'low', label: 'Низкий риск' },
]
const SORT_OPTIONS = [
  { value: 'priority', label: 'По приоритету' },
  { value: 'confidence', label: 'По уверенности' },
  { value: 'department', label: 'По подразделению' },
]

const chipTypes = computed(() =>
  TYPE_ORDER.map((type) => ({ type, count: findings.value.filter((f) => f.type === type).length })).filter(
    (t) => t.type !== 'unchanged' || t.count > 0,
  ),
)

function toggleType(type: FindingType) {
  filters.types = filters.types.includes(type) ? filters.types.filter((t) => t !== type) : [...filters.types, type]
}

const total = computed(() => findings.value.length)
const countLabel = computed(() =>
  visible.value.length === total.value
    ? `${total.value} ${pluralize(total.value, FINDINGS_WORD)}`
    : `Показано ${visible.value.length} из ${total.value}`,
)

const columns: QTableColumn<Finding>[] = [
  { name: 'severity', label: 'Риск', field: 'severity', align: 'left', headerStyle: 'width: 120px' },
  { name: 'type', label: 'Тип', field: 'type', align: 'left', headerStyle: 'width: 150px' },
  { name: 'title', label: 'Вывод', field: 'title', align: 'left' },
  { name: 'department', label: 'Подразделение', field: (r) => department(r), align: 'left', headerStyle: 'width: 210px' },
  { name: 'source', label: 'Источник', field: 'id', align: 'left', headerStyle: 'width: 220px' },
  { name: 'confidence', label: 'Уверенность', field: 'confidence', align: 'left', headerStyle: 'width: 120px' },
  { name: 'chevron', label: '', field: 'id', align: 'right', headerStyle: 'width: 28px' },
]
const visibleColumns = computed(() =>
  columns.map((c) => c.name).filter((name) => name !== 'department' || $q.screen.width >= 1200),
)
</script>

<style scoped lang="scss">
.section { gap: 12px; scroll-margin-top: 72px; }
.section-head { gap: 8px 16px; flex-wrap: wrap; }
.toolbar { gap: 10px; }
.toolbar-row { gap: 10px; flex-wrap: wrap; }
.search { flex: 0 1 360px; min-width: 220px; }
.chips { gap: 4px; flex-wrap: wrap; }
.select { flex: none; width: 168px; }
.table-card { overflow: hidden; }
.table { background: transparent; color: var(--sv-text);
  :deep(thead tr) { height: 38px; }
  :deep(th) { border-bottom: 1px solid var(--sv-divider) !important; padding: 10px 14px !important; }
  :deep(td) { border-bottom: 1px solid var(--sv-line) !important; padding: 12px 14px !important; white-space: normal; vertical-align: middle; }
  :deep(tbody tr:last-child td) { border-bottom: 0 !important; }
  :deep(.q-table__middle) { max-height: none; }
}
.row-click { cursor: pointer; &:hover { background: var(--sv-accent-tint); } }
.row--selected, .row--selected:hover { background: var(--sv-accent-tint); box-shadow: inset 0 0 0 1px var(--sv-accent-line); }
.title { font-size: 14px; line-height: 1.35; }
.row--high .title { font-weight: 500; }
.id { font-size: 11px; color: var(--sv-muted); }
.dept { font-size: 13px; line-height: 1.35; color: var(--sv-text-2); }
.source { gap: 2px; min-width: 0; max-width: 220px; font-size: 13px; }
.doc { font-size: 11px; color: var(--sv-muted); max-width: 200px; }
.cell-title { min-width: 240px; }
.empty { padding: 40px 16px; gap: 8px; }
.empty-title { font-size: 16px; font-weight: 500; }
.card-item { padding: 0; }
.finding-card {
  gap: 8px; padding: 14px 16px; border-bottom: 1px solid var(--sv-line); cursor: pointer; min-height: 44px;
  &:hover { background: var(--sv-accent-tint); }
}
@media (max-width: 599px) {
  .search { flex: 1 1 100%; }
  .select { flex: 1 1 140px; width: auto; }
  .chips { flex-wrap: nowrap; overflow-x: auto; width: 100%; padding-bottom: 2px; }
  :deep(.sv-filter-chip) { min-height: 44px; flex: none; }
}
</style>
