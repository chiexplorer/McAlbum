export interface JustifiedLayoutItem {
  id: string
  aspectRatio: number
}

export interface JustifiedLayoutTile {
  id: string
  width: number
  height: number
}

/**
 * 把照片按真实宽高比排成等高行。
 * 完整行铺满容器，末行保持目标高度以内，避免单张照片被强行放大。
 */
export function justifyPhotoRows(
  items: JustifiedLayoutItem[],
  containerWidth: number,
  gap: number,
  targetHeight: number | null,
): JustifiedLayoutTile[] {
  if (containerWidth <= 0 || items.length === 0) return []
  if (targetHeight === null) {
    return items.map(item => ({
      id: item.id,
      width: containerWidth,
      height: Math.round(containerWidth / item.aspectRatio),
    }))
  }

  const tiles: JustifiedLayoutTile[] = []
  let row: JustifiedLayoutItem[] = []
  let ratioSum = 0

  function flush(height: number, fillWidth: boolean): void {
    const rowGap = gap * Math.max(0, row.length - 1)
    let usedWidth = 0
    row.forEach((item, index) => {
      const isLast = index === row.length - 1
      const width = fillWidth && isLast
        ? containerWidth - rowGap - usedWidth
        : Math.floor(item.aspectRatio * height)
      tiles.push({ id: item.id, width, height: Math.floor(height) })
      usedWidth += width
    })
    row = []
    ratioSum = 0
  }

  items.forEach((item) => {
    row.push(item)
    ratioSum += item.aspectRatio
    const height = (containerWidth - gap * (row.length - 1)) / ratioSum
    if (height <= targetHeight) flush(height, true)
  })
  if (row.length > 0) {
    const availableHeight = (containerWidth - gap * (row.length - 1)) / ratioSum
    flush(Math.min(targetHeight, availableHeight), false)
  }
  return tiles
}

/** 根据照片区域宽度选择舒适的目标行高。 */
export function justifiedTargetHeight(containerWidth: number): number | null {
  if (containerWidth < 560) return null
  if (containerWidth < 900) return 230
  if (containerWidth < 1300) return 300
  return 340
}
