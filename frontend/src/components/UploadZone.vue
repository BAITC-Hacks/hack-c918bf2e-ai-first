<template>
  <section class="sv-card zone sv-col" :aria-label="title">
    <div class="row no-wrap items-start zone-head">
      <span class="sv-badge-ink">{{ badge }}</span>
      <div class="col sv-col zone-title-box">
        <div class="zone-title">{{ title }}</div>
        <div class="sv-meta">{{ sub }}</div>
      </div>
      <span class="sv-meta tabular no-wrap">{{ counter }}</span>
    </div>

    <div
      role="button"
      tabindex="0"
      class="drop sv-col items-center justify-center text-center"
      :class="{ 'drop--over': over, 'drop--compact': files.length > 0 }"
      :aria-label="`Добавить файлы в «${title}»`"
      @click="pick"
      @keydown.enter.prevent="pick"
      @keydown.space.prevent="pick"
      @dragenter.prevent="over = true"
      @dragover.prevent="over = true"
      @dragleave.prevent="over = false"
      @drop.prevent="onDrop"
    >
      <q-icon :name="over ? 'file_download' : 'upload_file'" size="28px" class="drop-icon" />
      <div class="drop-title">
        {{ over ? `Отпустите, чтобы добавить в «${title}»` : files.length ? 'Добавить ещё файлы' : 'Перетащите файлы сюда или нажмите, чтобы выбрать' }}
      </div>
      <div class="sv-meta">DOCX, PDF, XLSX · до {{ MAX_FILE_MB }} МБ на файл</div>
    </div>
    <input ref="input" type="file" multiple accept=".docx,.pdf,.xlsx" class="hidden" @change="onPick" />

    <ul v-if="files.length" class="files">
      <li v-for="f in files" :key="f.id" class="file" :class="{ 'file--err': f.status === 'error' }">
        <q-icon :name="f.status === 'error' ? 'block' : docIcon(f.name)" size="20px" :style="{ color: f.status === 'error' ? 'var(--sv-high)' : 'var(--sv-muted)' }" />
        <div class="sv-col file-main">
          <span class="file-name ellipsis" :title="f.name">{{ f.name }}</span>
          <span v-if="f.status === 'uploading'" class="file-progress"><span :style="{ width: `${f.progress * 100}%` }" /></span>
          <span v-if="f.status === 'error'" class="file-error row no-wrap items-start">
            <q-icon name="error_outline" size="14px" class="q-mr-xs" style="margin-top: 2px" />{{ f.error }}
          </span>
        </div>
        <span class="sv-meta tabular no-wrap row items-center file-meta">
          {{ fileExt(f.name) || 'Файл' }} · {{ formatBytes(f.size) }}
          <q-icon
            v-if="f.status !== 'error'"
            :name="f.status === 'uploading' ? 'more_horiz' : 'check_circle'"
            size="16px"
            :style="{ color: f.status === 'uploading' ? 'var(--sv-muted)' : 'var(--sv-low)' }"
          />
        </span>
        <q-btn flat class="sv-icon-btn remove-btn" icon="close" aria-label="Удалить файл" @click="removeFile(set, f.id)">
          <q-tooltip :delay="400">Удалить файл</q-tooltip>
        </q-btn>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useQuasar } from 'quasar'
import { MAX_FILES_PER_SET, MAX_FILE_MB, addFiles, draft, removeFile, type SetKey } from '@/stores/draft'
import { FILES, docIcon, fileExt, formatBytes, pluralize } from '@/utils/labels'

const props = defineProps<{ set: SetKey; badge: string; title: string; sub: string }>()
const $q = useQuasar()
const over = ref(false)
const input = ref<HTMLInputElement | null>(null)

const files = computed(() => draft[props.set])
const counter = computed(() => {
  const valid = files.value.filter((f) => f.status !== 'error')
  if (!valid.length) return 'Нет файлов'
  const size = valid.reduce((sum, f) => sum + f.size, 0)
  return `${valid.length} ${pluralize(valid.length, FILES)} · ${formatBytes(size)}`
})

function add(list: FileList | null | undefined) {
  if (!list?.length) return
  const { skipped, clearedDemo } = addFiles(props.set, Array.from(list))
  if (clearedDemo) {
    $q.notify({
      message: 'Демонстрационные файлы убраны: форма переключена на анализ ваших документов',
      icon: 'swap_horiz',
    })
  }
  if (skipped) $q.notify({ message: `Не более ${MAX_FILES_PER_SET} файлов в комплекте — пропущено: ${skipped}`, icon: 'error_outline' })
}

function pick() {
  input.value?.click()
}

function onPick(event: Event) {
  const target = event.target as HTMLInputElement
  add(target.files)
  target.value = ''
}

function onDrop(event: DragEvent) {
  over.value = false
  add(event.dataTransfer?.files)
}
</script>

<style scoped lang="scss">
.zone { padding: 16px; gap: 12px; min-width: 0; }
.zone-head { gap: 10px; }
.zone-title-box { gap: 2px; min-width: 0; }
.zone-title { font-size: 16px; font-weight: 500; }
.drop {
  min-height: 156px; gap: 6px; padding: 16px; border: 1.5px dashed var(--sv-dashed); border-radius: 8px;
  background: var(--sv-sunken); cursor: pointer; transition: background .12s ease-out, border-color .12s ease-out;
  &:hover { border-color: var(--sv-accent-line); }
}
.drop--compact { min-height: 84px; }
.drop--over { border-style: solid; border-color: var(--sv-accent); background: var(--sv-accent-tint); }
.drop-icon { color: var(--sv-accent); }
.drop-title { font-size: 14px; font-weight: 500; }
.files { list-style: none; margin: 0; padding: 0; border: 1px solid var(--sv-divider); border-radius: 8px; overflow: hidden; }
.file {
  display: grid; grid-template-columns: 28px minmax(0, 1fr) auto 32px; align-items: center; gap: 8px;
  padding: 8px 6px 8px 10px; border-bottom: 1px solid var(--sv-line);
  &:last-child { border-bottom: 0; }
}
.file--err { background: var(--sv-high-row); }
.file-main { gap: 2px; min-width: 0; }
.file-name { font-size: 13px; }
.file-progress { height: 3px; background: var(--sv-divider); border-radius: 2px; overflow: hidden; display: block;
  span { display: block; height: 100%; background: var(--sv-accent); transition: width .3s ease-out; } }
.file-error { font-size: 12px; color: var(--sv-high); line-height: 1.4; }
.file-meta { gap: 6px; }
.remove-btn.q-btn { width: 30px; height: 30px; min-height: 30px; &:hover { color: var(--sv-high); } }
@media (max-width: 599px) {
  .file { grid-template-columns: 24px minmax(0, 1fr) 44px; }
  .file-meta { grid-column: 2; grid-row: 2; }
  .remove-btn.q-btn { grid-column: 3; grid-row: 1 / span 2; width: 44px; height: 44px; }
}
</style>
