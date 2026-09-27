/* Claims Analysis Breakdown Component */

import type { ClaimDetail } from '../types/evaluation';

interface ClaimBreakdownProps {
  claims: ClaimDetail[];
}

export function ClaimBreakdown({ claims }: ClaimBreakdownProps) {
  if (!claims || claims.length === 0) return null;

  const supportedCount = claims.filter(c => c.supported === true).length;
  const unsupportedCount = claims.filter(c => c.supported === false).length;
  const unknownCount = claims.length - supportedCount - unsupportedCount;

  return (
    <div className="space-y-3 animate-fade-in">
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-bold uppercase tracking-wider text-surface-300 flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          Extracted Claims ({claims.length})
        </h4>
        <div className="flex gap-1.5">
          {supportedCount > 0 && (
            <span className="text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md border border-emerald-500/15 font-semibold text-[9px] flex items-center gap-1">
              <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              {supportedCount}
            </span>
          )}
          {unsupportedCount > 0 && (
            <span className="text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded-md border border-rose-500/15 font-semibold text-[9px] flex items-center gap-1">
              <svg className="w-2.5 h-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              {unsupportedCount}
            </span>
          )}
          {unknownCount > 0 && (
            <span className="text-surface-400 bg-surface-700/30 px-2 py-0.5 rounded-md border border-surface-600/20 font-semibold text-[9px]">
              ? {unknownCount}
            </span>
          )}
        </div>
      </div>

      {/* Claims List */}
      <div className="space-y-2">
        {claims.map((claim, idx) => {
          const isSupported = claim.supported === true;
          const isUnsupported = claim.supported === false;

          return (
            <div
              key={idx}
              className={`p-3.5 rounded-xl border text-xs transition-all ${
                isSupported
                  ? 'bg-emerald-950/15 border-emerald-500/20'
                  : isUnsupported
                  ? 'bg-rose-950/18 border-rose-500/25'
                  : 'bg-surface-900/50 border-surface-700/40'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-2.5 flex-1">
                  {/* Status Icon */}
                  <div className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 ${
                    isSupported
                      ? 'bg-emerald-500/15'
                      : isUnsupported
                      ? 'bg-rose-500/15'
                      : 'bg-surface-700/30'
                  }`}>
                    {isSupported ? (
                      <svg className="w-3 h-3 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                      </svg>
                    ) : isUnsupported ? (
                      <svg className="w-3 h-3 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    ) : (
                      <svg className="w-3 h-3 text-surface-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M12 18h.01" />
                      </svg>
                    )}
                  </div>

                  <div className="space-y-1.5 flex-1">
                    <p className="font-medium text-surface-100 leading-snug text-[12px]">
                      "{claim.claim}"
                    </p>
                    {claim.evidence && (
                      <div className="text-[10px] text-surface-400 bg-surface-950/50 p-2.5 rounded-lg border border-white/3 font-mono-code leading-relaxed">
                        <span className="text-primary-400 font-sans font-medium text-[10px]">Evidence: </span>
                        {claim.evidence}
                      </div>
                    )}
                  </div>
                </div>

                {claim.score !== null && claim.score !== undefined && (
                  <div className="shrink-0">
                    <span
                      className={`font-mono-code font-bold text-[10px] px-2 py-1 rounded-lg border ${
                        claim.score >= 0.7
                          ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20'
                          : claim.score >= 0.4
                          ? 'text-amber-400 bg-amber-500/10 border-amber-500/20'
                          : 'text-rose-400 bg-rose-500/10 border-rose-500/20'
                      }`}
                    >
                      {(claim.score * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
