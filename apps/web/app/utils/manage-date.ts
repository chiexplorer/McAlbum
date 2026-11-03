/** 返回中国北京当前日期，格式固定为 YYYY-MM-DD。 */
export function beijingToday(now = new Date()): string {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Asia/Shanghai',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(now)
  const values = Object.fromEntries(parts.map(part => [part.type, part.value]))
  return `${values.year}-${values.month}-${values.day}`
}

/**
 * 从文件名提取合法日期；支持 YYYY-MM-DD、YYYY_MM_DD 和 YYYY.MM.DD。
 * 时分秒等后续内容不会进入编目日期。
 */
export function dateFromFilename(filename: string, today = beijingToday()): string | null {
  const match = /(?:^|\D)(\d{4})[-_.](\d{2})[-_.](\d{2})(?:\D|$)/.exec(filename)
  if (!match) return null
  const [, yearText, monthText, dayText] = match
  const year = Number(yearText)
  const month = Number(monthText)
  const day = Number(dayText)
  const latestYear = Number(today.slice(0, 4)) + 5
  if (year < 2009 || year > latestYear) return null
  const candidate = new Date(Date.UTC(year, month - 1, day))
  const valid = candidate.getUTCFullYear() === year
    && candidate.getUTCMonth() === month - 1
    && candidate.getUTCDate() === day
  return valid ? `${yearText}-${monthText}-${dayText}` : null
}
