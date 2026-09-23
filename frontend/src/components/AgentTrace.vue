<template>
  <section class="sv-card trace" :aria-labelledby="headingId">
    <header class="trace-head row items-center">
      <q-icon name="account_tree" size="20px" style="color: var(--sv-accent)" />
      <h2 :id="headingId" class="trace-title">Работа агентов</h2>
      <span v-if="outcomeLabel" class="sv-chip outcome" :class="`outcome--${outcome}`">
        <q-icon :name="outcomeIcon" />{{ outcomeLabel }}
      </span>
      <q-space />
      <span v-if="qualityScore != null" class="score row items-center no-wrap" title="Суждение LLM-контролёра, а не измеренная точность">
        <q-icon name="fact_check" size="16px" class="sv-muted" />Оценка критика
        <b class="tabular">{{ Math.round(qualityScore * 100) }}%</b>
      </span>
    </header>

    <ol v-if="items.length" class="trace-list">
      <li v-for="(t, i) in items" :key="t.key" class="item" :class="[`tone--${t.tone}`, { 'item--last': i === items.length - 1 }]">
        <span class="rail" aria-hidden="true">
          <span class="dot"><q-icon :name="t.icon" size="16px" /></span>
        </span>
        <div class="sv-col body">
          <div class="row items-baseline item-head">
            <span class="item-label">{{ t.label }}</span>
            <span class="sv-meta">{{ t.agent }}</span>
            <q-space />
            <span class="status row items-center no-wrap" :class="`status--${t.status}`">
              <q-icon :name="t.statusIcon" size="15px" :class="{ 'sv-spin': t.status === 'processing' || t.status === 'running' }" />
              {{ t.statusLabel }}
            </span>
          </div>
          <p v-if="t.summary" class="summary">{{ t.summary }}</p>
        </div>
      </li>
      <li v-if="running" class="item item--waiting">
        <span class="rail" aria-hidden="true"><span class="dot dot--wait"><q-icon name="more_horiz" size="16px" /></span></span>
        <span class="sv-meta">Агенты продолжают работу — новые шаги появятся здесь.</span>
      </li>
    </ol>

    <div v-else class="empty sv-meta row items-center no-wrap">
      <q-icon name="hourglass_empty" size="18px" class="q-mr-sm" />
      {{ running ? 'Журнал агентов появится, когда сервис передаст первые шаги.' : 'Сервис не передал журнал работы агентов для этого анализа.' }}
    </div>

    <footer class="foot sv-meta">
      Показаны только итоги шагов. Внутренние инструкции моделей и промежуточные рассуждения не отображаются.
      Оценка критика — суждение LLM-контролёра, а не измеренная точность.
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTraceEntry } from '@/api/types'
import { revisionOutcome, toTraceView } from '@/utils/trace'

const props = defineProps<{ entries: AgentTraceEntry[]; qualityScore?: number | null; running?: boolean }>()

const headingId = `trace-${Math.random().toString(36).slice(2, 8)}`
const items = computed(() => toTraceView(props.entries))
const outcome = computed(() => revisionOutcome(props.entries, props.running))
const outcomeLabel = computed(() => {
  switch (outcome.value) {
    case 'none': return props.running ? '' : 'Исправления не потребовались'
    case 'accepted': return 'Исправление принято'
    case 'rolled_back': return 'Откат к лучшей версии'
    case 'pending': return 'Идёт исправление'
    case 'revised': return 'Выполнено исправление'
    default: return ''
  }
})
const outcomeIcon = computed(() =>
  ({ none: 'check', accepted: 'task_alt', rolled_back: 'undo', pending: 'edit_note', revised: 'edit_note' })[outcome.value ?? 'none'] ?? 'check',
)
</script>

<style scoped lang="scss">
.trace { padding: 18px 20px 14px; display: flex; flex-direction: column; gap: 14px; }
.trace-head { gap: 8px 10px; flex-wrap: wrap; }
.trace-title { font-size: 16px; line-height: 1.3; font-weight: 500; letter-spacing: normal; }
.outcome { border-color: var(--sv-border); color: var(--sv-text-2); }
.outcome--accepted { background: var(--sv-low-bg); border-color: var(--sv-low-border); color: var(--sv-low); }
.outcome--revised { background: var(--sv-accent-tint); border-color: var(--sv-accent-border); color: var(--sv-accent-strong); }
.outcome--rolled_back, .outcome--pending { background: var(--sv-medium-bg); border-color: var(--sv-medium-border); color: var(--sv-medium); }
.score { gap: 6px; font-size: 13px; color: var(--sv-text-2); b { font-size: 15px; font-weight: 600; color: var(--sv-text); } }
.trace-list { list-style: none; margin: 0; padding: 0; }
.item { display: grid; grid-template-columns: 28px minmax(0, 1fr); gap: 12px; position: relative; padding-bottom: 14px; }
.item--last:not(:has(+ .item--waiting)) { padding-bottom: 0; }
.rail { position: relative; display: flex; justify-content: center; }
.item:not(.item--last) .rail::after, .item--last:has(+ .item--waiting) .rail::after {
  content: ''; position: absolute; top: 28px; bottom: -14px; width: 1px; background: var(--sv-divider);
}
.dot {
  width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center;
  border: 1px solid var(--sv-border); background: var(--sv-surface); color: var(--sv-muted);
}
.tone--accent .dot { color: var(--sv-accent); border-color: var(--sv-accent-border); background: var(--sv-accent-tint); }
.tone--positive .dot { color: var(--sv-low); border-color: var(--sv-low-border); background: var(--sv-low-bg); }
.tone--warning .dot { color: var(--sv-medium); border-color: var(--sv-medium-border); background: var(--sv-medium-bg); }
.dot--wait { border-style: dashed; border-color: var(--sv-dashed); background: transparent; }
.item--waiting { align-items: center; padding-bottom: 0; }
.body { gap: 2px; padding-top: 3px; }
.item-head { gap: 4px 10px; flex-wrap: wrap; }
.item-label { font-size: 14px; font-weight: 500; }
.status { gap: 4px; font-size: 12px; color: var(--sv-muted); }
.status--completed { color: var(--sv-low); }
.status--failed { color: var(--sv-high); }
.status--processing, .status--running { color: var(--sv-accent); }
.summary { margin: 0; font-size: 13px; line-height: 1.5; color: var(--sv-text-2); text-wrap: pretty; }
.empty { padding: 6px 0; }
.foot { border-top: 1px solid var(--sv-line); padding-top: 10px; }
@media (max-width: 599px) { .trace { padding: 14px; } }
</style>
