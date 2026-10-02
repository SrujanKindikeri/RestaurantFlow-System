// =============================================================================
// RestaurantFlow — Centralized Axios API Client
//
// All API requests in the application MUST go through this client.
// Do not use raw axios or fetch calls scattered in components.
// =============================================================================

import axios, {
  type AxiosInstance,
  type AxiosRequestConfig,
  type AxiosResponse,
  type InternalAxiosRequestConfig,
} from 'axios'

// -----------------------------------------------------------------------------
// Base configuration
// -----------------------------------------------------------------------------

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  },
})

// -----------------------------------------------------------------------------
// Request interceptor — attach JWT access token
// -----------------------------------------------------------------------------

api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem('access_token')
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// -----------------------------------------------------------------------------
// Response interceptor — handle 401 and token refresh
// -----------------------------------------------------------------------------

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    // Attempt a single token refresh on 401
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      const refreshToken = localStorage.getItem('refresh_token')

      if (refreshToken) {
        try {
          const response = await axios.post(`${BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken,
          })
          const newAccess: string = response.data.access
          localStorage.setItem('access_token', newAccess)

          // Retry the original request with the new token
          if (originalRequest.headers) {
            (originalRequest.headers as Record<string, string>).Authorization = `Bearer ${newAccess}`
          }
          return api(originalRequest)
        } catch {
          // Refresh failed — clear tokens and let the app handle re-login
          localStorage.removeItem('access_token')
          localStorage.removeItem('refresh_token')
        }
      }
    }

    return Promise.reject(error)
  },
)

export default api

// -----------------------------------------------------------------------------
// Typed helper wrappers (optional convenience layer)
// -----------------------------------------------------------------------------

export const get = <T>(url: string, config?: AxiosRequestConfig) =>
  api.get<T>(url, config).then((r) => r.data)

export const post = <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
  api.post<T>(url, data, config).then((r) => r.data)

export const put = <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
  api.put<T>(url, data, config).then((r) => r.data)

export const patch = <T>(url: string, data?: unknown, config?: AxiosRequestConfig) =>
  api.patch<T>(url, data, config).then((r) => r.data)

export const del = <T>(url: string, config?: AxiosRequestConfig) =>
  api.delete<T>(url, config).then((r) => r.data)
