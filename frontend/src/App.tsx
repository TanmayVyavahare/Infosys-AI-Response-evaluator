import React, { Component, useState, type ReactNode } from 'react';
import './index.css';
import { useEvaluation } from './hooks/useEvaluation';
import { Header } from './components/Header';
import { EvaluationForm } from './components/EvaluationForm';
import { ResultsPanel } from './components/ResultsPanel';
import { AgentGrid } from './components/AgentGrid';
import { BatchDashboard } from './components/BatchDashboard';

interface ErrorBoundaryProps {
  children: ReactNode;
  onReset?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Uncaught error in UI:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) this.props.onReset();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="glass-card p-8 max-w-2xl mx-auto my-12 border-rose-500/30 text-center animate-fade-in space-y-5 overflow-hidden">
          <div className="h-[2px] bg-gradient-to-r from-transparent via-rose-500 to-transparent -mx-8 -mt-8 mb-6"></div>
          <div className="w-12 h-12 rounded-xl bg-rose-500/15 text-rose-400 mx-auto flex items-center justify-center">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-surface-50">Something went wrong</h3>
          <p className="text-xs text-rose-300 bg-surface-900/60 p-3.5 rounded-xl font-mono-code text-left overflow-x-auto border border-rose-500/15">
            {this.state.error?.message || 'Unknown UI Error'}
          </p>
          <button
            onClick={this.handleReset}
            className="btn-primary px-6 py-2.5 text-sm font-semibold"
          >
            ← Reset & Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

function MainApp() {
  const single = useEvaluation();
  const batch = useEvaluation();
  const { result, loading, error, elapsed, submit, cancel } = single;
  const { batchResult, submitBatch } = batch;
  const [singleKey, setSingleKey] = useState(0);
  const [batchKey, setBatchKey] = useState(0);
  const [mode, setMode] = useState<'single' | 'batch'>('single');

  const handleReset = () => {
    if (mode === 'single') { single.reset(); setSingleKey(key => key + 1); }
    else { batch.reset(); setBatchKey(key => key + 1); }
  };

  return (
    <div className="min-h-screen flex flex-col animate-fade-in">
      {/* Sticky Header */}
      <Header hasResult={Boolean(mode === 'single' ? result : batchResult)} onReset={handleReset} />

      {/* Main Content Container */}
      <main className="max-w-[1440px] mx-auto px-4 sm:px-8 py-6 sm:py-8 flex-1 w-full">
        <ErrorBoundary onReset={handleReset}>
          <div className="workspace-heading">
            <div>
              <h2>Review an AI response</h2>
              <p>Check what works, find gaps, and improve your next answer.</p>
            </div>
            <div className="mode-switch" role="group" aria-label="Evaluation type">
            <button
              onClick={() => setMode('single')} disabled={batch.loading}

              aria-pressed={mode === 'single'}
              className={`mode-switch-button ${
                mode === 'single'
                  ? 'mode-switch-button-active'
                  : 'mode-switch-button-inactive'
              }`}
            >
              <span>Single response</span>
              <span className="hidden sm:inline text-[11px] font-medium opacity-70">Review one answer</span>
            </button>
            <button
              onClick={() => setMode('batch')} disabled={loading}

              aria-pressed={mode === 'batch'}
              className={`mode-switch-button ${
                mode === 'batch'
                  ? 'mode-switch-button-active'
                  : 'mode-switch-button-inactive'
              }`}
            >
              <span>Batch review</span>
              <span className="hidden sm:inline text-[11px] font-medium opacity-70">Upload a CSV</span>
            </button>
            </div>
          </div>

          <section hidden={mode !== 'single'} aria-label="Single response review">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left panel: Form parameters */}
              <div className="lg:col-span-5 col-span-1 glass-card p-5 sm:p-6 border-white/5 bg-surface-900/40 rounded-2xl">
                <EvaluationForm
                  key={singleKey}
                  onSubmit={submit}
                  loading={loading}
                  elapsed={elapsed}
                  onCancel={cancel}
                />
              </div>

              {/* Right panel: Agents & Executive Dashboard */}
              <div className="lg:col-span-7 col-span-1 space-y-6 min-w-0">
                {loading && <AgentGrid result={result} loading={loading} />}

                {/* Error Callout */}
                {error && (
                  <div role="alert" className="glass-card p-0 overflow-hidden border-rose-500/30 bg-rose-950/15 animate-fade-in">
                    <div className="h-[2px] bg-gradient-to-r from-transparent via-rose-500 to-transparent"></div>
                    <div className="p-5 space-y-2">
                      <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                        </svg>
                        <span>Evaluation Error</span>
                      </div>
                      <p className="text-xs text-surface-300 leading-relaxed font-mono-code">
                        {error}
                      </p>
                    </div>
                  </div>
                )}

                {/* Ready for Evaluation State */}
                {!result && !loading && (
                  <div className="empty-state min-h-[320px] lg:min-h-[480px]">
                    <div className="empty-state-icon">✦</div>
                    <h4>Your report will appear here</h4>
                    <p>Add the question and AI response, then select <strong>Review response</strong>. We’ll highlight what is working and what needs attention.</p>
                  </div>
                )}

                {/* Loading State */}
                {loading && (
                  <div className="glass-card p-8 flex flex-col items-center justify-center text-center min-h-[300px] border-white/5 bg-surface-900/30 space-y-4">
                    <div className="relative w-12 h-12 flex items-center justify-center">
                      <span className="absolute inline-flex h-full w-full rounded-full bg-primary-500/10 animate-ping"></span>
                      <div className="w-8 h-8 rounded-full border-2 border-primary-500/20 border-t-primary-500 animate-spin"></div>
                    </div>
                    <div>
                      <h4 className="text-sm font-bold text-white tracking-wide mb-1">
                        Reviewing your response
                      </h4>
                      <p className="text-xs text-surface-500 max-w-md">
                        Checking relevance, accuracy, support from your sources, and completeness. You can cancel and keep your inputs.
                      </p>
                    </div>
                    <div className="text-xs text-primary-300 font-mono-code bg-primary-950/60 border border-primary-800/40 px-3 py-1.5 rounded-lg">
                      Elapsed Time: {elapsed.toFixed(1)}s
                    </div>
                  </div>
                )}

                {/* Results Dashboard Panel */}
                {result && !loading && (
                  <ResultsPanel result={result} />
                )}
              </div>
            </div>
          </section>
          <section hidden={mode !== 'batch'} aria-label="Batch review">
            <div className="space-y-6">
              {batch.error && (
                <div role="alert" className="glass-card p-0 overflow-hidden border-rose-500/30 bg-rose-950/15 animate-fade-in">
                  <div className="h-[2px] bg-gradient-to-r from-transparent via-rose-500 to-transparent"></div>
                  <div className="p-5 space-y-2">
                    <div className="flex items-center gap-2 text-rose-400 font-semibold text-sm">
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                      </svg>
                      <span>Batch Evaluation Error</span>
                    </div>
                    <p className="text-xs text-rose-300 leading-relaxed font-mono-code">
                      {batch.error}
                    </p>
                  </div>
                </div>
              )}
              <BatchDashboard
                key={batchKey}
                onSubmit={submitBatch}
                loading={batch.loading}
                elapsed={batch.elapsed}
                onCancel={batch.cancel}
                batchResult={batchResult}
                onReset={handleReset}
              />
            </div>
          </section>
        </ErrorBoundary>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 bg-surface-950/40 py-5 mt-auto backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-surface-500">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-surface-400">Aegis</span>
            <span className="text-surface-600">—</span>
            <span>AI Response Quality Assessment Engine</span>
          </div>
          <div className="flex flex-wrap justify-center items-center gap-3 text-[10px] font-medium text-surface-500">
            <span className="flex items-center gap-1">🎯 Relevance</span>
            <span className="text-surface-700">•</span>
            <span className="flex items-center gap-1">✅ Accuracy</span>
            <span className="text-surface-700">•</span>
            <span className="flex items-center gap-1">🔍 Groundedness</span>
            <span className="text-surface-700">•</span>
            <span className="flex items-center gap-1">📋 Completeness</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default function App() {
  return <MainApp />;
}
