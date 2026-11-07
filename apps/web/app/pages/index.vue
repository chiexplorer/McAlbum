<script setup lang="ts">
import type { PublicMediaAsset } from '~/schemas/content'
import { getHomeContent, getPhotoContent } from '~/repositories/json-content'

const { site, featuredStory, coverAsset } = getHomeContent()
const { photos: publicPhotos } = usePublicPhotos()
const selectedAsset = ref<PublicMediaAsset | null>(null)
const selectedTitle = ref('')
const activeTag = ref('全部记录')

const tags = ['全部记录', '夜景', '市集', '合影']
const daylight = getPhotoContent('mid-autumn-gate-daylight')
const night = getPhotoContent('mid-autumn-fireworks-03')
const recentPhotos = computed(() => [...publicPhotos.value]
  .sort((left, right) => right.photo.capturedAt.localeCompare(left.photo.capturedAt))
  .slice(0, 6))
const visiblePhotos = computed(() => activeTag.value === '全部记录'
  ? recentPhotos.value
  : recentPhotos.value.filter(entry => entry.photo.tags.includes(activeTag.value)))

function openLightbox(asset: PublicMediaAsset, title: string): void {
  selectedAsset.value = asset
  selectedTitle.value = title
}

const ogVariant = coverAsset.variants.find(variant => variant.name === 'w1920')
  ?? coverAsset.variants.at(-1)
usePageSeo({
  title: `${site.title} · 世界档案馆`,
  description: site.description,
  image: ogVariant ? `/${ogVariant.storageKey.replace(/^variants\//, 'media/')}` : undefined,
})
</script>

<template>
  <main id="main-content">
    <section class="hero">
      <div class="hero__media">
        <AppMedia
          :asset="coverAsset"
          :alt="coverAsset.altText"
          eager
          sizes="(max-width: 840px) 100vw, 68vw"
        />
        <div class="hero__caption">
          <span>最近入藏</span>
          <strong>{{ featuredStory.title }}</strong>
        </div>
      </div>

      <div class="hero__content">
        <p class="world-status">服务器世界持续运行</p>
        <h1>{{ site.title }}</h1>
        <p class="hero__statement">{{ site.worldStatement }}</p>
        <ArchiveStamp
          :date="site.startedAt"
          :world-day="site.worldDay ?? undefined"
          place="主世界"
        />
        <a class="text-link" href="#recent-photos">翻阅最近照片</a>
      </div>
    </section>

    <section class="intro page-container" aria-labelledby="intro-title">
      <p class="section-kicker">关于这座档案馆</p>
      <div>
        <h2 id="intro-title">把共同生活过的世界，留在版本更迭之后</h2>
        <p>{{ site.description }}照片、地点、作品和玩家不会被拆成孤立的数据；它们会沿着同一次建设、探索或节日重新相遇。</p>
      </div>
      <dl class="server-facts">
        <div><dt>Minecraft</dt><dd>{{ site.minecraftVersion }}</dd></div>
        <div><dt>Fabric</dt><dd>{{ site.fabricVersion }}</dd></div>
        <div><dt>时区</dt><dd>中国北京</dd></div>
      </dl>
    </section>

    <section class="principles-section page-container" aria-labelledby="principles-title">
      <header>
        <p class="section-kicker">共同游玩原则</p>
        <h2 id="principles-title">轻一些规则，长久一点相处。</h2>
      </header>
      <ol>
        <li v-for="(principle, index) in site.principles" :key="principle.title">
          <span>0{{ index + 1 }}</span>
          <h3>{{ principle.title }}</h3>
          <p>{{ principle.description }}</p>
        </li>
      </ol>
    </section>

    <section id="recent-photos" class="archive-section page-container" aria-labelledby="recent-title">
      <header class="section-heading">
        <div>
          <p class="section-kicker">照片散页</p>
          <h2 id="recent-title">最近整理的记录</h2>
        </div>
        <p>点击照片可以查看大图。文字内容目前为编辑草稿，正式发布前仍会校订。</p>
      </header>

      <div class="filter-row" aria-label="照片筛选示例">
        <TagFilter
          v-for="tag in tags"
          :key="tag"
          :label="tag"
          :active="activeTag === tag"
          @select="activeTag = tag"
        />
      </div>

      <div class="photo-grid">
        <PhotoCard
          v-for="entry in visiblePhotos"
          :key="entry.photo.id"
          :photo="entry.photo"
          :asset="entry.asset"
          @open="openLightbox"
        />
      </div>
      <EmptyState
        v-if="visiblePhotos.length === 0"
        title="这里还没有相关照片"
        description="换一个标签，或等下一批档案整理完成后再来看看。"
      />
      <NuxtLink class="text-link section-more" to="/album">打开完整相册</NuxtLink>
    </section>

    <section class="story-band" aria-labelledby="story-title">
      <div class="page-container story-band__inner">
        <ArchiveStamp date="2026-09-25" place="太极广场西侧" />
        <div>
          <p class="section-kicker">历史专题</p>
          <h2 id="story-title">{{ featuredStory.title }}</h2>
          <p>{{ featuredStory.summary }}</p>
        </div>
        <div class="story-band__actions">
          <span class="story-band__status">已入藏</span>
          <NuxtLink :to="`/stories/${featuredStory.id}`">阅读专题</NuxtLink>
        </div>
      </div>
    </section>

    <section v-if="daylight && night" class="comparison-section page-container" aria-labelledby="comparison-title">
      <header class="section-heading">
        <div><p class="section-kicker">场景对照</p><h2 id="comparison-title">同一门楼，从日光到烟花。</h2></div>
        <p>当前素材只能确认同日昼夜变化；待补充早期或施工截图后，这里可直接升级为真正的“过去与现在”。</p>
      </header>
      <ImageComparison :before="daylight.asset" :after="night.asset" before-label="日间 · 活动前" after-label="夜间 · 烟花时刻">
        并排呈现保留完整画面，不依赖拖拽控件，也便于键盘与触屏用户理解差异。
      </ImageComparison>
    </section>

    <ImageLightbox
      :asset="selectedAsset"
      :title="selectedTitle"
      @close="selectedAsset = null"
    />
  </main>
</template>
