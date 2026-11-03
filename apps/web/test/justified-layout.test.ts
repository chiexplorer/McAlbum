import { describe, expect, it } from 'vitest'
import { justifiedTargetHeight, justifyPhotoRows } from '../app/utils/justified-layout'

describe('justified photo layout', () => {
  it('fills a complete landscape row including its gap', () => {
    const tiles = justifyPhotoRows([
      { id: 'left', aspectRatio: 2 },
      { id: 'right', aspectRatio: 2 },
    ], 1200, 12, 340)

    expect(tiles).toHaveLength(2)
    expect(tiles[0]!.width + tiles[1]!.width + 12).toBe(1200)
    expect(tiles[0]!.height).toBe(297)
  })

  it('does not stretch an incomplete final row', () => {
    expect(justifyPhotoRows([
      { id: 'last', aspectRatio: 2 },
    ], 1200, 12, 340)).toEqual([{ id: 'last', width: 680, height: 340 }])
  })

  it('uses one natural-ratio column on narrow screens', () => {
    expect(justifiedTargetHeight(480)).toBeNull()
    expect(justifyPhotoRows([
      { id: 'mobile', aspectRatio: 2 },
    ], 480, 12, null)).toEqual([{ id: 'mobile', width: 480, height: 240 }])
  })
})
