/* Custom hook for evaluation state management */

import { useState, useCallback } from 'react';
import type { EvaluationRequest, EvaluationResponse, BatchEvaluationResponse } from '../types/evaluation';
import { evaluateResponse, evaluateBatch } from '../services/api';

interface UseEvaluationReturn {
  result: EvaluationResponse | null;
  batchResult: BatchEvaluationResponse | null;
  loading: boolean;
  error: string | null;
  elapsed: number;
  submit: (request: EvaluationRequest) => Promise<void>;
  submitBatch: (requests: EvaluationRequest[]) => Promise<void>;
  reset: () => void;
}

export function useEvaluation(): UseEvaluationReturn {
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [batchResult, setBatchResult] = useState<BatchEvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const [timerId, setTimerId] = useState<ReturnType<typeof setInterval> | null>(null);

  const submit = useCallback(async (request: EvaluationRequest) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setBatchResult(null);
    setElapsed(0);

    // Start elapsed timer
    const start = Date.now();
    const id = setInterval(() => {
      setElapsed((Date.now() - start) / 1000);
    }, 100);
    setTimerId(id);

    try {
      const response = await evaluateResponse(request);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Evaluation failed');
    } finally {
      clearInterval(id);
      setElapsed((Date.now() - start) / 1000);
      setLoading(false);
      setTimerId(null);
    }
  }, []);

  const submitBatch = useCallback(async (requests: EvaluationRequest[]) => {
    setLoading(true);
    setError(null);
    setResult(null);
    setBatchResult(null);
    setElapsed(0);

    // Start elapsed timer
    const start = Date.now();
    const id = setInterval(() => {
      setElapsed((Date.now() - start) / 1000);
    }, 100);
    setTimerId(id);

    try {
      const response = await evaluateBatch(requests);
      setBatchResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Batch evaluation failed');
    } finally {
      clearInterval(id);
      setElapsed((Date.now() - start) / 1000);
      setLoading(false);
      setTimerId(null);
    }
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setBatchResult(null);
    setError(null);
    setElapsed(0);
    if (timerId) clearInterval(timerId);
  }, [timerId]);

  return { result, batchResult, loading, error, elapsed, submit, submitBatch, reset };
}
