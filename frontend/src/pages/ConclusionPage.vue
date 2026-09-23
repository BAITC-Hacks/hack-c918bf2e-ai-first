<template>
  <div v-if="analysis && model" class="sv-container page layout">
    <article class="sv-card doc sv-col">
      <div v-if="model.demo" role="note" class="demo-mark">
        <q-icon name="dataset" size="18px" />{{ DEMO_NOTICE }}
      </div>
      <div class="sv-col" style="gap: 6px">
        <span class="sv-overline">Аналитическое заключение</span>
        <h2 class="doc-title">{{ analysis.title || 'Анализ без названия' }}</h2>
        <span class="sv-small sv-muted">{{ metaLine }}</span>
      </div>

      <section class="limits" :class="`limits--${model.coverage.kind}`" aria-labelledby="limits-h">
        <h3 id="limits-h" class="limits-title row items-center no-wrap">
          <q-icon :name="model.coverage.kind === 'complete' ? 'info' : 'report_problem'" size="18px" />Ограничения результата
        </h3>
        <ul>
          <li v-for="(l, i) in model.limitations" :key="i">{{ l }}</li>
        </ul>
      </section>

      <section class="sec">
        <span class="num tabular">01</span>
        <div class="sv-col sec-body">
          <h3 class="sec-title">Резюме</h3>
          <p v-for="(p, i) in model.summary" :key="i" class="para">{{ p }}</p>
          <p v-if="!model.summary.length" class="para sv-muted">Текст резюме не получен.</p>
        </div>
      </section>

      <section class="sec">
        <span class="num tabular">02</span>
        <div class="sv-col sec-body">
          <h3 class="sec-title">Ключевые риски</h3>
          <div v-if="model.keyRisks.length" class="risks sv-col">
            <button v-for="f in model.keyRisks" :key="f.id" type="button" class="risk-row" @click="openFinding(f.id, 'all')">
              <TypeLabel :type="f.type" class="risk-type" />
              <span class="sv-col" style="gap: 1px; min-width: 0">
                <span class="risk-title">{{ f.title }}</span>
                <span class="sv-meta">{{ sourceLine(f.before ?? f.after) }}</span>
              </span>
              <span class="risk-id row items-center no-wrap">{{ labelOf(f.id) }}<q-icon name="chevron_right" size="16px" /></span>
            </button>
          </div>
          <p v-else class="para">В принятых выводах нет отклонений высокого риска.</p>
        </div>
      </section>

      <section class="sec">
        <span class="num tabular">03</span>
        <div class="sv-col sec-body">
          <h3 class="sec-title">Полнота распределения функций</h3>
          <p class="para">{{ model.completeness }}</p>
        </div>
      </section>

      <section class="sec">
        <span class="num tabular">04</span>
        <div class="sv-col sec-body">
          <h3 class="sec-title">Потенциальные риски внутри редакции</h3>
          <p class="para">{{ model.risks.headline }}</p>
          <template v-if="model.risks.kind === 'present'">
            <span class="sv-meta">{{ RISKS_CAVEAT }}</span>
            <ol class="list risks-list">
              <li v-for="r in model.risks.risks" :key="r.id">
                <div class="row items-center risk-line">
                  <span class="risk-kind" :class="`risk-kind--${r.kind}`"><q-icon :name="RISK_KIND_META[r.kind].icon" size="15px" />{{ RISK_KIND_META[r.kind].label }}</span>
                  <span class="sv-meta">{{ SEVERITY_META[r.severity].label }} риск · {{ r.id }}</span>
                </div>
                <b class="risk-name">{{ r.title }}.</b> {{ r.explanation }}
                <ul class="risk-sources">
                  <li v-for="(item, i) in r.evidence" :key="i">
                    <span class="src">{{ riskSourceLine(item) }}</span> — «{{ item.evidence.quote }}»
                  </li>
                </ul>
                <div class="risk-reco">
                  Рекомендация: {{ r.recommendation }}
                  <span class="confirm"><q-icon name="person_search" size="13px" />требует подтверждения</span>
                </div>
              </li>
            </ol>
          </template>
          <template v-if="model.conflicts.length">
            <span class="sv-meta">{{ LEGACY_DUPLICATE_NOTE }}</span>
            <ol class="list">
              <li v-for="f in model.conflicts" :key="f.id">
                {{ f.explanation }}
                <button type="button" class="inline-link" @click="openFinding(f.id, 'all')">{{ labelOf(f.id) }}</button>
              </li>
            </ol>
          </template>
        </div>
      </section>

      <section class="sec">
        <span class="num tabular">05</span>
        <div class="sv-col sec-body">
          <h3 class="sec-title">Рекомендации</h3>
          <span class="sv-meta">Каждая рекомендация требует подтверждения ответственным сотрудником.</span>
          <ol v-if="model.recommendations.length" class="list">
            <li v-for="(r, i) in model.recommendations" :key="i">
              {{ r }}
              <span class="confirm"><q-icon name="person_search" size="13px" />требует подтверждения</span>
            </li>
          </ol>
          <p v-else class="para">Рекомендаций по отклонениям высокого и среднего риска нет.</p>
        </div>
      </section>

      <footer class="disclaimer">
        Заключение сформировано ИИ-агентом «Сверка» и носит рекомендательный характер. Выводы подлежат проверке
        ответственным сотрудником до принятия решения.
        <template v-if="model.demo"><br /><b>{{ DEMO_NOTICE }}</b></template>
      </footer>
    </article>

    <aside class="aside sv-col no-print">
      <q-btn flat no-caps class="sv-btn sv-btn--primary sv-btn--lg" icon="content_copy" label="Копировать текст" @click="copy" />
      <q-btn flat no-caps class="sv-btn sv-btn--secondary sv-btn--lg" icon="print" label="Печать / экспорт в PDF" @click="print" />
      <div class="sv-card qc sv-col">
        <span class="sv-overline sv-overline--muted">Контроль качества</span>
        <div v-if="analysis.quality_score != null" class="qc-item">
          <q-icon name="fact_check" size="17px" style="color: var(--sv-accent)" />
          <span>
            Оценка критика: <b class="tabular">{{ Math.round(analysis.quality_score * 100) }}%</b>{{ revisionNote }}
            <span class="sv-muted">Это суждение LLM-контролёра, а не измеренная точность.</span>
          </span>
        </div>
        <div v-for="(w, i) in warnings" :key="i" class="qc-item">
          <q-icon :name="isQcWarning(w) ? 'rule' : 'info'" size="17px" :style="{ color: isQcWarning(w) ? 'var(--sv-medium)' : 'var(--sv-muted)' }" />
          <span>{{ w }}</span>
        </div>
        <span v-if="!warnings.length && analysis.quality_score == null" class="sv-meta">Замечаний контроля качества нет.</span>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { copyToClipboard, useQuasar } from 'quasar'
import TypeLabel from '@/components/TypeLabel.vue'
import { useAnalysisContext } from '@/composables/analysisContext'
import { LEGACY_DUPLICATE_NOTE, buildConclusion, conclusionPlainText, sourceLine } from '@/utils/conclusion'
import { RISKS_CAVEAT, RISK_KIND_META, riskSourceLine } from '@/utils/risks'
import { DEMO_NOTICE } from '@/utils/demo'
import { isQcWarning } from '@/utils/findings'
import { revisionOutcome } from '@/utils/trace'
import { FINDINGS_WORD, SEVERITY_META, pluralize } from '@/utils/labels'

const { analysis, openFinding, labelOf } = useAnalysisContext()
const $q = useQuasar()

const model = computed(() => (analysis.value ? buildConclusion(analysis.value, labelOf) : null))
const warnings = computed(() => analysis.value?.warnings ?? [])
const revisionNote = computed(() => {
  switch (revisionOutcome(analysis.value?.agent_trace ?? [])) {
    case 'accepted': return ' — после исправления по замечаниям.'
    case 'rolled_back': return ' — исправление отклонено, сохранена лучшая версия.'
    case 'revised': return ' — после исправления по замечаниям критика.'
    case 'none': return ' — исправления не потребовались.'
    default: return '.'
  }
})
const metaLine = computed(() => {
  const a = analysis.value
  if (!a) return ''
  const date = a.created_at ? new Date(a.created_at).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : ''
  const n = a.findings?.length ?? 0
  return [date, `${n} ${pluralize(n, FINDINGS_WORD)}`, a.summary ? `${a.summary.high_risk} высокого риска` : ''].filter(Boolean).join(' · ')
})

async function copy() {
  if (!analysis.value || !model.value) return
  try {
    await copyToClipboard(conclusionPlainText(analysis.value, model.value, labelOf))
    $q.notify({ message: 'Заключение скопировано в буфер обмена', icon: 'check_circle' })
  } catch {
    $q.notify({ message: 'Не удалось скопировать — выделите текст вручную', icon: 'error_outline' })
  }
}

function print() {
  window.print()
}
</script>

<style scoped lang="scss">
.page { padding-top: 20px; padding-bottom: 48px; }
.layout { display: flex; flex-wrap: wrap; gap: 32px; align-items: flex-start; }
.doc { flex: 1 1 640px; max-width: 860px; min-width: 0; padding: 36px 40px; gap: 28px; }
.doc-title { font-size: 26px; font-weight: 500; letter-spacing: -.015em; line-height: 1.25; }
.aside { flex: 1 1 260px; max-width: 320px; position: sticky; top: 76px; gap: 12px; }
.sec { display: grid; grid-template-columns: 36px minmax(0, 1fr); gap: 4px 12px; }
.num { font-size: 13px; color: var(--sv-muted); padding-top: 3px; }
.sec-body { gap: 10px; min-width: 0; }
.sec-title { font-size: 18px; font-weight: 500; }
.para { margin: 0; font-size: 15px; line-height: 1.65; text-wrap: pretty; }
.risks { border: 1px solid var(--sv-divider); border-radius: 8px; overflow: hidden; }
.risk-row {
  display: grid; grid-template-columns: 150px minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 10px 12px;
  border: 0; border-bottom: 1px solid var(--sv-line); background: var(--sv-surface); text-align: left; font: inherit;
  cursor: pointer; color: var(--sv-text);
  &:last-child { border-bottom: 0; }
  &:hover { background: var(--sv-accent-tint); }
}
.risk-type { font-size: 12px; }
.risk-title { font-size: 14px; }
.risk-id { font-size: 12px; color: var(--sv-accent); gap: 2px; }
.list { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; font-size: 15px; line-height: 1.55; li { padding-left: 4px; } }
.inline-link { background: none; border: 0; padding: 0 2px; font: inherit; font-size: 13px; color: var(--sv-accent); cursor: pointer; text-decoration: underline; }
.confirm {
  margin-left: 8px; display: inline-flex; align-items: center; gap: 3px; font-size: 11px; color: var(--sv-medium);
  border: 1px solid var(--sv-medium-border); background: var(--sv-medium-bg); border-radius: 5px; padding: 1px 6px; vertical-align: 2px;
  white-space: nowrap;
}
.risks-list > li { padding-left: 4px; }
.risk-line { gap: 8px; margin-bottom: 2px; }
.risk-kind { display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 600; }
.risk-kind--duplicate { color: var(--sv-duplicate); }
.risk-kind--conflict_interest { color: var(--sv-medium); }
.risk-name { font-weight: 500; }
.risk-sources { margin: 6px 0; padding-left: 18px; font-size: 13px; line-height: 1.5; color: var(--sv-text-2); .src { color: var(--sv-text); font-weight: 500; } }
.risk-reco { font-size: 14px; }
.demo-mark {
  display: flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;
  background: var(--sv-accent-tint); color: var(--sv-accent-strong); border: 1px solid var(--sv-accent-border);
}
.limits { padding: 12px 14px; border: 1px solid var(--sv-divider); border-radius: 8px; background: var(--sv-sunken);
  ul { margin: 6px 0 0; padding-left: 18px; font-size: 13px; line-height: 1.55; color: var(--sv-text-2); display: flex; flex-direction: column; gap: 2px; } }
.limits--incomplete { background: var(--sv-medium-bg); border-color: var(--sv-medium-border); .limits-title { color: var(--sv-medium-text); } }
.limits-title { gap: 6px; font-size: 14px; font-weight: 600; }
@media print { .demo-mark, .limits { break-inside: avoid; -webkit-print-color-adjust: exact; print-color-adjust: exact; } }
.disclaimer { font-size: 12px; line-height: 1.5; color: var(--sv-muted); border-top: 1px solid var(--sv-divider); padding-top: 14px; }
.qc { padding: 14px 16px; gap: 10px; }
.qc-item { display: grid; grid-template-columns: 20px 1fr; gap: 8px; font-size: 12px; line-height: 1.5; color: var(--sv-text-2); }

// 600–1023: actions above the document, horizontally.
@media (max-width: 1023px) {
  .aside { order: -1; max-width: none; position: static; flex-direction: row; flex-wrap: wrap; flex-basis: 100%;
    > .q-btn { flex: 1 1 220px; } .qc { flex-basis: 100%; } }
  .doc { max-width: none; }
}
@media (max-width: 599px) {
  .aside { order: 1; flex-direction: column; }
  .doc { padding: 20px 16px; }
  .sec { grid-template-columns: 1fr; }
  .risk-row { grid-template-columns: minmax(0, 1fr) auto; .risk-type { grid-column: 1 / -1; } }
}
@media print {
  .doc { border: 0; padding: 0; max-width: none; }
  .page { padding: 0; }
}
</style>
