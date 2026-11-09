import { z } from 'zod'
import type {
  PhotoArchiveMonth,
  PhotoDetailContent,
  PhotoFeedPage,
  PhotoFeedQuery,
  ResolvedPhoto,
  ResolvedStory,
  StoryDetailContent,
} from './content-repository'
import {
  photoSchema,
  publicMediaAssetSchema,
  storySchema,
} from '../schemas/content'

const resolvedPhotoSchema = z.object({
  photo: photoSchema,
  asset: publicMediaAssetSchema,
}).strict()

const photoFeedSchema = z.object({
  items: z.array(resolvedPhotoSchema),
  nextCursor: z.object({
    capturedAt: z.iso.datetime({ offset: true }),
    id: z.string().min(1).max(120),
  }).strict().nullable(),
  hasMore: z.boolean(),
}).strict()

const photoArchiveMonthSchema = z.object({
  key: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/),
  year: z.number().int(),
  month: z.number().int().min(1).max(12),
  count: z.number().int().positive(),
}).strict()

const publicPhotoDetailSchema = resolvedPhotoSchema.extend({
  stories: z.array(storySchema),
  relatedPhotos: z.array(resolvedPhotoSchema),
}).strict()

const resolvedStorySchema = z.object({
  story: storySchema,
  coverAsset: publicMediaAssetSchema,
}).strict()

const publicStoryDetailSchema = z.object({
  story: storySchema,
  assets: z.array(publicMediaAssetSchema).min(1),
}).strict()

type PublicFetcher = <T>(url: string, options?: Record<string, unknown>) => Promise<T>

/** 从 FastAPI 获取已经过服务端状态和隐私过滤的公开照片。 */
export class ApiContentRepository {
  constructor(
    private readonly apiBase: string,
    private readonly fetcher: PublicFetcher = $fetch,
  ) {}

  async getPhotos(): Promise<ResolvedPhoto[]> {
    const payload = await this.fetcher<unknown>(`${this.apiBase}/public/photos`)
    return resolvedPhotoSchema.array().parse(payload)
  }

  async getTags(): Promise<string[]> {
    const payload = await this.fetcher<unknown>(`${this.apiBase}/public/tags`)
    return z.array(z.string().min(1).max(64)).parse(payload)
  }

  async getPhotoFeed(query: PhotoFeedQuery = {}): Promise<PhotoFeedPage> {
    const params = new URLSearchParams()
    params.set('limit', String(query.limit ?? 40))
    if (query.cursor) {
      params.set('before', query.cursor.capturedAt)
      params.set('before_id', query.cursor.id)
    }
    if (query.month) params.set('month', query.month)
    if (query.tag) params.set('tag', query.tag)
    const payload = await this.fetcher<unknown>(`${this.apiBase}/public/photos/feed?${params}`)
    return photoFeedSchema.parse(payload)
  }

  async getPhotoTimeline(tag?: string): Promise<PhotoArchiveMonth[]> {
    const params = new URLSearchParams()
    if (tag) params.set('tag', tag)
    const suffix = params.size ? `?${params}` : ''
    const payload = await this.fetcher<unknown>(`${this.apiBase}/public/photos/timeline${suffix}`)
    return photoArchiveMonthSchema.array().parse(payload)
  }

  async getPhoto(id: string): Promise<PhotoDetailContent | undefined> {
    try {
      const payload = await this.fetcher<unknown>(`${this.apiBase}/public/photos/${encodeURIComponent(id)}`)
      const parsed = publicPhotoDetailSchema.parse(payload)
      return parsed
    }
    catch (error: unknown) {
      if (isNotFound(error)) return undefined
      throw error
    }
  }

  async getStories(): Promise<ResolvedStory[]> {
    const payload = await this.fetcher<unknown>(`${this.apiBase}/public/stories`)
    return resolvedStorySchema.array().parse(payload)
  }

  async getStory(id: string): Promise<StoryDetailContent | undefined> {
    try {
      const payload = await this.fetcher<unknown>(`${this.apiBase}/public/stories/${encodeURIComponent(id)}`)
      const parsed = publicStoryDetailSchema.parse(payload)
      return {
        story: parsed.story,
        assetsById: new Map(parsed.assets.map(asset => [asset.id, asset])),
      }
    }
    catch (error: unknown) {
      if (isNotFound(error)) return undefined
      throw error
    }
  }
}

function isNotFound(error: unknown): boolean {
  return Boolean(
    error
    && typeof error === 'object'
    && 'response' in error
    && (error as { response?: { status?: number } }).response?.status === 404,
  )
}
