<script setup lang="ts">
defineProps<{
  date: string
  worldDay?: number | null
  place?: string
}>()
</script>

<template>
  <dl class="archive-stamp" aria-label="档案信息">
    <div>
      <dt>记录日期</dt>
      <dd>{{ date }}</dd>
    </div>
    <div v-if="worldDay !== null && worldDay !== undefined">
      <dt>世界日</dt>
      <dd>{{ worldDay }}</dd>
    </div>
    <div v-if="place">
      <dt>地点</dt>
      <dd>{{ place }}</dd>
    </div>
  </dl>
</template>
