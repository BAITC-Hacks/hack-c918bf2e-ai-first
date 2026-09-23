<template>
  <section id="conclusion" class="panel">
    <header class="panel-head">
      <q-icon name="gavel" color="primary" size="20px" />
      <h2 class="panel-title">Итоговое заключение</h2>
      <q-space />
      <q-btn flat dense no-caps icon="content_copy" label="Копировать" class="no-print" @click="copy" />
    </header>
    <div class="panel-body">
      <p v-if="conclusion" class="conclusion-text q-mb-none">{{ conclusion }}</p>
      <p v-else class="muted q-mb-none">Заключение не сформировано.</p>

      <div v-if="warnings.length" class="q-mt-md column q-gutter-y-sm">
        <q-banner v-for="(warning, i) in warnings" :key="i" dense rounded class="bg-orange-1 text-orange-10">
          <template #avatar><q-icon name="info" color="warning" /></template>
          {{ warning }}
        </q-banner>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { copyToClipboard, useQuasar } from 'quasar'

const props = defineProps<{ conclusion: string | null | undefined; warnings: string[] }>()
const $q = useQuasar()

async function copy() {
  try {
    await copyToClipboard(props.conclusion ?? '')
    $q.notify({ type: 'positive', message: 'Заключение скопировано', timeout: 2000 })
  } catch {
    $q.notify({ type: 'negative', message: 'Не удалось скопировать' })
  }
}
</script>
