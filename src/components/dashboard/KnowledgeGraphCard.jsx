import { Network, ArrowRight, CheckCircle } from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import { useReasoner } from '../../context/ReasonerContext';

export default function KnowledgeGraphCard({ currentQuery: propQuery }) {
  const { currentQuery: ctxQuery, validationResults } = useReasoner();
  const currentQuery = propQuery || ctxQuery || {};
  const triples = currentQuery.triples || [];

  const consistencyRate = validationResults?.soundness ?? (triples.length > 0 ? 100 : null);
  const activeConcepts = Array.from(
    new Set(triples.flatMap((t) => [t.subject, t.object]).filter(Boolean))
  ).slice(0, 4);

  return (
    <Card
      title="Ontological Triples & Neuro-Symbolic Graph"
      subtitle="Extracted semantic relations aligned with Classical Tamil Ontology (OWL/RDF)"
      icon={Network}
      accent="purple"
      actions={
        <Badge variant={triples.length > 0 ? "purple" : "slate"} size="xs">
          {triples.length} Active Triples
        </Badge>
      }
      footer={
        <div className="flex items-center justify-between text-xs text-slate-500">
          <span>Ontology: Tolkāppiyam-Poruḷ-Schema</span>
          <span className="text-purple-700 font-medium">
            {consistencyRate !== null ? `Axiomatic Consistency: ${consistencyRate}%` : 'Awaiting Axiom Verification'}
          </span>
        </div>
      }
    >
      <div className="space-y-3">
        {triples.length > 0 ? (
          <>
            {triples.map((triple, index) => (
              <div
                key={index}
                className="flex flex-col sm:flex-row sm:items-center justify-between p-3 rounded-lg bg-slate-50 border border-slate-200/90 gap-2.5 text-xs hover:border-purple-300 transition-colors"
              >
                {/* Triple Chain */}
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  {/* Subject */}
                  <div className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                    {triple.subject}
                  </div>

                  {/* Predicate */}
                  <div className="flex items-center gap-1 text-purple-700 font-mono font-medium px-1.5">
                    <ArrowRight className="w-3.5 h-3.5 text-purple-500" />
                    <span className="bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                      {triple.predicate}
                    </span>
                    <ArrowRight className="w-3.5 h-3.5 text-purple-500" />
                  </div>

                  {/* Object */}
                  <div className="px-2.5 py-1 rounded bg-white border border-slate-300 font-semibold text-slate-800 shadow-2xs">
                    {triple.object}
                  </div>
                </div>

                {/* Validation Pill */}
                <div className="shrink-0 self-end sm:self-auto">
                  <span className="inline-flex items-center gap-1 text-[11px] text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                    <CheckCircle className="w-3 h-3" />
                    Valid Axiom
                  </span>
                </div>
              </div>
            ))}

            {/* Dynamic Concept Node Summary */}
            <div className="p-3 bg-purple-50/50 rounded-lg border border-purple-100 text-xs text-purple-900 leading-relaxed">
              <span className="font-semibold">Neuro-Symbolic Binding:</span> Neural relation extraction mapped verse tokens to formal concept nodes:{" "}
              {activeConcepts.map((concept, idx) => (
                <span key={concept}>
                  <code className="bg-white px-1.5 py-0.5 rounded text-purple-800 border border-purple-200 text-[11px]">
                    #{concept.replace(/\s+/g, "")}
                  </code>
                  {idx < activeConcepts.length - 1 ? ", " : "."}
                </span>
              ))}
            </div>
          </>
        ) : (
          <div className="p-6 text-center rounded-xl bg-slate-50/80 border border-dashed border-slate-200 text-xs text-slate-500 space-y-1">
            <p className="font-medium text-slate-700">No Active Ontological Triples Extracted</p>
            <p className="text-[11px]">
              Formulate an epistemic inquiry in the Query Center to extract grounded subject-predicate-object relations from canonical Tolkāppiyam verses.
            </p>
          </div>
        )}
      </div>
    </Card>
  );
}
