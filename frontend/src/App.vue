<template>
  <q-layout view="hHh lpR fFf">
    <q-header class="sv-header no-print">
      <div class="sv-container row items-center no-wrap full-height header-row">
        <router-link :to="{ name: 'new' }" class="brand row items-center no-wrap" aria-label="Сверка — новый анализ">
          <q-icon name="account_tree" size="22px" class="brand-icon" />
          <span class="brand-name">Сверка</span>
          <span class="brand-sep" />
          <span class="brand-team">AI First</span>
        </router-link>
        <nav v-if="crumb" class="crumb row items-center no-wrap gt-xs" aria-label="Путь">
          <q-icon name="chevron_right" size="16px" class="crumb-icon" />
          <span class="ellipsis">{{ crumb }}</span>
        </nav>
        <q-space />
        <span v-if="isDemo" class="demo-chip row items-center no-wrap">
          <q-icon name="dataset" size="15px" /><span class="gt-xs">Демонстрация интерфейса</span>
        </span>
        <q-btn
          flat
          class="sv-icon-btn"
          :icon="theme === 'dark' ? 'light_mode' : 'dark_mode'"
          :aria-label="theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'"
          @click="toggleTheme"
        >
          <q-tooltip :delay="400">{{ theme === 'dark' ? 'Светлая тема' : 'Тёмная тема' }}</q-tooltip>
        </q-btn>
        <q-btn flat no-caps class="sv-btn sv-btn--secondary" icon="add" :to="{ name: 'new' }" aria-label="Новый анализ">
          <span class="gt-xs">Новый анализ</span>
        </q-btn>
      </div>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { isMockId } from '@/api/mock'
import { crumbTitle } from '@/composables/useAnalysis'
import { draft } from '@/stores/draft'
import { theme, toggleTheme } from '@/stores/theme'

const route = useRoute()
const isDemo = computed(() =>
  typeof route.params.id === 'string' ? isMockId(route.params.id) : route.name === 'new' && draft.mode === 'demo',
)
const crumb = computed(() => (route.name === 'new' ? 'Новый анализ' : route.params.id ? crumbTitle.value : ''))
</script>

<style scoped lang="scss">
.header-row { gap: 20px; }
@media (max-width: 599px) { .header-row { gap: 8px; } }
.brand { gap: 8px; color: var(--sv-text); text-decoration: none; border-radius: 6px; padding: 4px 0; }
.brand-icon { color: var(--sv-accent); }
.brand-name { font-size: 17px; font-weight: 500; letter-spacing: -.01em; }
.brand-sep { width: 1px; height: 16px; background: var(--sv-border-strong); }
.brand-team { font-size: 12px; color: var(--sv-muted); }
.crumb { gap: 4px; font-size: 13px; color: var(--sv-text); min-width: 0; }
.crumb-icon { color: var(--sv-icon-muted); }
.demo-chip {
  gap: 4px; font-size: 12px; color: var(--sv-accent); border: 1px solid var(--sv-accent-border);
  background: var(--sv-accent-tint); border-radius: 6px; padding: 3px 8px;
}
</style>
