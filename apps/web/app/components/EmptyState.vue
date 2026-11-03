<script setup lang="ts">
withDefaults(defineProps<{ title: string; description: string }>(), {})
</script>

<template>
  <section class="empty-state">
    <span aria-hidden="true">□</span>
    <div>
      <h2>{{ title }}</h2>
      <p>{{ description }}</p>
    </div>
  </section>
</template>
