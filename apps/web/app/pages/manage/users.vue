<script setup lang="ts">
interface PermissionItem { code: string; name_zh: string; group_name: string; description: string }
interface RoleItem { id: string; code: string; name_zh: string; description: string; permissions: string[] }
interface UserItem { id: string; username: string; display_name: string; minecraft_name: string | null; application_reason: string; review_reason: string | null; ban_reason: string | null; role_id: string; role: string; role_name: string; status: string; created_at: string }
interface CommentItem { id: string; photoId: string; body: string; status: string; deletionReason: string | null }

const api = useManageApi()
const permissions = ref<PermissionItem[]>([])
const roles = ref<RoleItem[]>([])
const users = ref<UserItem[]>([])
const comments = ref<CommentItem[]>([])
const error = ref('')
const message = ref('')

const groupedPermissions = computed(() => {
  const groups = new Map<string, PermissionItem[]>()
  for (const item of permissions.value) {
    const group = groups.get(item.group_name) || []
    group.push(item)
    groups.set(item.group_name, group)
  }
  return groups
})
const pendingUsers = computed(() => users.value.filter(user => user.status === 'pending'))
const statusNames: Record<string, string> = { active: '正常', rejected: '已拒绝', banned: '已封禁' }

useHead({ title: '账号与角色 · McAlbum' })

onMounted(async () => {
  if (!await api.restore()) return
  if (!['user.review', 'user.role.assign', 'user.ban', 'role.permissions.manage', 'comment.delete.any'].some(api.can)) return navigateTo('/manage')
  await reload()
})

async function reload() {
  error.value = ''
  try {
    const canReadUsers = ['user.review', 'user.role.assign', 'user.ban', 'role.permissions.manage'].some(api.can)
    const [userRows, permissionRows, roleRows, commentRows] = await Promise.all([
      canReadUsers ? api.request<UserItem[]>('/admin/users') : Promise.resolve([]),
      api.can('role.permissions.manage') ? api.request<PermissionItem[]>('/admin/permissions') : Promise.resolve([]),
      api.can('role.permissions.manage') || api.can('user.role.assign') ? api.request<RoleItem[]>('/admin/roles') : Promise.resolve([]),
      api.can('comment.delete.any') ? api.request<CommentItem[]>('/admin/comments') : Promise.resolve([]),
    ])
    users.value = userRows
    permissions.value = permissionRows
    roles.value = roleRows
    comments.value = commentRows
  } catch (caught) { error.value = api.errorMessage(caught) }
}

async function review(user: UserItem, action: 'approve' | 'reject') {
  const reason = action === 'reject' ? window.prompt('请填写拒绝原因') : null
  if (action === 'reject' && !reason) return
  await mutate(`/admin/users/${user.id}/review`, { method: 'POST', body: { action, reason } })
}

async function saveRole(user: UserItem) {
  await mutate(`/admin/users/${user.id}/role`, { method: 'PUT', body: { role_id: user.role_id } })
}

async function toggleBan(user: UserItem) {
  const banned = user.status !== 'banned'
  const reason = banned ? window.prompt('请填写封禁原因') : null
  if (banned && !reason) return
  await mutate(`/admin/users/${user.id}/ban`, { method: 'PUT', body: { banned, reason } })
}

async function saveRolePermissions(role: RoleItem) {
  await mutate(`/admin/roles/${role.id}/permissions`, { method: 'PUT', body: { permissions: role.permissions } })
}

async function deleteComment(comment: CommentItem) {
  if (!window.confirm('确认删除这条评论？该操作会保留审计记录。')) return
  await mutate(`/comments/${comment.id}`, { method: 'DELETE', body: { reason: '管理员删除' } })
}

async function rebuild() {
  await mutate('/admin/publish', { method: 'POST' }, false)
}

async function mutate(path: string, options: Record<string, unknown>, refresh = true) {
  error.value = ''; message.value = ''
  try {
    await api.request(path, options)
    message.value = '操作已保存。'
    if (refresh) await reload()
  } catch (caught) { error.value = api.errorMessage(caught) }
}
</script>

<template>
  <ManageShell>
    <header class="manage-heading">
      <p class="section-kicker">管理员</p>
      <h1>账号与角色</h1>
      <p>注册申请先经过人工确认；权限以中文能力项归入固定角色，不向单个用户零散授权。</p>
    </header>
    <ManageNotice v-if="error" kind="error">{{ error }}</ManageNotice>
    <ManageNotice v-if="message" kind="success">{{ message }}</ManageNotice>

    <section v-if="api.can('user.review')" class="manage-admin-section">
      <h2>待审核申请 <small>{{ pendingUsers.length }}</small></h2>
      <p v-if="pendingUsers.length === 0">目前没有等待处理的申请。</p>
      <article v-for="user in pendingUsers" :key="user.id" class="manage-user manage-user--application">
        <header><div><strong>{{ user.display_name }}</strong><span>@{{ user.username }} · {{ user.minecraft_name }}</span></div></header>
        <p>{{ user.application_reason }}</p>
        <div class="manage-actions"><button class="manage-primary" type="button" @click="review(user, 'approve')">通过并设为普通用户</button><button type="button" @click="review(user, 'reject')">拒绝</button></div>
      </article>
    </section>

    <section v-if="api.can('user.role.assign') || api.can('user.ban')" class="manage-admin-section">
      <h2>账号状态</h2>
      <article v-for="user in users.filter(item => item.status !== 'pending')" :key="user.id" class="manage-user">
        <header><div><strong>{{ user.display_name }}</strong><span>@{{ user.username }} · {{ user.minecraft_name || '未填写游戏名' }}</span></div><span class="manage-status" :data-status="user.status">{{ statusNames[user.status] || user.status }}</span></header>
        <p v-if="user.review_reason">审核备注：{{ user.review_reason }}</p><p v-if="user.ban_reason">封禁原因：{{ user.ban_reason }}</p>
        <div class="manage-actions">
          <template v-if="api.can('user.role.assign') && user.status === 'active'">
            <select v-model="user.role_id" :aria-label="`${user.display_name}的角色`"><option v-for="role in roles" :key="role.id" :value="role.id">{{ role.name_zh }}</option></select>
            <button type="button" @click="saveRole(user)">保存角色</button>
          </template>
          <button v-if="api.can('user.ban') && user.id !== api.session.value?.user.id && ['active', 'banned'].includes(user.status)" type="button" @click="toggleBan(user)">{{ user.status === 'banned' ? '解除封禁' : '封禁账号' }}</button>
        </div>
      </article>
    </section>

    <section v-if="api.can('role.permissions.manage')" class="manage-admin-section">
      <h2>角色权限</h2>
      <article v-for="role in roles" :key="role.id" class="manage-role">
        <header><div><h3>{{ role.name_zh }}</h3><p>{{ role.description }}</p></div><button type="button" @click="saveRolePermissions(role)">保存权限</button></header>
        <div v-for="[group, items] in groupedPermissions" :key="group" class="manage-permission-group">
          <h4>{{ group }}</h4><div class="manage-permission-grid"><label v-for="permission in items" :key="permission.code"><input v-model="role.permissions" type="checkbox" :value="permission.code"><span><strong>{{ permission.name_zh }}</strong><small>{{ permission.description }}</small></span></label></div>
        </div>
      </article>
    </section>

    <section v-if="api.can('comment.delete.any')" class="manage-admin-section">
      <h2>评论管理</h2><p v-if="comments.length === 0">还没有玩家评论。</p>
      <article v-for="comment in comments" :key="comment.id" class="manage-comment"><div><span class="manage-status" :data-status="comment.status">{{ comment.status }}</span><p>{{ comment.body }}</p><small>照片：{{ comment.photoId }}</small></div><button v-if="comment.status !== 'deleted'" type="button" @click="deleteComment(comment)">删除</button></article>
    </section>

    <section v-if="api.can('snapshot.publish')" class="manage-admin-section"><h2>归档快照</h2><p>日常内容通过公开 API 实时刷新；这里仅用于更新 SEO 页面和独立归档。</p><button class="manage-primary" type="button" @click="rebuild">同步并生成快照</button></section>
  </ManageShell>
</template>
