<script setup lang="ts">
const api = useManageApi()
const route = useRoute()

onMounted(async () => {
  const restored = await api.restore()
  if (!restored && route.path !== '/manage/login') await navigateTo('/manage/login')
})

const links = computed(() => [
  { to: '/manage', label: '工作台', show: true },
  { to: '/manage/photos', label: '上传照片', show: ['photo.create', 'photo.update.own', 'photo.delete.any'].some(api.can) },
  { to: '/manage/media', label: '媒体库', show: api.can('photo.create') },
  { to: '/manage/stories', label: '作品集', show: ['story.create', 'story.update.own', 'story.delete.any'].some(api.can) },
  { to: '/manage/tags', label: '标签管理', show: api.can('tag.manage') },
  { to: '/manage/profile', label: '玩家档案', show: api.can('profile.manage.own') },
  { to: '/manage/users', label: '账号与角色', show: ['user.review', 'user.role.assign', 'user.ban', 'role.permissions.manage', 'comment.delete.any'].some(api.can) },
].filter(item => item.show))
</script>

<template>
  <main id="main-content" class="manage-page">
    <div v-if="api.loading.value" class="manage-loading" role="status">正在核对档案权限……</div>
    <div v-else-if="api.session.value" class="manage-frame page-container">
      <aside class="manage-rail">
        <div>
          <p class="section-kicker">档案编目室</p>
          <p class="manage-identity">
            <strong>{{ api.session.value.user.display_name }}</strong>
            <span>{{ api.session.value.user.role_name }}</span>
          </p>
        </div>
        <nav aria-label="内容管理">
          <NuxtLink
            v-for="link in links"
            :key="link.to"
            :to="link.to"
            :aria-current="route.path === link.to ? 'page' : undefined"
          >{{ link.label }}</NuxtLink>
        </nav>
        <button class="manage-link-button" type="button" @click="api.logout">退出登录</button>
      </aside>
      <section class="manage-sheet">
        <slot />
      </section>
    </div>
  </main>
</template>
