/* Header Navigation Component with System Status & Info Modal */

import { useState, useEffect, useRef } from 'react';

interface HeaderProps {
  hasResult: boolean;
  onReset: () => void;
}

export function Header({ hasResult, onReset }: HeaderProps) {
  const [showInfo, setShowInfo] = useState(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (showInfo) dialogRef.current?.showModal();
    else dialogRef.current?.close();
  }, [showInfo]);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 8);
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <>
      <header
        className={`sticky top-0 z-50 transition-all duration-300 ${
          scrolled
            ? 'border-b border-white/8 backdrop-blur-2xl bg-surface-950/85 shadow-xl shadow-black/20'
            : 'border-b border-transparent backdrop-blur-xl bg-surface-950/60'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex flex-wrap gap-3 items-center justify-between">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3.5">
            {/* Animated logo with gradient ring */}
            <div className="relative group">
              <div className="absolute -inset-0.5 bg-gradient-to-r from-primary-500 via-accent-purple to-accent-cyan rounded-xl opacity-60 blur-sm group-hover:opacity-100 transition-opacity duration-300"></div>
              <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 via-accent-purple to-accent-cyan p-[1.5px]">
                <div className="w-full h-full bg-surface-950 rounded-[10px] flex items-center justify-center">
                  <span className="font-extrabold text-lg gradient-text-accent tracking-tighter select-none">Æ</span>
                </div>
              </div>
            </div>

            <div>
              <div className="flex items-center gap-2.5">
                <h1 className="text-lg font-extrabold text-white tracking-tight">
                  Aegis
                </h1>
                <span className="brand-badge badge-pill bg-primary-500/10 text-primary-300 border border-primary-500/20 text-[9px]">
                  Response evaluator
                </span>
              </div>
              <p className="text-[11px] text-surface-400 font-medium hidden sm:block tracking-wide">
                Understand and improve AI answers
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setShowInfo(true)}
              className="btn-ghost text-xs px-3.5 py-2 flex items-center gap-1.5"
              title="Learn about evaluation metrics" aria-label="How it works"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M12 18h.01" />
              </svg>
              <span className="inline">How it works</span>
            </button>

            {hasResult && (
              <button
                onClick={onReset}
                className="btn-primary text-xs px-4 py-2 flex items-center gap-1.5 animate-scale-in"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                </svg>
                <span>New Evaluation</span>
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Info Modal — Premium Overlay */}
      <dialog ref={dialogRef} aria-labelledby="help-title" onCancel={() => setShowInfo(false)} onClose={() => setShowInfo(false)}
          className="help-dialog"
          onClick={(e) => { if (e.target === e.currentTarget) setShowInfo(false); }}
        >
          {/* Backdrop */}


          {/* Modal Card */}
          <div className="glass-card max-w-2xl w-full p-0 border-primary-500/20 relative animate-scale-in overflow-hidden">
            {/* Top Accent Line */}
            <div className="h-[2px] bg-gradient-to-r from-transparent via-primary-500 to-transparent"></div>

            {/* Header */}
            <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-white/5">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500/20 to-accent-purple/20 border border-primary-500/20 flex items-center justify-center">
                  <span className="text-base">🛡️</span>
                </div>
                <div>
                  <h3 id="help-title" className="text-base font-bold text-white">How your review works</h3>
                  <p className="text-[11px] text-surface-400">Four-dimensional quality assessment</p>
                </div>
              </div>
              <button
                onClick={() => setShowInfo(false)} aria-label="Close help"
                className="w-8 h-8 rounded-lg bg-surface-800/60 hover:bg-surface-700 text-surface-400 hover:text-white flex items-center justify-center transition-all cursor-pointer"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {/* Metric Cards Grid */}
            <div className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-3">
              {[
                { icon: '🎯', title: 'Relevance', weight: '25%', color: 'primary', desc: 'Assesses whether the AI response directly answers the user\'s question, disregarding factual accuracy.' },
                { icon: '✅', title: 'Accuracy', weight: '30%', color: 'emerald', desc: 'Extracts atomic claims and verifies facts against reference answers or retrieved context.' },
                { icon: '🔍', title: 'Groundedness', weight: '25%', color: 'cyan', desc: 'Detects hallucinations by cross-referencing claims against source context. Flags unsupported assertions.' },
                { icon: '📋', title: 'Completeness', weight: '20%', color: 'amber', desc: 'Extracts sub-questions and concepts from the prompt to evaluate topic coverage.' },
              ].map((metric, idx) => (
                <div key={idx} className="glass-panel p-4 space-y-2 hover:border-white/10 transition-all">
                  <div className="flex items-center justify-between">
                    <div className={`font-semibold text-${metric.color}-400 flex items-center gap-1.5 text-sm`}>
                      <span>{metric.icon}</span> {metric.title}
                    </div>
                    <span className="text-[10px] font-bold text-surface-400 bg-surface-800/60 px-2 py-0.5 rounded-md">
                      {metric.weight}
                    </span>
                  </div>
                  <p className="text-[11px] text-surface-300 leading-relaxed">{metric.desc}</p>
                </div>
              ))}
            </div>

            {/* Footer */}
            <div className="px-6 pb-5 flex items-center justify-between">
              <p className="text-[11px] text-surface-400">
                Scores are review guidance. Add trusted sources for stronger fact checking.
              </p>
              <button
                onClick={() => setShowInfo(false)}
                className="btn-primary text-xs px-5 py-2 font-semibold"
              >
                Got it
              </button>
            </div>
          </div>
        </dialog>
    </>
  );
}
