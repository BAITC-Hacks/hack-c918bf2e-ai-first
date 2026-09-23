<template>
  <div v-if="analysis" class="sv-container page sv-col">
    <div class="sv-banner sv-banner--warn">
      <q-icon name="info" />
      <span class="col">
        Выводы сформированы ИИ-агентом и носят рекомендательный характер. Каждый вывод подтверждён цитатой из документа;
        решение принимает ответственный сотрудник.
      </span>
    </div>

    <SummaryStrip
      v-if="analysis.summary"
      :summary="analysis.summary"
      :active="filters.types.length === 1 ? filters.types[0] : null"
      @show-high="showHigh"
      @toggle-type="toggleType"
    />

    <AgentTrace
      v-if="analysis.agent_trace?.length || analysis.quality_score != null"
      :entries="analysis.agent_trace ?? []"
      :quality-score="analysis.quality_score"
    />

    <OrgMap :changes="analysis.organization_changes ?? []" />

    <FunctionRegistry v-if="analysis.function_registry" :registry="analysis.function_registry" />

    <div class="sv-col" style="gap: 12px">
      <FindingsTable :before-count="analysis.summary?.before_functions ?? 0" />

      <div v-if="qcWarnings.length" class="qc">
        <q-icon name="rule" size="20px" class="sv-muted" />
        <div class="sv-col" style="gap: 2px">
          <span class="qc-title">Исключено контролем качества: {{ qcWarnings.length }}</span>
          <span v-for="(w, i) in qcWarnings" :key="i" class="sv-small sv-text-2">{{ w }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick } from 'vue'
import AgentTrace from '@/components/AgentTrace.vue'
import FindingsTable from '@/components/FindingsTable.vue'
import FunctionRegistry from '@/components/FunctionRegistry.vue'
import OrgMap from '@/components/OrgMap.vue'
import SummaryStrip from '@/components/SummaryStrip.vue'
import type { FindingType } from '@/api/types'
import { useAnalysisContext } from '@/composables/analysisContext'
import { isQcWarning } from '@/utils/findings'

const { analysis, filters } = useAnalysisContext()

const qcWarnings = computed(() => (analysis.value?.warnings ?? []).filter(isQcWarning))

async function scrollToTable() {
  await nextTick()
  const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  document.getElementById('findings')?.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
}

function showHigh() {
  filters.risk = 'high'
  filters.types = []
  void scrollToTable()
}

function toggleType(type: FindingType) {
  const only = filters.types.length === 1 && filters.types[0] === type
  filters.types = only ? [] : [type]
  if (!only) void scrollToTable()
}
</script>

<style scoped lang="scss">
.page { padding-top: 18px; padding-bottom: 48px; gap: 28px; }
.qc {
  display: grid; grid-template-columns: 24px 1fr; gap: 10px; padding: 12px 16px; border: 1px dashed var(--sv-dashed);
  border-radius: 8px; background: var(--sv-sunken);
}
.qc-title { font-size: 14px; font-weight: 500; }
</style>
