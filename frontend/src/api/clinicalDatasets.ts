import apiClient from './client'

export interface ClinicalColumn {
  name: string
  label: string
  inferred_type: string
  missing_count: number
  missing_rate: number
  unique_count: number
  role: string | null
}

export interface ClinicalDataset {
  id: string
  name: string
  original_filename: string
  row_count: number
  column_count: number
  owner_id: string
  created_at: string
  updated_at: string
}

export interface ClinicalDatasetDetail extends ClinicalDataset {
  columns: ClinicalColumn[]
  preview_rows: Record<string, string>[]
}

export interface ClinicalStats {
  columns: ClinicalColumn[]
  numeric_summary: Record<string, { count: number; mean: number; min: number; max: number; median: number }>
  categorical_summary: Record<string, { value: string; count: number }[]>
  missing_summary: { name: string; missing_count: number; missing_rate: number }[]
}

export interface ClinicalTimelineEvent {
  patient_id: string
  date: string | null
  event_type: string
  title: string
  details: Record<string, string>
}

export interface ClinicalPatientSummary {
  patient_id: string
  age: string | null
  sex: string | null
  first_visit: string | null
  last_visit: string | null
  encounter_count: number
  diagnosis_count: number
  diagnoses: string[]
  risk_flags: string[]
}

export interface ClinicalLongitudinalView {
  patient_id_column: string | null
  date_column: string | null
  diagnosis_columns: string[]
  patient_count: number
  event_count: number
  patients: ClinicalPatientSummary[]
  events: ClinicalTimelineEvent[]
  top_diagnoses: { diagnosis: string; count: number }[]
  cohort_preview: Record<string, string | number>[]
  warnings: string[]
}

export const clinicalDatasetsApi = {
  list: () => apiClient.get<ClinicalDataset[]>('/clinical-datasets'),
  get: (id: string) => apiClient.get<ClinicalDatasetDetail>(`/clinical-datasets/${id}`),
  stats: (id: string) => apiClient.get<ClinicalStats>(`/clinical-datasets/${id}/stats`),
  longitudinal: (id: string) => apiClient.get<ClinicalLongitudinalView>(`/clinical-datasets/${id}/longitudinal`),
  upload: (file: File, name?: string) => {
    const form = new FormData()
    form.append('file', file)
    if (name) form.append('name', name)
    return apiClient.post<ClinicalDatasetDetail>('/clinical-datasets/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  suggestions: (id: string, data: { clinical_question?: string; exposure?: string; outcome?: string }) =>
    apiClient.post<{ content: string }>(`/clinical-datasets/${id}/research-suggestions`, data),
}
