<template>
  <div class="evidence panel column" :class="{ 'evidence--empty': !evidence }">
    <div class="evidence-head row items-center no-wrap">
      <span class="eyebrow">{{ label }}</span>
      <q-space />
      <span v-if="evidence?.clause" class="clause tabular">п. {{ evidence.clause }}</span>
    </div>
    <template v-if="evidence">
      <div class="text-weight-medium q-mb-xs">{{ evidence.department || 'Подразделение не указано' }}</div>
      <blockquote class="quote q-mb-sm">«{{ evidence.quote }}»</blockquote>
      <div class="text-caption muted row items-center no-wrap q-mt-auto">
        <q-icon name="description" size="14px" class="q-mr-xs" />
        <span class="ellipsis">{{ evidence.document }}</span>
        <span v-if="evidence.page" class="q-ml-xs no-wrap">· стр. {{ evidence.page }}</span>
      </div>
    </template>
    <div v-else class="col column items-center justify-center text-center q-py-md">
      <q-icon name="block" size="28px" color="grey-5" />
      <div class="text-body2 muted q-mt-xs">{{ emptyText }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Evidence } from '@/api/types'

defineProps<{ evidence: Evidence | null; label: string; emptyText: string }>()
</script>

<style scoped lang="scss">
.evidence { padding: 12px 14px; min-height: 100%; }
.evidence-head { margin-bottom: 8px; }
.evidence--empty { background: #fafbfc; border-style: dashed; }
.clause {
  font-size: 12px; font-weight: 600; color: $primary; background: #e8f1fb;
  padding: 2px 8px; border-radius: 4px;
}
</style>
