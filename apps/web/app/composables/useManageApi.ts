export interface SessionUser {
  id: string
  username: string
  display_name: string
  role: 'user' | 'admin'
  player_id: string | null
  permissions: string[]
}

interface SessionResponse {
  user: SessionUser
  csrf_token: string
  expires_at: string
}

/** 管理端 API 客户端；统一携带会话 Cookie、CSRF 令牌并整理错误消息。 */
export function useManageApi() {
  const config = useRuntimeConfig()
  const session = useState<SessionResponse | null>('manage-session', () => null)
  const loading = useState('manage-session-loading', () => false)

  function csrfFromCookie() {
    if (!import.meta.client) return ''
    const value = document.cookie.split('; ').find(item => item.startsWith('mcalbum_csrf='))
    return value ? decodeURIComponent(value.split('=').slice(1).join('=')) : ''
  }

  async function request<T>(path: string, options: Record<string, unknown> = {}) {
    const method = String(options.method || 'GET').toUpperCase()
    const headers = new Headers(options.headers as HeadersInit | undefined)
    if (!['GET', 'HEAD'].includes(method)) {
      headers.set('X-CSRF-Token', session.value?.csrf_token || csrfFromCookie())
    }
    return await $fetch<T>(`${config.public.apiBase}${path}`, {
      ...options,
      method: method as 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH',
      headers,
      credentials: 'include',
    })
  }

  async function restore() {
    if (!import.meta.client || loading.value || session.value) return session.value
    loading.value = true
    try {
      session.value = await request<SessionResponse>('/auth/session')
    } catch {
      session.value = null
    } finally {
      loading.value = false
    }
    return session.value
  }

  async function login(username: string, password: string) {
    session.value = await request<SessionResponse>('/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    return session.value
  }

  async function logout() {
    await request('/auth/logout', { method: 'POST' })
    session.value = null
    await navigateTo('/manage/login')
  }

  function can(permission: string) {
    return session.value?.user.role === 'admin' || session.value?.user.permissions.includes(permission)
  }

  function errorMessage(error: unknown) {
    const candidate = error as { data?: { detail?: string | { message?: string } }, message?: string }
    const detail = candidate.data?.detail
    if (typeof detail === 'string') return detail
    if (detail && typeof detail === 'object' && detail.message) return detail.message
    return candidate.message || '请求未完成，请检查后端服务和输入内容。'
  }

  return { session, loading, request, restore, login, logout, can, errorMessage }
}
