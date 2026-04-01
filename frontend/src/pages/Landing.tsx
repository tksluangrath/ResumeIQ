import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Zap, BarChart2, Lightbulb, CheckCircle, Target, ArrowRight, Download } from 'lucide-react'

function MiniBar({ label, value, delay }: { label: string; value: number; delay: number }) {
  const [width, setWidth] = useState(0)
  useEffect(() => {
    const t = setTimeout(() => setWidth(value), delay)
    return () => clearTimeout(t)
  }, [value, delay])
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span className="text-slate-500">{label}</span>
        <span className="font-medium text-slate-700">{value}%</span>
      </div>
      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className="h-full rounded-full bg-brand"
          style={{ width: `${width}%`, transition: 'width 700ms cubic-bezier(0.33, 1, 0.68, 1)' }}
        />
      </div>
    </div>
  )
}

function HeroScoreMock() {
  const pct = 78
  const circumference = 2 * Math.PI * 40
  const [displayPct, setDisplayPct] = useState(0)
  const [dashOffset, setDashOffset] = useState(circumference)
  const rafRef = useRef<number | null>(null)

  useEffect(() => {
    const delay = setTimeout(() => {
      let startTime: number | null = null
      const duration = 1400
      function animate(ts: number) {
        if (!startTime) startTime = ts
        const progress = Math.min((ts - startTime) / duration, 1)
        const eased = 1 - Math.pow(1 - progress, 3)
        setDisplayPct(Math.round(eased * pct))
        setDashOffset(circumference - (eased * pct / 100) * circumference)
        if (progress < 1) rafRef.current = requestAnimationFrame(animate)
      }
      rafRef.current = requestAnimationFrame(animate)
    }, 600)
    return () => {
      clearTimeout(delay)
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
    }
  }, [circumference])

  return (
    <div className="relative bg-white/90 backdrop-blur-md rounded-3xl border border-white/70 p-6 shadow-card-md">
      <div className="flex items-center justify-between mb-5">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide font-medium">Match Analysis</p>
          <p className="text-sm font-semibold text-slate-700 mt-0.5">Senior Product Designer · Airbnb</p>
        </div>
        <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-brand/10 text-brand">Live Demo</span>
      </div>

      <div className="flex items-center gap-5 mb-5">
        <svg width="96" height="96" viewBox="0 0 100 100" className="shrink-0">
          <circle cx="50" cy="50" r="40" fill="none" stroke="#f1f5f9" strokeWidth="10" />
          <circle
            cx="50" cy="50" r="40" fill="none"
            stroke="#06b6d4"
            strokeWidth="10"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            transform="rotate(-90 50 50)"
          />
          <text x="50" y="47" textAnchor="middle" dominantBaseline="central" fontSize="20" fontWeight="700" fill="#0f172a">
            {displayPct}
          </text>
          <text x="50" y="62" textAnchor="middle" dominantBaseline="central" fontSize="7" fill="#94a3b8">
            / 100
          </text>
        </svg>
        <div className="flex-1 space-y-3">
          <MiniBar label="Semantic" value={82} delay={800} />
          <MiniBar label="Skill Match" value={74} delay={950} />
          <MiniBar label="Title Fit" value={68} delay={1100} />
        </div>
      </div>

      <div className="space-y-2 pt-4 border-t border-slate-100">
        <div className="flex flex-wrap gap-1.5">
          {['Figma', 'Design Systems', 'Prototyping'].map(s => (
            <span key={s} className="px-2 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">{s}</span>
          ))}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {['+ User Research', '+ A/B Testing'].map(s => (
            <span key={s} className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200">{s}</span>
          ))}
        </div>
      </div>
    </div>
  )
}

const steps = [
  { n: '01', title: 'Upload Your Resume', desc: 'Drag and drop your PDF. We parse it with AI to extract your skills, titles, and experience.' },
  { n: '02', title: 'Paste Any Job Description', desc: 'Copy a job posting from anywhere — LinkedIn, Indeed, company sites. No formatting needed.' },
  { n: '03', title: 'Get Your Match Score', desc: 'See your semantic match score, skill gaps, and AI-powered next steps. All in under 3 seconds.' },
]

const features = [
  { icon: BarChart2, title: 'Instant Match Score', desc: 'Our AI uses sentence-transformer embeddings — not keyword counting — to score your resume against any job description with real semantic understanding.', wide: true },
  { icon: Target, title: 'Skill Gap Analysis', desc: 'See exactly which skills the employer wants that are missing from your resume, with a clear path to improve your score.', wide: false },
  { icon: Lightbulb, title: 'AI Suggestions', desc: 'LLM-powered bullet rewrites and keyword recommendations tailored specifically to the role you are targeting.', wide: false },
  { icon: Download, title: 'Resume Optimizer', desc: 'Export an improved resume with LaTeX-quality formatting — polished and ready to send to recruiters.', wide: false },
]

const plans = [
  {
    name: 'Free',
    price: '$0',
    desc: 'Get started today',
    scans: '5 scans / week',
    features: ['Match score', 'Skill breakdown', 'Recommendations'],
    cta: 'Get Started',
    href: '/register',
    highlight: false,
  },
  {
    name: 'Starter',
    price: '$9',
    desc: 'per month',
    scans: '25 scans / week',
    features: ['Everything in Free', 'LaTeX resume export', 'Scan history'],
    cta: 'Start Free Trial',
    href: '/register',
    highlight: true,
  },
  {
    name: 'Pro',
    price: '$19',
    desc: 'per month',
    scans: 'Unlimited scans',
    features: ['Everything in Starter', 'AI suggestions (LLM)', 'Priority support'],
    cta: 'Go Pro',
    href: '/register',
    highlight: false,
  },
]

export default function Landing() {
  return (
    <div className="min-h-screen bg-white">
      {/* Nav */}
      <header className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-100">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Zap className="text-brand" size={20} strokeWidth={2.5} />
            <span className="font-bold text-slate-900 text-lg tracking-tight font-display">ResumeIQ</span>
          </div>
          <div className="flex items-center gap-3">
            <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors">
              Log In
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 rounded-lg bg-brand text-white text-sm font-semibold hover:bg-brand-dark transition-colors shadow-sm"
            >
              Get Started Free
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden bg-white">
        {/* Aurora blobs */}
        <div className="absolute inset-0 pointer-events-none" aria-hidden="true">
          <div className="absolute top-[-15%] left-[-8%] w-[560px] h-[560px] rounded-full opacity-25"
            style={{ background: 'radial-gradient(circle, #06b6d4 0%, transparent 70%)', filter: 'blur(80px)' }} />
          <div className="absolute top-[-5%] right-[-5%] w-[480px] h-[480px] rounded-full opacity-15"
            style={{ background: 'radial-gradient(circle, #7c3aed 0%, transparent 70%)', filter: 'blur(80px)' }} />
          <div className="absolute bottom-[-15%] left-[35%] w-[380px] h-[380px] rounded-full opacity-15"
            style={{ background: 'radial-gradient(circle, #0e7490 0%, transparent 70%)', filter: 'blur(80px)' }} />
        </div>

        <div className="relative max-w-6xl mx-auto px-6 pt-20 pb-28">
          <div className="grid grid-cols-1 lg:grid-cols-[55fr_45fr] gap-12 items-center">
            {/* Left */}
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 text-brand text-xs font-semibold uppercase tracking-wider mb-6">
                <Zap size={11} strokeWidth={2.5} />
                AI-Powered Resume Matching
              </div>
              <h1 className="font-display text-5xl lg:text-[3.75rem] font-extrabold text-slate-900 leading-[1.08] tracking-tight mb-6">
                Know your match<br />
                score <span className="text-brand">before</span><br />
                you apply.
              </h1>
              <p className="text-xl text-slate-500 leading-relaxed mb-8 max-w-lg">
                Upload your resume and paste any job description. ResumeIQ scores the match, identifies skill gaps, and suggests improvements — in seconds.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 mb-5">
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl bg-brand text-white text-base font-bold hover:bg-brand-dark transition-colors shadow-glow-sm"
                >
                  Scan My Resume Free
                  <ArrowRight size={17} />
                </Link>
                <a
                  href="#how-it-works"
                  className="inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-xl border border-slate-200 text-slate-700 text-base font-semibold hover:bg-slate-50 transition-colors"
                >
                  See how it works
                </a>
              </div>
              <p className="text-sm text-slate-400">
                No credit card required &nbsp;·&nbsp; 5 free scans / week &nbsp;·&nbsp; Results in &lt; 3 seconds
              </p>
            </div>

            {/* Right — animated score mock */}
            <div className="hidden lg:block">
              <HeroScoreMock />
            </div>
          </div>
        </div>
      </section>

      {/* Stats bar */}
      <div className="border-y border-slate-100 bg-slate-50/60">
        <div className="max-w-5xl mx-auto px-6 py-5">
          <div className="flex flex-wrap justify-center gap-x-10 gap-y-3 text-sm text-slate-500">
            {[
              { value: '12,400+', label: 'resumes scanned' },
              { value: '4,200+', label: 'job seekers helped' },
              { value: '< 3s', label: 'average response time' },
              { value: '5 free', label: 'scans every week' },
            ].map(({ value, label }) => (
              <div key={label} className="flex items-center gap-2">
                <span className="font-bold text-slate-900">{value}</span>
                <span>{label}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* How it works */}
      <section id="how-it-works" className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="font-display text-3xl font-bold text-slate-900 text-center mb-2">How it works</h2>
          <p className="text-slate-500 text-center mb-12">Three steps. Under 30 seconds.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {steps.map(({ n, title, desc }) => (
              <div
                key={n}
                className="relative bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:-translate-y-0.5 hover:shadow-card-md transition-all duration-200"
              >
                <span className="absolute top-4 right-5 text-4xl font-extrabold text-slate-100 select-none font-display">{n}</span>
                <p className="text-xs font-semibold text-brand uppercase tracking-wider mb-2">Step {n}</p>
                <h3 className="font-semibold text-slate-900 mb-2 font-display">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features bento */}
      <section className="bg-surface py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="font-display text-3xl font-bold text-slate-900 text-center mb-2">Everything you need to land the job</h2>
          <p className="text-slate-500 text-center mb-12">Built for job seekers who want data, not guesswork.</p>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {/* Wide feature */}
            <div className="lg:col-span-2 bg-white rounded-2xl p-7 border border-slate-200 shadow-card hover:-translate-y-0.5 hover:shadow-card-md transition-all duration-200 flex gap-6 items-start">
              <div className="w-12 h-12 rounded-xl bg-brand/10 flex items-center justify-center shrink-0 mt-0.5">
                <BarChart2 className="text-brand" size={22} strokeWidth={1.5} />
              </div>
              <div>
                <h3 className="font-semibold text-slate-900 text-lg mb-2 font-display">Instant Match Score</h3>
                <p className="text-slate-500 leading-relaxed">
                  Our AI uses sentence-transformer embeddings — not keyword counting — to score your resume against any job description. You get a semantic match score that reflects how well your experience aligns to what the employer actually needs.
                </p>
              </div>
            </div>
            {/* Regular feature cards */}
            {features.slice(1).map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-white rounded-2xl p-6 border border-slate-200 shadow-card hover:-translate-y-0.5 hover:shadow-card-md transition-all duration-200">
                <div className="w-10 h-10 rounded-lg bg-brand/10 flex items-center justify-center mb-4">
                  <Icon className="text-brand" size={20} strokeWidth={1.5} />
                </div>
                <h3 className="font-semibold text-slate-900 mb-2 font-display">{title}</h3>
                <p className="text-sm text-slate-500 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="font-display text-3xl font-bold text-slate-900 text-center mb-2">Simple, transparent pricing</h2>
          <p className="text-slate-500 text-center mb-12">Start free. Upgrade when you're ready.</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.name}
                className={`rounded-2xl p-6 border transition-all ${
                  plan.highlight
                    ? 'border-brand bg-brand/5 ring-2 ring-brand shadow-card-md'
                    : 'border-slate-200 bg-white shadow-card'
                }`}
              >
                {plan.highlight && (
                  <span className="inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold bg-brand text-white mb-3">
                    Most Popular
                  </span>
                )}
                <p className="font-bold text-slate-900 text-lg font-display">{plan.name}</p>
                <div className="flex items-baseline gap-1 my-2">
                  <span className="text-4xl font-extrabold text-slate-900 font-display">{plan.price}</span>
                  <span className="text-slate-500 text-sm">{plan.desc}</span>
                </div>
                <p className="text-sm text-brand font-medium mb-4">{plan.scans}</p>
                <ul className="space-y-2 mb-6">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-center gap-2 text-sm text-slate-600">
                      <CheckCircle size={14} className="text-brand shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
                <Link
                  to={plan.href}
                  className={`block text-center py-2.5 rounded-lg text-sm font-semibold transition-colors ${
                    plan.highlight
                      ? 'bg-brand text-white hover:bg-brand-dark'
                      : 'bg-slate-100 text-slate-800 hover:bg-slate-200'
                  }`}
                >
                  {plan.cta}
                </Link>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-navy text-white">
        <div className="max-w-6xl mx-auto px-6 py-14">
          <div className="flex items-center gap-2 mb-10">
            <Zap className="text-brand" size={20} strokeWidth={2.5} />
            <span className="font-bold text-white text-lg tracking-tight font-display">ResumeIQ</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-10">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-white/50 mb-4">Company</p>
              <ul className="space-y-2.5 text-sm">
                <li><span className="text-white/30 cursor-default">About</span></li>
                <li><span className="text-white/30 cursor-default">Contact</span></li>
                <li><span className="text-white/30 cursor-default">Privacy Policy</span></li>
                <li><span className="text-white/30 cursor-default">Terms of Service</span></li>
              </ul>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-white/50 mb-4">Product</p>
              <ul className="space-y-2.5 text-sm">
                <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">Match Score</Link></li>
                <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">Skill Gap Analysis</Link></li>
                <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">AI Suggestions</Link></li>
                <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">Resume Optimizer</Link></li>
                <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">Scan History</Link></li>
              </ul>
            </div>
          </div>
        </div>
        <div className="border-t border-white/10">
          <div className="max-w-6xl mx-auto px-6 py-5">
            <p className="text-sm text-white/40">© {new Date().getFullYear()} ResumeIQ. All rights reserved.</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
