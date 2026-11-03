<script setup lang="ts">
const api = useManageApi()
useHead({ title: '编目工作台 · McAlbum' })

const tasks = computed(() => [
  { to: '/manage/photos', title: '上传一张照片', text: '一次完成原图入库，并补充标题、时间与标签。', permission: 'photo.create' },
  { to: '/manage/stories', title: '编排一篇作品集', text: '将文字与图片区块排成完整叙事。', permission: 'story.create' },
  { to: '/manage/profile', title: '维护玩家档案', text: '决定哪些个人信息可以在世界档案中出现。', permission: 'profile.self.update' },
].filter(task => api.can(task.permission)))
</script>

<template>
  <ManageShell>
    <header class="manage-heading">
      <p class="section-kicker">今日编目</p>
      <h1>从一条可靠的记录开始</h1>
      <p>新内容先保存为草稿。提交审核后，管理员或具有直接发布权限的作者才能把它放入公开档案。</p>
    </header>
    <div class="manage-task-list">
      <NuxtLink v-for="task in tasks" :key="task.to" :to="task.to">
        <strong>{{ task.title }}</strong><span>{{ task.text }}</span>
      </NuxtLink>
    </div>
    <section class="manage-state-guide">
      <h2>内容状态</h2>
      <ol>
        <li><strong>草稿</strong><span>只有作者和管理员可见，可继续修改。</span></li>
        <li><strong>待审核</strong><span>内容暂时锁定，等待管理员处理。</span></li>
        <li><strong>已发布</strong><span>进入下一次公开站点快照。</span></li>
        <li><strong>已归档</strong><span>从公开内容退出，但保留记录与审计。</span></li>
      </ol>
    </section>
  </ManageShell>
</template>
