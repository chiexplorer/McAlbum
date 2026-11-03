import { describe, expect, it, vi } from 'vitest'
import { ApiContentRepository } from '../app/repositories/api-content'

const entry = {
  photo: {
    id: 'photo-live-test',
    title: '刚刚发布的照片',
    description: '用于验证公开 API 动态加载。',
    assetId: 'media-livetest',
    capturedAt: '2026-10-28T12:00:00+08:00',
    timeZone: 'Asia/Shanghai',
    photographerId: null,
    playerIds: [],
    storyIds: [],
    tags: ['测试'],
    status: 'published',
    isMock: false,
    featured: false,
    displayVariant: 'normal',
    comments: [],
  },
  asset: {
    id: 'media-livetest',
    altText: '用于测试的 Minecraft 截图',
    focalPoint: { x: 0.5, y: 0.5 },
    variants: [{
      name: 'w480',
      storageKey: 'variants/2026/10/media-livetest/w480.webp',
      mimeType: 'image/webp',
      byteSize: 100,
      width: 480,
      height: 270,
      sha256: 'a'.repeat(64),
    }],
  },
} as const

const storyEntry = {
  story: {
    id: 'story-live-test',
    title: '刚刚发布的作品集',
    summary: '用于验证作品集动态加载。',
    coverAssetId: 'media-livetest',
    playerIds: [],
    sections: [{ id: 'section-live', type: 'text', body: '动态正文。' }],
    status: 'published',
    isMock: false,
  },
  coverAsset: entry.asset,
} as const

describe('ApiContentRepository', () => {
  it('从公开接口读取并校验照片列表', async () => {
    const fetcher = vi.fn().mockResolvedValue([entry])
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const photos = await repository.getPhotos()

    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/api/public/photos')
    expect(photos[0]?.photo.title).toBe('刚刚发布的照片')
  })

  it('读取公开照片详情及关联作品集', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ...entry,
      stories: [],
      relatedPhotos: [],
    })
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const detail = await repository.getPhoto('photo-live-test')

    expect(detail?.stories).toEqual([])
    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/api/public/photos/photo-live-test')
  })

  it('读取照片时间流并传递月份、标签和游标', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      items: [entry],
      nextCursor: { capturedAt: entry.photo.capturedAt, id: entry.photo.id },
      hasMore: true,
    })
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const page = await repository.getPhotoFeed({
      limit: 20,
      month: '2026-10',
      tag: '测试',
      cursor: { capturedAt: '2026-10-29T12:00:00+08:00', id: 'photo-cursor' },
    })

    expect(page.hasMore).toBe(true)
    const requestedUrl = String(fetcher.mock.calls[0]?.[0])
    expect(requestedUrl).toContain('/public/photos/feed?')
    expect(requestedUrl).toContain('limit=20')
    expect(requestedUrl).toContain('month=2026-10')
    expect(requestedUrl).toContain('tag=%E6%B5%8B%E8%AF%95')
    expect(requestedUrl).toContain('before_id=photo-cursor')
  })

  it('读取按拍摄时间生成的月份索引', async () => {
    const fetcher = vi.fn().mockResolvedValue([
      { key: '2026-10', year: 2026, month: 10, count: 12 },
    ])
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const timeline = await repository.getPhotoTimeline('建筑')

    expect(timeline[0]?.count).toBe(12)
    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/api/public/photos/timeline?tag=%E5%BB%BA%E7%AD%91')
  })

  it('从公开接口读取作品集列表', async () => {
    const fetcher = vi.fn().mockResolvedValue([storyEntry])
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const stories = await repository.getStories()

    expect(stories[0]?.story.title).toBe('刚刚发布的作品集')
    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/api/public/stories')
  })

  it('把作品集详情媒体转换为按 ID 访问的映射', async () => {
    const fetcher = vi.fn().mockResolvedValue({
      story: storyEntry.story,
      assets: [entry.asset],
    })
    const repository = new ApiContentRepository('http://localhost:8000/api', fetcher)

    const detail = await repository.getStory('story-live-test')

    expect(detail?.assetsById.get('media-livetest')?.altText).toContain('Minecraft')
    expect(fetcher).toHaveBeenCalledWith('http://localhost:8000/api/public/stories/story-live-test')
  })
})
