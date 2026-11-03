<script setup lang="ts">
const props = defineProps<{ title: string; text?: string }>()
const feedback = ref('')

async function share(): Promise<void> {
  const data = { title: props.title, text: props.text, url: window.location.href }
  if (navigator.share) {
    try {
      await navigator.share(data)
      return
    }
    catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
    }
  }

  await navigator.clipboard.writeText(window.location.href)
  feedback.value = '链接已复制'
  window.setTimeout(() => { feedback.value = '' }, 2400)
}
</script>

<template>
  <div class="share-control">
    <button type="button" @click="share">分享这页</button>
    <span aria-live="polite">{{ feedback }}</span>
  </div>
</template>
