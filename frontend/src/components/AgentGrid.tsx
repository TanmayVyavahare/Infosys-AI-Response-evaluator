import type { EvaluationResponse } from '../types/evaluation';
import { ScoreCard } from './ScoreCard';

interface AgentGridProps {
  result: EvaluationResponse | null;
  loading: boolean;
}

interface AgentCardProps {
  title: string;
  tooltip: string;
  loading: boolean;
}

function AgentPendingCard({ title, tooltip, loading }: AgentCardProps) {
  return (
    <div className="review-check-card">
      <div>
        <div className="flex items-center gap-2">
          <div className={`review-check-dot ${loading ? 'review-check-dot-active' : ''}`}></div>
          <h3 className="text-sm font-bold text-white tracking-wide">{title}</h3>
          <div className="group relative">
            <svg className="w-3.5 h-3.5 text-surface-500 cursor-help" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-48 p-2 bg-surface-950 text-[10px] text-surface-300 rounded-lg border border-white/10 shadow-xl z-30">
              {tooltip}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center gap-1.5 text-xs text-primary-400 mt-1.5 font-semibold">
            <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" opacity="0.25" />
              <path d="M12 2a10 10 0 019.95 9" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
            <span>Checking now</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-xs text-surface-500 mt-1.5 font-medium">
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <circle cx="12" cy="12" r="9" stroke="currentColor" strokeDasharray="3 3" />
            </svg>
            <span>Ready to check</span>
          </div>
        )}
      </div>

      <div className={`review-check-summary ${loading ? 'review-check-summary-active' : ''}`}>
        <span>{loading ? 'Analyzing your response and available context.' : tooltip}</span>
      </div>
    </div>
  );
}

export function AgentGrid({ result, loading }: AgentGridProps) {
  const agents = [
    {
      key: 'relevance',
      title: 'Answers the question',
      tooltip: 'Assesses whether the response directly addresses the query.',
    },
    {
      key: 'accuracy',
      title: 'Checks factual accuracy',
      tooltip: 'Verifies the factual reliability against the reference answer.',
    },
    {
      key: 'groundedness',
      title: 'Checks source support',
      tooltip: 'Cross-checks the statements against source context for factual grounding.',
    },
    {
      key: 'completeness',
      title: 'Checks for missing details',
      tooltip: 'Ensures the response addresses all key elements and concepts of the query.',
    },
  ];

  return (
    <section aria-label="Quality checks" className="space-y-3">
      {!result && <p className="section-kicker">Your quality checks</p>}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {agents.map((agent) => {
        const metricData = result?.metrics?.[agent.key];
        
        if (metricData) {
          return (
            <ScoreCard key={agent.key} metric={metricData} />
          );
        }

        return (
          <AgentPendingCard
            key={agent.key}
            title={agent.title}
            tooltip={agent.tooltip}
            loading={loading}
          />
        );
      })}
      </div>
    </section>
  );
}
