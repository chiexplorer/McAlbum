import { describe, expect, it } from 'vitest'
import type { ResolvedPhoto } from '../app/repositories/content-repository'
import {
  buildPhotoTimeline,
  groupPhotosByMonth,
  photoMonthKey,
} from '../app/utils/photo-archive'

function entry(id: string, capturedAt: string): ResolvedPhoto {
  return {
    photo: {
      id,
      title: id,
      description: '时间归档测试照片',
      assetId: `media-${id}`,
      capturedAt,
      timeZone: 'Asia/Shanghai',
      tags: ['测试'],
      status: 'published',
      isMock: false,
      featured: false,
      displayVariant: 'normal',
    },
    asset: {
      id: `media-${id}`,
      altText: id,
      focalPoint: { x: 0.5, y: 0.5 },
      variants: [{
        name: 'w480',
        storageKey: `variants/2026/10/media-${id}/w480.webp`,
        mimeType: 'image/webp',
        byteSize: 100,
        width: 480,
        height: 270,
        sha256: 'a'.repeat(64),
      }],
    },
  }
}

describe('photo archive', () => {
  it('始终按北京时间判断跨月边界', () => {
    expect(photoMonthKey('2026-10-31T16:30:00Z')).toBe('2026-11')
  })

  it('把照片整理为年份和月份两层结构', () => {
    const photos = [
      entry('photo-new-year', '2026-01-01T00:00:00+08:00'),
      entry('photo-old-year', '2025-12-31T23:00:00+08:00'),
    ]

    const groups = groupPhotosByMonth(photos)

    expect(groups.map(group => group.year)).toEqual([2026, 2025])
    expect(groups[0]?.months[0]?.key).toBe('2026-01')
  })

  it('从静态快照生成倒序月份索引', () => {
    const timeline = buildPhotoTimeline([
      entry('photo-a', '2026-10-20T12:00:00+08:00'),
      entry('photo-b', '2026-10-01T12:00:00+08:00'),
      entry('photo-c', '2026-09-20T12:00:00+08:00'),
    ])

    expect(timeline.map(item => [item.key, item.count])).toEqual([
      ['2026-10', 2],
      ['2026-09', 1],
    ])
  })
})
