<script setup lang="ts">
import type { PhotoArchiveMonth } from '~/repositories/content-repository'
import type { PublicMediaAsset } from '~/schemas/content'
import { getAlbumContent } from '~/repositories/json-content'

const route = useRoute()
const router = useRouter()
const selectedAsset = ref<PublicMediaAsset | null>(null)
const selectedTitle = ref('')
const availableTags = ref<string[]>(getAlbumContent().tags)
const rhythmTags = computed(() => ['全部', ...availableTags.value])

const activeTag = computed(() => {
  const value = typeof route.query.tag === 'string' ? route.query.tag : '全部'
  return rhythmTags.value.includes(value) ? value : '全部'
})
const activeMonth = computed(() => {
  const value = typeof route.query.month === 'string' ? route.query.month : undefined
  return value && /^\d{4}-(0[1-9]|1[0-2])$/.test(value) ? value : undefined
})
const requestedTag = computed(() => activeTag.value === '全部' ? undefined : activeTag.value)
const {
  photos: archivePhotos,
  tags: archiveTags,
  timeline,
  groups,
  total,
  hasMore,
  loading,
  loadingMore,
  loadMoreFailed,
  usingSnapshot,
  loadMore,
} = usePhotoArchive({ month: activeMonth, tag: requestedTag })
watchEffect(() => { availableTags.value = archiveTags.value })
const monthFormatter = new Intl.DateTimeFormat('zh-CN', { month: 'long', timeZone: 'Asia/Shanghai' })
const timelineYears = computed(() => {
  const years = new Map<number, PhotoArchiveMonth[]>()
  timeline.value.forEach((item) => {
    const months = years.get(item.year) ?? []
    months.push(item)
    years.set(item.year, months)
  })
  return [...years.entries()].map(([year, months]) => ({ year, months }))
})
const activeTotal = computed(() => activeMonth.value
  ? timeline.value.find(item => item.key === activeMonth.value)?.count ?? 0
  : total.value)

function selectTag(tag: string): void {
  router.push({ query: {
    ...(tag === '全部' ? {} : { tag }),
    ...(activeMonth.value ? { month: activeMonth.value } : {}),
  } })
}

function selectMonth(event: Event): void {
  const month = (event.target as HTMLSelectElement).value
  router.push({ query: {
    ...(activeTag.value === '全部' ? {} : { tag: activeTag.value }),
    ...(month ? { month } : {}),
  } })
}

function monthLabel(month: number): string {
  return monthFormatter.format(new Date(Date.UTC(2026, month - 1, 1)))
}

function monthCount(key: string, loaded: number): number {
  return timeline.value.find(item => item.key === key)?.count ?? loaded
}

function openLightbox(asset: PublicMediaAsset, title: string): void {
  selectedAsset.value = asset
  selectedTitle.value = title
}

usePageSeo({ title: '相册 · McAlbum', description: '按记录主题翻阅服务器照片。' })
</script>

<template>
  <main id="main-content" class="listing-page page-container album-page">
    <header class="page-intro page-intro--album">
      <p class="section-kicker">世界相册</p>
      <h1>虚拟的世界，<br>真实的故事。</h1>
      <p>从合影到散场后的空街，照片按照实际拍摄月份归档。当前索引收录 {{ total }} 张记录。</p>
      <p v-if="usingSnapshot && !loading" class="content-sync-note">当前展示离线快照；公开 API 恢复后刷新页面即可同步最新内容。</p>
    </header>

    <div class="filter-row" aria-label="按照片主题筛选">
      <TagFilter v-for="tag in rhythmTags" :key="tag" :label="tag" :active="activeTag === tag" @select="selectTag(tag)" />
    </div>

    <div class="archive-toolbar">
      <label for="archive-month">拍摄月份</label>
      <select id="archive-month" :value="activeMonth || ''" @change="selectMonth">
        <option value="">全部月份</option>
        <optgroup v-for="year in timelineYears" :key="year.year" :label="`${year.year} 年`">
          <option v-for="month in year.months" :key="month.key" :value="month.key">{{ monthLabel(month.month) }}（{{ month.count }} 张）</option>
        </optgroup>
      </select>
      <p class="filter-result" aria-live="polite">
        {{ activeTag === '全部' ? '全部主题' : activeTag }} · {{ activeMonth || '全部月份' }} · 已显示 {{ archivePhotos.length }} / {{ activeTotal }} 张
      </p>
    </div>

    <LoadingState v-if="loading && archivePhotos.length === 0" label="正在读取照片档案" />
    <div v-else class="archive-years">
      <section v-for="year in groups" :key="year.year" class="archive-year" :aria-labelledby="`year-${year.year}`">
        <header class="archive-year__rail"><h2 :id="`year-${year.year}`">{{ year.year }}</h2><span>年</span></header>
        <div class="archive-year__months">
          <section v-for="month in year.months" :id="`month-${month.key}`" :key="month.key" class="archive-month" :aria-labelledby="`month-title-${month.key}`">
            <header class="archive-month__heading">
              <h3 :id="`month-title-${month.key}`">{{ monthLabel(month.month) }}</h3>
              <span>{{ monthCount(month.key, month.photos.length) }} 张照片</span>
            </header>
            <JustifiedPhotoGrid :entries="month.photos" @open="openLightbox" />
          </section>
        </div>
      </section>
    </div>
    <div v-if="hasMore" class="archive-load-more">
      <button type="button" :disabled="loadingMore" @click="loadMore">
        {{ loadingMore ? '正在读取更早的照片……' : loadMoreFailed ? '读取失败，再试一次' : '继续翻阅更早的照片' }}
      </button>
    </div>
    <EmptyState v-if="!loading && archivePhotos.length === 0" title="这个月份还没有相关照片" description="选择其他月份或主题，继续翻阅已经整理的记录。" />
    <ImageLightbox :asset="selectedAsset" :title="selectedTitle" @close="selectedAsset = null" />
  </main>
</template>
