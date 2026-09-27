/* API service for communicating with the Aegis backend */

import type { EvaluationRequest, EvaluationResponse, BatchEvaluationResponse } from '../types/evaluation';

const API_BASE = '/api';

export async function evaluateResponse(
  request: EvaluationRequest
): Promise<EvaluationResponse> {
  const res = await fetch(`${API_BASE}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function evaluateBatch(
  requests: EvaluationRequest[]
): Promise<BatchEvaluationResponse> {
  const res = await fetch(`${API_BASE}/evaluate/batch`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requests),
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export async function healthCheck(): Promise<{
  status: string;
  app_name: string;
  version: string;
}> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: HTTP ${res.status}`);
  return res.json();
}
