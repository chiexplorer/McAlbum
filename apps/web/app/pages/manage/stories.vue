<script setup lang="ts">
type BlockType = 'text' | 'wide-image' | 'image-grid' | 'text-with-image'

interface Block {
  key: string
  id?: string
  type: BlockType
  body: string
  assetId: string
  assetIds: string[]
  caption: string
  imagePosition: 'left' | 'right'
}

interface StoryItem {
  id: string
  title: string
  summary: string
  cover_asset_id: string
  sections: Array<Record<string, unknown>>
  player_ids: string[]
  status: string
  rejection_reason: string | null
}

interface PhotoItem { id: string, title: string, asset_id: string, captured_at: string }

const api = useManageApi()
const stories = ref<StoryItem[]>([])
const photos = ref<PhotoItem[]>([])
const editingId = ref<string | null>(null)
const error = ref('')
const message = ref('')
const busy = ref(false)
const form = reactive({ title: '', summary: '', cover_asset_id: '' })
const blocks = ref<Block[]>([])
const blockTypes: Array<{ value: BlockType, label: string }> = [
  { value: 'text', label: '文字' },
  { value: 'wide-image', label: '宽幅图片' },
  { value: 'image-grid', label: '图片网格' },
  { value: 'text-with-image', label: '图文并排' },
]

useHead({ title: '作品集编排 · McAlbum' })

onMounted(async () => {
  if (!await api.restore()) return
  ;[stories.value, photos.value] = await Promise.all([
    api.request<StoryItem[]>('/manage/stories'),
    api.request<PhotoItem[]>('/manage/photos'),
  ])
})

function addBlock(type: BlockType = 'text') {
  blocks.value.push({
    key: crypto.randomUUID(), type, body: '', assetId: '', assetIds: [], caption: '',
    imagePosition: 'right',
  })
}

function sectionPayload(block: Block) {
  const identity = block.id ? { id: block.id } : {}
  if (block.type === 'text') return { ...identity, type: block.type, body: block.body }
  if (block.type === 'wide-image') {
    return { ...identity, type: block.type, assetId: block.assetId, caption: block.caption }
  }
  if (block.type === 'image-grid') {
    return { ...identity, type: block.type, assetIds: block.assetIds, caption: block.caption }
  }
  return {
    ...identity, type: block.type, body: block.body, assetId: block.assetId,
    imagePosition: block.imagePosition,
  }
}

function edit(story: StoryItem) {
  editingId.value = story.id
  Object.assign(form, {
    title: story.title, summary: story.summary, cover_asset_id: story.cover_asset_id,
  })
  blocks.value = story.sections.map(item => ({
    key: String(item.id || crypto.randomUUID()),
    id: typeof item.id === 'string' ? item.id : undefined,
    type: item.type as BlockType,
    body: String(item.body || ''),
    assetId: String(item.assetId || ''),
    assetIds: Array.isArray(item.assetIds) ? item.assetIds.map(String) : [],
    caption: String(item.caption || ''),
    imagePosition: item.imagePosition === 'left' ? 'left' : 'right',
  }))
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function save() {
  busy.value = true
  error.value = ''
  message.value = ''
  const body = {
    title: form.title,
    summary: form.summary,
    cover_asset_id: form.cover_asset_id,
    sections: blocks.value.map(sectionPayload),
    player_ids: [],
  }
  try {
    const path = editingId.value ? `/manage/stories/${editingId.value}` : '/manage/stories'
    const saved = await api.request<StoryItem>(path, {
      method: editingId.value ? 'PUT' : 'POST', body,
    })
    const index = stories.value.findIndex(value => value.id === saved.id)
    if (index >= 0) stories.value[index] = saved
    else stories.value.unshift(saved)
    edit(saved)
    message.value = `作品集草稿已保存，档案 ID 为 ${saved.id}`
  }
  catch (caught) { error.value = api.errorMessage(caught) }
  finally { busy.value = false }
}

async function transition(story: StoryItem, target_status: string) {
  const reason = target_status === 'rejected' ? window.prompt('填写退回原因') : null
  if (target_status === 'rejected' && !reason) return
  try {
    const updated = await api.request<StoryItem>(`/manage/stories/${story.id}/transition`, {
      method: 'POST', body: { target_status, reason },
    })
    stories.value[stories.value.findIndex(value => value.id === updated.id)] = updated
  }
  catch (caught) { error.value = api.errorMessage(caught) }
}
</script>

<template>
  <ManageShell>
    <header class="manage-heading">
      <p class="section-kicker">作品集编排</p>
      <h1>让图片形成一段可阅读的历史</h1>
      <p>作品集和内容区块的档案 ID 均由系统维护；选择图片时直接按最新照片标题辨认。</p>
    </header>
    <form class="manage-form manage-form--columns" @submit.prevent="save">
      <label>标题<input v-model.trim="form.title" required></label>
      <label>封面照片<select v-model="form.cover_asset_id" required><option value="" disabled>选择最新照片</option><option v-for="photo in photos" :key="photo.id" :value="photo.asset_id">{{ photo.title }} · {{ photo.captured_at.slice(0, 10) }}</option></select></label>
      <label class="manage-span">摘要<textarea v-model.trim="form.summary" rows="3" required /></label>
      <fieldset class="manage-span manage-blocks">
        <legend>内容区块</legend>
        <p>区块是作品集中的一段内容，可以是文字、一张图片、图片组或图文并排；保存后由系统自动编号。</p>
        <article v-for="(block, index) in blocks" :key="block.key">
          <label>类型<select v-model="block.type"><option value="text">文字</option><option value="wide-image">宽幅图片</option><option value="image-grid">图片网格</option><option value="text-with-image">图文并排</option></select></label>
          <label v-if="['text', 'text-with-image'].includes(block.type)" class="manage-span">正文<textarea v-model.trim="block.body" rows="3" required /></label>
          <label v-if="['wide-image', 'text-with-image'].includes(block.type)">照片<select v-model="block.assetId" required><option value="" disabled>选择照片</option><option v-for="photo in photos" :key="photo.id" :value="photo.asset_id">{{ photo.title }} · {{ photo.captured_at.slice(0, 10) }}</option></select></label>
          <label v-if="block.type === 'image-grid'" class="manage-span">照片组<select v-model="block.assetIds" multiple required size="6"><option v-for="photo in photos" :key="photo.id" :value="photo.asset_id">{{ photo.title }} · {{ photo.captured_at.slice(0, 10) }}</option></select><small>按住 Ctrl（macOS 为 Command）可选择多张。</small></label>
          <label v-if="['wide-image', 'image-grid'].includes(block.type)">图片说明<input v-model.trim="block.caption"></label>
          <label v-if="block.type === 'text-with-image'">图片位置<select v-model="block.imagePosition"><option value="left">左侧</option><option value="right">右侧</option></select></label>
          <button type="button" @click="blocks.splice(index, 1)">移除区块</button>
        </article>
        <div class="manage-actions"><button v-for="item in blockTypes" :key="item.value" type="button" @click="addBlock(item.value)">添加{{ item.label }}</button></div>
      </fieldset>
      <ManageNotice v-if="message" class="manage-span" kind="success">{{ message }}</ManageNotice>
      <ManageNotice v-if="error" class="manage-span" kind="error">{{ error }}</ManageNotice>
      <button class="manage-primary" type="submit" :disabled="busy || blocks.length === 0">保存作品集草稿</button>
    </form>
    <section class="manage-records">
      <h2>作品集记录</h2>
      <article v-for="story in stories" :key="story.id"><div><span class="manage-status" :data-status="story.status">{{ story.status }}</span><h3>{{ story.title }}</h3><p>{{ story.summary }}</p></div><div class="manage-actions"><button type="button" @click="edit(story)">编辑</button><button v-if="['draft', 'rejected'].includes(story.status)" type="button" @click="transition(story, api.can('story.publish') ? 'published' : 'pending')">{{ api.can('story.publish') ? '发布' : '提交审核' }}</button><button v-if="story.status === 'pending' && api.session.value?.user.role === 'admin'" type="button" @click="transition(story, 'published')">通过</button><button v-if="story.status === 'pending' && api.session.value?.user.role === 'admin'" type="button" @click="transition(story, 'rejected')">退回</button></div></article>
    </section>
  </ManageShell>
</template>
