import apiClient from './client'

export interface AuditLog {
  id: string
  user_id: string
  action: string
  resource_type: string
  resource_id: string | null
  details: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogListResponse {
  items: AuditLog[]
  total: number
  page: number
  page_size: number
}

export interface AuditLogParams {
  action?: string
  user_id?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export const auditLogsApi = {
  list: (params?: AuditLogParams) =>
    apiClient.get<AuditLogListResponse>('/admin/audit-logs', { params }),
}
