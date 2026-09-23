<template>
  <q-layout view="hHh lpR fFf" class="app-bg">
    <q-header class="app-header no-print">
      <q-toolbar class="app-container q-px-md">
        <router-link to="/" class="brand row items-center no-wrap">
          <span class="brand-mark">AI</span>
          <span class="column">
            <span class="brand-title">AI First</span>
            <span class="brand-sub gt-xs">Аудит организационной структуры и функций</span>
          </span>
        </router-link>
        <q-space />
        <q-btn flat no-caps icon="play_circle_outline" label="Демо-пример" class="gt-xs" @click="openDemo" />
        <q-btn flat round icon="play_circle_outline" class="xs" aria-label="Демо-пример" @click="openDemo" />
        <q-btn flat no-caps icon="add" label="Новый анализ" :to="{ name: 'upload' }" />
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
    </q-page-container>
  </q-layout>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { createAnalysis } from '@/api/client'

const router = useRouter()

async function openDemo() {
  const created = await createAnalysis({ beforeFiles: [], afterFiles: [] }, true)
  await router.push({ name: 'analysis', params: { id: created.id } })
}
</script>
