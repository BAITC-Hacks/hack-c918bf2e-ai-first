<template>
  <section aria-labelledby="org-h" class="sv-col section">
    <div class="row items-baseline section-head">
      <h2 id="org-h" class="sv-h2">Изменения организационной структуры</h2>
      <div class="row counts">
        <span v-for="c in counts" :key="c.status" class="row items-center no-wrap" :style="{ color: ORG_META[c.status].fg }">
          <q-icon :name="ORG_META[c.status].icon" size="16px" />{{ ORG_META[c.status].label }}
          <b class="tabular">{{ c.count }}</b>
        </span>
      </div>
    </div>

    <div v-if="!rows.length" class="sv-card empty sv-col items-center text-center">
      <q-icon name="account_tree" size="32px" style="color: var(--sv-icon-muted)" />
      <span class="sv-small sv-muted">Агент не выделил изменений в составе подразделений.</span>
    </div>

    <div v-else class="sv-card map-scroll">
      <div class="map">
        <div class="grid map-head sv-th gt-sm">
          <span>До реорганизации</span><span class="text-center">Изменение</span><span>После реорганизации</span><span>Пояснение и основание</span>
        </div>
        <div v-for="o in rows" :key="o.id" class="map-row">
          <div class="grid map-line">
            <div class="name" :class="nameClass(o, 'before')">
              <span class="side-label lt-md sv-meta">До</span>
              {{ o.before_name ?? (o.status === 'created' ? 'Не существовало' : '—') }}
            </div>
            <div class="change">
              <span class="line gt-sm" :style="{ background: o.status === 'preserved' ? 'var(--sv-border)' : ORG_META[o.status].fg }" />
              <span class="status-chip" :style="{ color: ORG_META[o.status].fg, borderColor: ORG_META[o.status].fg }">
                <q-icon :name="ORG_META[o.status].icon" size="15px" />{{ ORG_META[o.status].label }}
              </span>
            </div>
            <div class="name" :class="nameClass(o, 'after')">
              <span class="side-label lt-md sv-meta">После</span>
              {{ o.after_name ?? (o.status === 'removed' ? 'Упразднено' : '—') }}
            </div>
            <div class="sv-col why">
              <span class="why-text">{{ o.explanation }}</span>
              <button
                v-if="evidence(o)"
                type="button"
                class="ev-toggle"
                :aria-expanded="open.has(o.id)"
                @click="toggle(o.id)"
              >
                <q-icon name="format_quote" size="15px" />{{ evidenceLabel(o) }}
                <q-icon :name="open.has(o.id) ? 'expand_less' : 'expand_more'" size="16px" />
              </button>
            </div>
          </div>
          <q-slide-transition>
            <div v-if="open.has(o.id) && evidence(o)" class="quote-box sv-col">
              <span class="sv-meta row items-center no-wrap" style="gap: 6px">
                <q-icon :name="docIcon(evidence(o)!.document)" size="16px" />{{ evidence(o)!.document }}
              </span>
              <span class="quote-text">«{{ evidence(o)!.quote }}»</span>
            </div>
          </q-slide-transition>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import type { OrganizationChange, OrganizationChangeStatus } from '@/api/types'
import { clauseLabel } from '@/utils/findings'
import { ORG_META, docIcon } from '@/utils/labels'

const props = defineProps<{ changes: OrganizationChange[] }>()

const rows = computed(() => [...props.changes].sort((a, b) => ORG_META[a.status].order - ORG_META[b.status].order))
const counts = computed(() =>
  (Object.keys(ORG_META) as OrganizationChangeStatus[])
    .map((status) => ({ status, count: props.changes.filter((c) => c.status === status).length }))
    .filter((c) => c.count > 0),
)

const open = reactive(new Set<string>())
function toggle(id: string) {
  if (open.has(id)) open.delete(id)
  else open.add(id)
}

const evidence = (o: OrganizationChange) => o.after ?? o.before
function evidenceLabel(o: OrganizationChange) {
  const e = evidence(o)!
  return `${e.document.replace(/\.[a-z]+$/i, '')}, ${clauseLabel(e)}`
}

function nameClass(o: OrganizationChange, side: 'before' | 'after') {
  const missing = side === 'before' ? !o.before_name : !o.after_name
  return {
    'name--missing': missing,
    'name--removed': side === 'before' && o.status === 'removed',
    'name--created': side === 'after' && o.status === 'created',
  }
}
</script>

<style scoped lang="scss">
.section { gap: 12px; }
.section-head { gap: 8px 16px; flex-wrap: wrap; }
.counts { gap: 12px; font-size: 13px; flex-wrap: wrap; > span { gap: 4px; } b { font-weight: 600; } }
.empty { padding: 28px 16px; gap: 8px; }
.map-scroll { overflow-x: auto; }
.grid { display: grid; grid-template-columns: minmax(0, 1fr) 168px minmax(0, 1fr) minmax(0, 1.25fr); gap: 0 16px; }
@media (min-width: 1024px) { .map { min-width: 980px; } }
.map-head { padding: 10px 18px; border-bottom: 1px solid var(--sv-divider); }
.map-row { border-bottom: 1px solid var(--sv-line); &:last-child { border-bottom: 0; } }
.map-line { padding: 12px 18px; align-items: center; }
.name {
  min-height: 38px; display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px;
  border: 1px solid var(--sv-divider); background: var(--sv-sunken); font-size: 14px;
}
.name--missing { border-style: dashed; border-color: var(--sv-dashed); background: transparent; color: var(--sv-muted); }
.name--removed { text-decoration: line-through; color: var(--sv-muted); }
.name--created { background: var(--sv-created-bg); border-color: var(--sv-low-border); border-left: 3px dashed var(--sv-low); }
.change { position: relative; display: flex; align-items: center; justify-content: center; }
.line { position: absolute; left: -16px; right: -16px; top: 50%; height: 1px; }
.status-chip {
  position: relative; display: inline-flex; align-items: center; gap: 4px; padding: 3px 9px 3px 7px; border-radius: 12px;
  border: 1px solid; background: var(--sv-surface); font-size: 12px; font-weight: 500; white-space: nowrap;
}
.why { gap: 4px; min-width: 0; }
.why-text { font-size: 13px; line-height: 1.45; color: var(--sv-text-2); }
.ev-toggle {
  align-self: flex-start; background: none; border: 0; padding: 0; font: inherit; font-size: 12px; color: var(--sv-accent);
  cursor: pointer; display: inline-flex; align-items: center; gap: 4px; text-align: left; border-radius: 4px;
  &:hover { text-decoration: underline; }
}
.quote-box { margin: 0 18px 14px; padding: 12px 14px; background: var(--sv-sunken); border: 1px solid var(--sv-divider); border-radius: 6px; gap: 6px; }
.quote-text { font-size: 15px; line-height: 1.6; }
.side-label { min-width: 40px; }

// < 1024: cards instead of the 4-column map.
@media (max-width: 1023px) {
  .grid { grid-template-columns: 1fr; gap: 8px; }
  .map-line { padding: 14px; }
  .change { justify-content: flex-start; order: -1; }
  .quote-box { margin: 0 14px 14px; }
  .ev-toggle { min-height: 44px; }
}
</style>
