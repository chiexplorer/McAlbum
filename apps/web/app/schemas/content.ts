import { z } from 'zod'

const entityIdSchema = z.string().regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
const mediaIdSchema = z.string().regex(/^media-[a-z0-9]+(?:-[a-z0-9]+)*$/)
const schemaReference = z.string().optional()
const timestampSchema = z.iso.datetime({ offset: true })
const beijingTimeZoneSchema = z.literal('Asia/Shanghai')

export const publicationStatusSchema = z.enum([
  'draft',
  'pending',
  'published',
  'rejected',
  'archived',
])

export const siteContentSchema = z
  .object({
    $schema: schemaReference,
    title: z.string().min(1),
    description: z.string().min(1),
    worldStatement: z.string().min(1),
    principles: z.array(z.object({
      title: z.string().min(1),
      description: z.string().min(1),
    }).strict()).min(1),
    timeZone: beijingTimeZoneSchema,
    startedAt: z.iso.date(),
    worldDay: z.number().int().nonnegative().nullable(),
    minecraftVersion: z.string().min(1),
    fabricVersion: z.string().min(1),
  })
  .strict()

const focalPointSchema = z
  .object({
    x: z.number().min(0).max(1),
    y: z.number().min(0).max(1),
  })
  .strict()

const mediaVariantSchema = z
  .object({
    name: z.enum(['placeholder', 'w480', 'w960', 'w1440', 'w1920']),
    storageKey: z
      .string()
      .regex(/^(?:variants\/[0-9]{4}\/[0-9]{2}\/media-[a-z0-9]+|built-in-stories\/[a-z0-9]+(?:-[a-z0-9]+)*\/media-[a-z0-9]+(?:-[a-z0-9]+)*)\/(placeholder|w480|w960|w1440|w1920)\.webp$/),
    mimeType: z.literal('image/webp'),
    byteSize: z.number().int().positive(),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    sha256: z.string().regex(/^[a-f0-9]{64}$/),
  })
  .strict()

// 展示媒体不强制携带原图地址，便于内置作品集只保存经优化的公开变体。
export const displayMediaAssetSchema = z
  .object({
    id: mediaIdSchema,
    altText: z.string().min(1).max(240),
    focalPoint: focalPointSchema,
    variants: z.array(mediaVariantSchema).min(1),
  })
  .strict()

// 用户上传媒体在展示契约之上增加原图下载地址。
export const publicMediaAssetSchema = displayMediaAssetSchema.extend({
  originalUrl: z.string().regex(/^\/originals\/[0-9]{4}\/[0-9]{2}\/media-[a-z0-9]+\.(png|jpg|webp)$/),
}).strict()

const photoCommentSchema = z
  .object({
    id: entityIdSchema,
    authorPlayerId: entityIdSchema,
    body: z.string().min(1).max(1000),
    status: z.enum(['published', 'hidden']),
    createdAt: timestampSchema,
    hiddenReason: z.string().max(500).nullable().optional(),
  })
  .strict()

export const photoSchema = z
  .object({
    $schema: schemaReference,
    id: entityIdSchema,
    title: z.string().min(1),
    description: z.string(),
    assetId: mediaIdSchema,
    capturedAt: timestampSchema,
    timeZone: beijingTimeZoneSchema,
    worldDay: z.number().int().nonnegative().nullable().optional(),
    photographerId: entityIdSchema.nullable().optional(),
    playerIds: z.array(entityIdSchema).optional(),
    storyIds: z.array(entityIdSchema).optional(),
    tags: z.array(z.string().min(1)),
    status: publicationStatusSchema,
    isMock: z.boolean(),
    featured: z.boolean(),
    displayVariant: z.enum(['featured', 'normal', 'portrait', 'note']),
    comments: z.array(photoCommentSchema).optional(),
  })
  .strict()

const storySectionSchema = z.discriminatedUnion('type', [
  z.object({ id: entityIdSchema, type: z.literal('text'), body: z.string().min(1) }).strict(),
  z
    .object({
      id: entityIdSchema,
      type: z.literal('wide-image'),
      assetId: mediaIdSchema,
      caption: z.string().min(1),
    })
    .strict(),
  z
    .object({
      id: entityIdSchema,
      type: z.literal('image-grid'),
      assetIds: z.array(mediaIdSchema).min(2),
      caption: z.string().optional(),
    })
    .strict(),
  z
    .object({
      id: entityIdSchema,
      type: z.literal('text-with-image'),
      body: z.string().min(1),
      assetId: mediaIdSchema,
      imagePosition: z.enum(['left', 'right']),
    })
    .strict(),
  z
    .object({
      id: entityIdSchema,
      type: z.literal('player-quote'),
      playerId: entityIdSchema,
      quote: z.string().min(1).max(1000),
    })
    .strict(),
])

export const storySchema = z
  .object({
    $schema: schemaReference,
    id: entityIdSchema,
    title: z.string().min(1),
    summary: z.string().min(1),
    coverAssetId: mediaIdSchema,
    playerIds: z.array(entityIdSchema).optional(),
    sections: z.array(storySectionSchema).min(1),
    status: publicationStatusSchema,
    isMock: z.boolean(),
  })
  .strict()

export const builtInStoryPackageSchema = z
  .object({
    $schema: schemaReference,
    id: entityIdSchema,
    story: storySchema,
    assets: z.array(displayMediaAssetSchema).min(1),
  })
  .strict()

export const playerSchema = z
  .object({
    $schema: schemaReference,
    id: entityIdSchema,
    name: z.string().min(1),
    bio: z.string(),
    status: z.enum(['resident', 'historical', 'private']),
    avatarAssetId: mediaIdSchema.nullable().optional(),
    joinedAt: z.iso.date().nullable().optional(),
    workIds: z.array(entityIdSchema).optional(),
  })
  .strict()

export type SiteContent = z.infer<typeof siteContentSchema>
export type DisplayMediaAsset = z.infer<typeof displayMediaAssetSchema>
export type PublicMediaAsset = z.infer<typeof publicMediaAssetSchema>
export type BuiltInStoryPackage = z.infer<typeof builtInStoryPackageSchema>
export type Photo = z.infer<typeof photoSchema>
export type Story = z.infer<typeof storySchema>
export type Player = z.infer<typeof playerSchema>
