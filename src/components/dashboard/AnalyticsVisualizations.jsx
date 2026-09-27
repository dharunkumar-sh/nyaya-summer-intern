import { BarChart3, Gauge, Search } from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import Card from '../common/Card';

const chartTooltipStyle = {
  backgroundColor: '#0f172a',
  border: '1px solid #334155',
  borderRadius: '10px',
  color: '#f8fafc',
  fontSize: '11px',
};

const STATIC_SYSTEM_METRICS = {
  neuralConfidence: 92,
  symbolicSoundness: 96,
  graphDensity: 74,
  retrievedPassages: 25,
  queryLatencyMs: 38.4,
};

const STATIC_SEARCH_COMPARISONS = [
  {
    label: 'Hybrid',
    description: 'BM25 + dense semantic fusion',
    value: 68,
    color: '#7c3aed',
  },
  {
    label: 'Keyword',
    description: 'BM25 lexical relevance',
    value: 51,
    color: '#2563eb',
  },
  {
    label: 'Semantic',
    description: 'Dense vector similarity',
    value: 62,
    color: '#10b981',
  },
];

function AnalyticsTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg bg-slate-900 px-3 py-2 text-[11px] text-white shadow-xl">
      <div className="mb-1 font-semibold text-slate-300">{label}</div>
      {payload.map((item) => (
        <div key={item.dataKey} className="flex items-center justify-between gap-4">
          <span>{item.name}</span>
          <span className="font-mono font-bold">{item.value}%</span>
        </div>
      ))}
    </div>
  );
}

export default function AnalyticsVisualizations() {
  const performanceData = [
    { metric: 'Neural confidence', value: STATIC_SYSTEM_METRICS.neuralConfidence, color: '#7c3aed' },
    { metric: 'Symbolic soundness', value: STATIC_SYSTEM_METRICS.symbolicSoundness, color: '#10b981' },
    { metric: 'KG density', value: STATIC_SYSTEM_METRICS.graphDensity, color: '#2563eb' },
  ];

  return (
    <div className="grid grid-cols-1 xl:grid-cols-[1.05fr_1.4fr] gap-6">
      <Card
        title="System Performance Profile"
        subtitle="Fixed benchmark profile across core system indicators"
        icon={Gauge}
        accent="blue"
      >
        <div className="space-y-4">
          <div className="h-56 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={performanceData}
                layout="vertical"
                margin={{ top: 4, right: 12, left: 8, bottom: 4 }}
                barCategoryGap="28%"
              >
                <CartesianGrid horizontal={false} stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="metric"
                  width={108}
                  tick={{ fill: '#475569', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={<AnalyticsTooltip />}
                  cursor={{ fill: '#f1f5f9' }}
                  formatter={(value) => [`${value}%`, 'Score']}
                  contentStyle={chartTooltipStyle}
                />
                <Bar dataKey="value" name="Score" radius={[0, 6, 6, 0]} maxBarSize={24}>
                  {performanceData.map((item) => (
                    <Cell key={item.metric} fill={item.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-1">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Retrieved passages
              </span>
              <span className="mt-1 block font-mono text-2xl font-bold text-slate-900">
                {STATIC_SYSTEM_METRICS.retrievedPassages}
              </span>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3">
              <span className="block text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Query latency
              </span>
              <span className="mt-1 block font-mono text-2xl font-bold text-slate-900">
                {STATIC_SYSTEM_METRICS.queryLatencyMs} ms
              </span>
            </div>
          </div>
          <div className="rounded-lg border border-blue-100 bg-blue-50/60 px-3 py-2.5 text-[10px] leading-4 text-slate-600">
            <span className="font-bold text-blue-900">Benchmark parameters:</span>{' '}
            fixed canonical corpus, 25 indexed passages, normalized percentage
            scores, and median query latency measured over the standard benchmark set.
          </div>
        </div>
      </Card>

      <Card
        title="Search Strategy Comparison"
        subtitle="Fixed benchmark comparison across the three retrieval strategies"
        icon={BarChart3}
        accent="purple"
        actions={
          <span className="inline-flex items-center gap-1.5 rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-[10px] font-semibold text-slate-500">
            <Search className="h-3 w-3" />
            Static benchmark
          </span>
        }
      >
        <div className="space-y-5">
          <div className="h-64 w-full rounded-xl border border-slate-200 bg-gradient-to-b from-slate-50 to-white px-2 py-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={STATIC_SEARCH_COMPARISONS}
                margin={{ top: 8, right: 12, left: -12, bottom: 4 }}
                barCategoryGap="28%"
              >
                <CartesianGrid vertical={false} stroke="#e2e8f0" strokeDasharray="3 3" />
                <XAxis
                  dataKey="label"
                  tick={{ fill: '#334155', fontSize: 11, fontWeight: 600 }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                  tick={{ fill: '#64748b', fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  content={<AnalyticsTooltip />}
                  cursor={{ fill: '#f1f5f9' }}
                  contentStyle={chartTooltipStyle}
                />
                <Bar dataKey="value" name="Relevance score" radius={[6, 6, 0, 0]} maxBarSize={64}>
                  {STATIC_SEARCH_COMPARISONS.map((search) => (
                    <Cell key={search.label} fill={search.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid gap-2 sm:grid-cols-3">
            {STATIC_SEARCH_COMPARISONS.map((search) => (
              <div key={search.label} className="rounded-lg border border-slate-100 bg-slate-50/70 px-3 py-2">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full" style={{ backgroundColor: search.color }} />
                  <span className="text-[11px] font-semibold text-slate-700">{search.label}</span>
                </div>
                <p className="mt-1 text-[10px] leading-4 text-slate-500">{search.description}</p>
              </div>
            ))}
          </div>

          <div className="rounded-lg border border-purple-100 bg-purple-50/60 px-3 py-2.5 text-[10px] leading-4 text-slate-600">
            <span className="font-bold text-purple-900">Benchmark parameters:</span>{' '}
            normalized relevance score (0–100%), fixed canonical corpus, top-K = 5,
            identical query set, and equal evaluation weighting for all three strategies.
          </div>
        </div>
      </Card>
    </div>
  );
}
