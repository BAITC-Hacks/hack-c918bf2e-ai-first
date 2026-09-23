<template>
  <section id="structural-risks" class="sv-col section" aria-labelledby="risks-h">
    <div class="row items-baseline head">
      <h2 id="risks-h" class="sv-h2">Потенциальные риски внутри редакции</h2>
      <div v-if="state.kind === 'present'" class="row counts">
        <span v-for="k in RISK_KIND_ORDER" :key="k" class="row items-center no-wrap">
          <q-icon :name="RISK_KIND_META[k].icon" size="16px" />{{ RISK_KIND_META[k].label }}
          <b class="tabular">{{ state.byKind[k] }}</b>
        </span>
        <span class="sv-muted">·</span>
        <span v-for="s in SEVERITIES" v-show="state.bySeverity[s]" :key="s" class="row items-center no-wrap">
          {{ SEVERITY_META[s].label }} риск <b class="tabular">{{ state.bySeverity[s] }}</b>
        </span>
      </div>
    </div>

    <div v-if="state.kind !== 'present'" class="sv-card empty row no-wrap items-start">
      <q-icon :name="state.kind === 'missing' ? 'help_outline' : 'inbox'" size="22px" class="sv-muted" />
      <span class="sv-small sv-text-2">{{ state.headline }}</span>
    </div>

    <template v-else>
      <p class="sv-small sv-text-2 caveat">{{ RISKS_CAVEAT }} Эти записи не входят в счётчики и таблицу отклонений.</p>

      <article v-for="r in state.risks" :key="r.id" class="sv-card risk sv-col" :aria-labelledby="`risk-${r.id}`">
        <div class="row items-center chips">
          <RiskChip :severity="r.severity" suffix=" риск" />
          <span class="sv-chip kind" :class="`kind--${r.kind}`">
            <q-icon :name="RISK_KIND_META[r.kind].icon" />{{ RISK_KIND_META[r.kind].label }}
          </span>
          <span class="sv-chip conf" title="Уверенность ИИ-агента в выводе">
            <q-icon name="speed" class="sv-muted" />Уверенность ИИ {{ percent(r.confidence) }} · {{ confidenceLevel(r.confidence) }}
          </span>
          <q-space />
          <span class="sv-meta tabular">{{ r.id }}</span>
        </div>
        <h3 :id="`risk-${r.id}`" class="risk-title">{{ r.title }}</h3>
        <p class="explanation">{{ r.explanation }}</p>
        <span v-if="r.kind === 'conflict_interest'" class="sv-meta">{{ RISK_KIND_META.conflict_interest.note }}</span>

        <div class="sv-col" style="gap: 8px">
          <span class="dr-h3">Доказательства · {{ r.evidence.length }}</span>
          <ul class="ev-list">
            <li v-for="(item, i) in r.evidence" :key="i" class="ev-item">
              <div class="row items-center ev-meta">
                <span class="sv-badge-ink" :title="item.side === 'before' ? 'Комплект до' : 'Комплект после'">{{ riskSideLabel(item) }}</span>
                <q-icon :name="docIcon(item.evidence.document)" size="15px" class="sv-muted" />
                <span class="ev-doc">{{ item.evidence.document }}</span>
                <span v-if="item.evidence.clause" class="ev-loc">{{ locatorLabel(item.evidence.clause) }}</span>
                <span v-if="item.evidence.page" class="sv-meta">стр. {{ item.evidence.page }}</span>
                <span v-if="item.evidence.department" class="sv-meta">· {{ item.evidence.department }}</span>
              </div>
              <blockquote class="ev-quote">«{{ item.evidence.quote }}»</blockquote>
            </li>
          </ul>
        </div>

        <div class="reco sv-col">
          <div class="row items-center no-wrap reco-head">
            <q-icon name="person_search" size="18px" style="color: var(--sv-medium)" />
            <span>Рекомендация · требует проверки специалистом</span>
          </div>
          <p class="reco-text">{{ r.recommendation }}</p>
        </div>
      </article>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Analysis, Severity } from '@/api/types'
import RiskChip from './RiskChip.vue'
import { locatorLabel } from '@/utils/findings'
import { SEVERITY_META, confidenceLevel, docIcon, percent } from '@/utils/labels'
import { RISKS_CAVEAT, RISK_KIND_META, RISK_KIND_ORDER, riskSideLabel, riskState } from '@/utils/risks'

const props = defineProps<{ analysis: Analysis }>()
const SEVERITIES: Severity[] = ['high', 'medium', 'low', 'info']
const state = computed(() => riskState(props.analysis))
</script>

<style scoped lang="scss">
.section { gap: 12px; scroll-margin-top: 72px; }
.head { gap: 8px 16px; flex-wrap: wrap; }
.counts { gap: 6px 14px; font-size: 13px; color: var(--sv-text-2); flex-wrap: wrap; > span { gap: 4px; } b { font-weight: 600; color: var(--sv-text); } }
.empty { gap: 10px; padding: 14px 16px; }
.caveat { margin: 0; }
.risk { padding: 14px 18px; gap: 8px; }
.chips { gap: 6px; flex-wrap: wrap; }
.kind { font-weight: 500; }
.kind--duplicate { background: var(--sv-duplicate-bg); color: var(--sv-duplicate); }
.kind--conflict_interest { background: var(--sv-medium-bg); color: var(--sv-medium); border-color: var(--sv-medium-border); }
.conf { border-color: var(--sv-border); color: var(--sv-text-2); font-weight: 400; }
.risk-title { font-size: 17px; line-height: 1.35; font-weight: 500; letter-spacing: normal; }
.explanation { margin: 0; font-size: 14px; line-height: 1.55; }
.dr-h3 { font-size: 12px; letter-spacing: .06em; text-transform: uppercase; color: var(--sv-text-2); font-weight: 500; }
.ev-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 8px; }
.ev-item { border: 1px solid var(--sv-divider); border-radius: 8px; padding: 8px 12px; background: var(--sv-sunken); min-width: 0; }
.ev-meta { gap: 6px; flex-wrap: wrap; font-size: 12px; }
.ev-doc { overflow-wrap: anywhere; }
.ev-loc { font-weight: 600; }
.ev-quote { margin: 6px 0 0; font-size: 14px; line-height: 1.5; color: var(--sv-text); }
.reco { gap: 6px; padding: 12px 14px; border: 1px solid var(--sv-medium-border); background: var(--sv-medium-bg); border-radius: 8px; }
.reco-head { gap: 8px; color: var(--sv-medium-text); font-size: 13px; font-weight: 600; }
.reco-text { margin: 0; font-size: 14px; line-height: 1.55; color: var(--sv-text); }
@media (max-width: 599px) { .ev-list { grid-template-columns: 1fr; } .risk { padding: 14px; } }
@media print { .risk { break-inside: avoid; } }
</style>
