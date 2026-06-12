import apiClient from './client'

export interface User {
  id: string
  username: string
  email: string
  full_name: string
  role: string
  department: string | null
  is_active: boolean
  created_at: string
}

export interface UserListResponse {
  items: User[]
  total: number
  page: number
  page_size: number
}

export interface CreateUserParams {
  username: string
  email: string
  password: string
  full_name: string
  role: string
  department?: string
}

export interface UpdateUserParams {
  email?: string
  full_name?: string
  role?: string
  department?: string
  is_active?: boolean
}

export const usersApi = {
  list: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<UserListResponse>('/admin/users', { params }),

  get: (id: string) => apiClient.get<User>(`/admin/users/${id}`),

  create: (data: CreateUserParams) =>
    apiClient.post<User>('/admin/users', data),

  update: (id: string, data: UpdateUserParams) =>
    apiClient.patch<User>(`/admin/users/${id}`, data),

  resetPassword: (id: string, newPassword: string) =>
    apiClient.post(`/admin/users/${id}/reset-password`, { new_password: newPassword }),

  delete: (id: string) => apiClient.delete(`/admin/users/${id}`),
}
