import { useEffect, useRef, useState } from 'react'
import type { ScoreBreakdown } from '../types/api'

function ringColor(pct: number): string {
  if (pct >= 80) return '#f59e0b'
  if (pct >= 65) return '#06b6d4'
  if (pct >= 40) return '#f59e0b'
  return '#ef4444'
}

function scoreLabel(pct: number): string {
  if (pct >= 80) return 'Strong Match'
  if (pct >= 65) return 'Good Match'
  if (pct >= 40) return 'Partial Match'
  return 'Weak Match'
}

function scoreLabelColor(pct: number): string {
  if (pct >= 80) return 'text-amber-500'
  if (pct >= 65) return 'text-brand'
  if (pct >= 40) return 'text-amber-500'
  return 'text-red-500'
}

function AnimatedBar({ label, value, delay }: { label: string; value: number; delay: number }) {
  const pct = Math.round(value * 100)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setWidth(pct), delay)
    return () => clearTimeout(t)
  }, [pct, delay])

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-slate-600">{label}</span>
        <span className="font-medium text-slate-800">{pct}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full"
          style={{
            width: `${width}%`,
            backgroundColor: ringColor(pct),
            transition: 'width 700ms cubic-bezier(0.33, 1, 0.68, 1)',
          }}
        />
      </div>
    </div>
  )
}

interface Props {
  score: number
  breakdown: ScoreBreakdown
  processingMs: number
}

export default function ScoreDisplay({ score, breakdown, processingMs }: Props) {
  const pct = Math.round(score * 100)
  const circumference = 2 * Math.PI * 40
  const [displayPct, setDisplayPct] = useState(0)
  const [dashOffset, setDashOffset] = useState(circumference)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    setDisplayPct(0)
    setDashOffset(circumference)
    let startTime: number | null = null
    const duration = 1200

    function animate(ts: number) {
      if (!startTime) startTime = ts
      const progress = Math.min((ts - startTime) / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3)
      setDisplayPct(Math.round(eased * pct))
      setDashOffset(circumference - (eased * pct / 100) * circumference)
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate)
      }
    }

    rafRef.current = requestAnimationFrame(animate)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [pct, circumference])

  const color = ringColor(pct)
  const isStrong = pct >= 80

  return (
    <div className={`bg-white rounded-2xl border p-6 space-y-5 ${isStrong ? 'border-amber-200 shadow-card-gold' : 'border-slate-200 shadow-card-md'}`}>
      <div className="flex flex-col items-center gap-2">
        <svg width="130" height="130" viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#f1f5f9" strokeWidth="9" />
          <circle
            cx="50" cy="50" r="40" fill="none"
            stroke={color}
            strokeWidth="9"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 50 50)"
          />
          <text x="50" y="47" textAnchor="middle" dominantBaseline="central" fontSize="22" fontWeight="700" fill="#0f172a" fontFamily="Plus Jakarta Sans, sans-serif">
            {displayPct}
          </text>
          <text x="50" y="62" textAnchor="middle" dominantBaseline="central" fontSize="7" fill="#94a3b8">
            / 100
          </text>
        </svg>
        <p className={`text-base font-semibold font-display ${scoreLabelColor(pct)}`}>
          {scoreLabel(pct)}
        </p>
        <p className="text-xs text-slate-400">Analyzed in {processingMs}ms</p>
      </div>

      <div className="space-y-3">
        <AnimatedBar label="Semantic Similarity" value={breakdown.semantic_similarity} delay={400} />
        <AnimatedBar label="Skill Match" value={breakdown.skill_match.match_rate} delay={550} />
        <AnimatedBar label="Title Relevance" value={breakdown.title_relevance} delay={700} />
      </div>

      <p className="text-xs text-slate-500 text-center capitalize pt-1 border-t border-slate-100">
        Experience alignment: {breakdown.experience_match.replace(/_/g, ' ')}
      </p>
    </div>
  )
}
