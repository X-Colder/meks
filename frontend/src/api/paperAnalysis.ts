import apiClient from './client'

export interface PaperAnalysisResult {
  id: string
  document_id: string
  status: string
  data_statistics_score: number | null
  data_statistics_verdict: string | null
  logic_consistency_score: number | null
  logic_consistency_verdict: string | null
  credibility_score: number | null
  credibility_verdict: string | null
  overall_risk_score: number | null
  risk_level: string | null
  data_statistics_findings: string | null
  logic_consistency_findings: string | null
  credibility_findings: string | null
  reproducibility_score: number | null
  reproducibility_verdict: string | null
  reproducibility_findings: string | null
  figure_consistency_score: number | null
  figure_consistency_verdict: string | null
  figure_consistency_findings: string | null
  citation_manipulation_score: number | null
  citation_manipulation_verdict: string | null
  citation_manipulation_findings: string | null
  overall_summary: string | null
  recommendations: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface PaperAnalysisTriggerResponse {
  detail: string
  document_id: string
}

export const paperAnalysisApi = {
  trigger: (documentId: string) =>
    apiClient.post<PaperAnalysisTriggerResponse>(`/paper-analysis/${documentId}`),
  get: (documentId: string) =>
    apiClient.get<PaperAnalysisResult>(`/paper-analysis/${documentId}`),
}
