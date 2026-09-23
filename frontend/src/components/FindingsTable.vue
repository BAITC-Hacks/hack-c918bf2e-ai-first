<template>
  <section class="panel column findings-panel">
    <header class="panel-head">
      <h2 class="panel-title">Отклонения</h2>
      <q-badge color="grey-3" text-color="grey-9" class="tabular">{{ rows.length }} из {{ findings.length }}</q-badge>
      <q-space />
      <q-btn v-if="hasFilters" flat dense no-caps size="sm" icon="filter_alt_off" label="Сбросить" @click="reset" />
    </header>

    <div class="filters q-px-md q-pt-md">
      <div class="row q-gutter-xs q-mb-sm">
        <q-chip
          v-for="type in TYPE_ORDER"
          :key="type"
          clickable
          dense
          square
          :aria-pressed="types.includes(type)"
          :class="types.includes(type) ? `bg-${TYPE_META[type].color} text-white` : `bg-${TYPE_META[type].color}-soft text-${TYPE_META[type].color}`"
          @click="toggleType(type)"
        >
          {{ TYPE_META[type].label }}
          <span class="q-ml-xs tabular chip-count">{{ counts[type] }}</span>
        </q-chip>
      </div>
      <div class="row q-col-gutter-sm items-center">
        <div class="col-12 col-sm">
          <q-input v-model="search" dense outlined clearable placeholder="Поиск: функция, подразделение, пункт…">
            <template #prepend><q-icon name="search" /></template>
          </q-input>
        </div>
        <div class="col-12 col-sm-5 col-xl-4">
          <q-select
            v-model="severities"
            dense
            outlined
            multiple
            emit-value
            map-options
            :options="severityOptions"
            label="Уровень риска"
            :display-value="severities.length ? severities.map((s) => SEVERITY_META[s].label).join(', ') : 'Все'"
          />
        </div>
        <div class="col-12 col-sm-auto">
          <q-toggle v-model="showUnchanged" dense label="Без изменений" :disable="types.includes('unchanged')" />
        </div>
      </div>
    </div>

    <q-table
      flat
      class="findings-table"
      :rows="rows"
      :columns="columns"
      row-key="id"
      :pagination="{ rowsPerPage: 12, sortBy: 'severity' }"
      :rows-per-page-options="[12, 25, 0]"
      no-data-label="Нет отклонений по выбранным фильтрам"
      rows-per-page-label="Строк на странице"
      :grid="$q.screen.lt.sm"
    >
      <template #body="{ row }">
        <q-tr
          class="cursor-pointer finding-row"
          :class="{ 'finding-row--selected': row.id === selectedId }"
          tabindex="0"
          @click="$emit('select', row.id)"
          @keydown.enter="$emit('select', row.id)"
        >
          <q-td key="severity">
            <span class="row items-center no-wrap">
              <span class="sev-dot q-mr-sm" :class="`bg-${SEVERITY_META[row.severity as Severity].color}`" />
              {{ SEVERITY_META[row.severity as Severity].label }}
            </span>
          </q-td>
          <q-td key="type">
            <q-badge
              :class="`bg-${TYPE_META[row.type as FindingType].color}-soft text-${TYPE_META[row.type as FindingType].color}`"
              class="type-badge"
            >
              {{ TYPE_META[row.type as FindingType].label }}
            </q-badge>
          </q-td>
          <q-td key="title" class="title-cell">
            <div class="text-weight-medium">{{ row.title }}</div>
            <div class="text-caption muted">{{ departments(row) }}</div>
          </q-td>
          <q-td key="refs" class="text-caption tabular">{{ refs(row) }}</q-td>
          <q-td key="confidence" class="text-right tabular">
            <span :class="`text-${confidenceLevel(row.confidence).color}`">{{ percent(row.confidence) }}</span>
          </q-td>
        </q-tr>
      </template>

      <template #item="{ row }">
        <div class="col-12 q-pa-xs">
          <q-card flat bordered class="cursor-pointer" :class="{ 'finding-row--selected': row.id === selectedId }" @click="$emit('select', row.id)">
            <q-card-section class="q-pb-xs row items-center q-gutter-x-sm">
              <span class="sev-dot" :class="`bg-${SEVERITY_META[row.severity as Severity].color}`" />
              <q-badge :class="`bg-${TYPE_META[row.type as FindingType].color}-soft text-${TYPE_META[row.type as FindingType].color}`">
                {{ TYPE_META[row.type as FindingType].label }}
              </q-badge>
              <q-space />
              <span class="text-caption tabular">{{ percent(row.confidence) }}</span>
            </q-card-section>
            <q-card-section class="q-pt-xs">
              <div class="text-weight-medium">{{ row.title }}</div>
              <div class="text-caption muted">{{ departments(row) }}</div>
            </q-card-section>
          </q-card>
        </div>
      </template>
    </q-table>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { QTableColumn } from 'quasar'
import type { Finding, FindingType, Severity } from '@/api/types'
import { SEVERITY_META, SEVERITY_ORDER, TYPE_META, TYPE_ORDER, confidenceLevel, percent } from '@/utils/labels'

const props = defineProps<{ findings: Finding[]; selectedId: string | null }>()
defineEmits<{ select: [id: string] }>()

const types = defineModel<FindingType[]>('types', { default: () => [] })
const search = ref<string | null>('')
const severities = ref<Severity[]>([])
const showUnchanged = ref(false)

const severityOptions = SEVERITY_ORDER.map((value) => ({ value, label: SEVERITY_META[value].label }))

const counts = computed(() => {
  const result = Object.fromEntries(TYPE_ORDER.map((t) => [t, 0])) as Record<FindingType, number>
  props.findings.forEach((f) => (result[f.type] += 1))
  return result
})

const hasFilters = computed(() => types.value.length > 0 || !!search.value || severities.value.length > 0 || showUnchanged.value)

function toggleType(type: FindingType) {
  types.value = types.value.includes(type) ? types.value.filter((t) => t !== type) : [...types.value, type]
}

function reset() {
  types.value = []
  search.value = ''
  severities.value = []
  showUnchanged.value = false
}

watch(types, (value) => {
  if (value.includes('unchanged')) showUnchanged.value = true
})

function departments(f: Finding): string {
  const before = f.before?.department ?? '—'
  const after = f.after?.department ?? '—'
  if (f.type === 'duplicate') return `${before} ↔ ${after}`
  return before === after ? before : `${before} → ${after}`
}

function refs(f: Finding): string {
  const parts = [f.before?.clause, f.after?.clause].map((c) => (c ? `п. ${c}` : '—'))
  return f.type === 'duplicate' ? parts.join(' ↔ ') : parts.join(' → ')
}

const rows = computed(() => {
  const query = (search.value ?? '').trim().toLowerCase()
  return props.findings.filter((f) => {
    if (types.value.length && !types.value.includes(f.type)) return false
    if (!types.value.length && !showUnchanged.value && f.type === 'unchanged') return false
    if (severities.value.length && !severities.value.includes(f.severity)) return false
    if (!query) return true
    const haystack = [
      f.title,
      f.explanation,
      f.before?.department,
      f.after?.department,
      f.before?.clause,
      f.after?.clause,
      f.before?.document,
      f.after?.document,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(query)
  })
})

const columns: QTableColumn<Finding>[] = [
  {
    name: 'severity',
    label: 'Риск',
    field: 'severity',
    align: 'left',
    sortable: true,
    sort: (a: Severity, b: Severity, rowA: Finding, rowB: Finding) =>
      SEVERITY_META[a].rank - SEVERITY_META[b].rank || rowB.confidence - rowA.confidence,
    style: 'width: 96px',
  },
  {
    name: 'type',
    label: 'Тип',
    field: 'type',
    align: 'left',
    sortable: true,
    sort: (a: FindingType, b: FindingType) => TYPE_ORDER.indexOf(a) - TYPE_ORDER.indexOf(b),
    style: 'width: 120px',
  },
  { name: 'title', label: 'Функция · подразделения', field: 'title', align: 'left', sortable: true },
  { name: 'refs', label: 'Пункты', field: (row) => refs(row), align: 'left', classes: 'no-wrap' },
  { name: 'confidence', label: 'Увер.', field: 'confidence', align: 'right', sortable: true, style: 'width: 72px' },
]
</script>

<style scoped lang="scss">
.findings-panel { min-width: 0; overflow: hidden; }
.findings-table { background: transparent; max-width: 100%; }
.findings-table :deep(thead th) { font-weight: 600; color: var(--c-muted); font-size: 12px; }
.finding-row:hover { background: #f5f8fb; }
.finding-row:focus-visible { outline: 2px solid $primary; outline-offset: -2px; }
.finding-row--selected, .finding-row--selected:hover { background: #e8f1fb; box-shadow: inset 3px 0 0 $primary; }
.title-cell { white-space: normal; min-width: 220px; }
.type-badge { font-weight: 500; padding: 3px 8px; }
.chip-count { opacity: .8; }
</style>
