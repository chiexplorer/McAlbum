import type { Ref } from 'vue'
import type {
  PhotoArchiveMonth,
  PhotoFeedCursor,
  ResolvedPhoto,
} from '../repositories/content-repository'
import { ApiContentRepository } from '../repositories/api-content'
import { getAlbumContent } from '../repositories/json-content'
import {
  buildPhotoTimeline,
  groupPhotosByMonth,
  photoMonthKey,
} from '../utils/photo-archive'

interface PhotoArchiveOptions {
  month: Readonly<Ref<string | undefined>>
  tag: Readonly<Ref<string | undefined>>
}

/**
 * 管理相册时间归档、公开 API 游标和静态快照兜底。
 * month 与 tag 均为 URL 状态的只读引用；变化时自动重新读取第一页。
 */
export function usePhotoArchive(options: PhotoArchiveOptions) {
  const config = useRuntimeConfig()
  const repository = new ApiContentRepository(String(config.public.apiBase).replace(/\/$/, ''))
  const snapshot = [...getAlbumContent().photos]
    .sort((left, right) => right.photo.capturedAt.localeCompare(left.photo.capturedAt))
  const photos = ref<ResolvedPhoto[]>(filterSnapshot(snapshot, options.month.value, options.tag.value))
  const snapshotTags = getAlbumContent().tags
  const tags = ref<string[]>(snapshotTags)
  const timeline = ref<PhotoArchiveMonth[]>(buildPhotoTimeline(filterSnapshot(snapshot, undefined, options.tag.value)))
  const nextCursor = ref<PhotoFeedCursor | null>(null)
  const hasMore = ref(false)
  const loading = ref(true)
  const loadingMore = ref(false)
  const loadMoreFailed = ref(false)
  const usingSnapshot = ref(true)
  const requestVersion = ref(0)
  const groups = computed(() => groupPhotosByMonth(photos.value))
  const total = computed(() => timeline.value.reduce((sum, item) => sum + item.count, 0))

  async function refresh(): Promise<void> {
    const version = ++requestVersion.value
    loading.value = true
    loadMoreFailed.value = false
    try {
      const [feed, months, availableTags] = await Promise.all([
        repository.getPhotoFeed({
          limit: 40,
          month: options.month.value,
          tag: options.tag.value,
        }),
        repository.getPhotoTimeline(options.tag.value),
        repository.getTags(),
      ])
      if (version !== requestVersion.value) return
      photos.value = feed.items
      timeline.value = months
      tags.value = availableTags
      nextCursor.value = feed.nextCursor
      hasMore.value = feed.hasMore
      usingSnapshot.value = false
    }
    catch {
      if (version !== requestVersion.value) return
      const taggedSnapshot = filterSnapshot(snapshot, undefined, options.tag.value)
      photos.value = filterSnapshot(taggedSnapshot, options.month.value, undefined)
      timeline.value = buildPhotoTimeline(taggedSnapshot)
      tags.value = snapshotTags
      nextCursor.value = null
      hasMore.value = false
      usingSnapshot.value = true
    }
    finally {
      if (version === requestVersion.value) loading.value = false
    }
  }

  async function loadMore(): Promise<void> {
    if (loadingMore.value || !hasMore.value || !nextCursor.value) return
    const version = requestVersion.value
    loadingMore.value = true
    loadMoreFailed.value = false
    try {
      const feed = await repository.getPhotoFeed({
        limit: 40,
        cursor: nextCursor.value,
        month: options.month.value,
        tag: options.tag.value,
      })
      if (version !== requestVersion.value) return
      const knownIds = new Set(photos.value.map(entry => entry.photo.id))
      photos.value.push(...feed.items.filter(entry => !knownIds.has(entry.photo.id)))
      nextCursor.value = feed.nextCursor
      hasMore.value = feed.hasMore
    }
    catch {
      if (version === requestVersion.value) loadMoreFailed.value = true
    }
    finally {
      if (version === requestVersion.value) loadingMore.value = false
    }
  }

  onMounted(refresh)
  watch([options.month, options.tag], refresh)

  return {
    photos,
    tags,
    timeline,
    groups,
    total,
    hasMore,
    loading,
    loadingMore,
    loadMoreFailed,
    usingSnapshot,
    refresh,
    loadMore,
  }
}

function filterSnapshot(
  photos: ResolvedPhoto[],
  month?: string,
  tag?: string,
): ResolvedPhoto[] {
  return photos.filter(entry =>
    (!month || photoMonthKey(entry.photo.capturedAt) === month)
    && (!tag || entry.photo.tags.includes(tag)),
  )
}
