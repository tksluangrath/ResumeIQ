import { useQuery } from '@tanstack/react-query'
import { CheckCircle } from 'lucide-react'
import toast from 'react-hot-toast'
import Layout from '../components/Layout'
import { getBillingStatus, createCheckout, getPortal } from '../api/billing'
import { AxiosError } from 'axios'

const PLANS = [
  {
    id: 'starter' as const,
    name: 'Starter',
    price: '$9/mo',
    scans: '25 scans / week',
    features: ['Match score & breakdown', 'Skill gap analysis', 'LaTeX resume export', 'Scan history'],
  },
  {
    id: 'pro' as const,
    name: 'Pro',
    price: '$19/mo',
    scans: 'Unlimited scans',
    features: ['Everything in Starter', 'AI bullet rewrites (LLM)', 'Keyword injection', 'Career summary rewrite'],
  },
]

export default function Billing() {
  const { data, isLoading } = useQuery({
    queryKey: ['billing-status'],
    queryFn: getBillingStatus,
  })

  async function handleUpgrade(plan: 'starter' | 'pro') {
    try {
      const { checkout_url } = await createCheckout(
        plan,
        `${window.location.origin}/billing?success=1`,
        `${window.location.origin}/billing`,
      )
      window.location.href = checkout_url
    } catch (err) {
      const msg = err instanceof AxiosError ? err.response?.data?.detail : 'Could not start checkout'
      toast.error(msg ?? 'Could not start checkout')
    }
  }

  async function handlePortal() {
    try {
      const { portal_url } = await getPortal()
      window.location.href = portal_url
    } catch (err) {
      const msg = err instanceof AxiosError ? err.response?.data?.detail : 'Could not open portal'
      toast.error(msg ?? 'Could not open portal')
    }
  }

  const usagePercent = data
    ? data.scan_limit === null
      ? 0
      : Math.min(100, (data.scan_count / data.scan_limit) * 100)
    : 0

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-8 py-10">
        <h1 className="text-2xl font-bold text-slate-900 mb-8">Billing</h1>

        {isLoading && <div className="text-slate-400">Loading…</div>}

        {data && (
          <>
            {/* Current plan */}
            <div className="bg-white rounded-2xl border border-slate-200 p-6 mb-8">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm text-slate-500">Current plan</p>
                  <p className="text-lg font-bold text-slate-900 capitalize">{data.plan}</p>
                </div>
                {data.stripe_customer_id && (
                  <button
                    onClick={handlePortal}
                    className="text-sm text-brand hover:underline font-medium"
                  >
                    Manage subscription →
                  </button>
                )}
              </div>

              {data.scan_limit !== null && (
                <div>
                  <div className="flex justify-between text-sm text-slate-600 mb-1.5">
                    <span>Scans used this week</span>
                    <span>{data.scan_count} / {data.scan_limit}</span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full bg-brand transition-all"
                      style={{ width: `${usagePercent}%` }}
                    />
                  </div>
                </div>
              )}

              {data.scan_limit === null && (
                <p className="text-sm text-green-600 font-medium">Unlimited scans — {data.scan_count} used this week</p>
              )}
            </div>

            {/* Upgrade cards */}
            {data.plan !== 'pro' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {PLANS.filter((p) => p.id !== data.plan).map((plan) => (
                  <div key={plan.id} className="bg-white rounded-2xl border border-slate-200 p-6 flex flex-col">
                    <p className="font-bold text-slate-900 text-lg">{plan.name}</p>
                    <p className="text-2xl font-extrabold text-slate-900 mt-1 mb-0.5">{plan.price}</p>
                    <p className="text-sm text-brand font-medium mb-4">{plan.scans}</p>
                    <ul className="space-y-2 mb-6 flex-1">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-center gap-2 text-sm text-slate-600">
                          <CheckCircle size={14} className="text-brand shrink-0" />
                          {f}
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={() => handleUpgrade(plan.id)}
                      className="w-full py-2.5 rounded-lg bg-brand text-white text-sm font-semibold hover:bg-brand-dark transition-colors"
                    >
                      Upgrade to {plan.name}
                    </button>
                  </div>
                ))}
              </div>
            )}

            {data.plan === 'pro' && (
              <div className="text-center text-slate-400 py-8">
                <p className="font-medium text-slate-700">You're on the Pro plan</p>
                <p className="text-sm mt-1">Enjoying unlimited scans and all features.</p>
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  )
}
