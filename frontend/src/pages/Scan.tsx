import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { AxiosError } from 'axios'
import { ArrowRight, AlertCircle } from 'lucide-react'
import FileUpload from '../components/FileUpload'
import ScoreDisplay from '../components/ScoreDisplay'
import SkillPills from '../components/SkillPills'
import Layout from '../components/Layout'
import { scanResume } from '../api/match'
import { useAuth } from '../context/AuthContext'
import type { MatchResponse } from '../types/api'

const PHASES = [
  'Parsing your resume…',
  'Extracting skills and experience…',
  'Scoring semantic similarity…',
  'Generating recommendations…',
]

function SkeletonLoader() {
  const [phase, setPhase] = useState(0)

  useEffect(() => {
    const timings = [0, 700, 1600, 2600]
    const timeouts = timings.map((delay, i) =>
      setTimeout(() => setPhase(i), delay)
    )
    return () => timeouts.forEach(clearTimeout)
  }, [])

  return (
    <div className="space-y-4">
      <p className="text-sm font-medium text-brand transition-all duration-300">{PHASES[phase]}</p>

      {/* Score card skeleton */}
      <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-5">
        <div className="flex flex-col items-center gap-3">
          <div className="w-[130px] h-[130px] rounded-full skeleton" />
          <div className="h-4 w-28 rounded-full skeleton" />
          <div className="h-3 w-20 rounded-full skeleton" />
        </div>
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i}>
              <div className="flex justify-between mb-1.5">
                <div className="h-3 w-32 rounded skeleton" />
                <div className="h-3 w-8 rounded skeleton" />
              </div>
              <div className="h-1.5 rounded-full skeleton" />
            </div>
          ))}
        </div>
      </div>

      {/* Skills skeleton */}
      <div className="bg-white rounded-2xl border border-slate-200 p-5 space-y-3">
        <div className="h-4 w-24 rounded skeleton" />
        <div className="flex flex-wrap gap-2">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-7 w-20 rounded-full skeleton" />
          ))}
        </div>
        <div className="flex flex-wrap gap-2 pt-1">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-7 w-24 rounded-full skeleton" />
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Scan() {
  const { user } = useAuth()
  const [file, setFile] = useState<File | null>(null)
  const [jd, setJd] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<MatchResponse | null>(null)
  const [limitHit, setLimitHit] = useState(false)

  async function handleScan() {
    if (!file) { toast.error('Upload your resume PDF first'); return }
    if (jd.trim().length < 50) { toast.error('Job description must be at least 50 characters'); return }

    setLoading(true)
    setResult(null)
    setLimitHit(false)

    try {
      const data = await scanResume(file, jd.trim())
      setResult(data)
    } catch (err) {
      if (err instanceof AxiosError) {
        if (err.response?.status === 429) {
          setLimitHit(true)
        } else {
          toast.error(err.response?.data?.detail ?? 'Something went wrong')
        }
      } else {
        toast.error('Something went wrong')
      }
    } finally {
      setLoading(false)
    }
  }

  const canScan = !!file && jd.trim().length >= 50 && !loading

  return (
    <Layout>
      <div className="max-w-5xl mx-auto px-8 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900 font-display">Scan Resume</h1>
          {user && (
            <p className="text-sm text-slate-500 mt-1">
              {user.plan === 'pro'
                ? 'Pro plan — unlimited scans'
                : `${user.scan_count} scans used this week · ${user.plan} plan`}
            </p>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input panel */}
          <div className="space-y-5">
            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Resume (PDF)</label>
              <FileUpload file={file} onChange={setFile} />
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-2">Job Description</label>
              <textarea
                value={jd}
                onChange={(e) => setJd(e.target.value)}
                rows={12}
                placeholder="Paste the full job description here…"
                className="w-full px-3 py-2.5 rounded-xl border border-slate-200 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand/40 focus:border-brand transition-colors"
              />
              <p className="text-xs text-slate-400 mt-1">{jd.trim().length} / 50 min characters</p>
            </div>

            {limitHit && (
              <div className="flex items-start gap-3 p-4 rounded-xl bg-amber-50 border border-amber-200">
                <AlertCircle className="text-amber-500 shrink-0 mt-0.5" size={18} />
                <div>
                  <p className="text-sm font-semibold text-amber-800">Weekly scan limit reached</p>
                  <p className="text-sm text-amber-700 mt-0.5">
                    Upgrade to Starter or Pro to keep scanning.{' '}
                    <Link to="/billing" className="underline font-medium">View plans →</Link>
                  </p>
                </div>
              </div>
            )}

            <button
              onClick={handleScan}
              disabled={!canScan}
              className="flex items-center justify-center gap-2 w-full py-3 rounded-xl bg-brand text-white font-semibold text-sm hover:bg-brand-dark transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {loading ? (
                <span className="text-white/80">Analyzing…</span>
              ) : (
                <>Analyze Match <ArrowRight size={16} /></>
              )}
            </button>
          </div>

          {/* Results panel */}
          <div className="space-y-4">
            {loading && <SkeletonLoader />}

            {result && !loading && (
              <>
                <ScoreDisplay
                  score={result.overall_score}
                  breakdown={result.breakdown}
                  processingMs={result.processing_time_ms}
                />
                <SkillPills
                  matched={result.breakdown.skill_match.matched}
                  missing={result.breakdown.skill_match.missing}
                  score={result.overall_score}
                />
                {result.recommendations.length > 0 && (
                  <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-5">
                    <h3 className="font-semibold text-slate-800 mb-3 font-display">Next Steps</h3>
                    <ul className="space-y-2.5">
                      {result.recommendations.map((r, i) => (
                        <li key={i} className="flex items-start gap-2.5 text-sm text-slate-600">
                          <span className="text-brand font-bold mt-0.5 shrink-0">→</span>
                          {r}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}

            {!result && !loading && (
              <div className="flex flex-col items-center justify-center h-64 rounded-2xl border border-dashed border-slate-200 text-slate-400 text-sm text-center gap-2">
                <p className="font-medium text-slate-500">Your results will appear here</p>
                <p className="text-xs text-slate-300">Upload a PDF and paste a job description to get started</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}
