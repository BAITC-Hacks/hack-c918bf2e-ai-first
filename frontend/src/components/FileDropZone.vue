<template>
  <section class="panel column drop-panel">
    <header class="panel-head">
      <q-icon :name="icon" size="20px" color="primary" />
      <div class="col">
        <h2 class="panel-title">{{ title }}</h2>
        <div class="text-caption muted">{{ caption }}</div>
      </div>
      <q-badge v-if="modelValue.length" color="primary" outline class="tabular">
        {{ modelValue.length }} {{ pluralize(modelValue.length, ['файл', 'файла', 'файлов']) }}
      </q-badge>
    </header>

    <div class="panel-body col column q-gutter-y-md">
      <label
        class="dropzone column items-center justify-center text-center"
        :class="{ 'dropzone--active': dragging }"
        @dragenter.prevent="dragging = true"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
      >
        <input ref="input" type="file" multiple :accept="ACCEPT" class="hidden-input" @change="onPick" />
        <q-icon name="upload_file" size="36px" color="primary" />
        <div class="text-body1 q-mt-sm">Перетащите файлы или <span class="text-primary text-weight-medium">выберите</span></div>
        <div class="text-caption muted">PDF, DOCX · до {{ MAX_MB }} МБ на файл</div>
      </label>

      <q-list v-if="modelValue.length" bordered separator class="rounded-borders">
        <q-item v-for="(file, index) in modelValue" :key="file.name + file.size" dense class="q-py-sm">
          <q-item-section avatar>
            <q-icon :name="file.name.toLowerCase().endsWith('.pdf') ? 'picture_as_pdf' : 'description'" color="grey-7" />
          </q-item-section>
          <q-item-section>
            <q-item-label class="ellipsis">{{ file.name }}</q-item-label>
            <q-item-label caption>{{ formatBytes(file.size) }}</q-item-label>
          </q-item-section>
          <q-item-section side>
            <q-btn flat round dense icon="close" size="sm" :aria-label="`Удалить ${file.name}`" @click="remove(index)" />
          </q-item-section>
        </q-item>
      </q-list>
      <div v-else class="text-caption muted">Файлы не выбраны</div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useQuasar } from 'quasar'
import { formatBytes, pluralize } from '@/utils/labels'

const ACCEPT = '.pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document'
const MAX_MB = 25

const props = defineProps<{ modelValue: File[]; title: string; caption: string; icon: string }>()
const emit = defineEmits<{ 'update:modelValue': [files: File[]] }>()

const $q = useQuasar()
const dragging = ref(false)
const input = ref<HTMLInputElement | null>(null)

function add(files: FileList | null) {
  if (!files) return
  const accepted: File[] = []
  const rejected: string[] = []
  for (const file of Array.from(files)) {
    const okType = /\.(pdf|docx)$/i.test(file.name)
    const okSize = file.size <= MAX_MB * 1024 * 1024
    const duplicate = props.modelValue.some((f) => f.name === file.name && f.size === file.size)
    if (!okType || !okSize) rejected.push(file.name)
    else if (!duplicate) accepted.push(file)
  }
  if (rejected.length) {
    $q.notify({
      type: 'warning',
      message: `Пропущено: ${rejected.join(', ')}`,
      caption: `Поддерживаются только PDF и DOCX до ${MAX_MB} МБ`,
    })
  }
  if (accepted.length) emit('update:modelValue', [...props.modelValue, ...accepted])
}

function onDrop(event: DragEvent) {
  dragging.value = false
  add(event.dataTransfer?.files ?? null)
}

function onPick(event: Event) {
  add((event.target as HTMLInputElement).files)
  if (input.value) input.value.value = ''
}

function remove(index: number) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index))
}
</script>

<style scoped lang="scss">
.drop-panel { height: 100%; }
.dropzone {
  border: 1.5px dashed #b8c4d1; border-radius: 8px; padding: 28px 16px; cursor: pointer;
  background: #f8fafc; transition: border-color .15s, background .15s; min-height: 150px;
  &:hover, &:focus-within { border-color: $primary; background: #f1f6fc; }
}
.dropzone--active { border-color: $primary; background: #e8f1fb; }
.hidden-input { position: absolute; width: 1px; height: 1px; opacity: 0; }
</style>
