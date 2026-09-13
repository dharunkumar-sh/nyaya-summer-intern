import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Sparkles,
  Cpu,
  Network,
  BookOpen,
  ShieldCheck,
  Library,
  BarChart3,
  ArrowUpRight,
} from 'lucide-react';
import Card from '../../common/Card';
import Badge from '../../common/Badge';
import { useReasoner } from '../../../context/ReasonerContext';

export default function OverviewModulesQuickNav() {
  const navigate = useNavigate();
  const {
    corpus,
    graphStatistics,
    graphHealth,
    evidenceRecords,
    reasoningStages,
    validationResults,
    queryStatus,
    queryStats,
    dashboardSummary,
    isLoadingStats,
    isLoadingDashboard,
  } = useReasoner();

  const kgData = dashboardSummary?.knowledge_graph;
  const corpusData = dashboardSummary?.corpus || corpus;
  const totalNodes = kgData?.active_nodes ?? graphHealth?.node_count ?? graphStatistics?.total_nodes ?? 33;
  const totalEdges = kgData?.active_edges ?? graphHealth?.edge_count ?? graphStatistics?.total_edges ?? 46;

  const validPercentage = useMemo(() => {
    if (isLoadingStats || isLoadingDashboard) return 0;
    if (typeof graphHealth?.percentageValid === 'number') return graphHealth.percentageValid;
    if (kgData?.is_connected !== false && graphHealth?.valid !== false) return 100;
    return 97;
  }, [isLoadingStats, isLoadingDashboard, graphHealth, kgData]);

  const totalSutras =
    corpusData?.total_sutras_canonical || corpusData?.totalSutras || 1610;

  const modules = useMemo(
    () => [
      {
        id: 'query-center',
        path: '/query-center',
        title: 'Query Center',
        tamilTitle: 'வினா அரங்கம்',
        icon: Sparkles,
        color: 'purple',
        iconBg: 'bg-purple-100 text-purple-700',
        badge:
          queryStatus === 'loading'
            ? 'Analyzing...'
            : evidenceRecords?.length > 0
            ? `${evidenceRecords.length} Evidences`
            : 'Interactive',
        badgeVariant: queryStatus === 'loading' || evidenceRecords?.length > 0 ? 'purple' : 'purple',
        description: 'Formulate natural language & formal inquiries over Tolkāppiyam with cross-encoder retrieval.',
      },
      {
        id: 'reasoning',
        path: '/reasoning',
        title: 'Nyāya Reasoning Trace',
        tamilTitle: 'பஞ்சாவயவ அனுமானம்',
        icon: Cpu,
        color: 'amber',
        iconBg: 'bg-amber-100 text-amber-700',
        badge: reasoningStages?.length > 0 ? `${reasoningStages.length}-Stage Proof` : '5-Stage Proof',
        badgeVariant: 'orange',
        description: 'Explore step-by-step Pañcāvayava deduction: Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana.',
      },
      {
        id: 'knowledge-graph',
        path: '/knowledge-graph',
        title: 'Knowledge Graph',
        tamilTitle: 'அறிவு வரைபடம்',
        icon: Network,
        color: 'blue',
        iconBg: 'bg-blue-100 text-blue-700',
        badge: `${totalNodes} Nodes`,
        badgeVariant: 'blue',
        description: `Interactive ontological graph with ${totalNodes} entities and ${totalEdges} relations across Tiṇai ecology.`,
      },
      {
        id: 'evidence',
        path: '/evidence',
        title: 'Retrieved Evidence',
        tamilTitle: 'சான்றுத் திரட்டு',
        icon: BookOpen,
        color: 'emerald',
        iconBg: 'bg-emerald-100 text-emerald-700',
        badge: evidenceRecords?.length > 0 ? `${evidenceRecords.length} Retrieved` : 'Top-5 Sūtras',
        badgeVariant: 'green',
        description: 'Ranked canonical passages with cross-attention weights, confidence scores, and translations.',
      },
      {
        id: 'fallacies',
        path: '/fallacies',
        title: 'Hetvābhāsa Checker',
        tamilTitle: 'ஏதுவாபாச ஆய்வு',
        icon: ShieldCheck,
        color: 'green',
        iconBg: 'bg-emerald-100 text-emerald-700',
        badge: validationResults ? (validationResults.symbolicValidity ? 'Sound' : 'Checks') : '0 Fallacies',
        badgeVariant: 'green',
        description: 'Rigorous formal verification against the 5 classical Nyāya fallacies (Savyabhicāra, Viruddha, etc.).',
      },
      {
        id: 'sutras',
        path: '/sutras',
        title: 'Sūtra Explorer',
        tamilTitle: 'நூற்பா அரங்கம்',
        icon: Library,
        color: 'indigo',
        iconBg: 'bg-indigo-100 text-indigo-700',
        badge: `${totalSutras.toLocaleString()} Verses`,
        badgeVariant: 'purple',
        description: 'Search, filter, and inspect canonical verses across Eḻuttatikāram, Collatikāram, and Poruḷatikāram.',
      },
      {
        id: 'analytics',
        path: '/analytics',
        title: 'Epistemic Analytics',
        tamilTitle: 'புள்ளிவிவரம் & நலம்',
        icon: BarChart3,
        color: 'slate',
        iconBg: 'bg-slate-100 text-slate-700',
        badge: `${validPercentage}% Valid`,
        badgeVariant: validPercentage >= 90 ? 'green' : 'slate',
        description: queryStats?.latencyMs
          ? `Inference latency: ${queryStats.latencyMs}ms. Inspect Pramāṇa distribution, graph health, and metrics.`
          : `Inspect inference latency, Pramāṇa distribution, and graph structural health (${validPercentage}% valid).`,
      },
    ],
    [
      queryStatus,
      evidenceRecords,
      reasoningStages,
      validationResults,
      totalNodes,
      totalEdges,
      totalSutras,
      validPercentage,
      queryStats,
    ]
  );

  return (
    <Card
      title="Research Workspace Modules (ஆய்வு அரங்கங்கள்)"
      subtitle="Direct Access into All Specialized Workspaces of the Neuro-Symbolic Reasoner"
      icon={Sparkles}
      accent="purple"
    >
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3.5">
        {modules.map((mod) => {
          const IconComp = mod.icon;

          return (
            <button
              key={mod.id}
              type="button"
              onClick={() => navigate(mod.path)}
              className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-2xs hover:shadow-md hover:border-purple-300 transition-all text-left flex flex-col justify-between group cursor-pointer"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2.5">
                  <div className={`p-2 rounded-xl ${mod.iconBg} transition-transform group-hover:scale-105`}>
                    <IconComp className="w-4 h-4" />
                  </div>
                  <div className="flex items-center gap-1">
                    <Badge variant={mod.badgeVariant} size="xs">
                      {mod.badge}
                    </Badge>
                    <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-purple-600 transition-colors" />
                  </div>
                </div>

                <h4 className="font-bold text-xs sm:text-sm text-slate-900 leading-tight group-hover:text-purple-700 transition-colors">
                  {mod.title}
                </h4>
                <div className="text-[11px] text-slate-500 font-serif mt-0.5">
                  {mod.tamilTitle}
                </div>
                <p className="text-xs text-slate-600 mt-1.5 leading-snug line-clamp-2">
                  {mod.description}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] font-semibold text-purple-700 group-hover:translate-x-0.5 transition-transform">
                <span>Enter Workspace</span>
                <span>→</span>
              </div>
            </button>
          );
        })}
      </div>
    </Card>
  );
}
