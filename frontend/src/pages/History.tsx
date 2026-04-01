import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import Layout from '../components/Layout'
import { getHistory } from '../api/history'

function scoreColor(score: number) {
  const pct = score * 100
  if (pct >= 80) return 'text-green-600 bg-green-50'
  if (pct >= 65) return 'text-sky-600 bg-sky-50'
  if (pct >= 40) return 'text-amber-600 bg-amber-50'
  return 'text-red-600 bg-red-50'
}

export default function History() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['history', page],
    queryFn: () => getHistory(page, 20),
  })

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-8 py-10">
        <h1 className="text-2xl font-bold text-slate-900 mb-8">Scan History</h1>

        {isLoading && (
          <div className="text-center text-slate-400 py-16">Loading…</div>
        )}

        {data && data.items.length === 0 && (
          <div className="text-center text-slate-400 py-16">
            <p>No scans yet.</p>
            <p className="text-sm mt-1">Run your first scan to see results here.</p>
          </div>
        )}

        {data && data.items.length > 0 && (
          <>
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50">
                    <th className="text-left px-5 py-3 font-semibold text-slate-600">Date</th>
                    <th className="text-left px-5 py-3 font-semibold text-slate-600">Job</th>
                    <th className="text-left px-5 py-3 font-semibold text-slate-600">Type</th>
                    <th className="text-left px-5 py-3 font-semibold text-slate-600">Score</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((scan, i) => (
                    <tr
                      key={scan.id}
                      className={`border-b border-slate-50 hover:bg-slate-50 transition-colors ${
                        i === data.items.length - 1 ? 'border-b-0' : ''
                      }`}
                    >
                      <td className="px-5 py-3.5 text-slate-500 whitespace-nowrap">
                        {new Date(scan.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-5 py-3.5 text-slate-700 max-w-xs truncate">
                        {scan.job_snippet}
                      </td>
                      <td className="px-5 py-3.5">
                        <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 capitalize">
                          {scan.endpoint}
                        </span>
                      </td>
                      <td className="px-5 py-3.5">
                        <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${scoreColor(scan.overall_score)}`}>
                          {Math.round(scan.overall_score * 100)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-slate-500">
                {data.total} total scan{data.total !== 1 ? 's' : ''}
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={16} />
                </button>
                <span className="text-sm text-slate-600 px-2">Page {page}</span>
                <button
                  onClick={() => setPage((p) => p + 1)}
                  disabled={!data.has_next}
                  className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  )
}
