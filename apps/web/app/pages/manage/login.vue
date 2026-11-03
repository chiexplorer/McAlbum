<script setup lang="ts">
const api = useManageApi()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const displayName = ref('')
const password = ref('')
const invitationCode = ref('')
const error = ref('')
const busy = ref(false)

useHead({ title: '登录编目室 · McAlbum' })

onMounted(async () => {
  if (await api.restore()) await navigateTo('/manage')
})

async function submit() {
  error.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await api.login(username.value, password.value)
    } else {
      api.session.value = await api.request('/auth/register', {
        method: 'POST',
        body: {
          username: username.value,
          display_name: displayName.value,
          password: password.value,
          invitation_code: invitationCode.value,
        },
      })
    }
    await navigateTo('/manage')
  } catch (caught) {
    error.value = api.errorMessage(caught)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <main id="main-content" class="manage-login">
    <section class="manage-login__intro">
      <NuxtLink class="site-mark" to="/">
        <span class="site-mark__seal" aria-hidden="true">麦</span><span>McAlbum</span>
      </NuxtLink>
      <div>
        <p class="section-kicker">协作入口</p>
        <h1>进入档案编目室</h1>
        <p>整理照片、编辑作品集，并让每一次发布都保留清晰的来路。</p>
      </div>
    </section>
    <section class="manage-login__form">
      <div class="manage-login__switch" role="tablist" aria-label="账号方式">
        <button type="button" :aria-selected="mode === 'login'" @click="mode = 'login'">登录</button>
        <button type="button" :aria-selected="mode === 'register'" @click="mode = 'register'">使用邀请码</button>
      </div>
      <form class="manage-form" @submit.prevent="submit">
        <label>用户名<input v-model.trim="username" autocomplete="username" minlength="3" required></label>
        <label v-if="mode === 'register'">公开称呼<input v-model.trim="displayName" autocomplete="nickname" required></label>
        <label>密码<input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="10" required></label>
        <label v-if="mode === 'register'">邀请码<input v-model.trim="invitationCode" autocomplete="off" required></label>
        <ManageNotice v-if="error" kind="error">{{ error }}</ManageNotice>
        <button class="manage-primary" type="submit" :disabled="busy">{{ busy ? '正在核对……' : mode === 'login' ? '登录' : '创建账号' }}</button>
      </form>
    </section>
  </main>
</template>
