import { describe, expect, it } from 'vitest'
import { catalogDefaultsFromMedia } from '../app/utils/manage-media'

describe('media catalog defaults', () => {
  it('inherits the alt text and Beijing capture date', () => {
    expect(catalogDefaultsFromMedia({
      alt_text: '  出生点门楼夜景  ',
      captured_at: '2026-09-06T12:00:00+08:00',
    })).toEqual({
      title: '出生点门楼夜景',
      capturedAt: '2026-09-06',
    })
  })
})
