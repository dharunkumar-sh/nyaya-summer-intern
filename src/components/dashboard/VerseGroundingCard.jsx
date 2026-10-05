import { useState } from 'react';
import {
  BookOpen,
  Copy,
  Check,
  Languages,
  Sparkles,
  Quote,
  Network,
  ExternalLink,
} from 'lucide-react';
import Card from '../common/Card';
import Badge from '../common/Badge';
import Button from '../common/Button';
import { useReasoner } from '../../context/ReasonerContext';

export default function VerseGroundingCard({ currentQuery: propQuery }) {
  const reasoner = useReasoner();
  const currentQuery = propQuery || reasoner.currentQuery;
  const [copied, setCopied] = useState(false);

  const stages = reasoner.reasoningStages || [];
  const currentStage = stages[reasoner.selectedStageIndex] || null;
  const activeLinkedEvId = currentStage?.linkedEvidenceId;

  const activeEvidence =
    (activeLinkedEvId && reasoner.evidenceRecords?.find(
      (e) => e.id === activeLinkedEvId || e.code === activeLinkedEvId || e.passageId === activeLinkedEvId
    )) ||
    (reasoner.selectedEvidenceId && reasoner.evidenceRecords?.find(
      (e) => e.id === reasoner.selectedEvidenceId || e.code === reasoner.selectedEvidenceId || e.passageId === reasoner.selectedEvidenceId
    )) ||
    reasoner.evidenceRecords?.[0] ||
    null;

  const verseId = activeEvidence?.reference || activeEvidence?.code || activeEvidence?.id || currentQuery?.verseId || 'Tolkāppiyam';
  const corpusName = activeEvidence?.work || currentQuery?.corpus || 'Tolkāppiyam (தொல்காப்பியம்)';
  const sectionName = activeEvidence?.section || currentQuery?.domain || 'Akattiṇaiyiyal';
  const tamilText = activeEvidence?.tamilText || activeEvidence?.text || currentQuery?.tamilText || '';
  const transliteration = activeEvidence?.transliteration || currentQuery?.transliteration || '';
  const translation = activeEvidence?.translation || currentQuery?.translation || '';
  const entities = activeEvidence?.entities || [];
  const concepts = activeEvidence?.concepts || [];

  const handleCopy = () => {
    if (!tamilText) return;
    navigator.clipboard?.writeText(
      `${tamilText}\n\n${transliteration ? `${transliteration}\n\n` : ''}${translation}`
    );
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleFocusInGraph = () => {
    const targetId = activeEvidence?.passageId || activeEvidence?.id || activeLinkedEvId;
    if (targetId && reasoner.setSelectedGraphNodeId) {
      reasoner.setSelectedGraphNodeId(targetId);
    }
  };

  if (!tamilText) {
    return (
      <Card
        title="Textual Source Grounding"
        subtitle="Canonical Tolkāppiyam Verse"
        icon={BookOpen}
        accent="blue"
      >
        <div className="text-center py-10 px-4 space-y-2 text-slate-500">
          <BookOpen className="w-8 h-8 text-blue-500 mx-auto opacity-70" />
          <p className="text-xs font-medium text-slate-700">No Verse Grounding Selected</p>
          <p className="text-[11px] text-slate-400">
            Execute an inquiry or select a reasoning stage to inspect the underlying canonical verse.
          </p>
        </div>
      </Card>
    );
  }

  return (
    <Card
      title={`Textual Source Grounding: ${verseId}`}
      subtitle={`${corpusName}${sectionName ? ` • ${sectionName}` : ''}`}
      icon={BookOpen}
      accent="blue"
      actions={
        <div className="flex items-center gap-2">
          {activeEvidence?.code && (
            <Badge variant="purple" size="xs">
              {activeEvidence.code}
            </Badge>
          )}
          {activeEvidence?.confidenceFormatted && (
            <Badge variant="green" size="xs">
              {activeEvidence.confidenceFormatted}
            </Badge>
          )}
          <Button
            variant="ghost"
            size="xs"
            onClick={handleCopy}
            icon={copied ? Check : Copy}
            className="text-slate-500 hover:text-slate-800"
            title="Copy verse text"
          >
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        <div className="relative p-4 sm:p-5 rounded-xl bg-gradient-to-r from-blue-50/60 via-indigo-50/40 to-purple-50/30 border border-blue-200/70">
          <Quote className="absolute top-3 right-3 w-8 h-8 text-blue-200/60 pointer-events-none" />
          <div className="text-xs font-semibold text-blue-900/80 uppercase tracking-wider mb-2 flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-blue-600" />
              <span>மூலப் பாசுரம் / சூத்திரம் (Original Canonical Sūtra)</span>
            </div>
            {currentStage && (
              <span className="font-mono text-[10px] text-purple-700 bg-purple-100/70 px-2 py-0.5 rounded border border-purple-200">
                Grounds Stage {currentStage.stageNumber}: {currentStage.sanskritName}
              </span>
            )}
          </div>
          <p className="tamil-font text-lg sm:text-xl leading-relaxed text-slate-900 font-semibold whitespace-pre-line tracking-wide">
            {tamilText}
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {transliteration ? (
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Languages className="w-3.5 h-3.5 text-purple-600" />
                Scholarly Transliteration (ISO 15919)
              </div>
              <p className="text-xs font-mono text-slate-800 whitespace-pre-line leading-relaxed italic">
                {transliteration}
              </p>
            </div>
          ) : (
            <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80">
              <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                Epistemic Metadata
              </div>
              <p className="text-xs text-slate-600 leading-relaxed">
                Retrieved via {activeEvidence?.retrievalMethod || 'Hybrid RAG'}. Corroborated with Canonical Tolkāppiyam Ontological Knowledge Base.
              </p>
            </div>
          )}

          <div className="p-3.5 rounded-lg bg-slate-50 border border-slate-200/80">
            <div className="text-[11px] font-bold text-slate-500 uppercase tracking-wider mb-1 flex items-center gap-1">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Scholarly English Translation
            </div>
            <p className="text-xs text-slate-700 leading-relaxed">
              {translation ? `"${translation}"` : 'Translation pending lexical alignment.'}
            </p>
          </div>
        </div>

        {(entities.length > 0 || concepts.length > 0) && (
          <div>
            <div className="text-xs font-semibold text-slate-700 mb-2 flex items-center justify-between">
              <span>Ontological Entities & Concepts Grounded in Verse:</span>
              <button
                type="button"
                onClick={handleFocusInGraph}
                className="inline-flex items-center gap-1 text-[11px] text-blue-700 hover:text-blue-900 font-semibold cursor-pointer"
                title="Focus this node in Knowledge Graph"
              >
                <Network className="w-3 h-3" />
                <span>Highlight in Knowledge Graph</span>
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {entities.map((ent, idx) => {
                const name = typeof ent === 'string' ? ent : (ent.name || ent.label || 'Entity');
                const cat = typeof ent === 'object' && (ent.category || ent.type) ? ` (${ent.category || ent.type})` : '';
                return (
                  <span
                    key={`ent-${idx}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-purple-50 text-purple-800 border border-purple-200 text-xs font-medium"
                  >
                    <strong className="font-semibold">{name}</strong>
                    {cat && <span className="text-purple-600 text-[10px]">{cat}</span>}
                  </span>
                );
              })}
              {concepts.map((concept, idx) => {
                const name = typeof concept === 'string' ? concept : (concept.name || concept.label || 'Concept');
                return (
                  <span
                    key={`con-${idx}`}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-blue-50 text-blue-800 border border-blue-200 text-xs font-medium"
                  >
                    <span className="font-medium">{name}</span>
                  </span>
                );
              })}
            </div>
          </div>
        )}

        <div className="pt-1 flex items-center justify-between border-t border-slate-100 text-xs text-slate-500">
          <span>Tolkāppiyam Knowledge Graph Node: {activeEvidence?.passageId || activeEvidence?.id || verseId}</span>
          <button
            type="button"
            onClick={handleFocusInGraph}
            className="inline-flex items-center gap-1 text-purple-700 hover:text-purple-900 font-semibold cursor-pointer"
          >
            <span>Inspect in Graph Viewer</span>
            <ExternalLink className="w-3 h-3" />
          </button>
        </div>
      </div>
    </Card>
  );
}
