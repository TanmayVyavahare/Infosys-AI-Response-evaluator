/* ScoreCard Component with Tabbed Deep-Dive Analytics */

import { useState } from 'react';
import type { MetricResult } from '../types/evaluation';
import { ScoreGauge } from './ScoreGauge';
import { ClaimBreakdown } from './ClaimBreakdown';

interface ScoreCardProps {
  metric: MetricResult;
}

const METRIC_CONFIGS: Record<string, { icon: string; title: string; subtitle: string; color: string; accentVar: string }> = {
  relevance: {
    icon: '🎯',
    title: 'Answer Relevance',
    subtitle: 'Does the response directly address the prompt topic?',
    color: 'from-indigo-500/15 to-primary-600/8 border-primary-500/20',
    accentVar: '#6366f1',
  },
  accuracy: {
    icon: '✅',
    title: 'Factual Accuracy',
    subtitle: 'Are all claims factually correct and verifiable?',
    color: 'from-emerald-500/15 to-teal-600/8 border-emerald-500/20',
    accentVar: '#10b981',
  },
  groundedness: {
    icon: '🔍',
    title: 'Groundedness',
    subtitle: 'Are all statements backed by source material?',
    color: 'from-cyan-500/15 to-blue-600/8 border-cyan-500/20',
    accentVar: '#06b6d4',
  },
  completeness: {
    icon: '📋',
    title: 'Coverage Completeness',
    subtitle: 'Does it cover all sub-questions and key requirements?',
    color: 'from-amber-500/12 to-orange-600/8 border-amber-500/20',
    accentVar: '#f59e0b',
  },
};

export function ScoreCard({ metric }: ScoreCardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'claims' | 'requirements' | 'suggestions'>('overview');
  const [expanded, setExpanded] = useState(false);

  const config = METRIC_CONFIGS[metric.metric_name] ?? {
    icon: '📊',
    title: metric.metric_name,
    subtitle: 'Evaluation metric analysis',
    color: 'from-surface-800 to-surface-900 border-surface-700',
    accentVar: '#6366f1',
  };

  const strengths = metric.strengths ?? [];
  const weaknesses = metric.weaknesses ?? [];
  const evidence = metric.evidence ?? [];
  const claims = metric.claims ?? [];
  const requirements = metric.requirements ?? [];
  const suggestions = metric.suggestions ?? [];

  const hasDetails = evidence.length > 0 || claims.length > 0 || requirements.length > 0 || suggestions.length > 0;

  return (
    <div
      className={`glass-card p-0 overflow-hidden bg-gradient-to-br ${config.color} border transition-all flex flex-col justify-between metric-card`}
      style={{ '--accent-color': config.accentVar } as React.CSSProperties}
    >
      {/* Top accent line */}
      <div
        className="h-[2px]"
        style={{ background: `linear-gradient(90deg, transparent, ${config.accentVar}60, transparent)` }}
      ></div>

      <div className="p-8">
        {/* Header Row */}
        <div className="flex items-start justify-between gap-4 mb-5">
          <div className="flex-1">
            <div className="flex items-center gap-2.5 mb-1.5">
              <span className="text-lg">{config.icon}</span>
              <h3 className="text-base font-bold text-white tracking-tight">{config.title}</h3>
              <span
                className={`badge-pill text-[9px] ${metric.evaluated_with === 'llm'
                    ? 'badge-llm'
                    : metric.evaluated_with === 'fallback'
                      ? 'badge-fallback'
                      : 'bg-rose-500/15 text-rose-300 border border-rose-500/25'
                  }`}
              >
                {metric.evaluated_with === 'llm' ? '🤖 LLM' : metric.evaluated_with === 'fallback' ? '⚡ Local' : '⚠ Error'}
              </span>
            </div>
            <p className="text-[11px] text-surface-400 font-medium leading-relaxed">{config.subtitle}</p>
          </div>

          <ScoreGauge score={metric.score ?? null} size={80} strokeWidth={6} />
        </div>

        {/* Reason Explanation Box */}
        <div className="glass-panel p-5 mb-6">
          <p className="text-[12px] text-surface-200 leading-relaxed">
            {metric.reason}
          </p>
        </div>

        {/* Strengths & Weaknesses Quick Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          {strengths.length > 0 && (
            <div className="bg-emerald-950/15 border border-emerald-500/15 rounded-xl p-3.5">
              <span className="text-[10px] font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                Key Strengths
              </span>
              <ul className="space-y-1.5">
                {strengths.slice(0, 2).map((s, idx) => (
                  <li key={idx} className="text-[11px] text-surface-300 flex items-start gap-1.5 leading-snug">
                    <span className="w-1 h-1 rounded-full bg-emerald-400 mt-1.5 shrink-0"></span>
                    <span>{s}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {weaknesses.length > 0 && (
            <div className="bg-rose-950/15 border border-rose-500/15 rounded-xl p-3.5">
              <span className="text-[10px] font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1.5 mb-2">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                Improvements
              </span>
              <ul className="space-y-1.5">
                {weaknesses.slice(0, 2).map((w, idx) => (
                  <li key={idx} className="text-[11px] text-surface-300 flex items-start gap-1.5 leading-snug">
                    <span className="w-1 h-1 rounded-full bg-rose-400 mt-1.5 shrink-0"></span>
                    <span>{w}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Expandable Deep Dive Navigation */}
      {hasDetails && (
        <div className="border-t border-white/5">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between text-xs px-8 py-4 hover:bg-white/[0.02] transition-colors cursor-pointer"
          >
            <span className="flex items-center gap-2 text-primary-300 font-semibold">
              <svg
                className={`w-3.5 h-3.5 transition-transform duration-200 ${expanded ? 'rotate-90' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              <span>{expanded ? 'Hide Evidence & Analysis' : 'Show Evidence & Analysis'}</span>
            </span>
            <div className="flex items-center gap-1.5">
              {evidence.length > 0 && (
                <span className="text-[9px] bg-white/5 border border-white/5 text-surface-400 px-2 py-0.5 rounded-md font-mono-code">
                  {evidence.length} evidence
                </span>
              )}
              {claims.length > 0 && (
                <span className="text-[9px] bg-white/5 border border-white/5 text-surface-400 px-2 py-0.5 rounded-md font-mono-code">
                  {claims.length} claims
                </span>
              )}
              {requirements.length > 0 && (
                <span className="text-[9px] bg-white/5 border border-white/5 text-surface-400 px-2 py-0.5 rounded-md font-mono-code">
                  {requirements.length} reqs
                </span>
              )}
            </div>
          </button>

          {expanded && (
            <div className="px-8 pb-8 space-y-6 animate-slide-down">
              {/* Tab Navigation */}
              <div className="flex gap-1.5 overflow-x-auto pb-1">
                {evidence.length > 0 && (
                  <button
                    onClick={() => setActiveTab('overview')}
                    className={`tab-btn ${activeTab === 'overview' ? 'tab-btn-active' : 'tab-btn-inactive'}`}
                  >
                    Evidence ({evidence.length})
                  </button>
                )}
                {claims.length > 0 && (
                  <button
                    onClick={() => setActiveTab('claims')}
                    className={`tab-btn ${activeTab === 'claims' ? 'tab-btn-active' : 'tab-btn-inactive'}`}
                  >
                    Claims ({claims.length})
                  </button>
                )}
                {requirements.length > 0 && (
                  <button
                    onClick={() => setActiveTab('requirements')}
                    className={`tab-btn ${activeTab === 'requirements' ? 'tab-btn-active' : 'tab-btn-inactive'}`}
                  >
                    Requirements ({requirements.length})
                  </button>
                )}
                {suggestions.length > 0 && (
                  <button
                    onClick={() => setActiveTab('suggestions')}
                    className={`tab-btn ${activeTab === 'suggestions' ? 'tab-btn-active' : 'tab-btn-inactive'}`}
                  >
                    Suggestions ({suggestions.length})
                  </button>
                )}
              </div>

              {/* Tab 1: Evidence List */}
              {activeTab === 'overview' && (
                <div className="space-y-2 animate-fade-in">
                  {evidence.length > 0 ? (
                    evidence.map((item, idx) => (
                      <div key={idx} className="text-[11px] text-surface-300 bg-surface-950/50 border border-white/4 rounded-xl p-3.5 font-mono-code leading-relaxed">
                        {item}
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-surface-500 italic">No specific raw evidence items listed.</p>
                  )}
                </div>
              )}

              {/* Tab 2: Claims Analysis */}
              {activeTab === 'claims' && <ClaimBreakdown claims={claims} />}

              {/* Tab 3: Requirements Coverage */}
              {activeTab === 'requirements' && (
                <div className="space-y-2 text-xs animate-fade-in">
                  {requirements.map((req, idx) => {
                    const isCovered = req.status === 'covered';
                    const isPartial = req.status === 'partial';

                    return (
                      <div
                        key={idx}
                        className={`p-3.5 rounded-xl border flex flex-col gap-2 ${isCovered
                            ? 'bg-emerald-950/15 border-emerald-500/20'
                            : isPartial
                              ? 'bg-amber-950/15 border-amber-500/20'
                              : 'bg-rose-950/15 border-rose-500/20'
                          }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <span className="font-semibold text-surface-100 text-[12px]">{req.requirement}</span>
                          <span
                            className={`text-[9px] font-extrabold uppercase px-2.5 py-0.5 rounded-md border shrink-0 ${isCovered
                                ? 'bg-emerald-500/15 text-emerald-300 border-emerald-500/25'
                                : isPartial
                                  ? 'bg-amber-500/15 text-amber-300 border-amber-500/25'
                                  : 'bg-rose-500/15 text-rose-300 border-rose-500/25'
                              }`}
                          >
                            {req.status}
                          </span>
                        </div>
                        {req.evidence && (
                          <p className="text-[11px] text-surface-400 font-mono-code bg-surface-950/40 p-2.5 rounded-lg border border-white/3 leading-relaxed">
                            {req.evidence}
                          </p>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Tab 4: Suggestions */}
              {activeTab === 'suggestions' && (
                <div className="space-y-2 text-xs animate-fade-in">
                  {suggestions.map((sug, idx) => (
                    <div key={idx} className="bg-primary-950/20 border border-primary-500/15 text-surface-200 rounded-xl p-3.5 flex items-start gap-2.5">
                      <svg className="w-4 h-4 text-primary-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
                      </svg>
                      <span className="text-[12px] leading-relaxed">{sug}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
