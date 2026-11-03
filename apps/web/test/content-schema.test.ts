import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import {
  photoSchema,
  playerSchema,
  publicMediaAssetSchema,
  siteContentSchema,
  storySchema,
} from '../app/schemas/content'
import { internalMediaAssetSchema } from './internal-media-schema'

const contentRoot = fileURLToPath(new URL('../../../content/', import.meta.url))
const publicMediaPath = fileURLToPath(new URL('../app/generated/media-assets.json', import.meta.url))
const publicContentPath = fileURLToPath(new URL('../app/generated/content.json', import.meta.url))

function readJson(path: string): unknown {
  return JSON.parse(readFileSync(path, 'utf-8'))
}

function readCollection(name: string): unknown[] {
  const directory = `${contentRoot}/${name}`
  return readdirSync(directory)
    .filter(filename => filename.endsWith('.json'))
    .map(filename => readJson(`${directory}/${filename}`))
}

describe('content schemas', () => {
  it('accepts every current JSON content document through the Zod mirror', () => {
    siteContentSchema.parse(readJson(`${contentRoot}/site.json`))
    readCollection('media-assets').forEach(document => internalMediaAssetSchema.parse(document))
    readCollection('photos').forEach(document => photoSchema.parse(document))
    readCollection('stories').forEach(document => storySchema.parse(document))
    readCollection('players').forEach(document => playerSchema.parse(document))
  })

  it('accepts an empty optional photo description', () => {
    const photo = readCollection('photos')[0] as Record<string, unknown>
    expect(photoSchema.parse({ ...photo, description: '' }).description).toBe('')
  })

  it('keeps the browser media projection free of original-file metadata', () => {
    const assets = publicMediaAssetSchema.array().parse(readJson(publicMediaPath))
    expect(assets).toHaveLength(readCollection('media-assets').length)
    assets.forEach((asset) => {
      expect(asset).not.toHaveProperty('storageKey')
      expect(asset).not.toHaveProperty('originalFilename')
      expect(asset).not.toHaveProperty('sha256')
    })
  })

  it('keeps private players and hidden comments out of the public projection', () => {
    const projection = readJson(publicContentPath) as Record<string, unknown[]>
    expect(projection.players.every(player => (player as Record<string, unknown>).status !== 'private')).toBe(true)
    expect(projection.photos.every((photo) => {
      const comments = (photo as Record<string, unknown>).comments as Array<Record<string, unknown>>
      return comments.every(comment => comment.status === 'published')
    })).toBe(true)
  })

  it('rejects media focal points outside the normalized range', () => {
    const media = readCollection('media-assets')[0]
    expect(() =>
      internalMediaAssetSchema.parse({
        ...(media as Record<string, unknown>),
        focalPoint: { x: 1.1, y: 0.5 },
      }),
    ).toThrow()
  })

  it('rejects story sections without the fields required by their type', () => {
    const story = readCollection('stories')[0] as Record<string, unknown>
    expect(() =>
      storySchema.parse({
        ...story,
        sections: [{ id: 'broken-section', type: 'wide-image' }],
      }),
    ).toThrow()
  })
})
