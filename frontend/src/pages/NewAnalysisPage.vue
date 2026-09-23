<template>
  <q-page class="sv-container page">
    <div class="layout">
      <div class="main sv-col">
        <div class="sv-col intro">
          <div class="sv-overline">Новый анализ реорганизации</div>
          <h1 class="sv-display">Найдите потерянные и дублирующиеся функции до утверждения новой структуры</h1>
          <p class="sv-lead q-mb-none">
            Загрузите документы «до» и «после» реорганизации. Агент сопоставит подразделения и функции и подкрепит
            каждый вывод цитатой с указанием документа, пункта и страницы.
          </p>
        </div>

        <div v-if="submitError" role="alert" class="sv-banner sv-banner--err items-center">
          <q-icon :name="submitError.offline ? 'cloud_off' : 'error_outline'" size="20px" />
          <div class="col sv-col">
            <b>{{ submitError.offline ? 'Сервис анализа недоступен' : 'Не удалось запустить анализ' }}</b>
            <span>{{ submitError.offline ? 'Файлы сохранены в форме. Повторите запуск через минуту; если ошибка повторится, сообщите администратору.' : submitError.message }}</span>
          </div>
          <q-btn flat no-caps class="sv-btn sv-btn--secondary" icon="refresh" label="Повторить" :loading="submitting" @click="submit" />
        </div>

        <label class="sv-col title-field">
          <span class="sv-small sv-text-2">Название анализа <span class="sv-muted">— необязательно</span></span>
          <q-input
            v-model="draft.title"
            outlined
            class="sv-input"
            placeholder="Например, Реорганизация ИТ-блока, 2025"
            maxlength="200"
            aria-label="Название анализа"
          />
        </label>

        <div class="zones">
          <UploadZone set="before" badge="ДО" title="Комплект до" sub="Действующая структура: положения, оргструктура, инструкции" />
          <UploadZone set="after" badge="ПОСЛЕ" title="Комплект после" sub="Новая структура: приказ, положения, оргструктура" />
        </div>

        <div class="actions row items-center">
          <div class="security sv-meta row no-wrap items-center">
            <q-icon name="lock" size="16px" class="q-mr-xs" />
            Документы обрабатываются во внутреннем контуре и не используются для обучения моделей.
          </div>
          <div class="buttons row no-wrap items-center">
            <q-btn flat no-caps class="sv-btn sv-btn--secondary sv-btn--lg" icon="dataset" label="Демо на тестовых данных" @click="runDemoFill" />
            <q-btn
              flat
              no-caps
              class="sv-btn sv-btn--primary sv-btn--lg launch"
              icon="play_arrow"
              :label="submitting ? 'Запуск…' : 'Запустить анализ'"
              :loading="submitting"
              :disable="!!disabledReason"
              @click="submit"
            >
              <template #loading>
                <q-spinner size="18px" class="q-mr-sm" />Запуск…
              </template>
            </q-btn>
          </div>
        </div>
        <div v-if="disabledReason" class="sv-meta text-right hint">{{ disabledReason }}</div>
      </div>

      <aside class="aside sv-col">
        <div class="sv-card checklist sv-col">
          <div class="sv-overline sv-muted" style="color: var(--sv-muted)">Что проверит агент</div>
          <div v-for="c in CHECKS" :key="c.title" class="check">
            <q-icon :name="c.icon" size="20px" class="check-icon" />
            <div class="sv-col">
              <span class="check-title">{{ c.title }}</span>
              <span class="sv-meta">{{ c.note }}</span>
            </div>
          </div>
        </div>
        <div class="note">
          <q-icon name="verified_user" size="20px" class="sv-muted" />
          <span>Выводы носят рекомендательный характер. Решение по каждому отклонению принимает ответственный сотрудник.</span>
        </div>
        <div class="note">
          <q-icon name="folder_open" size="20px" class="sv-muted" />
          <span>Что загрузить: положения о подразделениях, организационные структуры, должностные инструкции, приказы и распоряжения.</span>
        </div>
      </aside>
    </div>
  </q-page>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import UploadZone from '@/components/UploadZone.vue'
import { ApiError, createAnalysis } from '@/api/client'
import { DEMO_FILES, DEMO_TITLE } from '@/api/mock'
import { draft, fillDemo, isDemoDraft, readyFiles, runMeta } from '@/stores/draft'

const CHECKS = [
  { icon: 'account_tree', title: 'Изменения подразделений', note: 'Созданные, сохранённые, преобразованные и упразднённые' },
  { icon: 'remove_circle_outline', title: 'Потерянные функции', note: 'Функции, не закреплённые ни за одним подразделением' },
  { icon: 'control_point_duplicate', title: 'Дублирование', note: 'Одна функция закреплена за несколькими подразделениями' },
  { icon: 'east', title: 'Передача и изменение функций', note: 'Куда перешла функция и как изменилась формулировка' },
  { icon: 'gavel', title: 'Конфликты интересов', note: 'Совмещение исполнения и контроля в одном подразделении' },
  { icon: 'format_quote', title: 'Доказательства', note: 'Каждый вывод — с документом, пунктом, страницей и цитатой' },
]

const router = useRouter()
const submitting = ref(false)
const submitError = ref<{ offline: boolean; message: string } | null>(null)

const disabledReason = computed(() => {
  const all = [...draft.before, ...draft.after]
  if (all.some((f) => f.status === 'uploading')) return 'Дождитесь окончания загрузки файлов'
  const before = readyFiles('before').length
  const after = readyFiles('after').length
  if (!before && !after) return 'Добавьте хотя бы один файл в каждый комплект'
  if (!before) return 'Добавьте файлы в «Комплект до»'
  if (!after) return 'Добавьте файлы в «Комплект после»'
  return ''
})

function runDemoFill() {
  submitError.value = null
  fillDemo(DEMO_FILES, DEMO_TITLE)
}

async function submit() {
  if (disabledReason.value || submitting.value) return
  submitting.value = true
  submitError.value = null
  const before = readyFiles('before')
  const after = readyFiles('after')
  try {
    const created = await createAnalysis(
      {
        title: draft.title,
        beforeFiles: before.flatMap((f) => (f.file ? [f.file] : [])),
        afterFiles: after.flatMap((f) => (f.file ? [f.file] : [])),
      },
      isDemoDraft(),
    )
    runMeta.set(created.id, { before: before.length, after: after.length })
    await router.push({ name: 'run', params: { id: created.id } })
  } catch (error) {
    const offline = error instanceof ApiError && error.kind !== 'http'
    submitError.value = { offline, message: error instanceof Error ? error.message : 'Неизвестная ошибка' }
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.page { padding-top: 32px; padding-bottom: 48px; }
.layout { display: flex; flex-wrap: wrap; gap: 32px; align-items: flex-start; }
.main { flex: 1 1 640px; min-width: 0; gap: 20px; }
.aside { flex: 1 1 300px; max-width: 400px; gap: 16px; }
@media (min-width: 1440px) { .aside { flex-basis: 360px; } }
@media (max-width: 1023px) { .aside { max-width: none; } }
.intro { gap: 8px; max-width: 820px; }
.title-field { gap: 6px; max-width: 520px; }
.zones { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
@media (max-width: 699px) { .zones { grid-template-columns: 1fr; } }
.actions { gap: 12px 16px; padding-top: 4px; }
.security { flex: 1 1 320px; }
.buttons { gap: 12px; }
.launch.q-btn { font-size: 15px; padding: 0 18px; }
.hint { margin-top: -12px; }
.checklist { padding: 18px; gap: 14px; }
.check { display: grid; grid-template-columns: 24px 1fr; gap: 10px; align-items: start; }
.check-icon { color: var(--sv-accent); }
.check-title { font-size: 14px; font-weight: 500; }
.note { display: grid; grid-template-columns: 24px 1fr; gap: 10px; padding: 0 4px; font-size: 12px; line-height: 1.5; color: var(--sv-text-2); }

@media (max-width: 599px) {
  .page { padding-top: 20px; padding-bottom: 150px; }
  .buttons {
    position: fixed; left: 0; right: 0; bottom: 0; z-index: 20; padding: 12px 16px;
    background: var(--sv-surface); border-top: 1px solid var(--sv-divider); gap: 8px;
    flex-direction: column-reverse; align-items: stretch;
  }
  .hint { margin-top: 0; text-align: left; }
}
</style>
