<template>
  <div v-if="analysis" class="sv-container page layout">
    <div class="main sv-col">
      <div class="sv-col head">
        <div class="sv-overline" :style="{ color: failed ? 'var(--sv-high)' : undefined }">{{ kicker }}</div>
        <h1 class="sv-h1 run-title">{{ analysis.title || 'Анализ без названия' }}</h1>
        <div v-if="meta" class="row sets">
          <span class="set-chip"><b>ДО</b>{{ meta.before }} {{ pluralize(meta.before, FILES) }}</span>
          <span class="set-chip"><b>ПОСЛЕ</b>{{ meta.after }} {{ pluralize(meta.after, FILES) }}</span>
        </div>
      </div>

      <div class="sv-col progress-box">
        <div class="row items-baseline">
          <span class="sv-small sv-text-2">{{ currentLabel }}</span>
          <q-space />
          <span class="pct tabular">{{ stageLabel }}</span>
        </div>
        <div
          role="progressbar"
          :aria-valuenow="analysis.progress"
          aria-valuemin="0"
          aria-valuemax="100"
          aria-label="Этап обработки"
          class="bar"
        >
          <div :style="{ width: `${analysis.progress}%`, background: failed ? 'var(--sv-high)' : 'var(--sv-accent)' }" />
        </div>
        <span class="sv-meta">Полоса показывает этап обработки по данным сервера ({{ analysis.progress }}%), а не прогноз времени.</span>
      </div>

      <ol class="steps sv-card">
        <li v-for="(step, i) in analysis.steps" :key="step.code" class="step" :class="`step--${step.status}`">
          <span class="step-icon">
            <q-icon
              :name="step.status === 'processing' && reducedMotion ? 'pending' : STEP_META[step.status].icon"
              size="22px"
              :class="{ 'sv-spin': step.status === 'processing' }"
              :style="{ color: STEP_META[step.status].fg }"
            />
          </span>
          <div class="sv-col step-body">
            <div class="row items-baseline step-title-row">
              <span class="step-n tabular">Этап {{ i + 1 }} из {{ analysis.steps.length }}</span>
              <span class="step-title">{{ step.title }}</span>
            </div>
            <span class="step-note">{{ STEP_NOTES[i] ?? '' }}</span>
            <div v-if="step.status === 'failed'" role="alert" class="step-error sv-col">
              <span>{{ errorText }}</span>
              <div class="row step-error-actions">
                <q-btn v-if="plan.kind !== 'reupload'" flat no-caps class="sv-btn sv-btn--primary" icon="refresh" label="Повторить запуск" :loading="restarting" @click="restart" />
                <q-btn flat no-caps :class="['sv-btn', plan.kind === 'reupload' ? 'sv-btn--primary' : 'sv-btn--ghost']" :icon="plan.kind === 'reupload' ? 'upload_file' : undefined" :label="plan.kind === 'reupload' ? 'Загрузить документы заново' : 'Вернуться к загрузке'" :to="{ name: 'new' }" />
              </div>
              <span v-if="plan.kind === 'reupload'" class="sv-meta">{{ REUPLOAD_NOTE }}</span>
            </div>
          </div>
          <span class="step-status" :style="{ color: STEP_META[step.status].fg }">{{ STEP_META[step.status].label }}</span>
        </li>
      </ol>

      <AgentTrace
        :entries="analysis.agent_trace ?? []"
        :quality-score="analysis.quality_score"
        :running="analysis.status === 'queued' || analysis.status === 'processing'"
      />

      <!-- Failure without a failed step in the payload (e.g. steps: []) -->
      <div v-if="failed && !hasFailedStep" role="alert" class="sv-banner sv-banner--err items-center">
        <q-icon name="error_outline" size="20px" />
        <div class="col sv-col">
          <span>{{ errorText }}</span>
          <span v-if="plan.kind === 'reupload'" class="sv-meta">{{ REUPLOAD_NOTE }}</span>
        </div>
        <q-btn v-if="plan.kind !== 'reupload'" flat no-caps class="sv-btn sv-btn--secondary" icon="refresh" label="Повторить запуск" :loading="restarting" @click="restart" />
        <q-btn v-else flat no-caps class="sv-btn sv-btn--secondary" icon="upload_file" label="Загрузить документы заново" :to="{ name: 'new' }" />
      </div>
    </div>

    <aside class="aside sv-col">
      <div class="sv-card sv-col aside-card">
        <span class="sv-meta">Прошло времени</span>
        <span class="clock tabular">{{ clock }}</span>
        <span class="sv-meta">Длительность зависит от объёма документов. Обычно — несколько минут.</span>
      </div>
      <div class="sv-card aside-card leave">
        <q-icon name="logout" size="20px" style="color: var(--sv-accent)" />
        <div class="sv-col" style="gap: 8px">
          <span class="leave-title">Можно закрыть страницу</span>
          <span class="sv-meta">Обработка идёт на сервере. Результат откроется по ссылке, пока сервер хранит этот анализ.</span>
          <q-btn flat no-caps class="sv-btn sv-btn--ghost self-start" style="margin-left: -8px" icon="link" label="Скопировать ссылку" @click="copyLink" />
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from 'vue'
import { useRouter } from 'vue-router'
import { copyToClipboard, useQuasar } from 'quasar'
import AgentTrace from '@/components/AgentTrace.vue'
import { createAnalysis } from '@/api/client'
import { useAnalysisContext } from '@/composables/analysisContext'
import { rememberRun, retryPlan, runSources } from '@/stores/draft'
import { FILES, STEP_META, STEP_NOTES, formatClock, pluralize } from '@/utils/labels'

const REUPLOAD_NOTE =
  'Исходные файлы этого анализа недоступны: страница обновлялась или анализ открыт по ссылке. ' +
  'Браузер не хранит документы — загрузите их заново.'

const { analysis } = useAnalysisContext()
const router = useRouter()
const $q = useQuasar()

const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
const meta = computed(() => (analysis.value ? runSources.get(analysis.value.id) : undefined))
const plan = computed(() => retryPlan(analysis.value?.id ?? ''))
const stageLabel = computed(() => {
  const steps = analysis.value?.steps ?? []
  if (!steps.length) return ''
  const active = steps.findIndex((s) => s.status === 'processing' || s.status === 'failed')
  const index = active >= 0 ? active + 1 : steps.filter((s) => s.status === 'completed').length
  return `Этап ${Math.max(index, 1)} из ${steps.length}`
})
const failed = computed(() => analysis.value?.status === 'failed')
const hasFailedStep = computed(() => analysis.value?.steps.some((s) => s.status === 'failed') ?? false)
const kicker = computed(() => {
  if (failed.value) return 'Анализ остановлен'
  if (analysis.value?.status === 'completed') return 'Обработка завершена'
  return 'Анализ выполняется'
})
const currentLabel = computed(() => {
  const a = analysis.value
  if (!a) return ''
  if (a.status === 'completed') return 'Все этапы выполнены — открываем результат'
  if (a.status === 'failed') {
    const step = a.steps.find((s) => s.status === 'failed')
    return `Ошибка на этапе «${step?.title ?? a.current_step}»`
  }
  return `Сейчас: ${a.current_step}`
})
const errorText = computed(() => {
  const error = analysis.value?.error
  if (error?.code === 'ANALYSIS_INTERRUPTED') {
    return 'Обработка была прервана (например, перезапуском сервиса). Автоматического продолжения нет — запустите анализ заново.'
  }
  const message = error?.message || 'Анализ остановлен из-за внутренней ошибки.'
  return error?.code ? `${message} (код: ${error.code})` : message
})

// Elapsed time only, no forecast.
const now = ref(Date.now())
const clockTimer = window.setInterval(() => {
  const status = analysis.value?.status
  if (status === 'queued' || status === 'processing') now.value = Date.now()
}, 1000)
onBeforeUnmount(() => window.clearInterval(clockTimer))
const clock = computed(() => {
  const created = analysis.value?.created_at ? Date.parse(analysis.value.created_at) : NaN
  return formatClock(Number.isNaN(created) ? 0 : now.value - created)
})

async function copyLink() {
  try {
    await copyToClipboard(window.location.href.replace(/\/run(\?.*)?$/, ''))
    $q.notify({ message: 'Ссылка на анализ скопирована', icon: 'check_circle' })
  } catch {
    $q.notify({ message: 'Не удалось скопировать — выделите текст вручную', icon: 'error_outline' })
  }
}

// The contract has no restart endpoint: resend exactly this run's files (see retryPlan).
const restarting = ref(false)
async function restart() {
  const p = plan.value
  if (p.kind === 'reupload') {
    await router.push({ name: 'new' })
    return
  }
  restarting.value = true
  try {
    const title = p.title || analysis.value?.title || ''
    const beforeFiles = p.kind === 'resend' ? p.before : []
    const afterFiles = p.kind === 'resend' ? p.after : []
    const created = await createAnalysis({ title, beforeFiles, afterFiles }, p.kind === 'demo')
    const old = runSources.get(analysis.value?.id ?? '')
    rememberRun(created.id, {
      mode: p.kind === 'demo' ? 'demo' : 'real', title, beforeFiles, afterFiles,
      beforeCount: old?.before ?? beforeFiles.length, afterCount: old?.after ?? afterFiles.length,
    })
    await router.replace({ name: 'run', params: { id: created.id } })
  } catch (error) {
    $q.notify({ message: error instanceof Error ? error.message : 'Не удалось перезапустить анализ', icon: 'error_outline' })
  } finally {
    restarting.value = false
  }
}
</script>

<style scoped lang="scss">
.page { padding-top: 32px; padding-bottom: 48px; }
.layout { display: flex; flex-wrap: wrap; gap: 32px; align-items: flex-start; }
.main { flex: 1 1 640px; min-width: 0; max-width: 880px; gap: 20px; }
.aside { flex: 1 1 280px; max-width: 360px; gap: 16px; }
@media (max-width: 1023px) { .aside { max-width: none; flex-direction: row; flex-wrap: wrap; > * { flex: 1 1 260px; } } }
.head { gap: 8px; }
.run-title { font-size: 30px; }
.sets { gap: 8px; margin-top: 4px; }
.set-chip {
  display: inline-flex; align-items: center; gap: 6px; font-size: 12px; padding: 4px 10px; border: 1px solid var(--sv-border);
  border-radius: 6px; background: var(--sv-surface); white-space: nowrap;
  b { font-weight: 600; font-size: 11px; letter-spacing: .06em; }
}
.progress-box { gap: 8px; }
.pct { font-size: 18px; font-weight: 500; }
.bar { height: 6px; background: var(--sv-divider); border-radius: 3px; overflow: hidden;
  div { height: 100%; transition: width .3s ease-out; } }
.steps { list-style: none; margin: 0; padding: 0; overflow: hidden; }
.step {
  display: grid; grid-template-columns: 40px minmax(0, 1fr) auto; gap: 4px 12px; padding: 16px 18px;
  border-bottom: 1px solid var(--sv-line); align-items: start;
  &:last-child { border-bottom: 0; }
}
.step--processing { background: var(--sv-accent-tint); }
.step--failed { background: var(--sv-high-row); }
.step-icon { width: 28px; height: 28px; display: grid; place-items: center; }
.step-body { gap: 3px; min-width: 0; }
.step-title-row { gap: 8px; flex-wrap: wrap; }
.step-n { font-size: 11px; color: var(--sv-muted); }
.step-title { font-size: 15px; font-weight: 500; }
.step--pending .step-title { color: var(--sv-muted); }
.step-note { font-size: 13px; line-height: 1.5; color: var(--sv-muted); }
.step-status { font-size: 12px; font-weight: 500; padding-top: 2px; white-space: nowrap; }
.step--pending .step-status { color: var(--sv-muted) !important; }
.step-error {
  margin-top: 8px; gap: 10px; padding: 12px; border: 1px solid var(--sv-high-border); background: var(--sv-high-bg);
  border-radius: 6px; font-size: 13px; line-height: 1.5; color: var(--sv-high-text);
}
.step-error-actions { gap: 8px; flex-wrap: wrap; }
.aside-card { padding: 18px; gap: 6px; }
.clock { font-size: 32px; font-weight: 500; letter-spacing: -.01em; }
.leave { display: grid; grid-template-columns: 24px 1fr; gap: 10px; }
.leave-title { font-size: 14px; font-weight: 500; }
@media (max-width: 599px) {
  .page { padding-top: 20px; }
  .run-title { font-size: 24px; }
  .step { grid-template-columns: 32px minmax(0, 1fr); padding: 14px; }
  .step-status { grid-column: 2; }
}
</style>
