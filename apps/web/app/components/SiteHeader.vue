<template>
  <header class="site-header">
    <div class="site-header__inner page-container">
      <NuxtLink class="site-mark" to="/" aria-label="McAlbum 世界首页">
        <span class="site-mark__seal" aria-hidden="true">麦</span>
        <span>McAlbum</span>
      </NuxtLink>
      <nav class="desktop-nav" aria-label="主导航">
        <ul class="site-nav">
          <li><NuxtLink to="/">世界首页</NuxtLink></li>
          <li><NuxtLink to="/album">相册</NuxtLink></li>
          <li><NuxtLink to="/stories">历史</NuxtLink></li>
          <li><NuxtLink to="/players">玩家志</NuxtLink></li>
          <li><NuxtLink to="/manage/login">编目室</NuxtLink></li>
        </ul>
      </nav>
      <details class="mobile-nav">
        <summary>浏览档案</summary>
        <nav aria-label="移动端主导航">
          <ul class="site-nav site-nav--mobile">
            <li><NuxtLink to="/">世界首页</NuxtLink></li>
            <li><NuxtLink to="/album">相册</NuxtLink></li>
            <li><NuxtLink to="/stories">历史</NuxtLink></li>
            <li><NuxtLink to="/players">玩家志</NuxtLink></li>
            <li><NuxtLink to="/manage/login">编目室</NuxtLink></li>
          </ul>
        </nav>
      </details>
    </div>
  </header>
</template>
