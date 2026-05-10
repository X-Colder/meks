import apiClient from './client'

export interface LoginParams {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserInfo {
  id: string
  username: string
  email: string
  full_name: string
  role: string
  department: string | null
  is_active: boolean
}

export const authApi = {
  login: (params: LoginParams) =>
    apiClient.post<TokenResponse>('/auth/login', params),

  refresh: (refreshToken: string) =>
    apiClient.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken }),

  getMe: () => apiClient.get<UserInfo>('/auth/me'),
}
