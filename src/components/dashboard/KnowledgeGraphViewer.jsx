import { useRef, useEffect, useState, useMemo, useCallback } from "react";
import cytoscape from "cytoscape";
import cola from "cytoscape-cola";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Network,
  X,
  Plus,
  Layers,
  Info,
  ArrowRight,
  RefreshCw,
  Compass,
  AlertTriangle,
  Search,
  Filter,
  Tag,
  ChevronDown,
  GitBranch,
  Sparkles,
} from "lucide-react";
import { useReasoner } from "../../context/ReasonerContext";
import { graphApi } from "../../services/apiClient";

// Register cola layout plugin with Cytoscape if not already registered
try {
  cytoscape.use(cola);
} catch {
  // Ignored if already registered
}

const CATEGORY_STYLES = {
  // Literary Hierarchy Entities
  Literature: {
    fill: "#f8fafc",
    stroke: "#1e293b",
    text: "#0f172a",
    badgeBg: "bg-slate-100 text-slate-900 border-slate-300 font-semibold",
  },
  Work: {
    fill: "#eef2ff",
    stroke: "#4f46e5",
    text: "#312e81",
    badgeBg: "bg-indigo-100 text-indigo-900 border-indigo-200 font-semibold",
  },
  Section: {
    fill: "#f1f5f9",
    stroke: "#475569",
    text: "#0f172a",
    badgeBg: "bg-slate-100 text-slate-800 border-slate-200 font-medium",
  },
  Verse: {
    fill: "#f0fdf4",
    stroke: "#16a34a",
    text: "#14532d",
    badgeBg: "bg-emerald-50 text-emerald-800 border-emerald-200 font-medium",
  },
  Concept: {
    fill: "#faf5ff",
    stroke: "#9333ea",
    text: "#581c87",
    badgeBg: "bg-purple-50 text-purple-800 border-purple-200 font-medium",
  },
  Entity: {
    fill: "#fff7ed",
    stroke: "#ea580c",
    text: "#7c2d12",
    badgeBg: "bg-orange-50 text-orange-800 border-orange-200 font-medium",
  },
  Event: {
    fill: "#fffbeb",
    stroke: "#d97706",
    text: "#78350f",
    badgeBg: "bg-amber-50 text-amber-800 border-amber-200 font-medium",
  },
  Evidence: {
    fill: "#eff6ff",
    stroke: "#2563eb",
    text: "#1e3a8a",
    badgeBg: "bg-blue-50 text-blue-800 border-blue-200 font-medium",
  },

  // Linguistic & Poetic Concept Layers
  Primary: {
    fill: "#eff6ff",
    stroke: "#3b82f6",
    text: "#1e3a8a",
    badgeBg: "bg-blue-100 text-blue-900 border-blue-200 font-semibold",
  },
  Secondary: {
    fill: "#faf5ff",
    stroke: "#8b5cf6",
    text: "#4c1d95",
    badgeBg: "bg-purple-100 text-purple-900 border-purple-200 font-semibold",
  },
  Aesthetic: {
    fill: "#fdf2f8",
    stroke: "#ec4899",
    text: "#831843",
    badgeBg: "bg-pink-100 text-pink-900 border-pink-200 font-semibold",
  },
  Person: {
    fill: "#f5f3ff",
    stroke: "#7c3aed",
    text: "#4c1d95",
    badgeBg: "bg-violet-100 text-violet-900 border-violet-200 font-semibold",
  },
  Object: {
    fill: "#f0fdf4",
    stroke: "#059669",
    text: "#064e3b",
    badgeBg: "bg-emerald-100 text-emerald-900 border-emerald-200 font-semibold",
  },

  // 5-Stage Pañcāvayava Reasoning Path Node Styles
  Premise: {
    fill: "#faf5ff",
    stroke: "#7c3aed",
    text: "#4c1d95",
    badgeBg: "bg-purple-100 text-purple-900 border-purple-200 font-bold",
  },
  Rule: {
    fill: "#fffbeb",
    stroke: "#d97706",
    text: "#78350f",
    badgeBg: "bg-amber-100 text-amber-900 border-amber-200 font-bold",
  },
  Inference: {
    fill: "#eef2ff",
    stroke: "#4f46e5",
    text: "#312e81",
    badgeBg: "bg-indigo-100 text-indigo-900 border-indigo-200 font-bold",
  },
  Conclusion: {
    fill: "#ecfdf5",
    stroke: "#059669",
    text: "#064e3b",
    badgeBg: "bg-emerald-100 text-emerald-900 border-emerald-200 font-bold",
  },
};

const LAYOUT_OPTIONS = [
  { id: "cose", label: "CoSE Physics" },
  { id: "cola", label: "Force Directed (Cola)" },
  { id: "preset", label: "Canonical Grid" },
  { id: "circle", label: "Circular Ring" },
  { id: "breadthfirst", label: "Hierarchy Tree" },
];

export default function KnowledgeGraphViewer({
  nodes: propNodes,
  edges: propEdges,
  categories: propCategories,
  selectedNodeId: propSelectedNodeId,
  onSelectNode: propOnSelectNode,
  fetchFromBackend = true,
  className = "",
  height = "h-[640px] sm:h-[700px] lg:h-[760px]",
  showToolbar = true,
  showLegend = true,
  initialLayout = "cose",
} = {}) {
  const context = useReasoner();
  const contextGraphNodes = context?.graphNodes;
  const contextGraphEdges = context?.graphEdges;
  const contextProofNodes = context?.proofNodes;
  const contextProofEdges = context?.proofEdges;
  const contextIsShowingProofTrace = context?.isShowingProofTrace;
  const contextShowProofTrace = context?.showProofTrace;
  const contextIsAnalyzing = context?.isAnalyzing;
  const contextWorkflowProgressPercent = context?.workflowProgressPercent;
  const contextCurrentWorkflowStage = context?.currentWorkflowStage;
  const contextInsufficientEvidence = context?.insufficientEvidence;
  const contextSetInsufficientEvidence = context?.setInsufficientEvidence;
  const contextLoadBenchmarkEvidence = context?.loadBenchmarkEvidence;
  const contextEvidenceRecords = context?.evidenceRecords;
  const contextSelectedEvidenceId = context?.selectedEvidenceId;
  const contextSetSelectedEvidenceId = context?.setSelectedEvidenceId;

  // Backend state for consuming Flask Neo4j graph API
  const [backendData, setBackendData] = useState(null);
  const [isLoadingBackend, setIsLoadingBackend] = useState(false);
  const [backendError, setBackendError] = useState(null);
  const [backendSource, setBackendSource] = useState(null); // 'neo4j_aura' | 'in_memory_kg' | 'cached'
  const [focusedCenterId, setFocusedCenterId] = useState(null);

  // Active selected ID & category filter
  const contextSelectedProofNodeId = context?.selectedProofNodeId;
  const activeSelectedId =
    propSelectedNodeId !== undefined
      ? propSelectedNodeId
      : (context?.selectedGraphNodeId || contextSelectedProofNodeId || contextSelectedEvidenceId);
  const setSelectedNodeId = propOnSelectNode || context?.setSelectedGraphNodeId;
  const activeCategoryFilter = context?.activeCategoryFilter;
  const setActiveCategoryFilter = context?.setActiveCategoryFilter;
  const setQueryText = context?.setQueryText;

  // DOM & Cytoscape Refs
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  // Component State
  const [selectedEdgeData, setSelectedEdgeData] = useState(null);
  const [clickedNodeData, setClickedNodeData] = useState(null);
  const [currentLayout, setCurrentLayout] = useState(initialLayout);
  const [zoomLevelPercent, setZoomLevelPercent] = useState(100);
  const [searchText, setSearchText] = useState("");
  const [selectedNodeTypeFilter, setSelectedNodeTypeFilter] = useState("ALL");

  // Keep a ref to activeSelectedId to avoid stale closures in Cytoscape event handlers
  const activeSelectedIdRef = useRef(activeSelectedId);
  useEffect(() => {
    activeSelectedIdRef.current = activeSelectedId;
  }, [activeSelectedId]);

  // Multi-hop depth state (1 to 5 hops) synchronized bidirectionally with ReasonerContext
  const contextDepth = context?.depth;
  const contextSetDepth = context?.setDepth;
  const [localHopDepth, setLocalHopDepth] = useState(contextDepth || 1);
  const hopDepth = contextDepth !== undefined ? contextDepth : localHopDepth;

  const setHopDepth = useCallback(
    (newHops) => {
      setLocalHopDepth(newHops);
      if (contextSetDepth) {
        contextSetDepth(newHops);
      }
    },
    [contextSetDepth],
  );

  const [popoverPos, setPopoverPos] = useState(null); // Dynamic { left, top, width } click anchor

  // Resolve reliable fallback center node for multi-hop expansion
  const getFallbackCenterId = useCallback(() => {
    if (activeSelectedId) return String(activeSelectedId);
    if (focusedCenterId) return String(focusedCenterId);
    if (cyRef.current && !cyRef.current.destroyed()) {
      const mutal = cyRef.current.getElementById("mutalporul");
      if (mutal && mutal.length > 0) return "mutalporul";
      const tolk = cyRef.current.getElementById("tolkappiyar");
      if (tolk && tolk.length > 0) return "tolkappiyar";
      const firstNode = cyRef.current.nodes().first();
      if (firstNode && firstNode.length > 0) return firstNode.id();
    }
    return "mutalporul";
  }, [activeSelectedId, focusedCenterId]);

  // Robust coordinate extractor for tap events on Cytoscape elements (canvas, node, or edge)
  const getClickCoords = useCallback((evt) => {
    if (
      evt?.renderedPosition &&
      typeof evt.renderedPosition.x === "number" &&
      !isNaN(evt.renderedPosition.x)
    ) {
      return { x: evt.renderedPosition.x, y: evt.renderedPosition.y };
    }
    if (evt?.target && typeof evt.target.renderedPosition === "function") {
      try {
        const rp = evt.target.renderedPosition();
        if (rp && typeof rp.x === "number" && !isNaN(rp.x)) return rp;
      } catch {
        // ignore
      }
    }
    if (evt?.originalEvent && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const orig = evt.originalEvent;
      const clientX =
        orig.clientX ?? (orig.touches && orig.touches[0]?.clientX);
      const clientY =
        orig.clientY ?? (orig.touches && orig.touches[0]?.clientY);
      if (typeof clientX === "number" && typeof clientY === "number") {
        return {
          x: clientX - rect.left,
          y: clientY - rect.top,
        };
      }
    }
    if (
      evt?.target &&
      typeof evt.target.isEdge === "function" &&
      evt.target.isEdge()
    ) {
      try {
        const s = evt.target.source()?.renderedPosition();
        const t = evt.target.target()?.renderedPosition();
        if (s && t) {
          return { x: (s.x + t.x) / 2, y: (s.y + t.y) / 2 };
        }
      } catch {
        // ignore
      }
    }
    return null;
  }, []);

  // Compute boundary-clamped position ensuring popover appears adjacent to clicked coordinates without clipping
  const calculateClampedPos = useCallback(
    (clickX, clickY, estimatedWidth = 380, estimatedHeight = 320) => {
      const container = containerRef.current;
      const containerW = container?.clientWidth || 800;
      const containerH = container?.clientHeight || 600;

      const actualWidth = Math.min(estimatedWidth, containerW - 24);
      const actualHeight = Math.min(estimatedHeight, containerH - 24);

      let left = clickX + 16;
      if (left + actualWidth > containerW - 12) {
        left = clickX - actualWidth - 16;
      }
      left = Math.max(12, Math.min(left, containerW - actualWidth - 12));

      let top = clickY - 20;
      if (top + actualHeight > containerH - 12) {
        top = clickY - actualHeight + 20;
      }
      top = Math.max(12, Math.min(top, containerH - actualHeight - 12));

      return {
        left: Math.round(left),
        top: Math.round(top),
        width: Math.round(actualWidth),
      };
    },
    [],
  );

  // Function to consume Flask backend graph API (Neo4j Aura or in-memory fallback)
  const fetchAbortRef = useRef(null);

  const fetchGraphData = useCallback(
    async (centerId = null, customHops = null) => {
      if (!fetchFromBackend) return;
      if (fetchAbortRef.current) {
        fetchAbortRef.current.abort();
      }
      const controller = new AbortController();
      fetchAbortRef.current = controller;

      setIsLoadingBackend(true);
      setBackendError(null);
      const hops = customHops !== null ? customHops : hopDepth;
      const timer = setTimeout(() => controller.abort(), 4000);
      try {
        const json = await graphApi.getElements({
          centerId,
          hops,
          limit: centerId ? 150 : 250,
          source: 'auto',
          signal: controller.signal,
          timeoutMs: 4000,
        });
        clearTimeout(timer);
        if (json.success && json.data) {
          setBackendData(json.data);
          const src =
            json.data.source ||
            (json.data.relationships ? "neo4j_aura" : "in_memory_kg");
          setBackendSource(src);
          setFocusedCenterId(centerId);
        } else {
          throw new Error(json.message || "Failed to retrieve graph data");
        }
      } catch (err) {
        if (err.name === "AbortError") return;
        clearTimeout(timer);
        console.warn(
          "Flask backend graph fetch warning (falling back to context cache):",
          err.message,
        );
        setBackendError(err.message);
        setBackendSource("cached");
      } finally {
        setIsLoadingBackend(false);
      }
    },
    [fetchFromBackend, hopDepth],
  );

  // Initial fetch on mount when not supplied with external propNodes
  useEffect(() => {
    if (!propNodes && fetchFromBackend) {
      queueMicrotask(() => {
        fetchGraphData(null, hopDepth);
      });
    }
    return () => {
      if (fetchAbortRef.current) {
        fetchAbortRef.current.abort();
      }
    };
  }, [propNodes, fetchFromBackend, fetchGraphData, hopDepth]);

  // Resolve active raw nodes & edges (including Nyāya proof trace nodes & edges)
  const rawNodes = useMemo(() => {
    let base;
    if (propNodes) {
      base = propNodes;
    } else if (backendData?.nodes && backendData.nodes.length > 0) {
      base = backendData.nodes;
    } else {
      base = contextGraphNodes || [];
    }

    const existingIds = new Set(base.map((n) => String(n.id)));
    const mergedNodes = [...base];

    if (contextProofNodes && contextProofNodes.length > 0) {
      contextProofNodes
        .filter((pn) => !existingIds.has(String(pn.id)))
        .forEach((pn, idx) => {
          existingIds.add(String(pn.id));
          mergedNodes.push({
            ...pn,
            label: pn.label || pn.id,
            name: pn.name || pn.label || pn.id,
            type: pn.type || "Evidence",
            category: pn.type || "Evidence",
            isProofTraceNode: true,
            stageOrder: idx,
            // Assign deterministic coordinates for preset layouts
            x: pn.x ?? 480 + idx * 85,
            y: pn.y ?? 260 + (idx % 2 === 0 ? 0 : 40),
          });
        });
    }

    if (contextEvidenceRecords && contextEvidenceRecords.length > 0) {
      contextEvidenceRecords.forEach((ev, idx) => {
        const pId = String(ev.passageId || ev.id);
        const cId = String(ev.code || `E${idx + 1}`);
        const aliases = [cId, String(ev.id), pId].filter((a, i, arr) => arr.indexOf(a) === i);
        if (!existingIds.has(pId)) {
          existingIds.add(pId);
          mergedNodes.push({
            id: pId,
            aliases,
            label: `${cId}: ${ev.reference || pId}`,
            name: ev.reference || ev.source || pId,
            type: "Evidence",
            category: "Evidence",
            evidenceType: ev.evidenceType || "Canonical Evidence",
            tamilLabel: ev.tamilText ? (ev.tamilText.length > 35 ? ev.tamilText.slice(0, 35) + "..." : ev.tamilText) : pId,
            description: ev.translation || ev.tamilText || "",
            text: ev.tamilText || ev.text || "",
            translation: ev.translation || "",
            confidence: ev.confidence || ev.relevanceScore || 0.9,
            relevanceScore: ev.confidence || ev.relevanceScore || 0.9,
            source: ev.source || ev.work || "Tolkāppiyam",
            sourceReference: ev.reference || "",
            workName: ev.work || "",
            sectionName: ev.section || "",
            chapterName: ev.chapter || "",
            sutraNumber: ev.sutraNumber || null,
            retrievalMethod: ev.retrievalMethod || (ev.retrievalMethods && ev.retrievalMethods[0]) || "",
            passageId: pId,
            isEvidenceRecord: true,
            x: 180 + (idx % 3) * 135,
            y: 450 + Math.floor(idx / 3) * 95,
          });
        }
      });
    }
    return mergedNodes;
  }, [propNodes, backendData, contextGraphNodes, contextProofNodes, contextEvidenceRecords]);

  const rawEdges = useMemo(() => {
    let base;
    if (propEdges) {
      base = propEdges;
    } else if (
      backendData?.relationships &&
      backendData.relationships.length > 0
    ) {
      base = backendData.relationships;
    } else if (backendData?.edges && backendData.edges.length > 0) {
      base = backendData.edges;
    } else {
      base = contextGraphEdges || [];
    }

    const mergedEdges = [...base];
    const existingEdgeIds = new Set(
      mergedEdges.map((e) =>
        e.id
          ? String(e.id)
          : `${e.source}_${e.type || e.relation}_${e.target}`,
      ),
    );

    if (contextProofEdges && contextProofEdges.length > 0) {
      contextProofEdges
        .filter((pe) => !existingEdgeIds.has(String(pe.id)))
        .forEach((pe) => {
          existingEdgeIds.add(String(pe.id));
          mergedEdges.push({
            ...pe,
            isProofTraceEdge:
              pe.isProofTraceEdge !== undefined ? pe.isProofTraceEdge : true,
          });
        });
    }

    if (contextEvidenceRecords && contextEvidenceRecords.length > 0) {
      const defaultConcepts = ["mutalporul", "karupporul", "uripporul", "meyppatu", "araneri"];
      contextEvidenceRecords.forEach((ev, idx) => {
        const pId = String(ev.passageId || ev.id);
        const cId = String(ev.code || `E${idx + 1}`);

        // 1. Connect to concepts associated with this evidence item
        const concepts = Array.isArray(ev.concepts) ? ev.concepts : [];
        if (concepts.length > 0) {
          concepts.forEach((c) => {
            const conceptId = typeof c === 'string' ? c : (c?.id || c?.label || c?.name);
            if (conceptId) {
              const edgeId = `edge_ev_${pId}_${conceptId}`;
              if (!existingEdgeIds.has(edgeId)) {
                existingEdgeIds.add(edgeId);
                mergedEdges.push({
                  id: edgeId,
                  source: pId,
                  target: String(conceptId),
                  type: "GROUNDS_IN",
                  relation: "GROUNDS_IN",
                  label: "grounds concept",
                  confidence: ev.confidence || ev.relevanceScore || 0.95,
                  isEvidenceEdge: true,
                });
              }
            }
          });
        }

        // 2. Connect to entities associated with this evidence item
        const entities = Array.isArray(ev.entities) ? ev.entities : [];
        if (entities.length > 0) {
          entities.forEach((ent) => {
            const entityId = typeof ent === 'string' ? ent : (ent?.id || ent?.label || ent?.name);
            if (entityId) {
              const edgeId = `edge_ev_${pId}_${entityId}`;
              if (!existingEdgeIds.has(edgeId)) {
                existingEdgeIds.add(edgeId);
                mergedEdges.push({
                  id: edgeId,
                  source: pId,
                  target: String(entityId),
                  type: "MENTIONS",
                  relation: "MENTIONS",
                  label: "mentions",
                  confidence: ev.confidence || ev.relevanceScore || 0.95,
                  isEvidenceEdge: true,
                });
              }
            }
          });
        }

        // 3. If neither concepts nor entities, connect to default canonical concept
        if (concepts.length === 0 && entities.length === 0) {
          const defaultConcept = defaultConcepts[idx % defaultConcepts.length];
          const edgeId = `edge_ev_${pId}_${defaultConcept}`;
          if (!existingEdgeIds.has(edgeId)) {
            existingEdgeIds.add(edgeId);
            mergedEdges.push({
              id: edgeId,
              source: pId,
              target: defaultConcept,
              type: "GROUNDS_IN",
              relation: "GROUNDS_IN",
              label: "grounds concept",
              confidence: ev.confidence || ev.relevanceScore || 0.95,
              isEvidenceEdge: true,
            });
          }
        }

        // 4. Connect alias node if cId is distinct from pId
        if (cId && cId !== pId) {
          const codeEdgeId = `edge_alias_${cId}_${pId}`;
          if (!existingEdgeIds.has(codeEdgeId)) {
            existingEdgeIds.add(codeEdgeId);
            mergedEdges.push({
              id: codeEdgeId,
              source: cId,
              target: pId,
              type: "IDENTIFIES",
              relation: "IDENTIFIES",
              label: "passage",
              confidence: 1.0,
              isEvidenceEdge: true,
            });
          }
        }
      });
    }

    return mergedEdges;
  }, [propEdges, backendData, contextGraphEdges, contextProofEdges, contextEvidenceRecords]);

  // Compute selected node object with fallback (rawNodes, clickedNodeData)
  const selectedNode = useMemo(() => {
    const targetId = activeSelectedId || clickedNodeData?.id;
    if (!targetId) return null;

    const found = rawNodes.find((n) => String(n.id) === String(targetId));
    if (found) return found;

    if (clickedNodeData && String(clickedNodeData.id) === String(targetId)) {
      return {
        id: clickedNodeData.id,
        label:
          clickedNodeData.label ||
          clickedNodeData.tamilLabel ||
          clickedNodeData.name ||
          clickedNodeData.id,
        name:
          clickedNodeData.name || clickedNodeData.label || clickedNodeData.id,
        type: clickedNodeData.type || clickedNodeData.category || "Concept",
        category: clickedNodeData.category || clickedNodeData.type || "Concept",
        transliteration: clickedNodeData.transliteration || "",
        hierarchy_level:
          clickedNodeData.hierarchyLevel ||
          clickedNodeData.hierarchy_level ||
          "",
        confidence: clickedNodeData.confidence,
        role: clickedNodeData.role || "",
        description: clickedNodeData.description || clickedNodeData.text || "",
        text: clickedNodeData.text || "",
        source: clickedNodeData.source || "",
        source_reference:
          clickedNodeData.sourceReference ||
          clickedNodeData.source_reference ||
          "",
        work_name: clickedNodeData.workName || clickedNodeData.work_name || "",
        section_name:
          clickedNodeData.sectionName || clickedNodeData.section_name || "",
        chapter_name:
          clickedNodeData.chapterName || clickedNodeData.chapter_name || "",
        sutra_number:
          clickedNodeData.sutraNumber || clickedNodeData.sutra_number,
        verse_number:
          clickedNodeData.verseNumber || clickedNodeData.verse_number,
      };
    }

    return null;
  }, [rawNodes, activeSelectedId, clickedNodeData]);

  // Connected edges count for selected node
  const connectedEdgeCount = useMemo(() => {
    const targetId = activeSelectedId || clickedNodeData?.id;
    if (!targetId) return 0;
    return rawEdges.filter(
      (e) =>
        String(e.source) === String(targetId) ||
        String(e.target) === String(targetId),
    ).length;
  }, [rawEdges, activeSelectedId, clickedNodeData]);

  // Available node types in active dataset for dropdown filter
  const availableNodeTypes = useMemo(() => {
    const types = new Set();
    rawNodes.forEach((n) => {
      if (n.type) types.add(n.type);
      if (n.category) types.add(n.category);
    });
    return Array.from(types).sort();
  }, [rawNodes]);

  // Pre-render validation, alias normalization, and Cytoscape elements creation
  const { canonicalStats, cyElements } = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    const hasFilter = selectedNodeTypeFilter !== "ALL" || query !== "";

    // Step 1: Normalize and deduplicate nodes
    const validNodeMap = new Map(); // id -> node
    const aliasMap = new Map(); // alias -> canonical id
    const deduplicatedNodes = [];
    const duplicateNodeIds = [];

    rawNodes.forEach((node) => {
      if (!node || node.id === undefined || node.id === null) return;
      const idStr = String(node.id).trim();
      if (!idStr) return;

      if (validNodeMap.has(idStr)) {
        duplicateNodeIds.push(idStr);
        return;
      }
      validNodeMap.set(idStr, node);
      deduplicatedNodes.push(node);

      // Register aliases
      if (idStr === "uriporul") aliasMap.set("uripporul", "uriporul");
      if (idStr === "uripporul") aliasMap.set("uriporul", "uripporul");
      if (Array.isArray(node.aliases)) {
        node.aliases.forEach((al) => aliasMap.set(String(al).trim(), idStr));
      }
    });

    const resolveNodeId = (id) => {
      const s = String(id || "").trim();
      if (validNodeMap.has(s)) return s;
      if (aliasMap.has(s)) return aliasMap.get(s);
      return null;
    };

    // Step 2: Validate all raw edges against the canonical node map
    const validCanonicalEdges = [];
    const orphanEdges = [];
    const seenEdgeIds = new Set();

    rawEdges.forEach((rel, idx) => {
      if (!rel) return;
      const rawSrc =
        rel.source !== undefined && rel.source !== null
          ? String(rel.source).trim()
          : "";
      const rawTgt =
        rel.target !== undefined && rel.target !== null
          ? String(rel.target).trim()
          : "";
      const resolvedSrc = resolveNodeId(rawSrc);
      const resolvedTgt = resolveNodeId(rawTgt);

      if (!resolvedSrc || !resolvedTgt) {
        orphanEdges.push({
          id: rel.id,
          source: rawSrc,
          target: rawTgt,
          relation: rel.type || rel.relation,
          reason: !resolvedSrc
            ? `Missing source node: "${rawSrc}"`
            : `Missing target node: "${rawTgt}"`,
        });
        return;
      }

      const edgeType = rel.type || rel.relation || "RELATED_TO";
      let edgeId = rel.id
        ? String(rel.id).trim()
        : `${resolvedSrc}_${edgeType}_${resolvedTgt}`;
      if (seenEdgeIds.has(edgeId)) {
        edgeId = `${edgeId}_${idx}`;
      }
      seenEdgeIds.add(edgeId);

      validCanonicalEdges.push({
        ...rel,
        id: edgeId,
        source: resolvedSrc,
        target: resolvedTgt,
        type: edgeType,
        relation: edgeType,
      });
    });

    // Step 3: Determine visible nodes based on active filters/search
    let matchingNodes = deduplicatedNodes;
    if (selectedNodeTypeFilter !== "ALL") {
      matchingNodes = matchingNodes.filter(
        (n) =>
          n.type === selectedNodeTypeFilter ||
          n.category === selectedNodeTypeFilter,
      );
    }
    if (query) {
      matchingNodes = matchingNodes.filter((n) => {
        const lbl = (n.label || n.name || "").toLowerCase();
        const tr = (n.transliteration || "").toLowerCase();
        const nid = String(n.id).toLowerCase();
        const desc = (n.description || n.text || "").toLowerCase();
        return (
          lbl.includes(query) ||
          tr.includes(query) ||
          nid.includes(query) ||
          desc.includes(query)
        );
      });
    }

    const visibleNodeIdSet = new Set(matchingNodes.map((n) => String(n.id)));
    // Always preserve proof trace nodes if proof trace mode is active
    if (contextIsShowingProofTrace && contextProofNodes) {
      contextProofNodes.forEach((pn) => {
        const resolvedPn = resolveNodeId(pn.id);
        if (resolvedPn) visibleNodeIdSet.add(resolvedPn);
      });
    }

    const finalRenderedNodes = deduplicatedNodes.filter((n) =>
      visibleNodeIdSet.has(String(n.id)),
    );

    // Step 4: Map visible nodes into Cytoscape format
    const cyNodes = finalRenderedNodes.map((node) => {
      const category = node.category || node.type || "Concept";
      const style =
        CATEGORY_STYLES[category] ||
        CATEGORY_STYLES[node.type] ||
        CATEGORY_STYLES.Concept;
      const meta = node.metadata || {};
      const isProofNode = !!(
        node.isProofTraceNode ||
        (contextProofNodes || []).some(
          (pn) => String(pn.id) === String(node.id),
        )
      );

      return {
        group: "nodes",
        data: {
          id: String(node.id),
          label: node.label || node.name || String(node.id),
          type: node.type || category,
          category: category,
          hierarchyLevel: node.hierarchy_level || meta.hierarchy_level || "L5",
          source: node.source || meta.source || "Tolkāppiyam",
          sourceReference:
            node.source_reference || meta.source_reference || node.source || "",
          sourceId: node.source_id || "",
          confidence:
            typeof node.confidence === "number" ? node.confidence : 1.0,
          validationStatus:
            node.validation_status || meta.validation_status || "verified",
          isProofTraceNode: isProofNode,
          stageOrder: node.stageOrder,

          // Linguistic & domain fields
          tamilLabel: node.label || node.name || String(node.id),
          transliteration: node.transliteration || meta.transliteration || "",
          role: node.role || meta.role || node.type || "",
          description: node.description || meta.description || "",
          tinai: node.tinai || meta.tinai || "",

          // Textual & canonical citations
          text: node.text || node.normalized_text || node.original_text || "",
          originalText: node.original_text || "",
          normalizedText: node.normalized_text || "",
          translation: node.translation || meta.translation || "",
          sutraNumber: node.sutra_number || meta.sutra_number,
          verseNumber:
            node.verse_number || node.passage_number || meta.verse_number,
          workName: node.work_name || meta.work_name || "",
          sectionName: node.section_name || meta.section_name || "",
          chapterName: node.chapter_name || meta.chapter_name || "",
          corpusInfo: node.corpus_info || meta.corpus_info || "",
          ontologyUri: node.ontologyUri || meta.ontologyUri || "",

          // Cytoscape visual formatting
          color: style.stroke,
          bgColor: style.fill,
          textColor: style.text,
          badgeBg: style.badgeBg,
          radius: node.radius || meta.radius || 28,
          metadata: meta,
        },
        position:
          node.x !== undefined && node.y !== undefined
            ? { x: node.x, y: node.y }
            : undefined,
      };
    });

    // Step 5: Filter and map visible edges
    const visibleEdges = validCanonicalEdges.filter(
      (rel) =>
        visibleNodeIdSet.has(rel.source) && visibleNodeIdSet.has(rel.target),
    );

    const cyEdges = visibleEdges.map((rel) => {
      const edgeType = rel.type || rel.relation || "RELATED_TO";
      const meta = rel.metadata || {};
      const isProofEdge = !!(
        rel.isProofTraceEdge ||
        (contextProofEdges || []).some(
          (pe) =>
            pe.isProofTraceEdge &&
            (String(pe.id) === rel.id ||
              (String(pe.source) === rel.source &&
                String(pe.target) === rel.target)),
        )
      );

      return {
        group: "edges",
        data: {
          id: rel.id,
          source: rel.source,
          target: rel.target,
          type: edgeType,
          relation: edgeType,
          label: rel.label || edgeType,
          confidence: typeof rel.confidence === "number" ? rel.confidence : 1.0,
          validationLevel:
            rel.validation_level || meta.validation_level || "corpus_grounded",
          sourceCorpus: rel.source_corpus || rel.source || "Tolkāppiyam",
          sourceReference: rel.source_reference || meta.source_reference || "",
          passageId: rel.passage_id || meta.passage_id || "",
          isProofTraceEdge: isProofEdge,
          metadata: meta,
          curved: !!rel.curved,
        },
      };
    });

    const stats = {
      totalEntities: deduplicatedNodes.length,
      totalEdges: validCanonicalEdges.length,
      renderedEntities: cyNodes.length,
      renderedEdges: cyEdges.length,
      isFiltered: hasFilter,
      orphanEdgesCount: orphanEdges.length,
      duplicateNodesCount: duplicateNodeIds.length,
    };

    // Step 6: Dev diagnostic telemetry
    if (
      Boolean(typeof window !== "undefined" && window.__DEV__) ||
      Boolean(import.meta.env?.DEV)
    ) {
      console.info(
        `%c[KnowledgeGraphViewer Diagnostics]%c API: ${rawNodes.length} nodes, ${rawEdges.length} edges | Valid Canonical: ${stats.totalEntities} entities, ${stats.totalEdges} edges | Cytoscape Rendered: ${stats.renderedEntities} nodes, ${stats.renderedEdges} edges (Filtered: ${hasFilter})`,
        "color: #7c3aed; font-weight: bold",
        "color: #334155",
      );
      if (orphanEdges.length > 0) {
        console.warn(
          `[KnowledgeGraphViewer Discrepancy Alert] ${orphanEdges.length} orphan edges dropped due to missing endpoints:`,
          orphanEdges,
        );
      }
      if (duplicateNodeIds.length > 0) {
        console.warn(
          `[KnowledgeGraphViewer Discrepancy Alert] ${duplicateNodeIds.length} duplicate node IDs dropped:`,
          duplicateNodeIds,
        );
      }
    }

    return {
      canonicalStats: stats,
      cyElements: [...cyNodes, ...cyEdges],
    };
  }, [
    rawNodes,
    rawEdges,
    searchText,
    selectedNodeTypeFilter,
    contextIsShowingProofTrace,
    contextProofNodes,
    contextProofEdges,
  ]);

  const activeLayoutRef = useRef(null);

  // Layout helper function with physics calibration and reliable layoutstop listener
  const applyCytoscapeLayout = useCallback((cy, layoutType, onComplete) => {
    if (!cy || cy.destroyed()) return;

    if (activeLayoutRef.current) {
      try {
        activeLayoutRef.current.stop();
      } catch {
        // ignore
      }
      activeLayoutRef.current = null;
    }

    let layoutConfig;

    if (layoutType === "cose") {
      layoutConfig = {
        name: "cose",
        animate: true,
        animationDuration: 600,
        nodeRepulsion: 50000,
        idealEdgeLength: 120,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 100,
        numIter: 800,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
        fit: true,
        padding: 40,
      };
    } else if (layoutType === "cola") {
      layoutConfig = {
        name: "cola",
        animate: true,
        refresh: 1,
        maxSimulationTime: 1200,
        ungrabifyWhileSimulating: false,
        fit: true,
        padding: 45,
        nodeSpacing: 35,
        edgeLengthVal: 140,
      };
    } else if (layoutType === "circle") {
      layoutConfig = {
        name: "circle",
        fit: true,
        padding: 45,
        animate: true,
        animationDuration: 500,
      };
    } else if (layoutType === "breadthfirst") {
      layoutConfig = {
        name: "breadthfirst",
        directed: true,
        fit: true,
        padding: 40,
        animate: true,
        animationDuration: 500,
        roots:
          'node[type = "Literature"], node[type = "Work"], node[hierarchyLevel = "L0"], node[hierarchyLevel = "L1"]',
      };
    } else {
      layoutConfig = {
        name: "preset",
        fit: true,
        padding: 40,
        animate: true,
        animationDuration: 400,
      };
    }

    const layout = cy.layout(layoutConfig);
    activeLayoutRef.current = layout;

    layout.one("layoutstop", () => {
      activeLayoutRef.current = null;
      if (!cy.destroyed()) {
        cy.fit(undefined, 40);
        setZoomLevelPercent(Math.round(cy.zoom() * 100));
        if (typeof onComplete === "function") onComplete();
      }
    });

    layout.run();
  }, []);

  // Initialize Cytoscape instance
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: cyElements,
      boxSelectionEnabled: false,
      autoungrabify: true, // nodes locked by default — triple-click to unlock
      wheelSensitivity: 0.25,
      minZoom: 0.35,
      maxZoom: 3.0,
      style: [
        // Base Node Style
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-family": "Noto Serif Tamil, Mukta Malar, serif, system-ui",
            "font-size": "10px",
            "font-weight": "600",
            "text-valign": "center",
            "text-halign": "center",
            color: "data(textColor)",
            "text-wrap": "wrap",
            "text-max-width": "80px",
            "background-color": "data(bgColor)",
            "border-width": 2.0,
            "border-color": "data(color)",
            width: 56,
            height: 56,
            "transition-property":
              "background-color, border-color, border-width, opacity, width, height",
            "transition-duration": "0.2s",
            "overlay-opacity": 0,
            "shadow-blur": 10,
            "shadow-color": "rgba(15, 23, 42, 0.06)",
            "shadow-offset-y": 2,
          },
        },

        // ----------------------------------------------------
        // Literary Hierarchy Entities (Distinct Academic Shapes)
        // ----------------------------------------------------
        {
          selector: 'node[type = "Literature"], node[category = "Literature"]',
          style: {
            shape: "barrel",
            width: 94,
            height: 54,
            "border-width": 3,
            "border-color": "#1e293b",
            "background-color": "#f8fafc",
            color: "#0f172a",
            "font-size": "11.5px",
            "font-weight": "bold",
            "text-max-width": "86px",
            "shadow-blur": 16,
            "shadow-color": "rgba(30, 41, 59, 0.16)",
          },
        },
        {
          selector: 'node[type = "Work"], node[category = "Work"]',
          style: {
            shape: "round-rectangle",
            "corner-radius": "12px",
            width: 86,
            height: 48,
            "border-width": 2.5,
            "border-color": "#4f46e5",
            "background-color": "#eef2ff",
            color: "#312e81",
            "font-size": "11px",
            "font-weight": "bold",
            "text-max-width": "78px",
            "shadow-blur": 14,
            "shadow-color": "rgba(79, 70, 229, 0.14)",
          },
        },
        {
          selector: 'node[type = "Section"], node[category = "Section"]',
          style: {
            shape: "round-rectangle",
            "corner-radius": "8px",
            width: 76,
            height: 44,
            "border-width": 2,
            "border-color": "#475569",
            "background-color": "#f1f5f9",
            color: "#1e293b",
            "font-size": "10px",
            "font-weight": "600",
            "text-max-width": "70px",
          },
        },
        {
          selector: 'node[type = "Passage"], node[category = "Passage"]',
          style: {
            shape: "round-tag",
            width: 72,
            height: 42,
            "border-width": 2,
            "border-color": "#0284c7",
            "background-color": "#f0f9ff",
            color: "#075985",
            "font-size": "9.5px",
            "font-weight": "600",
            "text-max-width": "66px",
          },
        },

        // ----------------------------------------------------
        // Semantic Knowledge & Cultural Ontology Entities
        // ----------------------------------------------------
        {
          selector: 'node[type = "Concept"], node[category = "Concept"]',
          style: {
            shape: "diamond",
            width: 60,
            height: 60,
            "border-width": 2.2,
            "border-color": "#059669",
            "background-color": "#ecfdf5",
            color: "#065f46",
            "font-size": "10px",
            "font-weight": "600",
            "text-max-width": "52px",
          },
        },
        {
          selector:
            'node[type = "Entity"], node[category = "Entity"], node[type = "Person"], node[category = "Person"]',
          style: {
            shape: "ellipse",
            width: 58,
            height: 58,
            "border-width": 2.2,
            "border-color": "#e11d48",
            "background-color": "#fff1f2",
            color: "#9f1239",
            "font-size": "9.5px",
            "font-weight": "600",
            "text-max-width": "52px",
          },
        },
        {
          selector: 'node[type = "Object"], node[category = "Object"]',
          style: {
            shape: "round-rectangle",
            "corner-radius": "6px",
            width: 58,
            height: 44,
            "border-width": 2,
            "border-color": "#2563eb",
            "background-color": "#eff6ff",
            color: "#1e40af",
            "font-size": "9.5px",
            "font-weight": "600",
            "text-max-width": "52px",
          },
        },
        {
          selector: 'node[type = "Event"], node[category = "Event"]',
          style: {
            shape: "round-octagon",
            width: 58,
            height: 58,
            "border-width": 2,
            "border-color": "#d97706",
            "background-color": "#fffbeb",
            color: "#92400e",
            "font-size": "9.5px",
            "font-weight": "600",
            "text-max-width": "52px",
          },
        },
        {
          selector: 'node[type = "Evidence"], node[category = "Evidence"]',
          style: {
            shape: "round-rectangle",
            "corner-radius": "6px",
            width: 66,
            height: 38,
            "border-width": 1.8,
            "border-style": "dashed",
            "border-color": "#0891b2",
            "background-color": "#ecfeff",
            color: "#155e75",
            "font-size": "9px",
            "font-weight": "600",
            "text-max-width": "60px",
          },
        },

        // ----------------------------------------------------
        // Nyāya Neuro-Symbolic Reasoning Entities
        // ----------------------------------------------------
        {
          selector: 'node[type = "Premise"], node[category = "Premise"]',
          style: {
            shape: "hexagon",
            width: 66,
            height: 48,
            "border-width": 2.2,
            "border-color": "#7c3aed",
            "background-color": "#f5f3ff",
            color: "#5b21b6",
            "font-size": "10px",
            "font-weight": "bold",
            "text-max-width": "58px",
          },
        },
        {
          selector: 'node[type = "Rule"], node[category = "Rule"]',
          style: {
            shape: "rhomboid",
            width: 68,
            height: 42,
            "border-width": 2,
            "border-color": "#2563eb",
            "background-color": "#eff6ff",
            color: "#1e40af",
            "font-size": "10px",
            "font-weight": "bold",
            "text-max-width": "60px",
          },
        },
        {
          selector: 'node[type = "Inference"], node[category = "Inference"]',
          style: {
            shape: "round-diamond",
            width: 60,
            height: 60,
            "border-width": 2,
            "border-color": "#9333ea",
            "background-color": "#faf5ff",
            color: "#6b21a8",
            "font-size": "9.5px",
            "font-weight": "bold",
            "text-max-width": "54px",
          },
        },
        {
          selector: 'node[type = "Conclusion"], node[category = "Conclusion"]',
          style: {
            shape: "round-pentagon",
            width: 68,
            height: 52,
            "border-width": 3,
            "border-style": "double",
            "border-color": "#16a34a",
            "background-color": "#f0fdf4",
            color: "#14532d",
            "font-size": "10.5px",
            "font-weight": "bold",
            "text-max-width": "60px",
            "shadow-blur": 16,
            "shadow-color": "rgba(22, 163, 74, 0.18)",
          },
        },

        // ----------------------------------------------------
        // Base Edge Style & Clean Typography
        // ----------------------------------------------------
        {
          selector: "edge",
          style: {
            width: 1.8,
            "line-color": "#94a3b8",
            "target-arrow-color": "#94a3b8",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.05,
            "curve-style": (ele) =>
              ele.data("curved") ? "unbundled-bezier" : "bezier",
            label: "data(label)",
            "font-family": "JetBrains Mono, Menlo, monospace, sans-serif",
            "font-size": "8.5px",
            "font-weight": "600",
            color: "#475569",
            "text-background-color": "#ffffff",
            "text-background-opacity": 0.96,
            "text-background-padding": "3px",
            "text-background-shape": "roundrectangle",
            "text-border-color": "#e2e8f0",
            "text-border-width": 1,
            "text-border-opacity": 1,
            "text-rotation": "autorotate",
            "line-style": "solid",
            "transition-property":
              "line-color, target-arrow-color, width, opacity",
            "transition-duration": "0.2s",
          },
        },

        // ----------------------------------------------------
        // Type-Based Edge Relationship Selectors
        // ----------------------------------------------------
        // Structural Hierarchy
        {
          selector:
            'edge[type = "HAS_WORK"], edge[relation = "HAS_WORK"], edge[type = "HAS_SECTION"], edge[relation = "HAS_SECTION"], edge[type = "HAS_PASSAGE"], edge[relation = "HAS_PASSAGE"]',
          style: {
            width: 2.4,
            "line-color": "#4f46e5",
            "target-arrow-color": "#4f46e5",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            color: "#3730a3",
            "text-border-color": "#c7d2fe",
            "text-background-color": "#eef2ff",
          },
        },

        // Literary / Poetic Relations (Thinai, Habitat, Uripporul)
        {
          selector:
            'edge[type = "PRESIDES_OVER"], edge[relation = "PRESIDES_OVER"], edge[type = "HAS_HABITAT"], edge[relation = "HAS_HABITAT"], edge[type = "HAS_URIPPORUL"], edge[relation = "HAS_URIPPORUL"], edge[type = "ASSOCIATED_WITH"], edge[relation = "ASSOCIATED_WITH"]',
          style: {
            width: 2.0,
            "line-color": "#7c3aed",
            "target-arrow-color": "#7c3aed",
            "target-arrow-shape": "triangle-backcurve",
            "curve-style": "unbundled-bezier",
            "control-point-distances": [20, -20],
            color: "#5b21b6",
            "text-border-color": "#ddd6fe",
            "text-background-color": "#f5f3ff",
          },
        },

        // Semantic / Textual Discussions
        {
          selector:
            'edge[type = "DISCUSSES"], edge[relation = "DISCUSSES"], edge[type = "DESCRIBES"], edge[relation = "DESCRIBES"], edge[type = "MENTIONS"], edge[relation = "MENTIONS"]',
          style: {
            width: 1.9,
            "line-color": "#8b5cf6",
            "target-arrow-color": "#8b5cf6",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            color: "#6d28d9",
            "text-border-color": "#e9d5ff",
            "text-background-color": "#faf5ff",
          },
        },

        // Evidence & Grounding
        {
          selector:
            'edge[type = "SUPPORTED_BY"], edge[relation = "SUPPORTED_BY"], edge[type = "GROUNDS_IN"], edge[relation = "GROUNDS_IN"], edge[type = "GROUNDS_IN_ONTOLOGY"], edge[relation = "GROUNDS_IN_ONTOLOGY"], edge[type = "PROVIDES_EVIDENCE"], edge[relation = "PROVIDES_EVIDENCE"]',
          style: {
            width: 1.8,
            "line-style": "dashed",
            "line-dash-pattern": [5, 3],
            "line-color": "#0891b2",
            "target-arrow-color": "#0891b2",
            "target-arrow-shape": "triangle",
            color: "#0e7490",
            "text-border-color": "#a5f3fc",
            "text-background-color": "#ecfeff",
          },
        },

        // Entailment & Derivation
        {
          selector:
            'edge[type = "DERIVED_FROM"], edge[relation = "DERIVED_FROM"], edge[type = "ENTAILS"], edge[relation = "ENTAILS"], edge[type = "SUBSUMES"], edge[relation = "SUBSUMES"]',
          style: {
            width: 2.0,
            "line-color": "#f59e0b",
            "target-arrow-color": "#f59e0b",
            "target-arrow-shape": "triangle",
            color: "#b45309",
            "text-border-color": "#fde68a",
            "text-background-color": "#fffbeb",
          },
        },

        // Contradiction / Conflict
        {
          selector:
            'edge[type = "CONTRADICTS"], edge[relation = "CONTRADICTS"]',
          style: {
            width: 2.2,
            "line-style": "dashed",
            "line-dash-pattern": [4, 2],
            "line-color": "#e11d48",
            "target-arrow-color": "#e11d48",
            "target-arrow-shape": "tee",
            color: "#be123c",
            "text-border-color": "#fecdd3",
            "text-background-color": "#fff1f2",
          },
        },

        // ----------------------------------------------------
        // Interaction & Selection States
        // ----------------------------------------------------
        {
          selector: "node:active, node:hover, node.hover-node",
          style: {
            "border-width": 3.5,
            cursor: "pointer",
            "shadow-blur": 18,
            "shadow-color": "rgba(124, 58, 237, 0.35)",
            "shadow-offset-y": 3,
          },
        },
        {
          selector: "edge.hover-edge",
          style: {
            width: 2.8,
            "line-color": "#7c3aed",
            "target-arrow-color": "#7c3aed",
            color: "#5b21b6",
            "z-index": 90,
          },
        },
        {
          selector: "node.selected-node",
          style: {
            "border-width": 4,
            "border-color": "#7c3aed",
            "background-color": "#ffffff",
            "shadow-blur": 24,
            "shadow-color": "rgba(124, 58, 237, 0.45)",
            "shadow-offset-y": 4,
          },
        },
        {
          selector: "node.connected-node",
          style: {
            "border-width": 3,
            "border-color": "#9333ea",
          },
        },
        {
          selector: "edge.highlighted-edge",
          style: {
            "line-color": "#7c3aed",
            "target-arrow-color": "#7c3aed",
            width: 3.2,
            color: "#6d28d9",
            "text-border-color": "#c4b5fd",
            "text-background-color": "#f5f3ff",
            "z-index": 99,
          },
        },
        // Dedicated styling for multi-hop evidence and reasoning pathways
        {
          selector: "node.reasoning-path-node",
          style: {
            "border-width": 3.5,
            "border-color": "#0891b2",
            "shadow-blur": 20,
            "shadow-color": "rgba(8, 145, 178, 0.4)",
          },
        },
        {
          selector: "edge.reasoning-path-edge",
          style: {
            "line-color": "#0891b2",
            "target-arrow-color": "#0891b2",
            width: 3.2,
            color: "#0e7490",
            "text-border-color": "#a5f3fc",
            "text-background-color": "#ecfeff",
            "z-index": 98,
          },
        },
        // Dedicated styling for dynamic Proof Trace Path (Evidence -> Premise -> Rule -> Inference -> Conclusion)
        {
          selector: "node.proof-path-node",
          style: {
            "border-width": 4.0,
            "border-color": "#f59e0b",
            "shadow-blur": 26,
            "shadow-color": "rgba(245, 158, 11, 0.65)",
            "shadow-offset-y": 2,
            "z-index": 99,
            opacity: 1.0,
          },
        },
        {
          selector: "edge.proof-path-edge",
          style: {
            width: 3.6,
            "line-color": "#d97706",
            "target-arrow-color": "#d97706",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.25,
            "line-style": "solid",
            color: "#92400e",
            "font-weight": "bold",
            "text-background-color": "#fef3c7",
            "text-background-opacity": 1.0,
            "text-border-color": "#fde68a",
            "text-border-width": 1.5,
            "z-index": 100,
            opacity: 1.0,
          },
        },
        {
          selector: ".dimmed",
          style: {
            opacity: 0.12,
          },
        },
      ],
    });

    cyRef.current = cy;

    // Helper: set cursor on the Cytoscape canvas element
    const setCursor = (cursorValue) => {
      const canvas = containerRef.current?.querySelector("canvas");
      if (canvas) canvas.style.cursor = cursorValue;
    };

    // Node tap → show popup modal (nodes are permanently non-draggable)
    cy.on("tap", "node", (evt) => {
      const clickedNode = evt.target;
      const clickedId = clickedNode.id();
      const nodeData = clickedNode.data();

      setSelectedEdgeData(null);
      setFocusedCenterId(clickedId);
      setClickedNodeData(nodeData);

      const coords = getClickCoords(evt);
      if (coords) {
        setPopoverPos(calculateClampedPos(coords.x, coords.y, 380, 320));
      }

      // Bidirectional sync: If clicked node matches an evidence item, synchronize selection with Evidence panel
      if (contextEvidenceRecords && contextEvidenceRecords.length > 0 && contextSetSelectedEvidenceId) {
        const matchedEv = contextEvidenceRecords.find(
          (ev) =>
            String(ev.id) === String(clickedId) ||
            String(ev.passageId) === String(clickedId) ||
            String(ev.code) === String(clickedId) ||
            (Array.isArray(nodeData?.aliases) && nodeData.aliases.some((a) => String(a) === String(ev.id) || String(a) === String(ev.passageId))) ||
            (nodeData?.passageId && String(nodeData.passageId) === String(ev.passageId))
        );
        if (matchedEv) {
          contextSetSelectedEvidenceId(matchedEv.id);
        }
      }

      if (setSelectedNodeId) {
        setSelectedNodeId((prev) => {
          if (prev === clickedId) {
            setPopoverPos(null);
            setFocusedCenterId(null);
            setClickedNodeData(null);
            return null;
          }
          return clickedId;
        });
      }
    });

    // Edge click handler - displays detailed relationship properties
    cy.on("tap", "edge", (evt) => {
      const edge = evt.target;
      const edgeData = edge.data();
      if (setSelectedNodeId) setSelectedNodeId(null);
      setClickedNodeData(null);

      const coords = getClickCoords(evt);
      if (coords) {
        setPopoverPos(calculateClampedPos(coords.x, coords.y, 368, 260));
      }

      const sourceNode = cy.getElementById(edgeData.source);
      const targetNode = cy.getElementById(edgeData.target);
      setSelectedEdgeData({
        id: edge.id(),
        label: edgeData.label,
        type: edgeData.type || edgeData.relation,
        relation: edgeData.relation || edgeData.type,
        sourceId: edgeData.source,
        targetId: edgeData.target,
        sourceLabel: sourceNode.data("label") || edgeData.source,
        targetLabel: targetNode.data("label") || edgeData.target,
        confidence: edgeData.confidence,
        validationLevel: edgeData.validationLevel,
        sourceReference: edgeData.sourceReference,
        sourceCorpus: edgeData.sourceCorpus,
        passageId: edgeData.passageId,
        metadata: edgeData.metadata || {},
      });
    });

    // Hover highlighting on nodes + pointer cursor to indicate clickability
    cy.on("mouseover", "node", (evt) => {
      const node = evt.target;
      node.addClass("hover-node");
      node.connectedEdges().addClass("hover-edge");
      setCursor("pointer");
    });

    cy.on("mouseout", "node", (evt) => {
      const node = evt.target;
      node.removeClass("hover-node");
      node.connectedEdges().removeClass("hover-edge");
      setCursor("default");
    });

    // Hover highlighting on edges
    cy.on("mouseover", "edge", (evt) => {
      evt.target.addClass("hover-edge");
    });

    cy.on("mouseout", "edge", (evt) => {
      evt.target.removeClass("hover-edge");
    });

    // Canvas background click — clear all selections and popover
    cy.on("tap", (evt) => {
      if (evt.target === cy) {
        if (setSelectedNodeId) setSelectedNodeId(null);
        setClickedNodeData(null);
        setSelectedEdgeData(null);
        setPopoverPos(null);
        setFocusedCenterId(null);
      }
    });

    // Track pan & zoom updates; keep popover pinned to selected node
    cy.on("pan zoom", () => {
      setZoomLevelPercent(Math.round(cy.zoom() * 100));
      if (activeSelectedIdRef.current) {
        const selNode = cy.getElementById(String(activeSelectedIdRef.current));
        if (
          selNode &&
          selNode.length > 0 &&
          typeof selNode.renderedPosition === "function"
        ) {
          try {
            const rp = selNode.renderedPosition();
            if (rp && typeof rp.x === "number" && !isNaN(rp.x)) {
              setPopoverPos(calculateClampedPos(rp.x, rp.y, 380, 320));
            }
          } catch {
            // ignore
          }
        }
      }
    });

    // Run initial layout
    applyCytoscapeLayout(cy, currentLayout);

    // Initial centering and fit once DOM dimensions stabilize
    const fitTimer = setTimeout(() => {
      if (cy && !cy.destroyed()) {
        cy.resize();
        cy.fit(undefined, 45);
        setZoomLevelPercent(Math.round(cy.zoom() * 100));
      }
    }, 150);

    // ResizeObserver for responsive sizing
    const resizeObserver = new ResizeObserver(() => {
      if (cy && !cy.destroyed()) {
        cy.resize();
      }
    });
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      if (activeLayoutRef.current) {
        try {
          activeLayoutRef.current.stop();
        } catch {
          // ignore
        }
        activeLayoutRef.current = null;
      }
      clearTimeout(fitTimer);
      resizeObserver.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Update elements when nodes or edges change
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;

    if (activeLayoutRef.current) {
      try {
        activeLayoutRef.current.stop();
      } catch {
        // ignore
      }
      activeLayoutRef.current = null;
    }

    cy.batch(() => {
      cy.elements().remove();
      cy.add(cyElements);
    });

    applyCytoscapeLayout(cy, currentLayout);
  }, [cyElements, currentLayout, applyCytoscapeLayout]);

  // Layout change handler
  const handleLayoutChange = (layoutId) => {
    setCurrentLayout(layoutId);
    if (cyRef.current) {
      applyCytoscapeLayout(cyRef.current, layoutId);
    }
  };

  // Sync styling when activeSelectedId, focusedCenterId, activeCategoryFilter, hopDepth, or isShowingProofTrace changes
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;

    cy.batch(() => {
      cy.elements().removeClass(
        "selected-node connected-node highlighted-edge dimmed reasoning-path-node reasoning-path-edge proof-path-node proof-path-edge",
      );

      // Mode 1: Exact Nyāya Proof Trace Focus (E1 -> P1 -> E2 -> P2 -> R1 -> I1 -> C1)
      if (contextIsShowingProofTrace) {
        const proofNodesList = contextProofNodes || [];
        const proofNodeIdSet = new Set(proofNodesList.map((n) => String(n.id)));
        const proofNodesCollection = cy
          .nodes()
          .filter((n) => proofNodeIdSet.has(n.id()));

        const proofEdgesList = contextProofEdges || [];
        const proofEdgeIdSet = new Set(
          proofEdgesList
            .filter((e) => e.isProofTraceEdge !== false)
            .map((e) => String(e.id)),
        );
        const proofEdgesCollection = cy.edges().filter((e) => {
          const d = e.data();
          return (
            proofEdgeIdSet.has(e.id()) ||
            d.isProofTraceEdge ||
            (proofNodeIdSet.has(d.source) && proofNodeIdSet.has(d.target))
          );
        });

        proofNodesCollection.addClass("proof-path-node");
        proofEdgesCollection.addClass("proof-path-edge");

        const activeEles = proofNodesCollection.union(proofEdgesCollection);
        cy.elements().difference(activeEles).addClass("dimmed");

        // If a particular proof node or evidence is active, highlight it with selected ring and connected edges
        if (activeSelectedId) {
          let selNode = cy.getElementById(String(activeSelectedId));
          if (selNode.length === 0) {
            selNode = cy.nodes().filter((n) => {
              const d = n.data();
              return (
                String(d.id) === String(activeSelectedId) ||
                String(d.passageId) === String(activeSelectedId) ||
                (Array.isArray(d.aliases) && d.aliases.some((a) => String(a) === String(activeSelectedId))) ||
                (d.label && String(d.label).startsWith(String(activeSelectedId)))
              );
            });
          }
          if (selNode.length > 0) {
            selNode.addClass("selected-node");
            selNode.connectedEdges().addClass("highlighted-edge");
          }
        }
        return;
      }

      // Mode 2: Multi-hop Subgraph Traversal & Neighborhood Focus
      const centerNodeId = activeSelectedId || focusedCenterId;
      const hasCategoryFilter = !!activeCategoryFilter;

      if (centerNodeId) {
        let targetNode = cy.getElementById(String(centerNodeId));
        if (targetNode.length === 0) {
          targetNode = cy.nodes().filter((n) => {
            const d = n.data();
            return (
              String(d.id) === String(centerNodeId) ||
              String(d.passageId) === String(centerNodeId) ||
              String(d.sourceId) === String(centerNodeId) ||
              (Array.isArray(d.aliases) && d.aliases.some((a) => String(a) === String(centerNodeId))) ||
              (d.label && String(d.label).startsWith(String(centerNodeId)))
            );
          });
        }
        if (targetNode.length > 0) {
          const pathNodes = cy.collection();
          pathNodes.merge(targetNode);

          cy.elements().bfs({
            root: targetNode,
            directed: false,
            visit: (v, e, u, i, depth) => {
              if (depth > hopDepth) return false;
              pathNodes.merge(v);
            },
          });

          // Induced edges: all edges whose source AND target are in pathNodes
          const pathEdges = pathNodes.connectedEdges().filter((edge) => {
            return pathNodes.has(edge.source()) && pathNodes.has(edge.target());
          });

          const isReasoning =
            ["Evidence", "Premise", "Rule", "Inference", "Conclusion"].includes(
              targetNode.data("type"),
            ) ||
            ["Evidence", "Premise", "Rule", "Inference", "Conclusion"].includes(
              targetNode.data("category"),
            ) ||
            Boolean(targetNode.data("isEvidenceRecord"));

          if (isReasoning) {
            targetNode.addClass("selected-node reasoning-path-node");
            pathNodes.difference(targetNode).addClass("connected-node reasoning-path-node");
            pathEdges.addClass("highlighted-edge reasoning-path-edge");
          } else {
            targetNode.addClass("selected-node");
            pathNodes.difference(targetNode).addClass("connected-node");
            pathEdges.addClass("highlighted-edge");
          }

          cy.elements()
            .difference(pathNodes)
            .difference(pathEdges)
            .addClass("dimmed");
        }
      } else if (hasCategoryFilter) {
        const matchingNodes = cy.nodes(
          `[category = "${activeCategoryFilter}"], [type = "${activeCategoryFilter}"]`,
        );
        const matchingEdges = matchingNodes.connectedEdges();

        cy.elements()
          .difference(matchingNodes)
          .difference(matchingEdges)
          .addClass("dimmed");
      }
    });

    // Smooth animated camera focus when user activates Proof Trace mode or selects a node/passage
    if (contextIsShowingProofTrace) {
      const proofNodesList = contextProofNodes || [];
      const proofNodeIdSet = new Set(proofNodesList.map((n) => String(n.id)));
      const proofEles = cy.elements().filter((ele) => {
        if (ele.isNode()) return proofNodeIdSet.has(ele.id());
        const d = ele.data();
        return proofNodeIdSet.has(d.source) && proofNodeIdSet.has(d.target);
      });
      if (proofEles.length > 0) {
        cy.animate({
          fit: { eles: proofEles, padding: 50 },
          duration: 500,
        });
      }
    } else if (activeSelectedId) {
      const targetId = String(activeSelectedId);
      let targetNode = cy.getElementById(targetId);
      if (targetNode.length === 0) {
        targetNode = cy.nodes().filter((n) => {
          const d = n.data();
          return (
            String(d.id) === targetId ||
            String(d.sourceId) === targetId ||
            String(d.passageId) === targetId ||
            (Array.isArray(d.aliases) && d.aliases.some((a) => String(a) === targetId)) ||
            (d.label && String(d.label).startsWith(targetId))
          );
        });
      }
      if (targetNode.length > 0) {
        const neighborhood = targetNode.closedNeighborhood();
        cy.animate({
          fit: { eles: neighborhood.length > 1 ? neighborhood : targetNode, padding: 60 },
          duration: 400,
        });
      }
    }
  }, [
    activeSelectedId,
    focusedCenterId,
    activeCategoryFilter,
    hopDepth,
    contextIsShowingProofTrace,
    contextProofNodes,
    contextProofEdges,
  ]);

  // Synchronize popover positioning when activeSelectedId changes externally (e.g. from query/evidence panel)
  useEffect(() => {
    if (!activeSelectedId) {
      const frameId = requestAnimationFrame(() => {
        setClickedNodeData(null);
        setPopoverPos(null);
      });
      return () => cancelAnimationFrame(frameId);
    }

    const frameId = requestAnimationFrame(() => {
      if (cyRef.current && !cyRef.current.destroyed()) {
        const cyNode = cyRef.current.getElementById(String(activeSelectedId));
        if (
          cyNode &&
          cyNode.length > 0 &&
          typeof cyNode.renderedPosition === "function"
        ) {
          try {
            const rPos = cyNode.renderedPosition();
            if (rPos && typeof rPos.x === "number" && !isNaN(rPos.x)) {
              setPopoverPos(
                (prev) => prev || calculateClampedPos(rPos.x, rPos.y, 380, 320),
              );
            }
          } catch {
            // ignore
          }
        }
      }
    });
    return () => cancelAnimationFrame(frameId);
  }, [activeSelectedId, calculateClampedPos]);

  // Toolbar Actions
  const handleZoomIn = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 1.25,
        renderedPosition: {
          x: cyRef.current.width() / 2,
          y: cyRef.current.height() / 2,
        },
      });
      setZoomLevelPercent(Math.round(cyRef.current.zoom() * 100));
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (cyRef.current) {
      cyRef.current.zoom({
        level: cyRef.current.zoom() * 0.8,
        renderedPosition: {
          x: cyRef.current.width() / 2,
          y: cyRef.current.height() / 2,
        },
      });
      setZoomLevelPercent(Math.round(cyRef.current.zoom() * 100));
    }
  }, []);

  const handleFit = useCallback(() => {
    if (cyRef.current && !cyRef.current.destroyed()) {
      cyRef.current.elements().removeClass("dimmed");
      cyRef.current.fit(undefined, 40);
      setZoomLevelPercent(Math.round(cyRef.current.zoom() * 100));
    }
  }, []);

  const handleToggleProofTrace = useCallback(() => {
    if (contextIsShowingProofTrace) {
      if (contextShowProofTrace) contextShowProofTrace();
    }
  }, [contextIsShowingProofTrace, contextShowProofTrace]);

  const handleAppendToQuery = (node) => {
    if (!setQueryText) return;
    setQueryText((prev) => {
      if (!prev.trim())
        return `தொல்காப்பியத்தில் ${node.label} (${node.transliteration}) நெறி யாது?`;
      if (prev.includes(node.label)) return prev;
      return `${prev} — ${node.label}`;
    });
  };

  // Dynamically compute legend categories based on active raw nodes & backend categories
  const displayCategories = useMemo(() => {
    if (propCategories && propCategories.length > 0) return propCategories;
    if (backendData?.categories && backendData.categories.length > 0) {
      return backendData.categories.map((c) => ({
        id: c.id,
        label: c.name || c.label || c.id,
        dot: c.dot || "bg-purple-600",
        count: rawNodes.filter((n) => n.category === c.id || n.type === c.id)
          .length,
      }));
    }
    const countMap = {};
    rawNodes.forEach((n) => {
      const cat = n.category || n.type || "Concept";
      countMap[cat] = (countMap[cat] || 0) + 1;
    });
    return Object.entries(countMap).map(([cat, cnt]) => {
      let dotColor = "bg-slate-400";
      if (cat === "Literature") dotColor = "bg-slate-800";
      else if (cat === "Work") dotColor = "bg-indigo-600";
      else if (cat === "Section") dotColor = "bg-slate-600";
      else if (cat === "Passage") dotColor = "bg-sky-600";
      else if (cat === "Concept") dotColor = "bg-emerald-600";
      else if (cat === "Entity") dotColor = "bg-rose-600";
      else if (cat === "Person") dotColor = "bg-fuchsia-600";
      else if (cat === "Object") dotColor = "bg-blue-600";
      else if (cat === "Event") dotColor = "bg-amber-600";
      else if (cat === "Evidence") dotColor = "bg-cyan-600";
      else if (cat === "Premise") dotColor = "bg-purple-600";
      else if (cat === "Rule") dotColor = "bg-blue-600";
      else if (cat === "Inference") dotColor = "bg-purple-700";
      else if (cat === "Conclusion") dotColor = "bg-emerald-700";

      return {
        id: cat,
        label: cat,
        dot: dotColor,
        count: cnt,
      };
    });
  }, [propCategories, backendData, rawNodes]);

  return (
    <div
      className={`bg-white rounded-2xl border border-slate-200 shadow-xs border-t-4 border-t-indigo-600 flex flex-col ${height} transition-all overflow-hidden relative ${className}`}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 sm:px-5 py-3 border-b border-slate-100 bg-slate-50/70">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-1.5 rounded-lg bg-purple-50 text-purple-700 border border-purple-200/70 shrink-0">
            <Network className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-xs sm:text-sm font-bold text-slate-900 tracking-tight truncate">
                KNOWLEDGE GRAPH VIEWER
              </h2>
           
              {/* Dynamic Backend Connection Badge */}
              {isLoadingBackend ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-200 animate-pulse">
                  <RefreshCw className="w-2.5 h-2.5 animate-spin" />
                  Syncing Flask...
                </span>
              ) : backendSource === "neo4j_aura" ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                  Flask API (Neo4j Aura)
                </span>
              ) : backendSource === "in_memory_kg" ? (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                  Flask API (In-Memory KG)
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-600 border border-slate-200">
                  <span className="w-1.5 h-1.5 rounded-full bg-slate-400 shrink-0" />
                  Local Context Cache
                </span>
              )}
              {backendError && (
                <span
                  className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] bg-amber-50 text-amber-700 border border-amber-200"
                  title={backendError}
                >
                  <AlertTriangle className="w-2.5 h-2.5 text-amber-600" />
                  <span>Offline Fallback</span>
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500 truncate mt-0.5">
              {canonicalStats.isFiltered ? (
                <>
                  Classical Tamil Ontology:{" "}
                  <span className="font-semibold text-purple-700">
                    {canonicalStats.renderedEntities}
                  </span>{" "}
                  of {canonicalStats.totalEntities} Entities •{" "}
                  <span className="font-semibold text-purple-700">
                    {canonicalStats.renderedEdges}
                  </span>{" "}
                  of {canonicalStats.totalEdges} Relational Edges
                  <span className="inline-flex items-center px-1.5 py-0.2 rounded text-[10px] bg-purple-50 text-purple-700 border border-purple-200 font-medium ml-1.5">
                    Filtered
                  </span>
                </>
              ) : (
                <>
                  Classical Tamil Ontology: {canonicalStats.totalEntities}{" "}
                  Entities • {canonicalStats.totalEdges} Relational Edges
                </>
              )}
              {focusedCenterId && (
                <span className="ml-1 text-purple-700 font-semibold font-mono">
                  (Focused: #{focusedCenterId})
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Toolbar Controls */}
        {showToolbar && (
          <div className="flex items-center gap-1.5 shrink-0 flex-wrap">
            {/* Show Proof Trace Action Button */}
            <button
              type="button"
              onClick={handleToggleProofTrace}
              className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-[11px] font-bold transition-all cursor-pointer shadow-2xs ${
                contextIsShowingProofTrace
                  ? "bg-amber-500 text-white hover:bg-amber-600 ring-2 ring-amber-400/40"
                  : "bg-white text-slate-700 hover:text-amber-800 hover:bg-amber-50/80 border border-slate-200/90"
              }`}
              title="Focus graph on Nyāya Proof Trace (Evidence → Premise → Rule → Inference → Conclusion)"
            >
              <Sparkles
                className={`w-3.5 h-3.5 ${contextIsShowingProofTrace ? "text-white" : "text-amber-600"}`}
              />
              <span>
                {contextIsShowingProofTrace
                  ? "Proof Trace Active"
                  : "Show Proof Trace"}
              </span>
            </button>

            {/* Layout Selector Dropdown */}
            <div className="relative inline-flex items-center">
              <Layers className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={currentLayout}
                onChange={(e) => handleLayoutChange(e.target.value)}
                className="appearance-none text-[11px] font-semibold bg-white hover:bg-purple-50/50 text-purple-950 pl-7 pr-7 py-1.5 rounded-xl border border-purple-200/90 hover:border-purple-400 shadow-2xs focus:ring-2 focus:ring-purple-500/25 focus:border-purple-500 focus:outline-none transition-all cursor-pointer"
                title="Select Cytoscape Automatic Layout Algorithm"
              >
                {LAYOUT_OPTIONS.map((l) => (
                  <option
                    key={l.id}
                    value={l.id}
                    className="bg-white text-slate-800 py-1"
                  >
                    {l.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-purple-500 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* Zoom / Fit Group */}
            <div className="flex items-center gap-0.5 bg-white border border-slate-200/90 rounded-xl p-0.5 shadow-2xs">
              <button
                type="button"
                onClick={handleZoomIn}
                className="p-1.5 rounded-lg text-slate-600 hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
                title="Zoom In"
                aria-label="Zoom In"
              >
                <ZoomIn className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleZoomOut}
                className="p-1.5 rounded-lg text-slate-600 hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
                title="Zoom Out"
                aria-label="Zoom Out"
              >
                <ZoomOut className="w-3.5 h-3.5" />
              </button>
              <button
                type="button"
                onClick={handleFit}
                className="p-1.5 rounded-lg text-slate-600 hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
                title="Fit to Screen"
                aria-label="Fit to Screen"
              >
                <Maximize2 className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Interactive Search, Node Type Filter & Multi-Hop Controls Bar */}
      {showToolbar && (
        <div className="flex items-center justify-between px-4 sm:px-5 py-2 bg-slate-50/50 border-b border-slate-100 gap-2 flex-wrap text-xs">
          <div className="flex items-center gap-2 flex-1 min-w-[220px] sm:min-w-[300px]">
            {/* Real-time Search Input */}
            <div className="relative flex-1">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search Tamil term, entity, verse, id..."
                className="w-full text-[11px] bg-white text-slate-700 pl-8 pr-7 py-1 rounded-xl border border-slate-200/90 shadow-2xs placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-purple-400 hover:border-slate-300"
              />
              {searchText && (
                <button
                  type="button"
                  onClick={() => setSearchText("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
                  title="Clear search"
                >
                  <X className="w-3 h-3" />
                </button>
              )}
            </div>

            {/* Node Type Filter Dropdown */}
            <div className="relative inline-flex items-center">
              <Filter className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={selectedNodeTypeFilter}
                onChange={(e) => setSelectedNodeTypeFilter(e.target.value)}
                className="appearance-none text-[11px] font-semibold bg-white hover:bg-purple-50/50 text-purple-950 pl-7 pr-7 py-1.5 rounded-xl border border-purple-200/90 hover:border-purple-400 shadow-2xs focus:ring-2 focus:ring-purple-500/25 focus:border-purple-500 focus:outline-none transition-all cursor-pointer"
                title="Filter by Node Type"
              >
                <option value="ALL" className="bg-white text-slate-800 py-1">
                  All Types
                </option>
                {availableNodeTypes.map((type) => (
                  <option
                    key={type}
                    value={type}
                    className="bg-white text-slate-800 py-1"
                  >
                    {type}
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-purple-500 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>

            {/* Category Filter Dropdown */}
            <div className="relative inline-flex items-center">
              <Tag className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              <select
                value={activeCategoryFilter || "ALL"}
                onChange={(e) => {
                  const val = e.target.value === "ALL" ? null : e.target.value;
                  if (setActiveCategoryFilter) setActiveCategoryFilter(val);
                }}
                className="appearance-none text-[11px] font-semibold bg-white hover:bg-purple-50/50 text-purple-950 pl-7 pr-7 py-1.5 rounded-xl border border-purple-200/90 hover:border-purple-400 shadow-2xs focus:ring-2 focus:ring-purple-500/25 focus:border-purple-500 focus:outline-none transition-all cursor-pointer max-w-[180px] truncate"
                title="Filter by Category"
              >
                <option value="ALL" className="bg-white text-slate-800 py-1">
                  All Categories ({rawNodes.length})
                </option>
                {displayCategories.map((cat) => (
                  <option
                    key={cat.id}
                    value={cat.id}
                    className="bg-white text-slate-800 py-1"
                  >
                    {cat.label} ({cat.count})
                  </option>
                ))}
              </select>
              <ChevronDown className="w-3.5 h-3.5 text-purple-500 absolute right-2 top-1/2 -translate-y-1/2 pointer-events-none" />
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Configurable Multi-hop Depth Selector (1 to 5 Hops matching Query Center) */}
            <div className="flex items-center gap-1.5 bg-white px-2 py-0.5 rounded-xl border border-slate-200/90 shadow-2xs">
              <GitBranch className="w-3.5 h-3.5 text-purple-600" />
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Hops:
              </span>
              {[1, 2, 3, 4, 5].map((hops) => (
                <button
                  key={hops}
                  type="button"
                  onClick={() => {
                    setHopDepth(hops);
                    const targetId = getFallbackCenterId();
                    setFocusedCenterId(targetId);
                    if (fetchFromBackend) {
                      fetchGraphData(targetId, hops);
                    }
                  }}
                  className={`px-2 py-0.5 rounded text-[10px] font-bold transition-colors cursor-pointer ${
                    hopDepth === hops
                      ? "bg-purple-600 text-white shadow-2xs"
                      : "text-slate-600 hover:bg-slate-100"
                  }`}
                  title={`Traverse ${hops}-hop neighborhood around ${activeSelectedId || focusedCenterId || "core ontology"}`}
                >
                  {hops}
                </button>
              ))}
            </div>

            {/* Reset Filters Quick Pill */}
            {(searchText ||
              selectedNodeTypeFilter !== "ALL" ||
              activeCategoryFilter) && (
              <button
                type="button"
                onClick={() => {
                  setSearchText("");
                  setSelectedNodeTypeFilter("ALL");
                  if (setActiveCategoryFilter) setActiveCategoryFilter(null);
                }}
                className="text-[10px] text-purple-700 hover:text-purple-900 bg-purple-50 hover:bg-purple-100 font-semibold px-2 py-1 rounded-lg border border-purple-200 cursor-pointer transition-colors"
                title="Reset Search and Filters"
              >
                Reset Filters
              </button>
            )}
          </div>
        </div>
      )}

      {/* Cytoscape Canvas Container */}
      <div className="relative flex-1 min-h-[360px] sm:min-h-[420px] bg-[#fbfcfe] overflow-hidden select-none">
        {/* Subtle grid background pattern */}
        <div
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(#94a3b8 0.75px, transparent 0.75px)",
            backgroundSize: "24px 24px",
          }}
        />

        {/* Cytoscape Canvas Mount Target */}
        <div
          ref={containerRef}
          className="w-full h-full cursor-grab active:cursor-grabbing"
        />

        {/* State 1: Loading Overlay */}
        {(contextIsAnalyzing || isLoadingBackend) && (
          <div className="absolute inset-0 z-30 bg-white/80 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-150">
            <div className="p-3 bg-purple-100/90 text-purple-700 rounded-2xl border border-purple-200/80 shadow-md mb-3 animate-pulse">
              <RefreshCw className="w-6 h-6 animate-spin text-purple-600" />
            </div>
            <h3 className="text-sm font-bold text-slate-800 tracking-tight">
              {contextIsAnalyzing
                ? `Synthesizing Tolkāppiyam Nyāya Proof Trace... (${contextWorkflowProgressPercent || 0}%)`
                : "Querying Flask & Neo4j Aura Graph Engine..."}
            </h3>
            <p className="text-xs text-slate-500 max-w-sm mt-1">
              {contextIsAnalyzing
                ? contextCurrentWorkflowStage?.desc ||
                  "Grounding Tiṇai invariants and structuring multi-hop reasoning DAG"
                : "Retrieving canonical verses, ontological entities, and relational edges"}
            </p>
          </div>
        )}

        {/* State 2: Empty State Overlay */}
        {!isLoadingBackend &&
          !contextIsAnalyzing &&
          cyElements.length === 0 && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center bg-slate-50/90">
              <div className="p-3 bg-slate-100 text-slate-500 rounded-2xl border border-slate-200 shadow-2xs mb-3">
                <Network className="w-8 h-8 stroke-[1.5]" />
              </div>
              <h3 className="text-sm font-bold text-slate-800">
                No Graph Nodes Match
              </h3>
              <p className="text-xs text-slate-500 max-w-xs mt-1 mb-4">
                {searchText
                  ? `No entities found matching "${searchText}". Try adjusting your search or clear filters.`
                  : "No graph entities are currently active for this filter."}
              </p>
              <div className="flex items-center gap-2">
                {(searchText || selectedNodeTypeFilter !== "ALL") && (
                  <button
                    type="button"
                    onClick={() => {
                      setSearchText("");
                      setSelectedNodeTypeFilter("ALL");
                    }}
                    className="px-3 py-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-colors cursor-pointer"
                  >
                    Clear Filters
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => {
                    if (contextLoadBenchmarkEvidence)
                      contextLoadBenchmarkEvidence();
                    handleFit();
                  }}
                  className="px-3 py-1.5 text-xs font-semibold text-white bg-purple-600 hover:bg-purple-700 rounded-lg shadow-2xs transition-colors cursor-pointer"
                >
                  Load Benchmark Graph
                </button>
              </div>
            </div>
          )}

        {/* State 3: API Error Banner */}
        {backendError && (
          <div className="absolute top-2 left-3 right-3 sm:left-4 sm:right-auto sm:max-w-md z-25 bg-amber-50/95 backdrop-blur-md border border-amber-200 text-amber-900 rounded-xl p-2.5 shadow-md flex items-start gap-2.5 text-xs animate-in fade-in slide-in-from-top-2 duration-150">
            <AlertTriangle className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <div className="font-semibold text-amber-900 flex items-center justify-between">
                <span>Flask Backend API Offline</span>
                <button
                  type="button"
                  onClick={() => setBackendError(null)}
                  className="text-amber-500 hover:text-amber-700 p-0.5 cursor-pointer"
                  title="Dismiss"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              <p className="text-[11px] text-amber-800 mt-0.5 leading-snug">
                Falling back to local verified Classical Tamil Ontology cache.
                Neo4j live queries paused.
              </p>
              <div className="mt-1.5 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => fetchGraphData(focusedCenterId, hopDepth)}
                  disabled={isLoadingBackend}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-600 hover:bg-amber-700 text-white transition-colors cursor-pointer disabled:opacity-50"
                >
                  <RefreshCw
                    className={`w-2.5 h-2.5 ${isLoadingBackend ? "animate-spin" : ""}`}
                  />
                  Retry Sync
                </button>
              </div>
            </div>
          </div>
        )}

        {/* State 4: Insufficient Evidence Alert */}
        {contextInsufficientEvidence && (
          <div className="absolute top-2 left-3 right-3 sm:left-4 sm:right-auto sm:max-w-lg z-25 bg-amber-500/10 backdrop-blur-md border border-amber-400/80 text-amber-950 rounded-xl p-3 shadow-lg flex items-start gap-2.5 text-xs animate-in fade-in slide-in-from-top-2 duration-150">
            <div className="p-1 bg-amber-100 rounded-lg text-amber-700 shrink-0">
              <AlertTriangle className="w-4 h-4 text-amber-600" />
            </div>
            <div className="flex-1 min-w-0">
              <div className="font-bold text-amber-900 flex items-center justify-between">
                <span>Insufficient Evidence for Complete Deduction</span>
                <button
                  type="button"
                  onClick={() =>
                    contextSetInsufficientEvidence &&
                    contextSetInsufficientEvidence(false)
                  }
                  className="text-amber-600 hover:text-amber-900 p-0.5 cursor-pointer"
                  title="Dismiss"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              <p className="text-[11px] text-amber-800 mt-1 leading-snug">
                The current query retrieved insufficient canonical sūtras to
                establish an invariant Nyāya proof chain. At least 2 grounded
                verses are required to derive Vyāpti.
              </p>
              <div className="mt-2 flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    if (contextLoadBenchmarkEvidence)
                      contextLoadBenchmarkEvidence();
                  }}
                  className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-amber-600 hover:bg-amber-700 text-white shadow-2xs transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3 h-3" />
                  Load Benchmark Evidence & Complete Proof
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Zoom Level Indicator */}
        <div className="absolute top-2.5 right-3 text-[10px] font-mono text-slate-400 bg-white/80 backdrop-blur-xs px-2 py-0.5 rounded-md border border-slate-200/60 shadow-2xs pointer-events-none">
          {zoomLevelPercent}%
        </div>

        {/* Node Information Card Overlay (Appears when a node is selected) */}
        {selectedNode && (
          <div
            style={
              popoverPos
                ? {
                    left: `${popoverPos.left}px`,
                    top: `${popoverPos.top}px`,
                    width: `${popoverPos.width}px`,
                  }
                : undefined
            }
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            className={`absolute ${
              popoverPos ? "" : "bottom-3 left-3 right-3 sm:right-auto sm:w-96"
            } bg-white/95 backdrop-blur-md rounded-xl border border-purple-200 shadow-2xl p-3.5 z-30 animate-in fade-in zoom-in-95 duration-150 text-xs max-h-[85%] overflow-y-auto`}
          >
            <div className="flex items-start justify-between gap-2 pb-2 mb-2 border-b border-slate-100">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="tamil-font font-bold text-sm text-slate-900">
                    {selectedNode.label || selectedNode.name}
                  </span>
                  {selectedNode.transliteration && (
                    <span className="text-[11px] font-mono text-slate-500">
                      ({selectedNode.transliteration})
                    </span>
                  )}
                </div>
                <div className="flex flex-wrap items-center gap-1.5 mt-1">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                      CATEGORY_STYLES[selectedNode.category]?.badgeBg ||
                      CATEGORY_STYLES[selectedNode.type]?.badgeBg ||
                      "bg-slate-100 text-slate-800"
                    }`}
                  >
                    {selectedNode.category || selectedNode.type || "Concept"}
                  </span>
                  {selectedNode.hierarchy_level && (
                    <span className="text-[10px] font-mono bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded border border-slate-200 font-semibold">
                      {selectedNode.hierarchy_level}
                    </span>
                  )}
                  {selectedNode.confidence !== undefined && (
                    <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200">
                      {Math.round(selectedNode.confidence * 100)}% conf
                    </span>
                  )}
                  {selectedNode.role && (
                    <span className="text-[10px] text-slate-500 font-medium truncate max-w-[150px]">
                      • {selectedNode.role}
                    </span>
                  )}
                </div>
              </div>

              <button
                type="button"
                onClick={() => {
                  if (setSelectedNodeId) setSelectedNodeId(null);
                  setClickedNodeData(null);
                  setPopoverPos(null);
                  setFocusedCenterId(null);
                }}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                title="Close"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Description / Text */}
            {(selectedNode.description || selectedNode.text) && (
              <p className="text-[11px] text-slate-600 leading-relaxed mb-2.5 max-h-24 overflow-y-auto">
                {selectedNode.description || selectedNode.text}
              </p>
            )}

            {/* Provenance & Sūtra/Verse details */}
            <div className="bg-slate-50 rounded-lg p-2 border border-slate-200 space-y-1 text-[10px] mb-2.5">
              {(selectedNode.source_reference || selectedNode.source) && (
                <div className="flex items-start justify-between gap-1 text-slate-600">
                  <span className="font-semibold text-slate-700">
                    Source Provenance:
                  </span>
                  <span className="font-mono text-purple-700 text-right truncate">
                    {selectedNode.source_reference || selectedNode.source}
                  </span>
                </div>
              )}
              {(selectedNode.work_name ||
                selectedNode.section_name ||
                selectedNode.chapter_name) && (
                <div className="flex items-start justify-between gap-1 text-slate-600">
                  <span className="font-semibold text-slate-700">
                    Hierarchy:
                  </span>
                  <span className="text-right truncate text-slate-700">
                    {[
                      selectedNode.work_name,
                      selectedNode.section_name,
                      selectedNode.chapter_name,
                    ]
                      .filter(Boolean)
                      .join(" › ")}
                  </span>
                </div>
              )}
              {(selectedNode.sutra_number || selectedNode.verse_number) && (
                <div className="flex items-center justify-between text-slate-600">
                  <span className="font-semibold text-slate-700">
                    Verse / Sūtra:
                  </span>
                  <span className="font-mono text-slate-800 font-semibold">
                    #{selectedNode.sutra_number || selectedNode.verse_number}
                  </span>
                </div>
              )}
              <div className="flex items-center justify-between text-slate-500 font-mono pt-0.5 border-t border-slate-200/60">
                <span className="truncate pr-1">ID: {selectedNode.id}</span>
                <span className="text-purple-700 font-bold shrink-0">
                  {connectedEdgeCount} Linked Edges
                </span>
              </div>
            </div>

            {/* Actions: Focus in Query & Expand Subgraph */}
            <div className="grid grid-cols-2 gap-1.5">
              {setQueryText && (
                <button
                  type="button"
                  onClick={() => handleAppendToQuery(selectedNode)}
                  className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-900 font-semibold text-[11px] transition-colors cursor-pointer"
                >
                  <Plus className="w-3 h-3 text-purple-600" />
                  <span>Focus in Query</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => fetchGraphData(selectedNode.id, hopDepth)}
                className="flex items-center justify-center gap-1 py-1.5 rounded-lg bg-blue-50 hover:bg-blue-100 border border-blue-200 text-blue-900 font-semibold text-[11px] transition-colors cursor-pointer"
                title={`Extract ${hopDepth}-hop neighborhood from Neo4j Aura`}
              >
                <Compass className="w-3 h-3 text-blue-600" />
                <span>Expand Subgraph ({hopDepth}-hop)</span>
              </button>
            </div>
          </div>
        )}

        {/* Edge Inspection Overlay (Appears when an edge is clicked) */}
        {selectedEdgeData && !selectedNode && (
          <div
            style={
              popoverPos
                ? {
                    left: `${popoverPos.left}px`,
                    top: `${popoverPos.top}px`,
                    width: `${popoverPos.width}px`,
                  }
                : undefined
            }
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
            className={`absolute ${
              popoverPos ? "" : "bottom-3 left-3 right-3 sm:right-auto sm:w-92"
            } bg-white/95 backdrop-blur-md rounded-xl border border-purple-200 shadow-2xl p-3 z-30 animate-in fade-in zoom-in-95 duration-150 text-xs max-h-[85%] overflow-y-auto`}
          >
            <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-100">
              <div className="flex items-center gap-1.5 font-bold text-slate-900">
                <Info className="w-3.5 h-3.5 text-purple-600" />
                <span>NEO4J RELATIONSHIP PROVENANCE</span>
              </div>
              <button
                type="button"
                onClick={() => {
                  setSelectedEdgeData(null);
                  setPopoverPos(null);
                }}
                className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
                title="Close"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>

            <div className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-slate-200 text-[11px] mb-2">
              <span className="font-semibold text-slate-800 tamil-font truncate max-w-[38%]">
                {selectedEdgeData.sourceLabel}
              </span>
              <div className="flex items-center gap-1 font-mono text-purple-700 font-bold text-[10px] px-1.5 py-0.5 bg-purple-50 rounded border border-purple-200 shrink-0">
                <ArrowRight className="w-3 h-3 text-purple-500" />
                <span>
                  {selectedEdgeData.type || selectedEdgeData.relation}
                </span>
                <ArrowRight className="w-3 h-3 text-purple-500" />
              </div>
              <span className="font-semibold text-slate-800 tamil-font truncate max-w-[38%]">
                {selectedEdgeData.targetLabel}
              </span>
            </div>

            <div className="space-y-1 bg-slate-50 rounded-lg p-2 border border-slate-200 text-[10px] text-slate-600 mb-1">
              {selectedEdgeData.sourceCorpus && (
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">Corpus:</span>
                  <span className="font-mono text-slate-800">
                    {selectedEdgeData.sourceCorpus}
                  </span>
                </div>
              )}
              {selectedEdgeData.sourceReference && (
                <div className="flex items-start justify-between gap-1">
                  <span className="font-semibold text-slate-700">
                    Source Reference:
                  </span>
                  <span className="font-mono text-purple-700 text-right truncate">
                    {selectedEdgeData.sourceReference}
                  </span>
                </div>
              )}
              {selectedEdgeData.validationLevel && (
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">
                    Validation Level:
                  </span>
                  <span className="font-mono bg-emerald-50 text-emerald-700 px-1 rounded border border-emerald-200">
                    {selectedEdgeData.validationLevel}
                  </span>
                </div>
              )}
              {selectedEdgeData.confidence !== undefined && (
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">
                    Edge Confidence:
                  </span>
                  <span className="font-mono text-slate-800 font-bold">
                    {Math.round(selectedEdgeData.confidence * 100)}%
                  </span>
                </div>
              )}
              {selectedEdgeData.passageId && (
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-700">
                    Passage ID:
                  </span>
                  <span className="font-mono text-purple-700">
                    {selectedEdgeData.passageId}
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Compact 1-Line Status Footer (Saves UI Vertical Space) */}
      {showLegend && (
        <div className="px-4 py-2 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 gap-2">
          <div className="flex items-center gap-2 truncate">
            <span className="font-medium text-slate-700">
              {canonicalStats.isFiltered ? (
                <>
                  Ontology Graph: {canonicalStats.renderedEntities} of{" "}
                  {canonicalStats.totalEntities} Nodes •{" "}
                  {canonicalStats.renderedEdges} of {canonicalStats.totalEdges}{" "}
                  Relational Edges
                </>
              ) : (
                <>
                  Ontology Graph: {canonicalStats.totalEntities} Nodes •{" "}
                  {canonicalStats.totalEdges} Relational Edges
                </>
              )}
            </span>
            {activeCategoryFilter && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-100 text-purple-800 text-[10px] font-semibold border border-purple-200">
                <span>Category: {activeCategoryFilter}</span>
                <button
                  type="button"
                  onClick={() =>
                    setActiveCategoryFilter && setActiveCategoryFilter(null)
                  }
                  className="hover:text-purple-950 cursor-pointer ml-0.5"
                  title="Clear category filter"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            )}
            {(activeSelectedId || focusedCenterId) && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-purple-100 text-purple-800 text-[10px] font-semibold border border-purple-200">
                <GitBranch className="w-2.5 h-2.5 text-purple-600" />
                <span>
                  {hopDepth}-Hop Focus:{" "}
                  {(() => {
                    const targetId = activeSelectedId || focusedCenterId;
                    const found = rawNodes.find((n) => n.id === targetId);
                    const lbl = found?.label || found?.name || targetId;
                    return typeof lbl === "object" ? (lbl?.label || lbl?.name || String(targetId)) : String(lbl);
                  })()}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    if (setSelectedNodeId) setSelectedNodeId(null);
                    setFocusedCenterId(null);
                  }}
                  className="hover:text-purple-950 cursor-pointer ml-0.5"
                  title="Clear hops focus"
                >
                  <X className="w-2.5 h-2.5" />
                </button>
              </span>
            )}
          </div>
          <div className="hidden sm:flex items-center gap-2 text-[10px] font-mono text-slate-400 shrink-0">
            <span>
              Layout:{" "}
              {LAYOUT_OPTIONS.find((l) => l.id === currentLayout)?.label ||
                currentLayout}
            </span>
            <span>•</span>
            <span>Zoom: {zoomLevelPercent}%</span>
          </div>
        </div>
      )}
    </div>
  );
}
