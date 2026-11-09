<script setup lang="ts">
import { beijingToday, dateFromFilename } from '~/utils/manage-date'
import { catalogDefaultsFromMedia } from '~/utils/manage-media'

interface MediaItem {
  id: string
  alt_text: string
  captured_at: string
  focal_x: number
  focal_y: number
  width: number
  height: number
  processing_status: string
  variants: Array<{ name: string, url: string, width: number, height: number }>
}
interface PhotoItem {
  id: string, title: string, description: string, asset_id: string, captured_at: string,
  photographer_id: string | null, tags: string[],
  player_ids: string[], story_ids: string[], featured: boolean,
  display_variant: 'featured' | 'normal' | 'portrait' | 'note', status: string,
  rejection_reason: string | null, author_user_id: string,
}
interface TagItem { id: string, name: string, usage_count: number, created_at: string }

const api = useManageApi()
const route = useRoute()
const photos = ref<PhotoItem[]>([])
const media = ref<MediaItem[]>([])
const tagOptions = ref<TagItem[]>([])
const editingId = ref<string | null>(null)
const fileInput = ref<HTMLInputElement | null>(null)
const file = ref<File | null>(null)
const altText = ref('')
const focalX = ref(0.5)
const focalY = ref(0.5)
const titleWasEdited = ref(false)
const busy = ref(false)
const error = ref('')
const message = ref('')
const form = reactive({
  title: '', description: '', asset_id: '', captured_at: beijingToday(), tags: [] as string[],
  featured: false, display_variant: 'normal' as PhotoItem['display_variant'],
})
const usedAssetIds = computed(() => new Set(photos.value.map(photo => photo.asset_id)))
const availableMedia = computed(() => media.value.filter(item => !usedAssetIds.value.has(item.id)))
const editableMedia = computed(() => media.value.filter(item => (
  item.id === form.asset_id || !usedAssetIds.value.has(item.id)
)))

useHead({ title: '上传照片 · McAlbum' })
onMounted(async () => {
  if (!await api.restore()) return
  [photos.value, media.value, tagOptions.value] = await Promise.all([
    api.request<PhotoItem[]>('/manage/photos'), api.request<MediaItem[]>('/manage/media'),
    api.request<TagItem[]>('/manage/tags'),
  ])
  const requestedAsset = typeof route.query.asset === 'string' ? route.query.asset : ''
  if (requestedAsset && availableMedia.value.some(item => item.id === requestedAsset)) {
    form.asset_id = requestedAsset
    applyMediaDefaults(requestedAsset)
  }
})

function applyMediaDefaults(assetId: string) {
  const asset = media.value.find(item => item.id === assetId)
  if (!asset) return
  const defaults = catalogDefaultsFromMedia(asset)
  form.title = defaults.title
  if (defaults.capturedAt) form.captured_at = defaults.capturedAt
  altText.value = asset.alt_text
  titleWasEdited.value = false
}

function selectMedia(event: Event) {
  file.value = null
  if (fileInput.value) fileInput.value.value = ''
  applyMediaDefaults((event.target as HTMLSelectElement).value)
}

function selectFile(event: Event) {
  file.value = (event.target as HTMLInputElement).files?.[0] || null
  if (!file.value) return
  const switchedFromLibrary = Boolean(form.asset_id)
  form.asset_id = ''
  if (switchedFromLibrary) {
    altText.value = ''
    if (!titleWasEdited.value) form.title = ''
  }
  form.captured_at = dateFromFilename(file.value.name) ?? beijingToday()
  if (!titleWasEdited.value) form.title = altText.value.trim()
}

function syncTitleFromAltText() {
  if (!titleWasEdited.value) form.title = altText.value.trim()
}

function markTitleEdited() {
  titleWasEdited.value = true
}

function payload(assetId = form.asset_id) {
  return {
    title: form.title, description: form.description, asset_id: assetId,
    captured_at: `${form.captured_at}T12:00:00+08:00`, photographer_id: null,
    tags: form.tags,
    player_ids: [], story_ids: [], featured: form.featured,
    display_variant: form.display_variant,
  }
}

function edit(photo: PhotoItem) {
  editingId.value = photo.id
  Object.assign(form, {
    title: photo.title, description: photo.description, asset_id: photo.asset_id,
    captured_at: photo.captured_at.slice(0, 10),
    tags: [...photo.tags], featured: photo.featured, display_variant: photo.display_variant,
  })
  const asset = media.value.find(item => item.id === photo.asset_id)
  altText.value = asset?.alt_text ?? ''
  titleWasEdited.value = true
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function clear() {
  editingId.value = null
  file.value = null
  altText.value = ''
  focalX.value = 0.5
  focalY.value = 0.5
  titleWasEdited.value = false
  if (fileInput.value) fileInput.value.value = ''
  Object.assign(form, {
    title: '', description: '', asset_id: '', captured_at: beijingToday(), tags: [],
    featured: false, display_variant: 'normal',
  })
}

async function save() {
  if (!editingId.value && !file.value && !form.asset_id) {
    error.value = '请选择一张新图片，或从媒体库选择已有图片。'
    return
  }
  busy.value = true
  error.value = ''
  message.value = ''
  const wasEditing = Boolean(editingId.value)
  let uploadedInThisSave = false
  try {
    let assetId = form.asset_id
    if (!editingId.value && file.value) {
      const data = new FormData()
      data.append('file', file.value)
      data.append('alt_text', altText.value)
      data.append('captured_at', `${form.captured_at}T12:00:00+08:00`)
      data.append('focal_x', String(focalX.value))
      data.append('focal_y', String(focalY.value))
      const created = await api.request<MediaItem>('/manage/media', { method: 'POST', body: data })
      media.value.unshift(created)
      assetId = created.id
      form.asset_id = created.id
      uploadedInThisSave = true
      file.value = null
      if (fileInput.value) fileInput.value.value = ''
    }
    const path = editingId.value ? `/manage/photos/${editingId.value}` : '/manage/photos'
    const saved = await api.request<PhotoItem>(path, {
      method: editingId.value ? 'PUT' : 'POST',
      body: payload(assetId),
    })
    const index = photos.value.findIndex(item => item.id === saved.id)
    if (index >= 0) photos.value[index] = saved
    else photos.value.unshift(saved)
    message.value = `${uploadedInThisSave ? '图片已入库，' : ''}草稿已保存，档案 ID 为 ${saved.id}`
    if (wasEditing) {
      edit(saved)
    }
    else {
      clear()
      await nextTick()
      fileInput.value?.focus()
    }
  }
  catch (caught) {
    const reason = api.errorMessage(caught)
    error.value = uploadedInThisSave
      ? `图片已经安全入库，但照片草稿未能保存：${reason}。请保留当前页面并重试保存。`
      : reason
  }
  finally { busy.value = false }
}

async function transition(photo: PhotoItem, target_status: string) {
  try {
    const updated = await api.request<PhotoItem>(`/manage/photos/${photo.id}/transition`, {
      method: 'POST', body: { target_status, reason: null },
    })
    photos.value[photos.value.findIndex(item => item.id === updated.id)] = updated
  }
  catch (caught) { error.value = api.errorMessage(caught) }
}

async function remove(photo: PhotoItem) {
  if (!window.confirm('确认删除这条照片记录？原图仍会保留。')) return
  try {
    const updated = await api.request<PhotoItem>(`/manage/photos/${photo.id}`, { method: 'DELETE' })
    photos.value[photos.value.findIndex(item => item.id === updated.id)] = updated
  } catch (caught) { error.value = api.errorMessage(caught) }
}
</script>

<template>
  <ManageShell>
    <header class="manage-heading">
      <p class="section-kicker">照片档案</p>
      <h1>{{ editingId ? '修订照片记录' : '上传并建立照片记录' }}</h1>
      <p>{{ editingId ? '标题和说明可以继续修订，公开网址始终保持稳定。' : '一次填写即可完成原图入库和草稿建立；媒体 ID 与照片 ID 均由系统维护。' }}</p>
    </header>
    <form v-if="api.can('photo.create') || editingId" class="manage-form manage-form--columns" @submit.prevent="save">
      <fieldset v-if="!editingId" class="manage-step manage-span">
        <legend><span>1</span> 选择图片</legend>
        <div class="manage-step__grid">
          <label class="manage-file">上传新的 PNG、JPEG 或 WebP<input ref="fileInput" type="file" accept="image/png,image/jpeg,image/webp" @change="selectFile"><small>若文件名包含类似 2026-09-06_17.16.37 的日期，将自动填入拍摄日期。</small></label>
          <label>或者使用媒体库中的图片<select v-model="form.asset_id" @change="selectMedia"><option value="">暂不选择已有图片</option><option v-for="item in availableMedia" :key="item.id" :value="item.id">{{ item.alt_text }}（{{ item.id.slice(0, 14) }}…）</option></select><small>只列出尚未编目的图片；选择后自动填充标题和拍摄日期。</small></label>
          <label v-if="file" class="manage-span">画面替代文本<textarea v-model.trim="altText" maxlength="240" rows="3" required placeholder="简洁描述画面内容" @input="syncTitleFromAltText" /><small>会自动填入标题，之后仍可分别修改。</small></label>
          <label v-if="file">横向焦点<input v-model.number="focalX" type="range" min="0" max="1" step="0.01"><output>{{ focalX.toFixed(2) }}</output></label>
          <label v-if="file">纵向焦点<input v-model.number="focalY" type="range" min="0" max="1" step="0.01"><output>{{ focalY.toFixed(2) }}</output></label>
        </div>
      </fieldset>
      <fieldset class="manage-step manage-span">
        <legend><span>{{ editingId ? '1' : '2' }}</span> 整理照片信息</legend>
        <div class="manage-step__grid">
          <label v-if="editingId">关联图片<select v-model="form.asset_id" required @change="selectMedia"><option v-for="item in editableMedia" :key="item.id" :value="item.id">{{ item.alt_text }}（{{ item.id.slice(0, 14) }}…）</option></select></label>
          <label>标题<input v-model.trim="form.title" required @input="markTitleEdited"></label>
          <ManageDateField v-model="form.captured_at" label="拍摄日期（北京时间）" />
          <label class="manage-span">说明（可选）<textarea v-model.trim="form.description" rows="4" placeholder="可补充画面背景、故事或值得记录的细节" /></label>
          <div class="manage-tag-picker">
            <span>标签</span>
            <details>
              <summary>{{ form.tags.length ? `已选择 ${form.tags.length} 项` : '选择标签' }}</summary>
              <div class="manage-tag-options" role="group" aria-label="照片标签候选项">
                <label v-for="tag in tagOptions" :key="tag.id">
                  <input v-model="form.tags" type="checkbox" :value="tag.name">
                  <span>{{ tag.name }}</span>
                </label>
                <p v-if="tagOptions.length === 0">标签目录为空，请联系管理员先建立标签。</p>
              </div>
            </details>
            <small>可多选；候选项由管理员维护。</small>
          </div>
          <label>版式<select v-model="form.display_variant"><option value="normal">普通</option><option value="featured">精选</option><option value="portrait">竖幅</option><option value="note">札记</option></select></label>
          <label class="manage-check"><input v-model="form.featured" type="checkbox">加入精选候选</label>
        </div>
      </fieldset>
      <ManageNotice v-if="message" class="manage-span" kind="success">{{ message }}</ManageNotice>
      <ManageNotice v-if="error" class="manage-span" kind="error">{{ error }}</ManageNotice>
      <div class="manage-actions manage-span"><button class="manage-primary" type="submit" :disabled="busy">{{ busy ? (file ? '正在处理图片……' : '正在保存……') : (editingId ? '保存修订' : '上传并保存草稿') }}</button><button v-if="editingId" type="button" @click="clear">上传另一张</button></div>
    </form>
    <section class="manage-records">
      <h2>照片记录</h2>
      <article v-for="photo in photos" :key="photo.id">
        <div><span class="manage-status" :data-status="photo.status">{{ photo.status }}</span><h3>{{ photo.title }}</h3><p>{{ photo.description }}</p><small v-if="photo.rejection_reason">退回原因：{{ photo.rejection_reason }}</small></div>
        <div class="manage-actions"><button v-if="photo.author_user_id === api.session.value?.user.id && api.can('photo.update.own')" type="button" @click="edit(photo)">编辑</button><button v-if="photo.author_user_id === api.session.value?.user.id && ['draft', 'rejected', 'archived'].includes(photo.status) && api.can('photo.publish.own')" type="button" @click="transition(photo, 'published')">发布</button><button v-if="photo.author_user_id === api.session.value?.user.id && photo.status === 'published' && api.can('photo.archive.own')" type="button" @click="transition(photo, 'archived')">归档</button><button v-if="photo.status !== 'deleted' && api.can('photo.delete.any')" type="button" @click="remove(photo)">删除</button></div>
      </article>
    </section>
  </ManageShell>
</template>
