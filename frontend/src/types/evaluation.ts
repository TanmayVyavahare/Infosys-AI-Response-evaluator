/* Evaluation types matching the backend response schema */

export interface ClaimDetail {
  claim: string;
  verdict?: 'CORRECT' | 'INCORRECT' | 'UNVERIFIABLE' | 'CONFLICTING' | 'SUPPORTED' | 'UNSUPPORTED' | 'CONTRADICTED' | null;
  supported: boolean | null;
  score: number | null;
  evidence: string | null;
}

export interface RequirementCoverage {
  requirement: string;
  status: 'covered' | 'partial' | 'missing';
  evidence: string | null;
}

export interface MetricResult {
  metric_name: string;
  evidence_coverage?: number | null;
  score: number | null;
  reason: string;
  review_warning?: string | null;
  evidence: string[];
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  claims: ClaimDetail[];
  requirements: RequirementCoverage[];
  evaluated_with: 'llm' | 'fallback' | 'error';
}

export interface EvaluationResponse {
  warnings?: string[];
  metrics: Record<string, MetricResult>;
  overall_score: number | null;
  verdict: string;
  confidence: number;
  processing_time_seconds: number;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
}

export interface EvaluationRequest {
  question: string;
  ai_response: string;
  reference_answer?: string;
  source_document?: string;
}

export interface BatchEvaluationResponse {
  results: EvaluationResponse[];
  total_count: number;
  average_score: number | null;
  verdict_counts: Record<string, number>;
  average_metrics: Record<string, number>;
}
