import { useQuery } from '@tanstack/react-query'

export default function App() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: async () => {
      const res = await fetch('/api/v1/health')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return (await res.json()) as { status: string }
    },
  })

  return (
    <main className="min-h-screen bg-slate-50 p-8 text-slate-900">
      <h1 className="text-2xl font-semibold">UK Wind Forecast Monitor</h1>
      <p className="mt-2 text-sm text-slate-600">
        API: {health.isPending ? 'checking...' : health.isError ? 'unreachable' : health.data.status}
      </p>
    </main>
  )
}
