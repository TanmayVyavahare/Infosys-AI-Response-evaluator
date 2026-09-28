import { useState, useCallback, useEffect, useRef } from 'react';
import type { EvaluationRequest, EvaluationResponse, BatchEvaluationResponse } from '../types/evaluation';
import { evaluateResponse, evaluateBatch } from '../services/api';

export function useEvaluation() {
  const [result, setResult] = useState<EvaluationResponse | null>(null);
  const [batchResult, setBatchResult] = useState<BatchEvaluationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const active = useRef<AbortController | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  const cancel = useCallback(() => {
    active.current?.abort();
    active.current = null;
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    setLoading(false);
  }, []);

  useEffect(() => () => {
    active.current?.abort();
    if (timer.current) clearInterval(timer.current);
  }, []);

  const run = useCallback(async (request: EvaluationRequest | EvaluationRequest[]) => {
    cancel();
    const controller = new AbortController();
    active.current = controller;
    setLoading(true);
    setError(null);
    setResult(null);
    setBatchResult(null);
    setElapsed(0);
    const start = Date.now();
    timer.current = setInterval(() => setElapsed((Date.now() - start) / 1000), 250);
    try {
      if (Array.isArray(request)) {
        const response = await evaluateBatch(request, controller.signal);
        if (active.current === controller) setBatchResult(response);
      } else {
        const response = await evaluateResponse(request, controller.signal);
        if (active.current === controller) setResult(response);
      }
    } catch (err) {
      if (active.current === controller && !controller.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Review failed. Please try again.');
      }
    } finally {
      if (active.current === controller) {
        cancel();
        setElapsed((Date.now() - start) / 1000);
      }
    }
  }, [cancel]);

  const reset = useCallback(() => {
    cancel();
    setResult(null);
    setBatchResult(null);
    setError(null);
    setElapsed(0);
  }, [cancel]);

  return { result, batchResult, loading, error, elapsed, submit: run, submitBatch: run, reset, cancel };
}
