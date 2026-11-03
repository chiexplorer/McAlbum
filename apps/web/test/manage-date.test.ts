import { describe, expect, it } from 'vitest'
import { beijingToday, dateFromFilename } from '../app/utils/manage-date'

describe('manage date helpers', () => {
  it('extracts the date and ignores the filename time', () => {
    expect(dateFromFilename('2026-09-06_17.16.37.png', '2026-10-28')).toBe('2026-09-06')
  })

  it('rejects impossible and missing filename dates', () => {
    expect(dateFromFilename('2026-02-30_17.16.37.png', '2026-10-28')).toBeNull()
    expect(dateFromFilename('spawn-overlook.png', '2026-10-28')).toBeNull()
  })

  it('uses the Beijing calendar date around UTC midnight', () => {
    expect(beijingToday(new Date('2026-10-27T16:30:00Z'))).toBe('2026-10-28')
  })
})
