<script setup lang="ts">
interface CommentItem { id: string, body: string, status: string, created_at?: string, author_user_id?: string }
const props = defineProps<{ photoId: string, initialComments?: Array<{ id: string, body: string }> }>()
const api = useManageApi()
const comments = ref<CommentItem[]>((props.initialComments || []).map(item => ({ ...item, status: 'published' })))
const body = ref(''); const error = ref(''); const busy = ref(false); const ready = ref(false)
onMounted(async () => {
  if (await api.restore()) {
    try { comments.value = await api.request(`/comments/photo/${props.photoId}`) } catch { /* 静态评论仍可继续展示。 */ }
  }
  ready.value = true
})
async function publish() {
  busy.value = true; error.value = ''
  try { const created = await api.request<CommentItem>(`/comments/photo/${props.photoId}`, { method: 'POST', body: { body: body.value } }); comments.value.push(created); body.value = '' }
  catch (caught) { error.value = api.errorMessage(caught) }
  finally { busy.value = false }
}
</script>

<template>
  <div class="photo-comments">
    <ol v-if="comments.length" class="photo-comments__list">
      <li v-for="comment in comments" :key="comment.id"><p>{{ comment.body }}</p><small>已登录玩家 · {{ comment.created_at ? new Date(comment.created_at).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }) : '档案评论' }}</small></li>
    </ol>
    <EmptyState v-else title="还没有公开评论" description="登录后可以留下与这张照片有关的补充记录。" />
    <form v-if="api.session.value && api.can('comment.create')" class="photo-comments__form" @submit.prevent="publish">
      <label for="photo-comment">添加评论</label><textarea id="photo-comment" v-model.trim="body" maxlength="1000" rows="3" required />
      <ManageNotice v-if="error" kind="error">{{ error }}</ManageNotice><button class="manage-primary" type="submit" :disabled="busy">{{ busy ? '正在发布……' : '发布评论' }}</button>
    </form>
    <p v-else-if="ready" class="photo-comments__login"><NuxtLink to="/manage/login">登录编目室</NuxtLink>后参与评论。</p>
  </div>
</template>
