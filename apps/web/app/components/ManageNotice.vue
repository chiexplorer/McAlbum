<script setup lang="ts">
defineProps<{ kind?: 'success' | 'error' | 'info' }>()
</script>

<template>
  <p class="manage-notice" :data-kind="kind || 'info'" role="status"><slot /></p>
</template>
