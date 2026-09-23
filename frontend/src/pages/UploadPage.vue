<template>
  <q-page class="app-container page-pad">
    <div class="q-mb-lg">
      <div class="eyebrow">Новый анализ</div>
      <h1 class="page-title q-mt-xs">Сравнение оргструктуры до и после реорганизации</h1>
      <p class="muted q-mt-sm q-mb-none text-body1" style="max-width: 760px">
        Загрузите положения о подразделениях и организационные структуры. Агент сопоставит функции
        и сформирует заключение со ссылками на пункты документов.
      </p>
    </div>

    <q-form @submit.prevent="submit">
      <section class="panel q-mb-md">
        <div class="panel-body">
          <q-input
            v-model="title"
            outlined
            dense
            label="Название анализа (необязательно)"
            placeholder="Например: Реорганизация блока эксплуатации"
            maxlength="200"
          />
        </div>
      </section>

      <div class="row q-col-gutter-md q-mb-md">
        <div class="col-12 col-md-6">
          <FileDropZone
            v-model="beforeFiles"
            title="Комплект «до»"
            caption="Действующие положения и структура"
            icon="history"
          />
        </div>
        <div class="col-12 col-md-6">
          <FileDropZone
            v-model="afterFiles"
            title="Комплект «после»"
            caption="Проект новых положений и структуры"
            icon="update"
          />
        </div>
      </div>

      <section class="panel q-mb-lg">
        <div class="panel-body row items-center q-col-gutter-md">
          <div class="col-12 col-md">
            <div class="text-weight-medium q-mb-sm">Что проверит агент</div>
            <div class="row q-gutter-sm">
              <q-chip
                v-for="type in CHECKED_TYPES"
                :key="type"
                dense
                square
                :icon="TYPE_META[type].icon"
                :class="`bg-${TYPE_META[type].color}-soft text-${TYPE_META[type].color}`"
              >
                {{ TYPE_META[type].label }}
                <q-tooltip>{{ TYPE_META[type].hint }}</q-tooltip>
              </q-chip>
            </div>
          </div>
          <div class="col-12 col-md-auto row q-gutter-sm justify-end">
            <q-btn outline no-caps color="primary" icon="play_circle_outline" label="Демо на тестовых данных" @click="runDemo" />
            <q-btn
              unelevated
              no-caps
              color="primary"
              icon-right="arrow_forward"
              label="Запустить анализ"
              type="submit"
              :loading="submitting"
              :disable="!canSubmit"
            >
              <q-tooltip v-if="!canSubmit">Добавьте хотя бы по одному файлу в каждый комплект</q-tooltip>
            </q-btn>
          </div>
        </div>
      </section>
    </q-form>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useQuasar } from 'quasar'
import FileDropZone from '@/components/FileDropZone.vue'
import { ApiError, createAnalysis } from '@/api/client'
import type { FindingType } from '@/api/types'
import { TYPE_META } from '@/utils/labels'

const CHECKED_TYPES: FindingType[] = ['lost', 'duplicate', 'changed', 'moved', 'added']

const router = useRouter()
const $q = useQuasar()
const title = ref('')
const beforeFiles = ref<File[]>([])
const afterFiles = ref<File[]>([])
const submitting = ref(false)

const canSubmit = computed(() => beforeFiles.value.length > 0 && afterFiles.value.length > 0 && !submitting.value)

async function start(useMock: boolean) {
  const created = await createAnalysis(
    { title: title.value, beforeFiles: beforeFiles.value, afterFiles: afterFiles.value },
    useMock,
  )
  await router.push({ name: 'analysis', params: { id: created.id } })
}

async function submit() {
  if (!canSubmit.value) return
  submitting.value = true
  try {
    await start(false)
  } catch (error) {
    const offline = error instanceof ApiError && error.kind !== 'http'
    $q.notify({
      type: 'negative',
      message: error instanceof Error ? error.message : 'Не удалось запустить анализ',
      caption: offline ? 'Можно продолжить на демонстрационных данных' : 'Проверьте файлы и повторите попытку',
      timeout: 0,
      actions: [
        ...(offline ? [{ label: 'Демо-данные', color: 'white', handler: () => void start(true) }] : []),
        { label: 'Повторить', color: 'white', handler: () => void submit() },
        { icon: 'close', color: 'white', round: true },
      ],
    })
  } finally {
    submitting.value = false
  }
}

function runDemo() {
  void start(true)
}
</script>
