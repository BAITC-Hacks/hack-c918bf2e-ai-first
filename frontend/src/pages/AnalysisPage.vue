<template>
  <q-page class="app-container page-pad">
    <div v-if="loading && !analysis" class="column q-gutter-y-md">
      <q-skeleton type="text" width="40%" height="36px" />
      <q-skeleton height="320px" />
    </div>

    <q-banner v-if="pollError" rounded class="bg-red-1 text-red-10 q-mb-md no-print">
      <template #avatar><q-icon name="cloud_off" color="negative" /></template>
      {{ pollError }}
      <template #action>
        <q-btn flat no-caps color="negative" label="Повторить" @click="retry" />
        <q-btn flat no-caps color="negative" label="Новый анализ" :to="{ name: 'upload' }" />
      </template>
    </q-banner>

    <template v-if="analysis">
      <!-- Header -->
      <div class="row items-start q-col-gutter-md q-mb-lg">
        <div class="col-12 col-md">
          <div class="eyebrow row items-center q-gutter-x-sm">
            <span>Анализ реорганизации</span>
            <q-badge v-if="isDemo" color="orange-2" text-color="orange-10" label="Демо-данные" />
          </div>
          <h1 class="page-title q-mt-xs">{{ analysis.title || 'Анализ без названия' }}</h1>
          <div class="row items-center q-gutter-x-md q-mt-xs text-body2 muted">
            <span class="row items-center" :class="`text-${status.color}`">
              <q-icon :name="status.icon" size="18px" class="q-mr-xs" />{{ status.label }}
            </span>
            <span v-if="analysis.created_at">{{ formatDateTime(analysis.created_at) }}</span>
            <span v-if="running" class="tabular">{{ elapsed }}</span>
          </div>
        </div>
        <div v-if="completed" class="col-12 col-md-auto row q-gutter-sm no-print">
          <q-btn outline no-caps color="primary" icon="gavel" label="К заключению" @click="scrollToConclusion" />
          <q-btn outline no-caps color="primary" icon="print" label="Печать / PDF" @click="print" />
        </div>
      </div>

      <!-- Failed -->
      <template v-if="analysis.status === 'failed'">
        <q-banner rounded class="bg-red-1 text-red-10 q-mb-md">
          <template #avatar><q-icon name="error" color="negative" /></template>
          <div class="text-weight-medium">{{ analysis.error?.message || 'Анализ завершился с ошибкой' }}</div>
          <div v-if="analysis.error?.code" class="text-caption">Код: {{ analysis.error.code }}</div>
          <template #action>
            <q-btn flat no-caps color="negative" label="Обновить статус" @click="retry" />
            <q-btn unelevated no-caps color="negative" label="Новый анализ" :to="{ name: 'upload' }" />
          </template>
        </q-banner>
        <RunProgress
          v-if="analysis.steps.length"
          :steps="analysis.steps"
          :progress="analysis.progress"
          :current-step="analysis.current_step"
          :status="analysis.status"
        />
      </template>

      <!-- Running -->
      <div v-else-if="running" class="row q-col-gutter-md">
        <div class="col-12 col-md-8">
          <RunProgress
            :steps="analysis.steps"
            :progress="analysis.progress"
            :current-step="analysis.current_step"
            :status="analysis.status"
          />
        </div>
        <div class="col-12 col-md-4">
          <section class="panel">
            <header class="panel-head"><h2 class="panel-title">Как формируется вывод</h2></header>
            <div class="panel-body text-body2 column q-gutter-y-sm">
              <div class="row no-wrap"><q-icon name="rule" color="primary" class="q-mr-sm q-mt-xs" />Каждое отклонение опирается на пункт документа и цитату.</div>
              <div class="row no-wrap"><q-icon name="verified" color="primary" class="q-mr-sm q-mt-xs" />Контролёр отклоняет выводы без существующей ссылки.</div>
              <div class="row no-wrap"><q-icon name="percent" color="primary" class="q-mr-sm q-mt-xs" />Выводы с уверенностью ниже 60 % помечаются для проверки экспертом.</div>
              <div class="text-caption muted q-mt-md">Страницу можно не держать открытой: статус сохраняется на сервере.</div>
            </div>
          </section>
        </div>
      </div>

      <!-- Completed -->
      <template v-else-if="completed">
        <KpiStrip v-if="analysis.summary" :summary="analysis.summary" :active="activeKpi" class="q-mb-md" @select="onKpi" />

        <div class="row q-col-gutter-md q-mb-md items-start">
          <div class="col-12" :class="{ 'col-lg-7': wide }">
            <FindingsTable
              v-model:types="typeFilter"
              :findings="findings"
              :selected-id="selectedId"
              @select="select"
            />
          </div>
          <div v-if="wide" class="col-12 col-lg-5 detail-sticky">
            <FindingDetail :finding="selected" />
          </div>
        </div>

        <ConclusionPanel :conclusion="analysis.conclusion" :warnings="analysis.warnings ?? []" class="q-mb-md" />

        <q-expansion-item
          dense
          icon="timeline"
          label="Журнал выполнения агента"
          header-class="text-body2 muted"
          class="panel no-print"
        >
          <RunProgress
            :steps="analysis.steps"
            :progress="analysis.progress"
            :current-step="analysis.current_step"
            :status="analysis.status"
            class="run-log"
          />
        </q-expansion-item>
      </template>
    </template>

    <q-dialog v-if="!wide" v-model="dialogOpen" :maximized="$q.screen.lt.sm" position="right">
      <div class="dialog-detail">
        <FindingDetail :finding="selected" closable stacked @close="dialogOpen = false" />
      </div>
    </q-dialog>
  </q-page>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, toRef, watch } from 'vue'
import { useQuasar } from 'quasar'
import ConclusionPanel from '@/components/ConclusionPanel.vue'
import FindingDetail from '@/components/FindingDetail.vue'
import FindingsTable from '@/components/FindingsTable.vue'
import KpiStrip from '@/components/KpiStrip.vue'
import RunProgress from '@/components/RunProgress.vue'
import { isMockId } from '@/api/mock'
import type { FindingType } from '@/api/types'
import { useAnalysisPolling } from '@/composables/useAnalysisPolling'
import { SEVERITY_META, STATUS_META, formatDateTime } from '@/utils/labels'

const props = defineProps<{ id: string }>()
const $q = useQuasar()

const { analysis, pollError, loading, retry } = useAnalysisPolling(toRef(props, 'id'))

const isDemo = computed(() => isMockId(props.id))
const status = computed(() => STATUS_META[analysis.value?.status ?? 'queued'])
const running = computed(() => analysis.value?.status === 'queued' || analysis.value?.status === 'processing')
const completed = computed(() => analysis.value?.status === 'completed')
const wide = computed(() => $q.screen.gt.md)

const findings = computed(() => analysis.value?.findings ?? [])
const typeFilter = ref<FindingType[]>([])
const selectedId = ref<string | null>(null)
const dialogOpen = ref(false)
const selected = computed(() => findings.value.find((f) => f.id === selectedId.value) ?? null)
const activeKpi = computed(() => (typeFilter.value.length === 1 ? typeFilter.value[0] : null))

function select(id: string) {
  selectedId.value = id
  if (!wide.value) dialogOpen.value = true
}

function onKpi(type: FindingType | null) {
  typeFilter.value = type ? [type] : []
}

// Pre-select the most critical finding so the detail panel is never empty in the demo.
watch(completed, (done) => {
  if (!done || selectedId.value) return
  const top = [...findings.value]
    .filter((f) => f.type !== 'unchanged')
    .sort((a, b) => SEVERITY_META[a.severity].rank - SEVERITY_META[b.severity].rank || b.confidence - a.confidence)[0]
  selectedId.value = top?.id ?? null
}, { immediate: true })

watch(() => props.id, () => {
  selectedId.value = null
  typeFilter.value = []
})

// Elapsed timer while the agent is running.
const now = ref(Date.now())
const startedAt = ref(Date.now())
watch(() => analysis.value?.created_at, (iso) => {
  const parsed = iso ? Date.parse(iso) : NaN
  if (!Number.isNaN(parsed) && parsed > 0 && parsed <= Date.now()) startedAt.value = parsed
}, { immediate: true })
const clock = window.setInterval(() => (now.value = Date.now()), 1000)
onBeforeUnmount(() => window.clearInterval(clock))
const elapsed = computed(() => {
  const seconds = Math.max(0, Math.floor((now.value - startedAt.value) / 1000))
  return `${String(Math.floor(seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`
})

function scrollToConclusion() {
  document.getElementById('conclusion')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function print() {
  window.print()
}
</script>

<style scoped lang="scss">
.detail-sticky { position: sticky; top: 66px; }
.dialog-detail { width: 560px; max-width: 100vw; background: #fff; }
.run-log { border: 0; border-top: 1px solid var(--c-border); border-radius: 0; }
</style>
