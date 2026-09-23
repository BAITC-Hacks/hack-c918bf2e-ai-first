<template>
  <section class="panel">
    <header class="panel-head">
      <h2 class="panel-title">Работа агента</h2>
      <q-space />
      <span class="text-caption muted tabular">{{ doneCount }} из {{ steps.length }} шагов</span>
    </header>
    <div class="panel-body">
      <div class="row items-center q-mb-sm">
        <div class="text-body2">
          <span class="muted">Текущий шаг:</span>
          <span class="text-weight-medium q-ml-xs">{{ currentStep || '—' }}</span>
        </div>
        <q-space />
        <div class="text-h6 tabular">{{ progress }}%</div>
      </div>
      <q-linear-progress
        :value="progress / 100"
        size="8px"
        rounded
        :color="failed ? 'negative' : 'primary'"
        track-color="grey-3"
        :indeterminate="status === 'queued'"
        class="q-mb-lg"
      />

      <ol class="steps">
        <li v-for="(step, index) in steps" :key="step.code" class="step" :class="`step--${step.status}`">
          <div class="step-marker">
            <q-spinner v-if="step.status === 'processing'" size="22px" color="primary" />
            <q-icon v-else :name="STEP_ICON[step.status]" size="22px" />
          </div>
          <div class="step-body">
            <div class="step-title">
              <span class="muted tabular q-mr-xs">{{ index + 1 }}.</span>{{ step.title }}
            </div>
            <div class="text-caption muted">{{ STEP_HINT[step.code] ?? '' }}</div>
          </div>
          <div class="step-state text-caption">{{ STEP_LABEL[step.status] }}</div>
        </li>
      </ol>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { AnalysisStatus, AnalysisStep, StepStatus } from '@/api/types'
import { STEP_HINT, STEP_ICON } from '@/utils/labels'

const STEP_LABEL: Record<StepStatus, string> = {
  pending: 'Ожидает',
  processing: 'Выполняется',
  completed: 'Готово',
  failed: 'Ошибка',
}

const props = defineProps<{ steps: AnalysisStep[]; progress: number; currentStep: string; status: AnalysisStatus }>()

const doneCount = computed(() => props.steps.filter((s) => s.status === 'completed').length)
const failed = computed(() => props.status === 'failed')
</script>

<style scoped lang="scss">
.steps { list-style: none; margin: 0; padding: 0; }
.step {
  display: grid; grid-template-columns: 32px 1fr auto; gap: 12px; align-items: start;
  padding: 12px 0; position: relative;
  & + & { border-top: 1px solid var(--c-border); }
}
.step-marker { display: flex; justify-content: center; padding-top: 1px; color: #a3aebb; }
.step-title { font-weight: 500; }
.step-state { color: var(--c-muted); padding-top: 2px; }
.step--completed .step-marker { color: $positive; }
.step--processing { .step-title, .step-state { color: $primary; } }
.step--failed { .step-marker, .step-state, .step-title { color: $negative; } }
.step--pending .step-title { color: var(--c-muted); }
</style>
