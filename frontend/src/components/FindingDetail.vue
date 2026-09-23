<template>
  <section class="panel detail">
    <template v-if="finding">
      <header class="panel-head">
        <span class="sev-dot" :class="`bg-${sev.color}`" />
        <span class="text-caption text-weight-medium">{{ sev.label }} риск</span>
        <q-badge :class="`bg-${type.color}-soft text-${type.color}`" class="q-py-xs q-px-sm">
          <q-icon :name="type.icon" size="14px" class="q-mr-xs" />{{ type.label }}
        </q-badge>
        <q-space />
        <q-btn v-if="closable" flat round dense icon="close" aria-label="Закрыть" @click="$emit('close')" />
      </header>

      <div class="panel-body column q-gutter-y-md">
        <h3 class="detail-title">{{ finding.title }}</h3>

        <div>
          <div class="row items-center q-mb-xs">
            <span class="text-caption muted">Уверенность агента</span>
            <q-space />
            <span class="text-caption text-weight-medium tabular" :class="`text-${conf.color}`">
              {{ percent(finding.confidence) }} · {{ conf.label }}
            </span>
          </div>
          <q-linear-progress :value="finding.confidence" :color="conf.color" track-color="grey-3" rounded size="6px" />
        </div>

        <div>
          <div class="eyebrow q-mb-xs">Обоснование</div>
          <p class="q-mb-none text-body2" style="line-height: 1.55">{{ finding.explanation }}</p>
        </div>

        <div>
          <div class="eyebrow q-mb-sm">Доказательства из документов</div>
          <div class="row q-col-gutter-sm">
            <div class="col-12" :class="{ 'col-md-6': !stacked }">
              <EvidenceCard :evidence="finding.before" :label="labels[0]" :empty-text="emptyBefore" />
            </div>
            <div class="col-12" :class="{ 'col-md-6': !stacked }">
              <EvidenceCard :evidence="finding.after" :label="labels[1]" :empty-text="emptyAfter" />
            </div>
          </div>
        </div>

        <div class="recommendation">
          <div class="row items-center no-wrap q-mb-xs">
            <q-icon name="task_alt" color="primary" size="18px" class="q-mr-sm" />
            <span class="text-weight-medium">Рекомендация</span>
          </div>
          <div class="text-body2">{{ finding.recommendation }}</div>
        </div>
      </div>
    </template>

    <div v-else class="column items-center justify-center text-center detail-empty">
      <q-icon name="ads_click" size="40px" color="grey-5" />
      <div class="text-body1 q-mt-sm">Выберите отклонение в таблице</div>
      <div class="text-caption muted">Здесь появятся цитаты «до/после», уверенность и рекомендация</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { Finding } from '@/api/types'
import EvidenceCard from './EvidenceCard.vue'
import { SEVERITY_META, TYPE_META, confidenceLevel, percent } from '@/utils/labels'

const props = defineProps<{ finding: Finding | null; closable?: boolean; stacked?: boolean }>()
defineEmits<{ close: [] }>()

const sev = computed(() => SEVERITY_META[props.finding?.severity ?? 'info'])
const type = computed(() => TYPE_META[props.finding?.type ?? 'unchanged'])
const conf = computed(() => confidenceLevel(props.finding?.confidence ?? 0))
const labels = computed<[string, string]>(() =>
  props.finding?.type === 'duplicate' ? ['Закрепление 1', 'Закрепление 2'] : ['До реорганизации', 'После реорганизации'],
)
const emptyBefore = 'В комплекте «до» функция отсутствует'
const emptyAfter = 'В комплекте «после» функция не найдена'
</script>

<style scoped lang="scss">
.detail-title { font-size: 18px; font-weight: 600; line-height: 1.35; margin: 0; }
.detail-empty { min-height: 320px; padding: 24px; }
.recommendation { background: #eef4fb; border: 1px solid #cfe0f3; border-radius: 6px; padding: 12px 14px; }
</style>
