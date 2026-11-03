<script setup lang="ts">
defineProps<{ label: string; active?: boolean }>()
defineEmits<{ select: [] }>()
</script>

<template>
  <button class="tag-filter" type="button" :aria-pressed="active" @click="$emit('select')">{{ label }}</button>
</template>
