<script setup lang="ts">
const api = useManageApi()
const mode = ref<'login' | 'register'>('login')
const username = ref('')
const displayName = ref('')
const minecraftName = ref('')
const applicationReason = ref('')
const password = ref('')
const website = ref('')
const error = ref('')
const success = ref('')
const busy = ref(false)

useHead({ title: '登录编目室 · McAlbum' })

onMounted(async () => {
  if (await api.restore()) await navigateTo('/manage')
})

async function submit() {
  error.value = ''
  success.value = ''
  busy.value = true
  try {
    if (mode.value === 'login') {
      await api.login(username.value, password.value)
      await navigateTo('/manage')
      return
    }
    const result = await api.request<{ message: string }>('/auth/register', {
      method: 'POST',
      body: {
        username: username.value,
        display_name: displayName.value,
        minecraft_name: minecraftName.value,
        application_reason: applicationReason.value,
        password: password.value,
        website: website.value,
      },
    })
    success.value = result.message
    password.value = ''
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
        <p>整理照片、编辑作品集，让每一次发布都保留清晰的来路。</p>
      </div>
    </section>
    <section class="manage-login__form">
      <div class="manage-login__switch" role="tablist" aria-label="账号方式">
        <button type="button" :aria-selected="mode === 'login'" @click="mode = 'login'">登录</button>
        <button type="button" :aria-selected="mode === 'register'" @click="mode = 'register'">申请账号</button>
      </div>
      <form class="manage-form" @submit.prevent="submit">
        <label>用户名<input v-model.trim="username" autocomplete="username" minlength="3" maxlength="64" required></label>
        <template v-if="mode === 'register'">
          <label>公开称呼<input v-model.trim="displayName" autocomplete="nickname" maxlength="80" required></label>
          <label>Minecraft 名称<input v-model.trim="minecraftName" autocomplete="off" minlength="3" maxlength="16" pattern="[A-Za-z0-9_]+" required></label>
          <label>申请说明<textarea v-model.trim="applicationReason" maxlength="1000" rows="4" required placeholder="请简单说明你在服务器中的身份"></textarea></label>
          <label class="manage-honeypot" aria-hidden="true">个人网站<input v-model="website" tabindex="-1" autocomplete="off"></label>
        </template>
        <label>密码<input v-model="password" type="password" :autocomplete="mode === 'login' ? 'current-password' : 'new-password'" minlength="8" :pattern="mode === 'register' ? '(?=.*[A-Za-z])(?=.*[0-9]).{8,}' : undefined" required></label>
        <p v-if="mode === 'register'" class="manage-field-note">至少 8 位，并同时包含字母和数字。提交后需由管理员审核。</p>
        <ManageNotice v-if="error" kind="error">{{ error }}</ManageNotice>
        <ManageNotice v-if="success" kind="success">{{ success }}</ManageNotice>
        <button class="manage-primary" type="submit" :disabled="busy">{{ busy ? '正在核对…' : mode === 'login' ? '登录' : '提交申请' }}</button>
      </form>
    </section>
  </main>
</template>
