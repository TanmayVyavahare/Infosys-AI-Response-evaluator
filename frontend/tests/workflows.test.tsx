import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import App from '../src/App';
import { useEvaluation } from '../src/hooks/useEvaluation';
import { BatchDashboard } from '../src/components/BatchDashboard';
import { ResultsPanel } from '../src/components/ResultsPanel';
import { evaluateResponse } from '../src/services/api';
import type { EvaluationResponse, MetricResult } from '../src/types/evaluation';

// jsdom does not implement native dialog methods; browser coverage checks focus/Escape.
Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open'); } });
Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', ''); } });

afterEach(() => { cleanup(); vi.unstubAllGlobals(); vi.restoreAllMocks(); });
const request = { question: 'What is two plus two?', ai_response: 'Four.' };
const report: EvaluationResponse = { metrics: {}, overall_score: 0, verdict: 'Insufficient Data', confidence: 0, processing_time_seconds: 1, strengths: [], weaknesses: [], recommendations: [] };
const response = (body: unknown) => ({ ok: true, json: async () => body }) as Response;

const metric = (metric_name: string, score: number | null): MetricResult => ({ metric_name, score, reason: 'Compared with supplied evidence.', evidence: [], strengths: [], weaknesses: [], suggestions: [], claims: [], requirements: [], evaluated_with: 'llm' });

it('clearly labels local estimates and preserves the limitation in copied reports', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<ResultsPanel result={{ ...report, overall_score: .95, verdict: 'Local Estimate',
    warnings: ['The AI service reached its usage limit. Retry later.'],
    metrics: { relevance: { ...metric('relevance', .95), evaluated_with: 'fallback' }, accuracy: metric('accuracy', null) } }} />);
  expect(screen.getByText('Local Estimate')).toBeTruthy();
  expect(screen.getByText('Provisional estimate')).toBeTruthy();
  expect(screen.getByText(/These local estimates are provisional/)).toBeTruthy();
  expect(screen.getByRole('alert').textContent).toContain('usage limit');
  expect(screen.queryByText('Excellent Quality')).toBeNull();
  fireEvent.click(screen.getByRole('button', { name: /Copy Report/ }));
  await waitFor(() => expect(writeText).toHaveBeenCalledOnce());
  expect(writeText.mock.calls[0][0]).toContain('Verdict: Local Estimate');
  expect(writeText.mock.calls[0][0]).toContain('usage limit');
});

it('shows limited evidence and check coverage instead of misleading confidence', () => {
  render(<ResultsPanel result={{ ...report, overall_score: 1, verdict: 'Limited Evidence', confidence: .5, metrics: { relevance: metric('relevance', 1), accuracy: metric('accuracy', null), groundedness: metric('groundedness', null), completeness: metric('completeness', 1) } }} />);
  expect(screen.getByText('Limited Evidence')).toBeTruthy();
  expect(screen.getByText('Available-check score')).toBeTruthy();
  expect(screen.getByText('2 of 4')).toBeTruthy();
  expect(screen.queryByText(/Overall Confidence/i)).toBeNull();
});

it('keeps unverifiable, unsupported and contradicted claims distinct', () => {
  const accuracy = { ...metric('accuracy', 1), evidence_coverage: .5, claims: [{ claim: 'Unknown launch year', supported: null, verdict: 'UNVERIFIABLE' as const, score: null, evidence: 'The source has no launch year.' }] };
  const groundedness = { ...metric('groundedness', 0), claims: [
    { claim: 'Free laptop', supported: false, verdict: 'UNSUPPORTED' as const, score: null, evidence: 'The source does not mention a laptop.' },
    { claim: 'Wrong price', supported: false, verdict: 'CONTRADICTED' as const, score: null, evidence: 'The source specifies another price.' },
  ] };
  render(<ResultsPanel result={{ ...report, verdict: 'Limited Evidence', metrics: { accuracy, groundedness } }} />);
  for (const status of ['Unverifiable', 'Unsupported', 'Contradicted']) expect(screen.getByText(status)).toBeTruthy();
  expect(screen.getByText(/50% of claims could be verified/)).toBeTruthy();
  expect(screen.queryByRole('columnheader', { name: /Confidence/i })).toBeNull();
});

it('explains conflicting evidence instead of treating the answer as a hallucination', () => {
  render(<ResultsPanel result={{ ...report, verdict: 'Conflicting Evidence' }} />);
  expect(screen.getByText('Conflicting Evidence')).toBeTruthy();
  expect(screen.getByText(/The reference and source disagree/)).toBeTruthy();
  expect(screen.queryByText('Critical Hallucination')).toBeNull();
});

it('cancels a review without allowing a late response to replace the current report', async () => {
  let finish!: (response: Response) => void;
  vi.stubGlobal('fetch', vi.fn().mockImplementationOnce(() => new Promise(resolve => { finish = resolve; })).mockResolvedValueOnce(response(report)));
  const { result } = renderHook(() => useEvaluation());
  let pending!: Promise<void>;
  act(() => { pending = result.current.submit(request); });
  expect(result.current.loading).toBe(true);
  act(() => result.current.cancel());
  expect(result.current.loading).toBe(false);
  await act(() => result.current.submit(request));
  await act(async () => { finish(response({ ...report, verdict: 'OLD RESULT' })); await pending; });
  expect(result.current.result?.verdict).toBe('Insufficient Data');
});

it('aborts a pending request when the view unmounts', () => {
  let signal!: AbortSignal;
  vi.stubGlobal('fetch', vi.fn((_url, options) => { signal = options.signal; return new Promise(() => {}); }));
  const { result, unmount } = renderHook(() => useEvaluation());
  act(() => { void result.current.submit(request); });
  unmount();
  expect(signal.aborted).toBe(true);
});

it('preserves single inputs while switching modes and clicking the active mode', () => {
  render(<App />);
  fireEvent.change(screen.getByLabelText(/Question/), { target: { value: 'Keep this question' } });
  fireEvent.click(screen.getByRole('button', { name: /Batch review/ }));
  fireEvent.click(screen.getByRole('button', { name: /Single response/ }));
  fireEvent.click(screen.getByRole('button', { name: /Single response/ }));
  expect((screen.getByLabelText(/Question/) as HTMLTextAreaElement).value).toBe('Keep this question');
});

it('turns API validation errors into useful field messages', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 422, json: async () => ({ detail: [{ loc: ['body', 'question'], msg: 'Required' }] }) }));
  await expect(evaluateResponse(request)).rejects.toThrow('question: Required');
});

function batch() {
  const onSubmit = vi.fn();
  const view = render(<BatchDashboard onSubmit={onSubmit} loading={false} elapsed={0} batchResult={null} onReset={vi.fn()} onCancel={vi.fn()} />);
  const upload = (text: string) => {
    const file = new File([text], 'test.csv', { type: 'text/csv' });
    Object.defineProperty(file, 'text', { value: async () => text });
    fireEvent.change(view.container.querySelector('input[type=file]')!, { target: { files: [file] } });
  };
  return { upload, onSubmit };
}

describe('CSV import', () => {
  it('handles quoted commas, newlines, escaped quotes, and reference-first columns', async () => {
    const { upload, onSubmit } = batch();
    upload('reference_answer,question,ai_response\r\n"Known answer","Question, one","Line one\nHe said ""yes"""');
    const button = await screen.findByRole('button', { name: /Review batch/ });
    fireEvent.click(button);
    expect(onSubmit).toHaveBeenCalledWith([{ question: 'Question, one', ai_response: 'Line one\nHe said "yes"', reference_answer: 'Known answer', source_document: undefined }]);
  });
  it('does not silently skip missing required cells', async () => {
    const { upload, onSubmit } = batch();
    upload('question,ai_response\nQuestion,Answer\nMissing answer,');
    await screen.findByText(/Missing question or response in data rows 2/);
    expect((screen.getByRole('button', { name: /Review batch/ }) as HTMLButtonElement).disabled).toBe(true);
    expect(onSubmit).not.toHaveBeenCalled();
  });
  it.each([
    ['question,question\nA,B', /unique, non-empty header/],
    ['question,ai_response\n"A,B', /quoted field is not closed/],
    ['question,ai_response\nA,B,C', /same number of columns/],
    ['question,ai_response\n' + 'A,B\n'.repeat(51), /up to 50 responses/],
  ])('rejects malformed or oversized CSV content', async (csv, message) => {
    const { upload } = batch();
    upload(csv);
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringMatching(message));
  });
});

it('copies a zero score correctly and keeps the report ID stable', async () => {
  const writeText = vi.fn().mockResolvedValue(undefined);
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText } });
  render(<ResultsPanel result={report} />);
  fireEvent.click(screen.getByRole('button', { name: /Copy/ }));
  await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
  const first = writeText.mock.calls[0][0];
  expect(first).toContain('Overall Score: 0/100');
  fireEvent.click(screen.getByRole('button', { name: /Copied/ }));
  await waitFor(() => expect(writeText).toHaveBeenCalledTimes(2));
  expect(writeText.mock.calls[1][0]).toBe(first);
  expect(screen.queryByText('Unacceptable Quality')).toBeNull();
});

it('downloads the complete JSON report and opens the print dialog', () => {
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (this: HTMLAnchorElement) {
    expect(this.download).toMatch(/^aegis-audit-.*\.json$/);
    expect(JSON.parse(decodeURIComponent(this.href.split(',')[1]))).toEqual(report);
  });
  const print = vi.spyOn(window, 'print').mockImplementation(() => {});
  render(<ResultsPanel result={report} />);
  fireEvent.click(screen.getByRole('button', { name: 'Download JSON' }));
  expect(click).toHaveBeenCalledTimes(1);
  fireEvent.click(screen.getByRole('button', { name: 'Print PDF Report' }));
  expect(print).toHaveBeenCalledTimes(1);
});

it('reports clipboard failures without falsely claiming success', async () => {
  Object.defineProperty(navigator, 'clipboard', { configurable: true, value: { writeText: vi.fn().mockRejectedValue(new Error('Denied')) } });
  render(<ResultsPanel result={report} />);
  fireEvent.click(screen.getByRole('button', { name: 'Copy Report' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('Copy is unavailable'));
  expect(screen.queryByText('Copied!')).toBeNull();
});
