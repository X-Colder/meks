import apiClient from './client'

export interface MedicalRecordItem {
  id: string
  document_id: string
  patient_name: string | null
  gender: string | null
  age: number | null
  department: string | null
  primary_diagnosis: string | null
  icd10_code: string | null
  severity: string | null
  treatment_outcome: string | null
  admission_date: string | null
  discharge_date: string | null
  hospital_days: number | null
  medications: string | null
  procedures: string | null
  chief_complaint: string | null
  created_at: string
}

export interface MedicalRecordListResponse {
  items: MedicalRecordItem[]
  total: number
  page: number
  page_size: number
}

export const medicalRecordsApi = {
  list: (params?: {
    knowledge_base_id?: string
    severity?: string
    department?: string
    icd10_code?: string
    date_from?: string
    date_to?: string
    page?: number
    page_size?: number
  }) => apiClient.get<MedicalRecordListResponse>('/medical-records', { params }),

  get: (id: string) => apiClient.get<MedicalRecordItem>(`/medical-records/${id}`),

  getByDocument: (documentId: string) =>
    apiClient.get<MedicalRecordItem>(`/documents/${documentId}/medical-record`),
}
