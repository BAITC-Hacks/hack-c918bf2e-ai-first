<template>
  <q-dialog
    :model-value="!!finding"
    position="right"
    full-height
    :maximized="$q.screen.lt.sm"
    transition-show="slide-left"
    transition-hide="slide-right"
    :transition-duration="200"
    class="sv-drawer-dialog"
    no-route-dismiss
    @hide="$emit('close')"
  >
    <aside
      v-if="finding"
      class="drawer sv-col no-wrap"
      :style="{ width }"
      role="dialog"
      aria-labelledby="dr-title"
    >
      <div class="drawer-head row items-center no-wrap">
        <span class="sv-meta tabular">{{ label }} · {{ position }} из {{ total }}</span>
        <q-space />
        <q-btn flat class="sv-icon-btn" icon="keyboard_arrow_up" aria-label="Предыдущее отклонение" @click="$emit('step', -1)" title="Предыдущее (↑)" />
        <q-btn flat class="sv-icon-btn" icon="keyboard_arrow_down" aria-label="Следующее отклонение" @click="$emit('step', 1)" title="Следующее (↓)" />
        <q-btn flat class="sv-icon-btn" icon="close" aria-label="Закрыть" @click="$emit('close')" title="Закрыть (Esc)" />
      </div>

      <div ref="body" class="drawer-body sv-col no-wrap" tabindex="-1">
        <div class="sv-col" style="gap: 10px">
          <div class="row items-center" style="gap: 6px">
            <RiskChip :severity="finding.severity" suffix=" риск" />
            <TypeLabel :type="finding.type" filled />
            <span class="sv-chip conf" title="Уверенность ИИ-агента в выводе">
              <q-icon name="speed" class="sv-muted" />Уверенность ИИ {{ percent(finding.confidence) }} · {{ confidenceLevel(finding.confidence) }}
            </span>
          </div>
          <h2 id="dr-title" class="dr-title">{{ finding.title }}</h2>
        </div>

        <section class="sv-col" style="gap: 10px">
          <div class="row items-baseline" style="gap: 6px 14px">
            <h3 class="dr-h3">Доказательства</h3>
            <span v-if="diff" class="sv-meta row legend">
              <span><span class="seg-del">зачёркнуто</span> — нет в «после»</span>
              <span><span class="seg-add">подчёркнуто</span> — появилось</span>
            </span>
          </div>
          <div class="evidence-grid">
            <EvidenceCard
              :evidence="finding.before"
              :badge="isDup ? 'ФРАГМЕНТ 1' : 'ДО'"
              :set-label="isDup ? 'Комплект после' : 'Комплект до'"
              :segments="diff?.before"
              missing-title="В комплекте «до» функции не было"
              missing-text="Аналог не найден ни в одном документе исходной структуры."
            />
            <EvidenceCard
              :evidence="finding.after"
              :badge="isDup ? 'ФРАГМЕНТ 2' : 'ПОСЛЕ'"
              set-label="Комплект после"
              :segments="diff?.after"
              missing-title="В комплекте «после» функция не найдена"
              missing-text="Агент проверил все документы новой структуры; соответствующего пункта нет."
            />
          </div>
        </section>

        <section class="sv-col" style="gap: 6px">
          <h3 class="dr-h3">Объяснение</h3>
          <p class="explanation">{{ finding.explanation }}</p>
        </section>

        <section class="reco sv-col">
          <div class="row items-center no-wrap reco-head">
            <q-icon name="person_search" size="18px" style="color: var(--sv-medium)" />
            <span>Рекомендация · требует проверки специалистом</span>
          </div>
          <p class="reco-text">{{ finding.recommendation }}</p>
          <q-btn
            flat
            no-caps
            class="sv-btn sv-btn--secondary self-start no-print"
            :icon="reviewed ? 'task_alt' : 'check_box_outline_blank'"
            :label="reviewed ? 'Отмечено как проверенное' : 'Отметить как проверенное'"
            :aria-pressed="reviewed"
            @click="toggleReviewed(analysisId, finding.id)"
          />
        </section>
      </div>
    </aside>
  </q-dialog>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useQuasar } from 'quasar'
import type { Finding } from '@/api/types'
import EvidenceCard from './EvidenceCard.vue'
import RiskChip from './RiskChip.vue'
import TypeLabel from './TypeLabel.vue'
import { useAnalysisContext } from '@/composables/analysisContext'
import { isReviewed, toggleReviewed } from '@/stores/reviewed'
import { wordDiff } from '@/utils/findings'
import { confidenceLevel, percent } from '@/utils/labels'

const props = defineProps<{ finding: Finding | null; label: string; position: number; total: number }>()
const emit = defineEmits<{ close: []; step: [delta: number] }>()

const $q = useQuasar()
const { analysis } = useAnalysisContext()
const analysisId = computed(() => analysis.value?.id ?? '')
const body = ref<HTMLElement | null>(null)

const isDup = computed(() => props.finding?.type === 'duplicate')
const diff = computed(() => {
  const f = props.finding
  if (!f || !f.before || !f.after || (f.type !== 'changed' && f.type !== 'moved')) return null
  return wordDiff(f.before.quote, f.after.quote)
})
const reviewed = computed(() => (props.finding ? isReviewed(analysisId.value, props.finding.id) : false))
const width = computed(() => {
  const w = $q.screen.width
  if (w < 600) return '100vw'
  if (w < 1024) return '100vw'
  if (w < 1440) return '720px'
  return '760px'
})

// ↑/↓ browse findings while the panel is open (not while typing in a field).
function onKey(event: KeyboardEvent) {
  if (!props.finding || (event.key !== 'ArrowUp' && event.key !== 'ArrowDown')) return
  const target = event.target
  if (target instanceof Element && target.closest('input, textarea, select, [contenteditable]')) return
  event.preventDefault()
  emit('step', event.key === 'ArrowUp' ? -1 : 1)
}
window.addEventListener('keydown', onKey)
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

// New finding: back to the top and keep keyboard focus inside the panel.
watch(
  () => props.finding?.id,
  async (id) => {
    if (!id) return
    await nextTick()
    body.value?.scrollTo({ top: 0 })
    body.value?.focus({ preventScroll: true })
  },
)
</script>

<style scoped lang="scss">
.drawer { height: 100%; max-width: 100vw; background: var(--sv-surface); color: var(--sv-text); box-shadow: var(--sv-shadow-lg); }
.drawer-head { flex: none; gap: 8px; padding: 10px 16px 10px 24px; border-bottom: 1px solid var(--sv-divider); background: var(--sv-surface); }
.drawer-body { flex: 1; overflow-y: auto; padding: 20px 24px 32px; gap: 22px; outline: none; }
.conf { border-color: var(--sv-border); color: var(--sv-text-2); font-weight: 400; }
.dr-title { font-size: 22px; line-height: 1.3; font-weight: 500; letter-spacing: -.01em; text-wrap: pretty; }
.dr-h3 { font-size: 13px; letter-spacing: .06em; text-transform: uppercase; color: var(--sv-text-2); font-weight: 500; }
.legend { gap: 10px; }
.seg-del { background: var(--sv-high-bg); color: var(--sv-del-text); text-decoration: line-through; padding: 0 3px; border-radius: 2px; }
.seg-add { background: var(--sv-low-bg); color: var(--sv-add-text); text-decoration: underline; padding: 0 3px; border-radius: 2px; }
.evidence-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.explanation { margin: 0; font-size: 15px; line-height: 1.6; text-wrap: pretty; }
.reco { gap: 10px; padding: 14px 16px; border: 1px solid var(--sv-medium-border); background: var(--sv-medium-bg); border-radius: 8px; }
.reco-head { gap: 8px; color: var(--sv-medium-text); font-size: 13px; font-weight: 600; }
.reco-text { margin: 0; font-size: 14px; line-height: 1.55; color: var(--sv-text); }
@media (max-width: 599px) {
  .drawer-head { padding: 6px 8px 6px 16px; }
  .drawer-body { padding: 16px 16px 32px; }
  .evidence-grid { grid-template-columns: 1fr; }
}
</style>
