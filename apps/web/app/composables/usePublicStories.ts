import type { ResolvedStory, StoryDetailContent } from '~/repositories/content-repository'
import { ApiContentRepository } from '~/repositories/api-content'
import {
  getBuiltInStoryContent,
  getBuiltInStoryIndexContent,
  getStoryContent,
  getStoryIndexContent,
} from '~/repositories/json-content'

function withBuiltInStories(dynamicStories: ResolvedStory[]): ResolvedStory[] {
  const builtIn = getBuiltInStoryIndexContent().stories
  const builtInIds = new Set(builtIn.map(item => item.story.id))
  return [...builtIn, ...dynamicStories.filter(item => !builtInIds.has(item.story.id))]
}

/** 先用构建快照渲染，再从公开 API 同步最新发布作品集。 */
export function usePublicStories() {
  const config = useRuntimeConfig()
  const stories = ref<ResolvedStory[]>(getStoryIndexContent().stories)
  const refreshing = ref(true)
  const usingSnapshot = ref(true)
  const repository = new ApiContentRepository(String(config.public.apiBase).replace(/\/$/, ''))

  async function refresh() {
    refreshing.value = true
    try {
      stories.value = withBuiltInStories(await repository.getStories())
      usingSnapshot.value = false
    }
    catch {
      usingSnapshot.value = true
    }
    finally {
      refreshing.value = false
    }
  }

  onMounted(refresh)
  return { stories, refreshing, usingSnapshot, refresh }
}

/** 允许访问尚未进入静态快照、但已经发布的作品集详情。 */
export function usePublicStory(id: string) {
  const config = useRuntimeConfig()
  const content = ref<StoryDetailContent | undefined>(getStoryContent(id))
  const loading = ref(content.value === undefined)
  const unavailable = ref(false)
  const repository = new ApiContentRepository(String(config.public.apiBase).replace(/\/$/, ''))

  async function refresh() {
    const builtInContent = getBuiltInStoryContent(id)
    if (builtInContent) {
      content.value = builtInContent
      loading.value = false
      unavailable.value = false
      return
    }
    loading.value = content.value === undefined
    unavailable.value = false
    try {
      content.value = await repository.getStory(id)
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
