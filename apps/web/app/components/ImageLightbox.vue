<script setup lang="ts">
import type { PublicMediaAsset } from '~/schemas/content'

const props = defineProps<{ asset: PublicMediaAsset | null; title?: string }>()
const emit = defineEmits<{ close: [] }>()
const dialog = ref<HTMLDialogElement>()

watch(() => props.asset, async (asset) => {
  await nextTick()
  if (asset && dialog.value && !dialog.value.open) dialog.value.showModal()
  if (!asset && dialog.value?.open) dialog.value.close()
})

function close(): void {
  dialog.value?.close()
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dialog" class="lightbox" aria-label="图片查看器" @close="emit('close')" @click.self="close">
      <div v-if="asset" class="lightbox__inner">
        <button class="lightbox__close" type="button" @click="close">关闭</button>
        <AppMedia :asset="asset" :alt="asset.altText" eager sizes="100vw" />
        <div class="lightbox__caption">
          <strong>{{ title }}</strong>
          <span>{{ asset.altText }}</span>
        </div>
      </div>
    </dialog>
  </Teleport>
</template>
