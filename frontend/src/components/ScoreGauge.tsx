/* ScoreGauge — animated SVG gauge with glowing gradient stroke */

import { useEffect, useState } from 'react';

interface ScoreGaugeProps {
  score: number | null;
  size?: number;
  strokeWidth?: number;
  label?: string;
}

function getGaugeColor(score: number): { stroke: string; glow: string; text: string; bg: string } {
  if (score >= 0.85) return { stroke: '#10b981', glow: 'rgba(16, 185, 129, 0.5)', text: 'text-emerald-400', bg: 'rgba(16, 185, 129, 0.06)' };
  if (score >= 0.70) return { stroke: '#34d399', glow: 'rgba(52, 211, 153, 0.4)', text: 'text-emerald-300', bg: 'rgba(52, 211, 153, 0.06)' };
  if (score >= 0.55) return { stroke: '#fbbf24', glow: 'rgba(251, 191, 36, 0.4)', text: 'text-amber-400', bg: 'rgba(251, 191, 36, 0.06)' };
  if (score >= 0.40) return { stroke: '#f97316', glow: 'rgba(249, 115, 22, 0.4)', text: 'text-orange-400', bg: 'rgba(249, 115, 22, 0.06)' };
  return { stroke: '#f43f5e', glow: 'rgba(244, 63, 94, 0.5)', text: 'text-rose-400', bg: 'rgba(244, 63, 94, 0.06)' };
}

export function ScoreGauge({ score, size = 120, strokeWidth = 8, label }: ScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    if (score === null || score === undefined) return;
    const duration = 1200;
    const start = performance.now();
    const animate = (now: number) => {
      const progress = Math.min((now - start) / duration, 1);
      // Smooth easeOutExpo curve
      const eased = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
      setAnimatedScore(score * eased);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [score]);

  const gaugeId = `gauge-${Math.random().toString(36).slice(2, 9)}`;

  if (score === null || score === undefined) {
    return (
      <div className="flex flex-col items-center gap-2">
        <div className="score-gauge" style={{ width: size, height: size }}>
          <svg width={size} height={size}>
            <circle
              cx={size / 2}
              cy={size / 2}
              r={radius}
              fill="none"
              stroke="rgba(255, 255, 255, 0.06)"
              strokeWidth={strokeWidth}
            />
          </svg>
          <span className="score-text text-surface-500 font-semibold" style={{ fontSize: size * 0.15 }}>
            N/A
          </span>
        </div>
        {label && <span className="text-[10px] font-semibold text-surface-500 uppercase tracking-wider">{label}</span>}
      </div>
    );
  }

  const colorConfig = getGaugeColor(score);
  const offset = circumference - animatedScore * circumference;

  return (
    <div className="flex flex-col items-center gap-2">
      <div
        className="score-gauge"
        style={{
          width: size,
          height: size,
          background: `radial-gradient(circle, ${colorConfig.bg} 0%, transparent 70%)`,
          borderRadius: '50%',
        }}
      >
        <svg width={size} height={size}>
          <defs>
            <linearGradient id={gaugeId} x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor={colorConfig.stroke} stopOpacity="0.6" />
              <stop offset="50%" stopColor={colorConfig.stroke} stopOpacity="1" />
              <stop offset="100%" stopColor={colorConfig.stroke} stopOpacity="0.8" />
            </linearGradient>
          </defs>
          {/* Background track */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255, 255, 255, 0.05)"
            strokeWidth={strokeWidth}
          />
          {/* Animated score arc */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={`url(#${gaugeId})`}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{
              filter: `drop-shadow(0 0 10px ${colorConfig.glow}) drop-shadow(0 0 4px ${colorConfig.glow})`,
              transition: 'stroke-dashoffset 0.08s linear',
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className={`font-black tracking-tighter ${colorConfig.text}`}
            style={{ fontSize: size * 0.24, lineHeight: 1 }}
          >
            {Math.round(animatedScore * 100)}
          </span>
          <span className="text-[9px] uppercase font-bold text-surface-500 tracking-widest mt-0.5">
            / 100
          </span>
        </div>
      </div>
      {label && (
        <span className="text-[10px] font-semibold text-surface-300 tracking-wider uppercase">
          {label}
        </span>
      )}
    </div>
  );
}
