<template>
  <q-page>
    <div v-if="pollError" class="sv-container q-pt-lg">
      <div role="alert" class="sv-banner sv-banner--err items-center">
        <q-icon name="cloud_off" size="20px" />
        <div class="col sv-col">
          <b>Нет связи с сервисом анализа</b>
          <span>{{ pollError }}</span>
        </div>
        <q-btn flat no-caps class="sv-btn sv-btn--secondary" icon="refresh" label="Повторить" @click="retry" />
      </div>
    </div>

    <div v-if="!analysis && !pollError" class="sv-container q-pt-lg sv-col q-gutter-y-md">
      <q-skeleton type="text" width="45%" height="40px" />
      <q-skeleton type="rect" height="150px" />
      <q-skeleton type="rect" height="320px" />
    </div>

    <template v-if="analysis">
      <div v-if="showResultHeader" class="sv-container result-head sv-col">
        <div class="row items-end head-row">
          <div class="sv-col head-main">
            <h1 class="sv-h1">{{ title }}</h1>
            <div class="row items-center meta">
              <span class="row items-center no-wrap status"><q-icon name="check_circle" size="18px" />Анализ завершён</span>
              <span v-if="durationMs" class="row items-center no-wrap"><q-icon name="timer" size="16px" class="sv-muted" />Время выполнения {{ formatDuration(durationMs) }}</span>
              <span v-if="analysis.quality_score != null" class="row items-center no-wrap" title="Оценка качества результата агентом-критиком">
                <q-icon name="fact_check" size="16px" class="sv-muted" />Оценка критика {{ Math.round(analysis.quality_score * 100) }}%
              </span>
              <span v-if="docsLabel" class="row items-center no-wrap"><q-icon name="description" size="16px" class="sv-muted" />{{ docsLabel }}</span>
            </div>
          </div>
          <div class="row no-wrap head-actions no-print">
            <q-btn flat no-caps class="sv-btn sv-btn--secondary" icon="print" label="Печать / PDF" @click="print" />
            <q-btn
              v-if="route.name !== 'conclusion'"
              flat
              no-caps
              class="sv-btn sv-btn--primary"
              icon="summarize"
              label="Открыть заключение"
              :to="{ name: 'conclusion', params: { id } }"
            />
          </div>
        </div>
        <q-tabs
          dense
          no-caps
          align="left"
          class="tabs no-print"
          active-class="tab--active"
          indicator-color="transparent"
          :breakpoint="0"
        >
          <q-route-tab :to="{ name: 'overview', params: { id } }" exact icon="dashboard" label="Обзор" class="tab" />
          <q-route-tab :to="{ name: 'conclusion', params: { id } }" exact icon="summarize" label="Заключение" class="tab" />
        </q-tabs>
      </div>

      <router-view />

      <FindingDrawer
        :finding="drawerFinding"
        :label="drawerFinding ? labelOf(drawerFinding.id) : ''"
        :position="drawerPosition"
        :total="navList.length"
        @close="closeFinding"
        @step="stepFinding"
      />
    </template>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, provide, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import FindingDrawer from '@/components/FindingDrawer.vue'
import { ANALYSIS_CTX, type TableFilters } from '@/composables/analysisContext'
import { useAnalysis } from '@/composables/useAnalysis'
import { runMeta } from '@/stores/draft'
import { department, sortFindings } from '@/utils/findings'
import { DOCS_WORD, formatDuration, pluralize } from '@/utils/labels'

const props = defineProps<{ id: string }>()
const route = useRoute()
const router = useRouter()

const handle = computed(() => useAnalysis(props.id))
const analysis = computed(() => handle.value.analysis.value)
const pollError = computed(() => handle.value.pollError.value)
const durationMs = computed(() => handle.value.durationMs.value)
const retry = () => handle.value.retry()

const title = computed(() => analysis.value?.title || 'Анализ без названия')
const showResultHeader = computed(() => analysis.value?.status === 'completed' && route.name !== 'run')
const docsLabel = computed(() => {
  const meta = runMeta.get(props.id)
  if (!meta) return ''
  const total = meta.before + meta.after
  return `${total} ${pluralize(total, DOCS_WORD)}: ${meta.before} до, ${meta.after} после`
})

// ---- Route follows status ----
let redirectTimer: number | undefined
watch(
  () => [analysis.value?.status, route.name] as const,
  ([status, name]) => {
    window.clearTimeout(redirectTimer)
    if (!status) return
    const running = status === 'queued' || status === 'processing'
    if ((running || status === 'failed') && name !== 'run') {
      void router.replace({ name: 'run', params: { id: props.id } })
    } else if (status === 'completed' && name === 'run') {
      redirectTimer = window.setTimeout(() => void router.replace({ name: 'overview', params: { id: props.id } }), 500)
    }
  },
  { immediate: true },
)
onBeforeUnmount(() => window.clearTimeout(redirectTimer))

// ---- Table state shared by overview and the panel ----
const findings = computed(() => analysis.value?.findings ?? [])
const filters = reactive<TableFilters>({ query: '', types: [], risk: 'all', sort: 'priority' })
const visible = computed(() => {
  const q = filters.query.trim().toLowerCase()
  const rows = findings.value.filter((f) => {
    if (filters.types.length && !filters.types.includes(f.type)) return false
    if (filters.risk !== 'all' && f.severity !== filters.risk) return false
    if (!q) return true
    return [f.title, f.explanation, f.id, labelOf(f.id), department(f), f.before?.department, f.after?.department, f.before?.document, f.after?.document]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
      .includes(q)
  })
  return sortFindings(rows, filters.sort)
})
function resetFilters() {
  Object.assign(filters, { query: '', types: [], risk: 'all', sort: 'priority' })
}
watch(() => props.id, resetFilters)

// ---- Finding panel (?finding=F-02) ----
const navSource = ref<'table' | 'all'>('table')
const selectedId = computed(() => (typeof route.query.finding === 'string' ? route.query.finding : null))
const navList = computed(() => {
  const inTable = visible.value.some((f) => f.id === selectedId.value)
  return navSource.value === 'table' && inTable ? visible.value : sortFindings(findings.value, 'priority')
})
const drawerFinding = computed(() => findings.value.find((f) => f.id === selectedId.value) ?? null)
const drawerPosition = computed(() => navList.value.findIndex((f) => f.id === selectedId.value) + 1)

function openFinding(id: string, from: 'table' | 'all' = 'table') {
  navSource.value = from
  void router.replace({ query: { ...route.query, finding: id } })
}
function closeFinding() {
  const { finding: _drop, ...rest } = route.query
  void router.replace({ query: rest })
}
function stepFinding(delta: number) {
  const list = navList.value
  if (!list.length) return
  const index = list.findIndex((f) => f.id === selectedId.value)
  const next = list[(index + delta + list.length) % list.length]
  void router.replace({ query: { ...route.query, finding: next.id } })
}

const labels = computed(() => {
  const map = new Map<string, string>()
  sortFindings(findings.value, 'priority').forEach((f, i) => {
    map.set(f.id, /^F-\d+$/.test(f.id) ? f.id : `F-${String(i + 1).padStart(2, '0')}`)
  })
  return map
})
const labelOf = (id: string) => labels.value.get(id) ?? id

provide(ANALYSIS_CTX, {
  analysis,
  findings,
  filters,
  visible,
  resetFilters,
  openFinding,
  selectedId,
  labelOf,
})

function print() {
  window.print()
}
</script>

<style scoped lang="scss">
.result-head { padding-top: 24px; gap: 14px; }
.head-row { gap: 12px 24px; flex-wrap: wrap; }
.head-main { flex: 1 1 480px; gap: 8px; min-width: 0; }
.meta { gap: 6px 16px; font-size: 13px; color: var(--sv-text-2); flex-wrap: wrap; > span { gap: 5px; } }
.status { font-weight: 500; color: var(--sv-low); }
.head-actions { gap: 8px; }
.tabs { border-bottom: 1px solid var(--sv-border); color: var(--sv-muted); }
.tab { padding: 0 12px; min-height: 42px; font-weight: 500; border-bottom: 2px solid transparent; margin-bottom: -1px;
  :deep(.q-tab__content) { flex-direction: row; gap: 6px; }
  :deep(.q-tab__icon) { font-size: 18px; }
  :deep(.q-tab__label) { font-size: 14px; font-weight: 500; }
  &:hover { color: var(--sv-accent); }
}
.tab--active { color: var(--sv-accent-strong); border-bottom-color: var(--sv-accent); }
@media (max-width: 599px) { .head-actions { width: 100%; .q-btn { flex: 1; } } }
</style>
