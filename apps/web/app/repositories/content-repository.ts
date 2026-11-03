import type {
  Photo,
  Player,
  PublicMediaAsset,
  SiteContent,
  Story,
} from '~/schemas/content'

export interface ResolvedPhoto {
  photo: Photo
  asset: PublicMediaAsset
}

export interface ResolvedStory {
  story: Story
  coverAsset: PublicMediaAsset
}

export interface PhotoFeedCursor {
  capturedAt: string
  id: string
}

export interface PhotoFeedPage {
  items: ResolvedPhoto[]
  nextCursor: PhotoFeedCursor | null
  hasMore: boolean
}

export interface PhotoArchiveMonth {
  key: string
  year: number
  month: number
  count: number
}

export interface PhotoFeedQuery {
  limit?: number
  cursor?: PhotoFeedCursor | null
  month?: string
  tag?: string
}

export interface HomeContent {
  site: SiteContent
  featuredStory: Story
  coverAsset: PublicMediaAsset
  recentPhotos: ResolvedPhoto[]
}

export interface AlbumContent {
  photos: ResolvedPhoto[]
  tags: string[]
}

export interface PhotoDetailContent extends ResolvedPhoto {
  stories: Story[]
  relatedPhotos: ResolvedPhoto[]
}

export interface StoryDetailContent {
  story: Story
  assetsById: Map<string, PublicMediaAsset>
}

export interface StoryIndexContent {
  stories: ResolvedStory[]
}

export interface PlayerIndexContent {
  players: Player[]
}

export interface PlayerDetailContent {
  player: Player
  avatarAsset?: PublicMediaAsset
  works: Story[]
}

export interface ContentRepository {
  getHomeContent(): HomeContent
  getAlbumContent(): AlbumContent
  getPhotoContent(id: string): PhotoDetailContent | undefined
  getStoryContent(id: string): StoryDetailContent | undefined
  getStoryIndexContent(): StoryIndexContent
  getPlayerIndexContent(): PlayerIndexContent
  getPlayerContent(id: string): PlayerDetailContent | undefined
}
