import type { ResolvedPhoto } from '../repositories/content-repository'

const archiveMonthFormatter = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Shanghai',
  year: 'numeric',
  month: '2-digit',
})

export interface PhotoMonthGroup {
  key: string
  year: number
  month: number
  photos: ResolvedPhoto[]
}

export interface PhotoYearGroup {
  year: number
  months: PhotoMonthGroup[]
}

/** 按北京时间计算照片所属月份，避免客户端本地时区改变归档结果。 */
export function photoMonthKey(capturedAt: string): string {
  const parts = archiveMonthFormatter.formatToParts(new Date(capturedAt))
  const year = parts.find(part => part.type === 'year')?.value
  const month = parts.find(part => part.type === 'month')?.value
  if (!year || !month) throw new Error(`无法计算照片月份：${capturedAt}`)
  return `${year}-${month}`
}

/** 把已经按时间倒序的照片整理为年份和月份两层结构。 */
export function groupPhotosByMonth(photos: ResolvedPhoto[]): PhotoYearGroup[] {
  const years = new Map<number, Map<string, PhotoMonthGroup>>()
  photos.forEach((entry) => {
    const key = photoMonthKey(entry.photo.capturedAt)
    const year = Number(key.slice(0, 4))
    const month = Number(key.slice(5, 7))
    const months = years.get(year) ?? new Map<string, PhotoMonthGroup>()
    const group = months.get(key) ?? { key, year, month, photos: [] }
    group.photos.push(entry)
    months.set(key, group)
    years.set(year, months)
  })
  return [...years.entries()]
    .sort(([left], [right]) => right - left)
    .map(([year, months]) => ({
      year,
      months: [...months.values()].sort((left, right) => right.month - left.month),
    }))
}

/** 从静态快照生成与动态月份接口相同的离线索引。 */
export function buildPhotoTimeline(photos: ResolvedPhoto[]) {
  const counts = new Map<string, number>()
  photos.forEach((entry) => {
    const key = photoMonthKey(entry.photo.capturedAt)
    counts.set(key, (counts.get(key) ?? 0) + 1)
  })
  return [...counts.entries()]
    .sort(([left], [right]) => right.localeCompare(left))
    .map(([key, count]) => ({
      key,
      year: Number(key.slice(0, 4)),
      month: Number(key.slice(5, 7)),
      count,
    }))
}
