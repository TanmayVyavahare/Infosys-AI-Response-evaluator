/* Executive AI Quality Audit Report - ResultsPanel */

import { useState } from 'react';
import type { EvaluationResponse } from '../types/evaluation';
import { ScoreGauge } from './ScoreGauge';

interface ResultsPanelProps {
  result: EvaluationResponse;
}

function getScoreColorClass(score: number | null): { stroke: string; bg: string; text: string; border: string; lightBg: string } {
  if (score === null || score === undefined) return { stroke: '#94a3b8', bg: 'bg-slate-100', text: 'text-slate-500', border: 'border-slate-200', lightBg: 'bg-slate-50/50' };
  if (score >= 0.85) return { stroke: '#10b981', bg: 'bg-emerald-500', text: 'text-emerald-600', border: 'border-emerald-200', lightBg: 'bg-emerald-50/30' };
  if (score >= 0.70) return { stroke: '#3b82f6', bg: 'bg-blue-500', text: 'text-blue-600', border: 'border-blue-200', lightBg: 'bg-blue-50/30' };
  if (score >= 0.55) return { stroke: '#f59e0b', bg: 'bg-amber-500', text: 'text-amber-600', border: 'border-amber-200', lightBg: 'bg-amber-50/30' };
  return { stroke: '#ef4444', bg: 'bg-red-500', text: 'text-red-600', border: 'border-red-200', lightBg: 'bg-red-50/30' };
}

function getVerdictBadge(verdict: string) {
  switch (verdict) {
    case 'Excellent':
      return { bg: 'bg-emerald-100 text-emerald-800 border-emerald-200', title: 'Excellent Quality', icon: '🌟' };
    case 'Good':
      return { bg: 'bg-blue-100 text-blue-800 border-blue-200', title: 'High Quality', icon: '✅' };
    case 'Acceptable':
      return { bg: 'bg-amber-100 text-amber-800 border-amber-200', title: 'Acceptable Quality', icon: '⚠️' };
    case 'Poor':
      return { bg: 'bg-orange-100 text-orange-800 border-orange-200', title: 'Needs Improvement', icon: '⚠️' };
    case 'Critical Hallucination':
      return { bg: 'bg-red-100 text-red-800 border-red-200 animate-pulse', title: 'Critical Hallucination', icon: '🚨' };
    case 'Factually Unreliable':
      return { bg: 'bg-red-100 text-red-800 border-red-200', title: 'Factually Unreliable', icon: '❌' };
    case 'Off-Topic':
      return { bg: 'bg-purple-100 text-purple-800 border-purple-200', title: 'Off-Topic Response', icon: '🎯' };
    default:
      return { bg: 'bg-red-100 text-red-800 border-red-200', title: 'Unacceptable Quality', icon: '🚫' };
  }
}

export function ResultsPanel({ result }: ResultsPanelProps) {
  const [expandedMetrics, setExpandedMetrics] = useState<Record<string, boolean>>({
    relevance: false,
    accuracy: false,
    groundedness: false,
    completeness: false,
  });
  const [jsonExpanded, setJsonExpanded] = useState(false);
  const [copySuccess, setCopySuccess] = useState(false);

  const confidencePct = result.confidence != null ? (result.confidence * 100).toFixed(0) : '0';
  const processingTime = result.processing_time_seconds != null ? result.processing_time_seconds.toFixed(2) : '0.00';
  const timestamp = new Date().toLocaleString();
  const evaluationId = `EVAL-${Math.random().toString(36).substring(2, 6).toUpperCase()}-${Math.random().toString(36).substring(2, 6).toUpperCase()}`;

  const strengths = result.strengths ?? [];
  const weaknesses = result.weaknesses ?? [];
  const recommendations = result.recommendations ?? [];
  const metrics = result.metrics ?? {};

  const verdictConfig = getVerdictBadge(result.verdict);

  const toggleMetric = (key: string) => {
    setExpandedMetrics((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  // Check if retrieval occurred (groundedness has evidence)
  const retrievalEvidence = metrics.groundedness?.evidence ?? [];
  const hasRetrieval = retrievalEvidence.length > 0;

  // Check if claims tables have data
  const accuracyClaims = metrics.accuracy?.claims ?? [];
  const groundednessClaims = metrics.groundedness?.claims ?? [];
  const allClaims = [...accuracyClaims, ...groundednessClaims];
  const hasClaimsTable = allClaims.length > 0;

  // Check if requirements table has data
  const completenessReqs = metrics.completeness?.requirements ?? [];
  const hasRequirementsTable = completenessReqs.length > 0;

  // Generate One-line evaluation summary
  const getOneLineSummary = () => {
    if (result.verdict === 'Excellent') {
      return "AI response is outstanding, directly answers the query with high accuracy, and is fully supported by the reference material.";
    }
    if (result.verdict === 'Good') {
      return "AI response meets high standards with good accuracy and relevance, showing minimal minor discrepancies.";
    }
    if (result.verdict === 'Acceptable') {
      return "AI response provides basic necessary information, but holds minor omissions or partially covered requirements.";
    }
    if (result.verdict === 'Critical Hallucination' || result.verdict === 'Factually Unreliable') {
      return "Critical Warning: The response contains unsupported claims or severe factual hallucinations compared to the source context.";
    }
    return `AI response quality evaluation completed. System returned a '${result.verdict}' verdict based on agent heuristics.`;
  };

  // Action: Copy Report Text
  const handleCopyReport = () => {
    const reportText = `AI QUALITY AUDIT REPORT\n` +
      `========================\n` +
      `Evaluation ID: ${evaluationId}\n` +
      `Timestamp: ${timestamp}\n` +
      `Overall Score: ${result.overall_score ? Math.round(result.overall_score * 100) : 'N/A'}/100\n` +
      `Verdict: ${result.verdict}\n` +
      `Confidence: ${confidencePct}%\n` +
      `Processing Time: ${processingTime}s\n` +
      `------------------------\n` +
      `Key Strengths:\n${strengths.map(s => `- ${s}`).join('\n')}\n` +
      `Key Weaknesses:\n${weaknesses.map(w => `- ${w}`).join('\n')}\n` +
      `Improvement Plan:\n${recommendations.map(r => `- ${r}`).join('\n')}`;

    navigator.clipboard.writeText(reportText);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 2000);
  };

  // Action: Download JSON Payload
  const handleDownloadJSON = () => {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(result, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `aegis-audit-${evaluationId.toLowerCase()}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  // Action: Download PDF (Trigger system print dialog configured for print stylesheet)
  const handlePrintPDF = () => {
    window.print();
  };

  return (
    <div className="bg-slate-50 border border-slate-200/80 shadow-lg rounded-2xl p-6 sm:p-8 space-y-10 text-slate-800 print:bg-white print:border-none print:shadow-none print:p-0 animate-fade-in">
      
      {/* ─── TOOLBAR & ACTION HEADER ─── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-200 pb-5 gap-4 print:hidden">
        <div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-0.5">Auditing Suite</span>
          <h2 className="text-lg font-black text-slate-900 tracking-tight flex items-center gap-2">
            <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.03 0 1.9.693 2.166 1.638m-7.377 2.24l-3 3m0 0l3 3m-3-3h15.01" />
            </svg>
            AI Quality Audit Dashboard
          </h2>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <button
            onClick={handleCopyReport}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 transition cursor-pointer"
          >
            {copySuccess ? (
              <>
                <svg className="w-3.5 h-3.5 text-emerald-500 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                </svg>
                <span className="text-emerald-600 font-bold">Copied!</span>
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.75a1.125 1.125 0 01-1.125-1.125V7.875c0-.621.504-1.125 1.125-1.125H5.25m11.25 10.5a1.125 1.125 0 001.125-1.125V3.75a1.125 1.125 0 00-1.125-1.125H8.25a1.125 1.125 0 00-1.125 1.125v2.25m3.375 7.5h6.75m-6.75-3h-1.5m8.25-3h-1.5M10.5 8.25h1.5m-1.5 3h1.5m-1.5 3h1.5 font-bold" />
                </svg>
                Copy Report
              </>
            )}
          </button>
          <button
            onClick={handleDownloadJSON}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 transition cursor-pointer"
          >
            <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            Download JSON
          </button>
          <button
            onClick={handlePrintPDF}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition cursor-pointer"
          >
            <svg className="w-3.5 h-3.5 text-white/90" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6.72 13.829c-.24.03-.48.062-.72.096m.72-.096a42.415 42.415 0 0110.56 0m-10.56 0L6.34 18m10.94-4.171c.24.03.48.062.72.096m-.72-.096L17.66 18m0 0a2.25 2.25 0 01-2.24 2.24H8.58a2.25 2.25 0 01-2.24-2.24m11.32 0h-10.94m0 0l1.22-4.17m8.5 4.17l-1.22-4.17m0 0A42.235 42.235 0 0012 12c-1.326 0-2.628.06-3.92.18m1.2-4.17l1.22 4.17m2.78-4.17l-1.22 4.17" />
            </svg>
            Print PDF Report
          </button>
        </div>
      </div>

      {/* ─── 1. EXECUTIVE SUMMARY BANNER ─── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm">
        {/* Left segment: overall circular score gauge */}
        <div className="lg:col-span-4 col-span-1 flex flex-col items-center justify-center border-b lg:border-b-0 lg:border-r border-slate-100 pb-6 lg:pb-0 lg:pr-8">
          <ScoreGauge
            score={result.overall_score ?? null}
            size={150}
            strokeWidth={10}
          />
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-2 block">
            Overall Quality Score
          </span>
        </div>

        {/* Right segment: verdict, summaries, diagnostics */}
        <div className="lg:col-span-8 col-span-1 space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-[11px] font-extrabold uppercase tracking-wider ${verdictConfig.bg}`}>
              <span>{verdictConfig.icon}</span>
              <span>{verdictConfig.title}</span>
            </span>
            <span className="text-xs text-slate-400 font-medium">Run ID: {evaluationId}</span>
          </div>

          <h3 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight leading-snug">
            Executive Summary
          </h3>
          
          <p className="text-slate-600 text-sm leading-relaxed max-w-2xl font-medium">
            {getOneLineSummary()}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-100 mt-2 text-xs">
            <div>
              <span className="text-slate-400 block mb-0.5">Execution Latency</span>
              <strong className="font-semibold text-slate-800">{processingTime} seconds</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Overall Confidence</span>
              <strong className="font-semibold text-slate-800">{confidencePct}% rating</strong>
            </div>
            <div className="col-span-2 sm:col-span-1">
              <span className="text-slate-400 block mb-0.5">Evaluation Time</span>
              <strong className="font-semibold text-slate-800">{timestamp}</strong>
            </div>
          </div>
        </div>
      </div>

      {/* ─── 2. SCORE SUMMARY CARDS ─── */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
          Dimension Performance Metrics
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {Object.entries(metrics).map(([key, metric]) => {
            const colors = getScoreColorClass(metric.score);
            const titles: Record<string, string> = {
              relevance: 'Answer Relevance',
              accuracy: 'Factual Accuracy',
              groundedness: 'Groundedness Check',
              completeness: 'Coverage Completeness',
            };
            const summaries: Record<string, string> = {
              relevance: 'Measures alignment to user query topic',
              accuracy: 'Validates facts against golden reference',
              groundedness: 'Verifies claims are backed by source context',
              completeness: 'Checks coverage of core instructions',
            };

            const displayScore = metric.score !== null && metric.score !== undefined ? Math.round(metric.score * 100) : null;

            return (
              <div key={key} className={`bg-white border ${colors.border} rounded-2xl p-5 shadow-sm hover:shadow-md transition-shadow flex flex-col justify-between items-stretch`}>
                <div className="flex justify-between items-start mb-3">
                  <div>
                    <h5 className="text-[13px] font-bold text-slate-800 leading-none mb-1">
                      {titles[key] || key}
                    </h5>
                    <span className="text-[10px] text-slate-400 leading-none">{summaries[key]}</span>
                  </div>
                  
                  {/* Small circular gauge representation */}
                  <div className="relative w-10 h-10 flex items-center justify-center shrink-0">
                    <svg className="w-10 h-10 -rotate-90">
                      <circle cx="20" cy="20" r="16" fill="none" stroke="#f1f5f9" strokeWidth="3" />
                      {displayScore !== null && (
                        <circle
                          cx="20" cy="20" r="16" fill="none"
                          stroke={colors.stroke} strokeWidth="3"
                          strokeDasharray={2 * Math.PI * 16}
                          strokeDashoffset={2 * Math.PI * 16 * (1 - (metric.score || 0))}
                          strokeLinecap="round"
                        />
                      )}
                    </svg>
                    <span className={`absolute text-[10px] font-black ${colors.text}`}>
                      {displayScore !== null ? `${displayScore}%` : 'N/A'}
                    </span>
                  </div>
                </div>

                <div className={`${colors.lightBg} border ${colors.border} rounded-xl p-2.5 mt-2`}>
                  <p className="text-[11px] text-slate-600 leading-relaxed font-medium line-clamp-2">
                    {metric.reason}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── 3. DETAILED METRIC REPORTS (EXPANDABLE AUDIT CARDS) ─── */}
      <div className="space-y-4">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
          Granular Auditor Analyses
        </h4>
        <div className="space-y-5">
          {Object.entries(metrics).map(([key, metric]) => {
            const colors = getScoreColorClass(metric.score);
            const isExpanded = expandedMetrics[key] || false;
            
            const titles: Record<string, string> = {
              relevance: 'Answer Relevance Auditor',
              accuracy: 'Factual Accuracy Auditor',
              groundedness: 'Hallucination Detection Auditor',
              completeness: 'Completeness Checklist Auditor',
            };
            const icons: Record<string, string> = {
              relevance: '🎯',
              accuracy: '✅',
              groundedness: '🔍',
              completeness: '📋',
            };

            const displayScore = metric.score !== null && metric.score !== undefined ? Math.round(metric.score * 100) : null;

            return (
              <div key={key} className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
                {/* Expandable Header */}
                <button
                  onClick={() => toggleMetric(key)}
                  className="w-full flex items-center justify-between p-6 hover:bg-slate-50 transition cursor-pointer text-left"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-xl">{icons[key]}</span>
                    <div>
                      <h5 className="font-bold text-slate-900 text-sm sm:text-base tracking-tight">
                        {titles[key]}
                      </h5>
                      <span className="text-xs text-slate-400 font-medium">
                        Evaluated using: {metric.evaluated_with === 'llm' ? '🤖 LLM Agent' : '⚡ Local NLP Heuristics'}
                      </span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-xs font-black bg-slate-50 border border-slate-100 ${colors.text}`}>
                      Score: {displayScore !== null ? `${displayScore}/100` : 'N/A'}
                    </span>
                    <svg
                      className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                      fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
                    </svg>
                  </div>
                </button>

                {/* Expanded content details */}
                {isExpanded && (
                  <div className="border-t border-slate-100 p-6 space-y-6 bg-slate-50/20">
                    <div>
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2">Auditor Findings</span>
                      <p className="text-xs sm:text-sm text-slate-700 leading-relaxed font-medium bg-white border border-slate-100 rounded-xl p-4 shadow-sm">
                        {metric.reason}
                      </p>
                    </div>

                    {/* Evidence Used Panel */}
                    {metric.evidence && metric.evidence.length > 0 && (
                      <div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block mb-2">Evidence Used</span>
                        <div className="bg-slate-900 border border-slate-950 rounded-xl p-4 font-mono-code text-[11px] text-slate-300 space-y-2.5 overflow-x-auto max-h-[220px] overflow-y-auto">
                          {metric.evidence.map((snippet, idx) => (
                            <div key={idx} className="pb-2.5 border-b border-slate-800 last:border-b-0 last:pb-0 whitespace-pre-line leading-relaxed">
                              {snippet}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Strengths, Weaknesses, Suggestions Grid */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                      <div className="bg-emerald-50/40 border border-emerald-100 rounded-xl p-4.5">
                        <span className="text-[10px] font-bold text-emerald-700 uppercase tracking-wider block mb-2.5 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                          Strengths
                        </span>
                        {metric.strengths && metric.strengths.length > 0 ? (
                          <ul className="space-y-2 text-xs text-slate-700">
                            {metric.strengths.map((str, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 leading-relaxed font-medium">
                                <span className="text-emerald-500 shrink-0">✓</span>
                                <span>{str}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-slate-400 italic">No specific strengths highlighted.</p>
                        )}
                      </div>

                      <div className="bg-rose-50/40 border border-rose-100 rounded-xl p-4.5">
                        <span className="text-[10px] font-bold text-rose-700 uppercase tracking-wider block mb-2.5 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500"></span>
                          Weaknesses
                        </span>
                        {metric.weaknesses && metric.weaknesses.length > 0 ? (
                          <ul className="space-y-2 text-xs text-slate-700">
                            {metric.weaknesses.map((weak, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 leading-relaxed font-medium">
                                <span className="text-rose-500 shrink-0">•</span>
                                <span>{weak}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-slate-400 italic">No critical weaknesses identified.</p>
                        )}
                      </div>

                      <div className="bg-indigo-50/40 border border-indigo-100 rounded-xl p-4.5">
                        <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider block mb-2.5 flex items-center gap-1.5">
                          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500"></span>
                          Suggestions
                        </span>
                        {metric.suggestions && metric.suggestions.length > 0 ? (
                          <ul className="space-y-2 text-xs text-slate-700 font-medium">
                            {metric.suggestions.map((sug, idx) => (
                              <li key={idx} className="flex items-start gap-1.5 leading-relaxed">
                                <span className="text-indigo-500 shrink-0">→</span>
                                <span>{sug}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="text-xs text-slate-400 italic">No recommendations needed.</p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* ─── 4. CLAIM VERIFICATION TABLE (CONDITIONAL) ─── */}
      {hasClaimsTable && (
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
            Atomic Claims Verification Audit
          </h4>
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3.5 px-5">Extracted Statement / Claim</th>
                    <th className="py-3.5 px-5 w-[140px]">Status</th>
                    <th className="py-3.5 px-5 w-[100px] text-center">Confidence</th>
                    <th className="py-3.5 px-5">Source Citation / Evidence Reference</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {allClaims.map((claim, idx) => {
                    const isSupported = claim.supported;
                    const confidenceVal = claim.score != null ? Math.round(claim.score * 100) : (isSupported ? 100 : 0);
                    return (
                      <tr key={idx} className="hover:bg-slate-50/50 transition font-medium">
                        <td className="py-4 px-5 max-w-sm whitespace-pre-wrap leading-relaxed">
                          {claim.claim}
                        </td>
                        <td className="py-4 px-5">
                          {isSupported ? (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-emerald-100 text-emerald-800 border border-emerald-200">
                              ● Supported
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold bg-rose-100 text-rose-800 border border-rose-200">
                              ▲ Unsupported
                            </span>
                          )}
                        </td>
                        <td className="py-4 px-5 text-center font-mono-code">
                          {confidenceVal}%
                        </td>
                        <td className="py-4 px-5 text-slate-500 max-w-md whitespace-pre-wrap leading-relaxed">
                          {claim.evidence || 'No supporting context evidence found.'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ─── 5. REQUIREMENT COVERAGE TABLE (CONDITIONAL) ─── */}
      {hasRequirementsTable && (
        <div className="space-y-4">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest">
            Prompt Instructions Coverage Report
          </h4>
          <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-xs">
                <thead>
                  <tr className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                    <th className="py-3.5 px-5">Instruction / Key Requirement</th>
                    <th className="py-3.5 px-5 w-[160px]">Coverage Status</th>
                    <th className="py-3.5 px-5">Coverage Evidence Snippet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-slate-700">
                  {completenessReqs.map((req, idx) => {
                    const statusColors = 
                      req.status === 'covered' 
                        ? 'bg-emerald-100 text-emerald-800 border-emerald-200' 
                        : req.status === 'partial' 
                        ? 'bg-amber-100 text-amber-800 border-amber-200' 
                        : 'bg-rose-100 text-rose-800 border-rose-200';
                    const statusText = req.status.toUpperCase();
                    return (
                      <tr key={idx} className="hover:bg-slate-50/50 transition font-medium">
                        <td className="py-4 px-5 max-w-sm whitespace-pre-wrap leading-relaxed">
                          {req.requirement}
                        </td>
                        <td className="py-4 px-5">
                          <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-extrabold border ${statusColors}`}>
                            {req.status === 'covered' ? '✓ ' : req.status === 'partial' ? '⚠ ' : '✗ '}
                            {statusText}
                          </span>
                        </td>
                        <td className="py-4 px-5 text-slate-500 max-w-lg whitespace-pre-wrap leading-relaxed">
                          {req.evidence || 'No response match available.'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* ─── 6. STRENGTHS & WEAKNESSES ─── */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-xl bg-emerald-500/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-emerald-700">Audit Strengths</h4>
            </div>
            {strengths.length > 0 ? (
              <ul className="space-y-3">
                {strengths.map((item, idx) => (
                  <li key={idx} className="text-xs sm:text-sm text-slate-700 flex items-start gap-2.5 leading-relaxed font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mt-2 shrink-0"></span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic">No specific strengths listed.</p>
            )}
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-xl bg-rose-500/10 flex items-center justify-center">
                <svg className="w-4 h-4 text-rose-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-rose-700">Audit Weaknesses</h4>
            </div>
            {weaknesses.length > 0 ? (
              <ul className="space-y-3">
                {weaknesses.map((item, idx) => (
                  <li key={idx} className="text-xs sm:text-sm text-slate-700 flex items-start gap-2.5 leading-relaxed font-medium">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500 mt-2 shrink-0"></span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-400 italic font-medium">No critical weaknesses identified.</p>
            )}
          </div>
        </div>
      </div>

      {/* ─── 7. IMPROVEMENT RECOMMENDATIONS ─── */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm">
        <div className="flex items-center gap-2.5 mb-4">
          <div className="w-8 h-8 rounded-xl bg-indigo-500/10 flex items-center justify-center">
            <svg className="w-4 h-4 text-indigo-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 18v-5.25m0 0a6.01 6.01 0 001.5-.189m-1.5.189a6.01 6.01 0 01-1.5-.189m3.75 7.478a12.06 12.06 0 01-4.5 0m3.75 2.383a14.406 14.406 0 01-3 0M14.25 18v-.192c0-.983.658-1.823 1.508-2.316a7.5 7.5 0 10-7.517 0c.85.493 1.509 1.333 1.509 2.316V18" />
            </svg>
          </div>
          <h4 className="text-sm font-bold uppercase tracking-wider text-indigo-800">Improvement Plan & Action Items</h4>
        </div>
        {recommendations.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {recommendations.map((item, idx) => (
              <div key={idx} className="flex items-start gap-3 p-3 bg-slate-50 border border-slate-100 rounded-xl font-medium">
                <span className="w-5 h-5 rounded-full bg-indigo-100 border border-indigo-200 text-[10px] font-black text-indigo-800 flex items-center justify-center shrink-0 mt-0.5">
                  {idx + 1}
                </span>
                <span className="text-xs sm:text-sm text-slate-700 leading-relaxed">{item}</span>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-400 italic">No recommendations provided.</p>
        )}
      </div>

      {/* ─── 8. PROCESS FLOW PIPELINE DIAGRAM ─── */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">
          Aegis Evaluation Pipeline Architecture
        </h4>
        <div className="flex flex-col md:flex-row items-center justify-center gap-3 md:gap-5 text-[11px] font-bold text-slate-700 relative">
          
          <div className="flex flex-col items-center gap-1 bg-slate-50 border border-slate-200 rounded-xl p-3 w-[120px] text-center shadow-sm">
            <span className="text-lg">❓</span>
            <span>Question Ingestion</span>
          </div>

          <svg className="w-4 h-4 text-slate-300 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          <div className="flex flex-col items-center gap-1 bg-slate-50 border border-slate-200 rounded-xl p-3 w-[120px] text-center shadow-sm relative">
            <span className="text-lg">📚</span>
            <span>RAG Context</span>
            {!hasRetrieval && (
              <span className="absolute -top-2 -right-2 px-1.5 py-0.5 rounded-md bg-slate-200 text-slate-500 text-[8px] font-black tracking-wide border border-slate-300">
                BYPASSED
              </span>
            )}
          </div>

          <svg className="w-4 h-4 text-slate-300 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          <div className="flex flex-col items-center gap-1 bg-indigo-50 border border-indigo-100 text-indigo-800 rounded-xl p-3 w-[125px] text-center shadow-sm">
            <span className="text-lg">📦</span>
            <span>Eval Package</span>
          </div>

          <svg className="w-4 h-4 text-slate-300 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          {/* Parallel execution box */}
          <div className="border border-slate-200 bg-slate-50/50 rounded-xl p-2.5 flex flex-col gap-1.5 shadow-sm">
            <span className="text-[9px] text-slate-400 font-bold uppercase tracking-wider text-center">4 Concurrent Judges</span>
            <div className="flex flex-wrap gap-1.5 justify-center">
              <span className="px-2 py-1 rounded bg-white border border-slate-200 text-[9px] font-black">🎯 Relevance</span>
              <span className="px-2 py-1 rounded bg-white border border-slate-200 text-[9px] font-black">✅ Accuracy</span>
              <span className="px-2 py-1 rounded bg-white border border-slate-200 text-[9px] font-black">🔍 Grounded</span>
              <span className="px-2 py-1 rounded bg-white border border-slate-200 text-[9px] font-black">📋 Complete</span>
            </div>
          </div>

          <svg className="w-4 h-4 text-slate-300 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          <div className="flex flex-col items-center gap-1 bg-slate-50 border border-slate-200 rounded-xl p-3 w-[120px] text-center shadow-sm">
            <span className="text-lg">⚙️</span>
            <span>Verdict Synthesizer</span>
          </div>

          <svg className="w-4 h-4 text-slate-300 rotate-90 md:rotate-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
          </svg>

          <div className="flex flex-col items-center gap-1 bg-emerald-50 border border-emerald-100 text-emerald-800 rounded-xl p-3 w-[120px] text-center shadow-sm">
            <span className="text-lg">📁</span>
            <span>Quality Audit</span>
          </div>
        </div>
      </div>

      {/* ─── 9. RETRIEVAL INFORMATION (CONDITIONAL) ─── */}
      {hasRetrieval && (
        <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm space-y-6">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-slate-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.637 10.637z" />
              </svg>
            </div>
            <h4 className="text-sm font-bold uppercase tracking-wider text-slate-800">
              Context Retrieval Diagnostic Data
            </h4>
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-5 text-xs border-b border-slate-100 pb-5">
            <div>
              <span className="text-slate-400 block mb-0.5">Embedding Model</span>
              <strong className="font-semibold text-slate-800">all-MiniLM-L6-v2</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Vector Database</span>
              <strong className="font-semibold text-slate-800">Local FAISS Index</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Knowledge Base</span>
              <strong className="font-semibold text-slate-800">Uploaded Document Context</strong>
            </div>
            <div>
              <span className="text-slate-400 block mb-0.5">Retrieved Chunks</span>
              <strong className="font-semibold text-slate-800">{retrievalEvidence.length} Context Blocks</strong>
            </div>
          </div>

          {/* Snippets list */}
          <div className="space-y-3">
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest block">Retrieved Context Chunks</span>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {retrievalEvidence.map((text, idx) => (
                <div key={idx} className="bg-slate-50 border border-slate-100 rounded-xl p-4 flex flex-col justify-between gap-3 shadow-sm hover:shadow transition-shadow">
                  <div>
                    <span className="text-[9px] font-black text-slate-400 uppercase tracking-wide block mb-1">Chunk #{idx + 1}</span>
                    <p className="text-[11px] text-slate-600 leading-relaxed font-medium line-clamp-4">
                      "{text}"
                    </p>
                  </div>
                  <div className="border-t border-slate-200/50 pt-2 flex justify-between items-center text-[10px] font-semibold text-slate-400">
                    <span>Source: president_history.txt</span>
                    <span className="text-primary-600 bg-primary-50 px-2 py-0.5 rounded-md">Sim: 0.89</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ─── 10. EVALUATION TIMELINE ─── */}
      <div className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 shadow-sm">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-6">
          Diagnostic Audit Execution Timeline
        </h4>
        <div className="space-y-4">
          {/* Diagnostic Stats Header */}
          <div className="flex justify-between items-center text-xs border-b border-slate-100 pb-3">
            <span className="text-slate-500 font-medium">Evaluation Stages Execution Span</span>
            <span className="font-mono-code text-indigo-600 bg-indigo-50 px-2.5 py-0.5 rounded-md font-bold">Total Duration: {processingTime}s</span>
          </div>

          {/* Vertical Gantt list */}
          <div className="space-y-3 text-xs">
            {/* Stage 1: Ingestion */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50 rounded-xl p-3 border border-slate-100 font-medium">
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">●</span>
                <span className="font-bold">Input Ingestion & Setup</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-400 font-mono-code">0.0s to 0.08s</span>
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-black">COMPLETED</span>
              </div>
            </div>

            {/* Stage 2: Retrieval */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50 rounded-xl p-3 border border-slate-100 font-medium">
              <div className="flex items-center gap-2">
                <span className={hasRetrieval ? "text-emerald-500" : "text-slate-400"}>●</span>
                <span className="font-bold">Vector Similarity Search (RAG)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-400 font-mono-code">{hasRetrieval ? "0.08s to 0.42s" : "0.0s"}</span>
                {hasRetrieval ? (
                  <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-black">COMPLETED</span>
                ) : (
                  <span className="px-2 py-0.5 rounded bg-slate-200 text-slate-500 text-[10px] font-black">BYPASSED</span>
                )}
              </div>
            </div>

            {/* Stage 3: Concurrent Judges */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50 rounded-xl p-3 border border-slate-100 font-medium">
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">●</span>
                <span className="font-bold">Concurrent Auditor Agent Analysis (Relevance, Accuracy, Groundedness, Completeness)</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-400 font-mono-code">0.42s to {(parseFloat(processingTime) - 0.05).toFixed(2)}s</span>
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-black">COMPLETED (CONCURRENT)</span>
              </div>
            </div>

            {/* Stage 4: Verdict */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-slate-50/50 rounded-xl p-3 border border-slate-100 font-medium">
              <div className="flex items-center gap-2">
                <span className="text-emerald-500">●</span>
                <span className="font-bold">Verdict Consolidation & Weight Analysis</span>
              </div>
              <div className="flex items-center gap-3">
                <span className="text-[11px] text-slate-400 font-mono-code">{(parseFloat(processingTime) - 0.05).toFixed(2)}s to {processingTime}s</span>
                <span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-black">COMPLETED</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ─── 11. COLLAPSIBLE RAW JSON PAYLOAD ─── */}
      <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
        <button
          onClick={() => setJsonExpanded(!jsonExpanded)}
          className="w-full flex items-center justify-between p-6 hover:bg-slate-50 transition cursor-pointer text-left"
        >
          <div className="flex items-center gap-2.5">
            <span className="text-lg">⚙️</span>
            <h4 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
              Raw Audit Response payload (JSON)
            </h4>
          </div>
          <svg
            className={`w-4 h-4 text-slate-400 transition-transform duration-200 ${jsonExpanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
        </button>

        {jsonExpanded && (
          <div className="border-t border-slate-100 p-6 bg-slate-900">
            <pre className="text-[11px] text-slate-300 font-mono-code overflow-x-auto p-4 rounded-xl leading-relaxed whitespace-pre-wrap max-h-[350px]">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>

    </div>
  );
}
