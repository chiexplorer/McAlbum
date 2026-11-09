<script setup lang="ts">
interface TagItem {
  id: string
  name: string
  usage_count: number
  created_at: string
  draftName: string
}

const api = useManageApi()
const tags = ref<TagItem[]>([])
const newName = ref('')
const busyId = ref<string | null>(null)
const error = ref('')
const message = ref('')

useHead({ title: '标签管理 · McAlbum' })

onMounted(async () => {
  if (!await api.restore()) return
  if (!api.can('tag.manage')) return navigateTo('/manage')
  await reload()
})

async function reload() {
  const rows = await api.request<Omit<TagItem, 'draftName'>[]>('/manage/tags')
  tags.value = rows.map(item => ({ ...item, draftName: item.name }))
}

async function createTag() {
  await mutate('new', '/admin/tags', { method: 'POST', body: { name: newName.value } })
  newName.value = ''
}

async function renameTag(tag: TagItem) {
  if (tag.draftName.trim() === tag.name) return
  await mutate(tag.id, `/admin/tags/${tag.id}`, {
    method: 'PUT', body: { name: tag.draftName },
  })
}

async function deleteTag(tag: TagItem) {
  const usage = tag.usage_count ? `，并从 ${tag.usage_count} 张照片移除` : ''
  if (!window.confirm(`确认删除标签“${tag.name}”${usage}？`)) return
  await mutate(tag.id, `/admin/tags/${tag.id}`, { method: 'DELETE' })
}

async function mutate(id: string, path: string, options: Record<string, unknown>) {
  busyId.value = id
  error.value = ''
  message.value = ''
  try {
    await api.request(path, options)
    await reload()
    message.value = '标签目录已更新。'
  }
  catch (caught) { error.value = api.errorMessage(caught) }
  finally { busyId.value = null }
}
</script>

<template>
  <ManageShell>
    <header class="manage-heading">
      <p class="section-kicker">照片索引</p>
      <h1>标签管理</h1>
      <p>维护统一的照片主题词。重命名会同步影响所有关联照片；删除会解除已有照片关系。</p>
    </header>

    <ManageNotice v-if="error" kind="error">{{ error }}</ManageNotice>
    <ManageNotice v-if="message" kind="success">{{ message }}</ManageNotice>

    <form class="manage-form manage-tag-create" @submit.prevent="createTag">
      <label>新标签名称<input v-model.trim="newName" required maxlength="64" placeholder="例如：建筑"></label>
      <button class="manage-primary" type="submit" :disabled="busyId === 'new'">添加标签</button>
    </form>

    <section class="manage-admin-section manage-tag-catalog">
      <h2>标签目录 <small>{{ tags.length }}</small></h2>
      <p v-if="tags.length === 0">目前还没有标签，先建立一个供照片编目使用。</p>
      <article v-for="tag in tags" :key="tag.id">
        <label :for="`tag-${tag.id}`">
          <span>标签名称</span>
          <input :id="`tag-${tag.id}`" v-model.trim="tag.draftName" maxlength="64">
        </label>
        <p>{{ tag.usage_count }} 张照片正在使用</p>
        <div class="manage-actions">
          <button type="button" :disabled="busyId === tag.id || tag.draftName === tag.name" @click="renameTag(tag)">保存名称</button>
          <button type="button" :disabled="busyId === tag.id" @click="deleteTag(tag)">删除</button>
        </div>
      </article>
    </section>
  </ManageShell>
</template>
