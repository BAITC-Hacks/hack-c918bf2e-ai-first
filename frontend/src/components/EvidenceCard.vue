<template>
  <div v-if="evidence" class="ev sv-col">
    <div class="ev-head row items-center no-wrap">
      <span class="sv-badge-ink">{{ badge }}</span>
      <span class="sv-meta sv-text-2">{{ setLabel }}</span>
    </div>
    <div class="ev-body sv-col">
      <blockquote class="quote">
        «<template v-if="segments"><span v-for="(s, i) in segments" :key="i" :class="`seg-${s.kind}`">{{ s.text }}</span></template><template v-else>{{ evidence.quote }}</template>»
      </blockquote>
      <dl class="meta">
        <dt>Документ</dt>
        <dd class="row items-center no-wrap" style="gap: 4px; min-width: 0">
          <q-icon :name="docIcon(evidence.document)" size="15px" class="sv-muted" />
          <span class="ellipsis" :title="evidence.document">{{ evidence.document }}</span>
        </dd>
        <dt>Пункт</dt>
        <dd class="strong">{{ evidence.clause || 'не указан' }}</dd>
        <dt>Страница</dt>
        <dd>{{ evidence.page ?? `нет данных${fileExt(evidence.document) ? ` (${fileExt(evidence.document)})` : ''}` }}</dd>
        <dt>Подразделение</dt>
        <dd>{{ evidence.department || 'не указано' }}</dd>
      </dl>
      <q-btn
        flat
        no-caps
        class="sv-btn sv-btn--ghost self-start copy no-print"
        icon="content_copy"
        label="Копировать цитату со ссылкой"
        @click="copy"
      />
    </div>
  </div>

  <div v-else class="ev ev--missing sv-col">
    <div class="ev-head row items-center no-wrap">
      <span class="sv-badge-ink">{{ badge }}</span>
      <span class="sv-meta sv-text-2">{{ setLabel }}</span>
    </div>
    <div class="missing sv-col items-center justify-center text-center">
      <q-icon name="search_off" size="30px" style="color: var(--sv-icon-muted)" />
      <span class="missing-title">{{ missingTitle }}</span>
      <span class="sv-meta" style="max-width: 260px">{{ missingText }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { copyToClipboard, useQuasar } from 'quasar'
import type { Evidence } from '@/api/types'
import { citation, type DiffSegment } from '@/utils/findings'
import { docIcon, fileExt } from '@/utils/labels'

const props = defineProps<{
  evidence: Evidence | null
  badge: string
  setLabel: string
  segments?: DiffSegment[] | null
  missingTitle?: string
  missingText?: string
}>()
const $q = useQuasar()

async function copy() {
  if (!props.evidence) return
  try {
    await copyToClipboard(citation(props.evidence))
    $q.notify({ message: 'Цитата скопирована со ссылкой на пункт', icon: 'check_circle' })
  } catch {
    $q.notify({ message: 'Не удалось скопировать — выделите текст вручную', icon: 'error_outline' })
  }
}
</script>

<style scoped lang="scss">
.ev { border: 1px solid var(--sv-border-strong); border-radius: 8px; background: var(--sv-surface); overflow: hidden; min-width: 0; }
.ev--missing { border-style: dashed; border-color: var(--sv-dashed); background: transparent; }
.ev-head { gap: 8px; padding: 8px 12px; border-bottom: 1px solid var(--sv-divider); background: var(--sv-sunken); }
.ev-body { padding: 14px 14px 12px; gap: 12px; flex: 1; }
.quote { margin: 0; font-size: 16px; line-height: 1.65; color: var(--sv-text); text-wrap: pretty; }
.seg-del { background: var(--sv-high-bg); color: var(--sv-del-text); text-decoration: line-through; border-radius: 2px; }
.seg-add { background: var(--sv-low-bg); color: var(--sv-add-text); text-decoration: underline; border-radius: 2px; }
.meta {
  margin: auto 0 0; display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 4px 12px; font-size: 12px; line-height: 1.45;
  padding-top: 10px; border-top: 1px solid var(--sv-line);
  dt { color: var(--sv-muted); }
  dd { margin: 0; color: var(--sv-text); }
  .strong { font-weight: 600; }
}
.copy.q-btn { font-size: 12px; padding-left: 0; margin-left: -2px; }
.missing { flex: 1; min-height: 180px; padding: 20px; gap: 8px; }
.missing-title { font-size: 14px; font-weight: 500; }
</style>
