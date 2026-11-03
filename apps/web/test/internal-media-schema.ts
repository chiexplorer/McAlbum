import { z } from 'zod'

const mediaIdSchema = z.string().regex(/^media-[a-z0-9]+$/)
const timestampSchema = z.iso.datetime({ offset: true })
const focalPointSchema = z.object({
  x: z.number().min(0).max(1),
  y: z.number().min(0).max(1),
}).strict()
const mediaVariantSchema = z.object({
  name: z.enum(['placeholder', 'w480', 'w960', 'w1440', 'w1920']),
  storageKey: z.string().regex(
    /^variants\/[0-9]{4}\/[0-9]{2}\/media-[a-z0-9]+\/(placeholder|w480|w960|w1440|w1920)\.webp$/,
  ),
  mimeType: z.literal('image/webp'),
  byteSize: z.number().int().positive(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
}).strict()

// 完整媒体契约只用于测试和导入校验，不得进入浏览器运行时代码。
export const internalMediaAssetSchema = z.object({
  $schema: z.string().optional(),
  id: mediaIdSchema,
  originalFilename: z.string().min(1),
  storageKey: z.string().regex(
    /^originals\/[0-9]{4}\/[0-9]{2}\/media-[a-z0-9]+\.(png|jpg|webp)$/,
  ),
  mimeType: z.enum(['image/png', 'image/jpeg', 'image/webp']),
  extension: z.enum(['png', 'jpg', 'webp']),
  byteSize: z.number().int().positive(),
  width: z.number().int().positive(),
  height: z.number().int().positive(),
  sha256: z.string().regex(/^[a-f0-9]{64}$/),
  capturedAt: timestampSchema,
  timeZone: z.literal('Asia/Shanghai'),
  altText: z.string().min(1).max(240),
  focalPoint: focalPointSchema,
  editorialStatus: z.enum(['mock', 'draft', 'verified']),
  processingStatus: z.enum(['pending', 'ready', 'failed', 'deleted']),
  allowOriginalDownload: z.boolean(),
  variants: z.array(mediaVariantSchema).min(1),
  importedAt: timestampSchema,
}).strict()
