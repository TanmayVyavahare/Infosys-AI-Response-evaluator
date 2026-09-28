import type { EvaluationRequest, EvaluationResponse, BatchEvaluationResponse } from '../types/evaluation';

async function post<T>(path: string, body: unknown, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api/${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error('Cannot reach the review service. Check your connection and make sure the backend is running, then try again.');
  }
  if (!res.ok) {
    const data = await res.json().catch(() => null);
    const detail = data?.detail;
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { loc?: (string | number)[]; msg?: string }) => `${item.loc?.slice(1).join(' → ') || 'Input'}: ${item.msg || 'Invalid value'}`).join('; ')
      : res.status >= 500 ? 'The review service is unavailable. Make sure the backend is running, then try again.' : `Review failed (${res.status}). Please check your inputs.`;
    throw new Error(message);
  }
  return res.json();
}

export function evaluateResponse(request: EvaluationRequest, signal?: AbortSignal) {
  return post<EvaluationResponse>('evaluate', request, signal);
}

export function evaluateBatch(requests: EvaluationRequest[], signal?: AbortSignal) {
  return post<BatchEvaluationResponse>('evaluate/batch', requests, signal);
}

export async function healthCheck() {
  const res = await fetch('/api/health');
  if (!res.ok) throw new Error('Review service unavailable');
  return res.json();
}
