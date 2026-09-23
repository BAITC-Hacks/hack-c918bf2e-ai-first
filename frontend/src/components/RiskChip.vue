<template>
  <span class="sv-chip sv-risk" :class="`sv-risk--${severity}`">
    <q-icon :name="SEVERITY_META[severity].icon" />{{ SEVERITY_META[severity].label }}{{ suffix ?? '' }}
  </span>
</template>

<script setup lang="ts">
import type { Severity } from '@/api/types'
import { SEVERITY_META } from '@/utils/labels'

defineProps<{ severity: Severity; suffix?: string }>()
</script>
