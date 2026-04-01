interface Props {
  matched: string[]
  missing: string[]
  score?: number
}

export default function SkillPills({ matched, missing, score }: Props) {
  const estimatedBoost = Math.min(15, missing.length * 3)
  const targetScore = score !== undefined ? Math.min(100, Math.round(score * 100) + estimatedBoost) : null

  return (
    <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-5 space-y-4">
      <h3 className="font-semibold text-slate-800 font-display">Skills Analysis</h3>

      {matched.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            {matched.length} Matched
          </p>
          <div className="flex flex-wrap gap-1.5">
            {matched.map((s) => (
              <span key={s} className="px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                {s}
              </span>
            ))}
          </div>
        </div>
      )}

      {missing.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-2">
            {targetScore !== null
              ? `Add these to potentially reach ${targetScore}%`
              : `${missing.length} skills to add`}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {missing.map((s) => (
              <span key={s} className="px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">
                + {s}
              </span>
            ))}
          </div>
          <p className="text-xs text-slate-400 mt-3 pt-3 border-t border-slate-100">
            Update your resume with these skills · Re-scan to see your new score
          </p>
        </div>
      )}
    </div>
  )
}
