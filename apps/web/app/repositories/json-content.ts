import publicMediaSources from '~/generated/media-assets.json'
import publicContentSources from '~/generated/content.json'
import type {
  AlbumContent,
  ContentRepository,
  HomeContent,
  PhotoDetailContent,
  PlayerDetailContent,
  PlayerIndexContent,
  ResolvedPhoto,
  StoryDetailContent,
  StoryIndexContent,
} from './content-repository'
import {
  photoSchema,
  playerSchema,
  siteContentSchema,
  storySchema,
  publicMediaAssetSchema,
} from '~/schemas/content'

class JsonContentRepository implements ContentRepository {
  private readonly site = siteContentSchema.parse(publicContentSources.site)
  private readonly assets = publicMediaAssetSchema.array().parse(publicMediaSources)
  private readonly photos = publicContentSources.photos.map(source => photoSchema.parse(source))
  private readonly stories = publicContentSources.stories.map(source => storySchema.parse(source))
  private readonly players = publicContentSources.players.map(source => playerSchema.parse(source))
  private readonly assetsById = new Map(this.assets.map(asset => [asset.id, asset]))
  private readonly photosById = new Map(this.photos.map(photo => [photo.id, photo]))

  private resolvePhoto(photoId: string): ResolvedPhoto {
    const photo = this.photosById.get(photoId)
    if (!photo) throw new Error(`照片 ${photoId} 不存在`)
    const asset = this.assetsById.get(photo.assetId)
    if (!asset) throw new Error(`照片 ${photo.id} 引用的媒体 ${photo.assetId} 不存在`)
    return { photo, asset }
  }

  getHomeContent(): HomeContent {
    const featuredStory = this.stories.find(story => story.id === '2026-mid-autumn-night')
    if (!featuredStory) throw new Error('首页专题不存在')
    const coverAsset = this.assetsById.get(featuredStory.coverAssetId)
    if (!coverAsset) throw new Error(`专题封面媒体 ${featuredStory.coverAssetId} 不存在`)

    const recentPhotos = [...this.photos]
      .sort((left, right) => right.capturedAt.localeCompare(left.capturedAt))
      .slice(0, 6)
      .map(photo => this.resolvePhoto(photo.id))

    return { site: this.site, featuredStory, coverAsset, recentPhotos }
  }

  getAlbumContent(): AlbumContent {
    const photos = [...this.photos]
      .sort((left, right) => left.capturedAt.localeCompare(right.capturedAt))
      .map(photo => this.resolvePhoto(photo.id))
    const tags = [...new Set(this.photos.flatMap(photo => photo.tags))].sort((a, b) => a.localeCompare(b, 'zh-CN'))
    return { photos, tags }
  }

  getPhotoContent(id: string): PhotoDetailContent | undefined {
    const photo = this.photosById.get(id)
    if (!photo) return undefined
    const resolved = this.resolvePhoto(id)
    const stories = this.stories.filter(story => photo.storyIds?.includes(story.id))
    const relatedPhotos = this.photos
      .filter(item => item.id !== id && item.tags.some(tag => photo.tags.includes(tag)))
      .slice(0, 3)
      .map(item => this.resolvePhoto(item.id))
    return { ...resolved, stories, relatedPhotos }
  }

  getStoryContent(id: string): StoryDetailContent | undefined {
    const story = this.stories.find(item => item.id === id)
    if (!story) return undefined
    return {
      story,
      assetsById: this.assetsById,
    }
  }

  getStoryIndexContent(): StoryIndexContent {
    return {
      stories: [...this.stories]
        .map((story) => {
          const coverAsset = this.assetsById.get(story.coverAssetId)
          if (!coverAsset) throw new Error(`专题封面媒体 ${story.coverAssetId} 不存在`)
          return { story, coverAsset }
        })
        .sort((left, right) => left.story.title.localeCompare(right.story.title, 'zh-CN')),
    }
  }


  getPlayerIndexContent(): PlayerIndexContent {
    return { players: this.players.filter(player => player.status !== 'private') }
  }

  getPlayerContent(id: string): PlayerDetailContent | undefined {
    const player = this.players.find(item => item.id === id && item.status !== 'private')
    if (!player) return undefined
    return {
      player,
      avatarAsset: player.avatarAssetId ? this.assetsById.get(player.avatarAssetId) : undefined,
      works: this.stories.filter(story => player.workIds?.includes(story.id)),
    }
  }
}

const repository = new JsonContentRepository()

export const getHomeContent = (): HomeContent => repository.getHomeContent()
export const getAlbumContent = (): AlbumContent => repository.getAlbumContent()
export const getPhotoContent = (id: string): PhotoDetailContent | undefined => repository.getPhotoContent(id)
export const getStoryContent = (id: string): StoryDetailContent | undefined => repository.getStoryContent(id)
export const getStoryIndexContent = (): StoryIndexContent => repository.getStoryIndexContent()
export const getPlayerIndexContent = (): PlayerIndexContent => repository.getPlayerIndexContent()
export const getPlayerContent = (id: string): PlayerDetailContent | undefined => repository.getPlayerContent(id)
