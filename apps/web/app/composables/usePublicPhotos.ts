import type { PhotoDetailContent, ResolvedPhoto } from '~/repositories/content-repository'
import { ApiContentRepository } from '~/repositories/api-content'
import { getAlbumContent, getPhotoContent } from '~/repositories/json-content'

/** 先使用静态快照渲染，再在浏览器端用公开 API 更新为最新发布内容。 */
export function usePublicPhotos(): {
  photos: Ref<ResolvedPhoto[]>
  refreshing: Ref<boolean>
  usingSnapshot: Ref<boolean>
  refresh: () => Promise<void>
} {
  const config = useRuntimeConfig()
  const photos = ref<ResolvedPhoto[]>(getAlbumContent().photos)
  // 首次挂载前视为正在同步，避免离线提示在 API 响应前短暂闪现。
  const refreshing = ref(true)
  const usingSnapshot = ref(true)
  const repository = new ApiContentRepository(String(config.public.apiBase).replace(/\/$/, ''))

  async function refresh(): Promise<void> {
    refreshing.value = true
    try {
      photos.value = await repository.getPhotos()
      usingSnapshot.value = false
    }
    catch {
      // API 暂时不可用时保留构建期快照，公开页面仍可浏览。
      usingSnapshot.value = true
    }
    finally {
      refreshing.value = false
    }
  }

  onMounted(refresh)
  return { photos, refreshing, usingSnapshot, refresh }
}

/** 支持尚未进入静态快照的新照片详情页。 */
export function usePublicPhoto(id: string): {
  content: Ref<PhotoDetailContent | undefined>
  loading: Ref<boolean>
  unavailable: Ref<boolean>
  refresh: () => Promise<void>
} {
  const config = useRuntimeConfig()
  const content = ref<PhotoDetailContent | undefined>(getPhotoContent(id))
  const loading = ref(content.value === undefined)
  const unavailable = ref(false)
  const repository = new ApiContentRepository(String(config.public.apiBase).replace(/\/$/, ''))

  async function refresh(): Promise<void> {
    loading.value = content.value === undefined
    unavailable.value = false
    try {
      content.value = await repository.getPhoto(id)
    }
    catch {
      unavailable.value = content.value === undefined
    }
    finally {
      loading.value = false
    }
  }

  onMounted(refresh)
  return { content, loading, unavailable, refresh }
}
