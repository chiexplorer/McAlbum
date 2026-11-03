export interface CatalogMediaDefaultsSource {
  alt_text: string
  captured_at: string
}

/** 把媒体入库元数据转换为散图编目的可编辑默认值。 */
export function catalogDefaultsFromMedia(media: CatalogMediaDefaultsSource) {
  const capturedAt = /^\d{4}-\d{2}-\d{2}/.exec(media.captured_at)?.[0] ?? ''
  return { title: media.alt_text.trim(), capturedAt }
}
