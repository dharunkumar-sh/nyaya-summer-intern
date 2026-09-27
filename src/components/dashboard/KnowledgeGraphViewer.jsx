import { useRef, useEffect, useState, useMemo, useCallback } from "react";
import * as d3 from "d3";
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  Crosshair,
  Network,
  X,
  Layers,
  Info,
  ArrowRight,
  RefreshCw,
  RotateCcw,
  Compass,
  AlertTriangle,
  Search,
  Filter,
  ChevronDown,
  GitBranch,
  Sparkles,
  Activity,
  Eye,
  Share2,
  Zap,
  BookOpen,
  ChevronRight,
  CheckCircle2,
  FileText,
} from "lucide-react";
import { useReasoner } from "../../context/ReasonerContext";
import { graphApi } from "../../services/apiClient";
import {
  normalizeGraphData,
  extractNodeId,
} from "../../services/graphNormalization";
import {
  findNodeByStableId,
  getInducedSubgraphNeighborhood,
} from "../../services/nodeSyncService";

const CATEGORY_STYLES = {
  // Literary Hierarchy Entities
  Literature: {
    fill: "#f8fafc",
    stroke: "#1e293b",
    text: "#0f172a",
    badgeBg: "bg-slate-100 text-slate-900 border-slate-300 font-semibold",
    shape: "rect",
    width: 96,
    height: 52,
    radius: 38,
  },
  Work: {
    fill: "#eef2ff",
    stroke: "#4f46e5",
    text: "#312e81",
    badgeBg: "bg-indigo-100 text-indigo-900 border-indigo-200 font-semibold",
    shape: "rect",
    width: 86,
    height: 48,
    radius: 34,
  },
  Section: {
    fill: "#f1f5f9",
    stroke: "#475569",
    text: "#0f172a",
    badgeBg: "bg-slate-100 text-slate-800 border-slate-200 font-medium",
    shape: "rect",
    width: 80,
    height: 44,
    radius: 30,
  },
  Verse: {
    fill: "#f0fdf4",
    stroke: "#16a34a",
    text: "#14532d",
    badgeBg: "bg-emerald-50 text-emerald-800 border-emerald-200 font-medium",
    shape: "circle",
    radius: 28,
  },
  Concept: {
    fill: "#faf5ff",
    stroke: "#9333ea",
    text: "#581c87",
    badgeBg: "bg-purple-50 text-purple-800 border-purple-200 font-medium",
    shape: "circle",
    radius: 28,
  },
  Entity: {
    fill: "#fff7ed",
    stroke: "#ea580c",
    text: "#7c2d12",
    badgeBg: "bg-orange-50 text-orange-800 border-orange-200 font-medium",
    shape: "circle",
    radius: 26,
  },
  Event: {
    fill: "#fffbeb",
    stroke: "#d97706",
    text: "#78350f",
    badgeBg: "bg-amber-50 text-amber-800 border-amber-200 font-medium",
    shape: "circle",
    radius: 26,
  },
  Evidence: {
    fill: "#eff6ff",
    stroke: "#2563eb",
    text: "#1e3a8a",
    badgeBg: "bg-blue-50 text-blue-800 border-blue-200 font-medium",
    shape: "circle",
    radius: 28,
  },

  // Linguistic & Poetic Concept Layers
  Primary: {
    fill: "#eff6ff",
    stroke: "#3b82f6",
    text: "#1e3a8a",
    badgeBg: "bg-blue-100 text-blue-900 border-blue-200 font-semibold",
    shape: "circle",
    radius: 28,
  },
  Secondary: {
    fill: "#faf5ff",
    stroke: "#8b5cf6",
    text: "#4c1d95",
    badgeBg: "bg-purple-100 text-purple-900 border-purple-200 font-semibold",
    shape: "circle",
    radius: 28,
  },
  Aesthetic: {
    fill: "#fdf2f8",
    stroke: "#ec4899",
    text: "#831843",
    badgeBg: "bg-pink-100 text-pink-900 border-pink-200 font-semibold",
    shape: "circle",
    radius: 28,
  },
  Person: {
    fill: "#f5f3ff",
    stroke: "#7c3aed",
    text: "#4c1d95",
    badgeBg: "bg-violet-100 text-violet-900 border-violet-200 font-semibold",
    shape: "circle",
    radius: 26,
  },
  Object: {
    fill: "#f0fdf4",
    stroke: "#059669",
    text: "#064e3b",
    badgeBg: "bg-emerald-100 text-emerald-900 border-emerald-200 font-semibold",
    shape: "circle",
    radius: 26,
  },

  // 5-Stage Pañcāvayava Reasoning Path Node Styles
  Premise: {
    fill: "#faf5ff",
    stroke: "#7c3aed",
    text: "#4c1d95",
    badgeBg: "bg-purple-100 text-purple-900 border-purple-200 font-bold",
    shape: "pill",
    width: 88,
    height: 44,
    radius: 32,
  },
  Rule: {
    fill: "#fffbeb",
    stroke: "#d97706",
    text: "#78350f",
    badgeBg: "bg-amber-100 text-amber-900 border-amber-200 font-bold",
    shape: "pill",
    width: 88,
    height: 44,
    radius: 32,
  },
  Inference: {
    fill: "#eef2ff",
    stroke: "#4f46e5",
    text: "#312e81",
    badgeBg: "bg-indigo-100 text-indigo-900 border-indigo-200 font-bold",
    shape: "pill",
    width: 88,
    height: 44,
    radius: 32,
  },
  Conclusion: {
    fill: "#ecfdf5",
    stroke: "#059669",
    text: "#064e3b",
    badgeBg: "bg-emerald-100 text-emerald-900 border-emerald-200 font-bold",
    shape: "pill",
    width: 88,
    height: 44,
    radius: 32,
  },
};

const LAYOUT_OPTIONS = [
  { id: "force", label: "Force-Directed (Physics)" },
  { id: "hierarchical", label: "Hierarchical (L0-L5)" },
  { id: "radial", label: "Radial (Concentric)" },
  { id: "preset", label: "Canonical Semiotic Grid" },
];

export default function KnowledgeGraphViewer({
  nodes: propNodes,
  edges: propEdges,
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
  const contextIsAnalyzing = context?.isAnalyzing;
  const contextWorkflowProgressPercent = context?.workflowProgressPercent;
  const contextCurrentWorkflowStage = context?.currentWorkflowStage;
  const contextInsufficientEvidence = context?.insufficientEvidence;
  const contextSetInsufficientEvidence = context?.setInsufficientEvidence;
  const contextEvidenceRecords = context?.evidenceRecords;
  const contextSetSelectedEvidenceId = context?.setSelectedEvidenceId;
  const contextIsQueryGraphActive = context?.isQueryGraphActive;
  const contextQuerySubgraph = context?.querySubgraph;
  const contextQueryString = context?.queryText || context?.query || "";
  const contextIsLoadingGraph = context?.isLoadingGraph;
  const contextIsMutatingGraph = context?.isMutatingGraph;
  const contextMutationError = context?.mutationError;
  const contextMutateKnowledgeGraph = context?.mutateKnowledgeGraph;

  // Backend state for consuming Flask Neo4j graph API
  const [backendData, setBackendData] = useState(null);
  const [isLoadingBackend, setIsLoadingBackend] = useState(false);
  const [backendError, setBackendError] = useState(null);
  const [backendSource, setBackendSource] = useState(null);
  const [focusedCenterId, setFocusedCenterId] = useState(null);
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);

  // Dynamic Neo4j Node Selection & Multi-Hop Traversal State
  const [isExpandingNode, setIsExpandingNode] = useState(false);
  const [nodeConnectedData, setNodeConnectedData] = useState(null);
  const [dynamicallyExpandedData, setDynamicallyExpandedData] = useState({
    nodes: [],
    edges: [],
  });
  const [expansionFeedback, setExpansionFeedback] = useState(null);
  const [isNodeInspectorOpen, setIsNodeInspectorOpen] = useState(true);
  const [expansionDepth, setExpansionDepth] = useState(2);
  const [expansionDirection, setExpansionDirection] = useState("both");
  const [expansionExcludedTypes, setExpansionExcludedTypes] = useState([]);
  const [expansionActiveTab, setExpansionActiveTab] = useState("details");
  const expandSelectedNodeRef = useRef(null);

  // Active selected ID & category filter (only track explicit graph/proof selections, never background evidence loading)
  const contextSelectedProofNodeId = context?.selectedProofNodeId;
  const activeSelectedId =
    propSelectedNodeId !== undefined
      ? propSelectedNodeId
      : context?.selectedGraphNodeId || contextSelectedProofNodeId || null;
  const setSelectedNodeId = propOnSelectNode || context?.setSelectedGraphNodeId;
  const activeCategoryFilter = context?.activeCategoryFilter;
  const setActiveCategoryFilter = context?.setActiveCategoryFilter;

  // DOM Refs
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const zoomBehaviorRef = useRef(null);
  const simulationRef = useRef(null);
  const prevPositionsRef = useRef(new Map());
  const dragStartPosRef = useRef({ x: 0, y: 0, moved: false });
  const syncHighlightsRef = useRef(null);

  // Stable Callback & Data Refs (Prevents rebuilding D3 graph on context updates)
  const evidenceRecordsRef = useRef(contextEvidenceRecords);
  const setSelectedEvidenceIdRef = useRef(contextSetSelectedEvidenceId);
  const setSelectedNodeIdRef = useRef(setSelectedNodeId);
  const selectSynchronizedItem = context?.selectSynchronizedItem;
  const selectSynchronizedItemRef = useRef(selectSynchronizedItem);

  useEffect(() => {
    evidenceRecordsRef.current = contextEvidenceRecords;
    setSelectedEvidenceIdRef.current = contextSetSelectedEvidenceId;
    setSelectedNodeIdRef.current = setSelectedNodeId;
    selectSynchronizedItemRef.current = selectSynchronizedItem;
  }, [
    contextEvidenceRecords,
    contextSetSelectedEvidenceId,
    setSelectedNodeId,
    selectSynchronizedItem,
  ]);

  const showAllTimerRef = useRef(null);
  const [isSimulating, setIsSimulating] = useState(false);

  useEffect(() => {
    return () => {
      if (showAllTimerRef.current) clearTimeout(showAllTimerRef.current);
    };
  }, []);

  // Component State
  const [selectedEdgeData, setSelectedEdgeData] = useState(null);
  const [clickedNodeData, setClickedNodeData] = useState(null);
  const [currentLayout, setCurrentLayout] = useState(
    initialLayout === "cose" || initialLayout === "cola"
      ? "force"
      : initialLayout === "breadthfirst"
        ? "hierarchical"
        : initialLayout === "circle"
          ? "radial"
          : initialLayout || "force",
  );
  const [zoomLevelPercent, setZoomLevelPercent] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const [selectedEntityType, setSelectedEntityType] = useState("ALL");
  const [selectedRelationshipType, setSelectedRelationshipType] =
    useState("ALL");
  const [selectedSourceFilter, setSelectedSourceFilter] = useState("ALL");
  const [selectedHierarchyLevel, setSelectedHierarchyLevel] = useState("ALL");
  const [popoverPos, setPopoverPos] = useState(null);

  // Multi-hop depth state (1 to 5 hops, or "ALL")
  const contextDepth = context?.depth;
  const contextSetDepth = context?.setDepth;
  const [localHopDepth, setLocalHopDepth] = useState(contextDepth || "ALL");
  const hopDepth = localHopDepth;

  const setHopDepth = useCallback(
    (newHops) => {
      setLocalHopDepth(newHops);
      if (contextSetDepth && typeof newHops === "number") {
        contextSetDepth(newHops);
      }
    },
    [contextSetDepth],
  );

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
      // Prevent duplicate network calls if authoritative query subgraph is already active in context
      if (
        contextIsQueryGraphActive &&
        contextGraphNodes &&
        contextGraphNodes.length > 0 &&
        !centerId
      ) {
        setIsLoadingBackend(false);
        return;
      }
      if (fetchAbortRef.current) {
        fetchAbortRef.current.abort();
      }
      const controller = new AbortController();
      fetchAbortRef.current = controller;

      setIsLoadingBackend(true);
      setBackendError(null);
      const hops = customHops !== null ? customHops : hopDepth;
      const timer = setTimeout(() => controller.abort(), 8000);
      try {
        let json;
        const currentQuery = contextQueryString.trim();
        // If an active user query exists and no specific center node is pinned, retrieve the query-aware subgraph
        if (currentQuery && !centerId) {
          try {
            json = await graphApi.queryGraph({
              query: currentQuery,
              hops: typeof hops === "number" ? hops : 2,
              limit: 250,
              signal: controller.signal,
              timeoutMs: 8000,
            });
          } catch (subgraphErr) {
            console.warn("Query-aware graph fetch error:", subgraphErr);
            json = null;
          }
        } else if (centerId) {
          json = await graphApi.getElements({
            centerId,
            hops: typeof hops === "number" ? hops : 2,
            limit: 250,
            source: "auto",
            signal: controller.signal,
            timeoutMs: 6000,
          });
        }
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
    [
      fetchFromBackend,
      hopDepth,
      contextQueryString,
      contextGraphNodes,
      contextIsQueryGraphActive,
    ],
  );

  // Abort any ongoing network request on unmount
  useEffect(() => {
    return () => {
      if (fetchAbortRef.current) {
        fetchAbortRef.current.abort();
      }
    };
  }, []);

  // When active query string or authoritative query nodes change, smoothly reset selections & traversal state
  const lastQueryRef = useRef(contextQueryString);
  const lastNodesRef = useRef(contextGraphNodes);
  useEffect(() => {
    const queryChanged = lastQueryRef.current !== contextQueryString;
    const nodesChanged = lastNodesRef.current !== contextGraphNodes;
    if (queryChanged || nodesChanged) {
      lastQueryRef.current = contextQueryString;
      lastNodesRef.current = contextGraphNodes;
      setSelectedEdgeData(null);
      setClickedNodeData(null);
      setPopoverPos(null);
      setFocusedCenterId(null);
      setDynamicallyExpandedData({ nodes: [], edges: [] });
      setNodeConnectedData(null);
      setExpansionFeedback(null);
      if (setSelectedNodeIdRef.current) {
        setSelectedNodeIdRef.current(null);
      }
      prevPositionsRef.current.clear();
      if (zoomBehaviorRef.current && svgRef.current) {
        d3.select(svgRef.current)
          .transition()
          .duration(300)
          .call(zoomBehaviorRef.current.transform, d3.zoomIdentity);
      }
    }
  }, [contextQueryString, contextGraphNodes]);

  // Dynamic Neo4j Node Selection & Multi-Hop Traversal Expansion
  const expandSelectedNode = useCallback(
    async (nodeObj, options = {}) => {
      if (!nodeObj) return;
      const targetId = extractNodeId(nodeObj) || nodeObj.id || nodeObj.name;
      if (!targetId) return;

      setIsExpandingNode(true);
      const hops = options.hops !== undefined ? options.hops : expansionDepth;
      const direction =
        options.direction !== undefined
          ? options.direction
          : expansionDirection;
      const excludedTypes =
        options.excludedTypes !== undefined
          ? options.excludedTypes
          : expansionExcludedTypes;
      const allowedTypes =
        options.allowedTypes !== undefined ? options.allowedTypes : null;

      try {
        const res = await graphApi.getNodeConnected(targetId, {
          hops,
          limit: 150,
          direction,
          excludedTypes:
            excludedTypes && excludedTypes.length > 0 ? excludedTypes : null,
          allowedTypes,
        });

        if (res && res.success && res.data) {
          const {
            selected_node,
            connected_nodes,
            relationships,
            paths,
            metadata,
          } = res.data;
          setNodeConnectedData({
            selected_node,
            connected_nodes: connected_nodes || [],
            relationships: relationships || [],
            paths: paths || [],
            metadata: metadata || {},
          });

          // Identify existing nodes across current graph simulation
          const currentNodes = graphDataRef.current.nodes || [];
          const existingIds = new Set(
            currentNodes.map((n) => String(n.id || n.name)),
          );
          const rawNewNodes = (connected_nodes || []).filter(
            (cn) => !existingIds.has(String(cn.id || cn.name)),
          );

          // Position newly retrieved connected nodes radially around the selected node
          // with multi-hop hierarchical fan-out grouping
          const selectedX =
            nodeObj.x ?? (containerRef.current?.clientWidth || 800) / 2;
          const selectedY =
            nodeObj.y ?? (containerRef.current?.clientHeight || 600) / 2;

          // Build position map of existing nodes
          const posMap = new Map();
          currentNodes.forEach((n) => {
            if (typeof n.x === "number" && typeof n.y === "number") {
              posMap.set(String(n.id || n.name), { x: n.x, y: n.y });
            }
          });
          posMap.set(String(targetId), { x: selectedX, y: selectedY });

          // Group new nodes by hop_distance
          const nodesByHop = new Map();
          rawNewNodes.forEach((node) => {
            const h = node.hop_distance || 1;
            if (!nodesByHop.has(h)) nodesByHop.set(h, []);
            nodesByHop.get(h).push(node);
          });

          const positionedNewNodes = [];
          const sortedHops = Array.from(nodesByHop.keys()).sort(
            (a, b) => a - b,
          );

          for (const hop of sortedHops) {
            const hopNodes = nodesByHop.get(hop);

            if (hop === 1) {
              // Hop 1: Radial circle directly around selected root
              const radius = 75 + Math.min(hopNodes.length * 6, 130);
              const angleStep = (2 * Math.PI) / (hopNodes.length || 1);

              hopNodes.forEach((nn, i) => {
                const angle = i * angleStep;
                const jitter = (Math.random() - 0.5) * 16;
                const px = selectedX + Math.cos(angle) * radius + jitter;
                const py = selectedY + Math.sin(angle) * radius + jitter;
                posMap.set(String(nn.id || nn.name), { x: px, y: py });
                prevPositionsRef.current.set(String(nn.id), {
                  x: px,
                  y: py,
                  vx: 0,
                  vy: 0,
                });
                positionedNewNodes.push({
                  ...nn,
                  x: px,
                  y: py,
                  vx: 0,
                  vy: 0,
                });
              });
            } else {
              // Hop 2+: Group by parent_id and fan out radially away from the root
              const byParent = new Map();
              hopNodes.forEach((n) => {
                const pid = n.parent_id ? String(n.parent_id) : "unknown";
                if (!byParent.has(pid)) byParent.set(pid, []);
                byParent.get(pid).push(n);
              });

              byParent.forEach((children, pid) => {
                const parentPos = posMap.get(pid) || {
                  x: selectedX,
                  y: selectedY,
                };
                const baseAngle =
                  parentPos.x === selectedX && parentPos.y === selectedY
                    ? Math.random() * 2 * Math.PI
                    : Math.atan2(
                        parentPos.y - selectedY,
                        parentPos.x - selectedX,
                      );

                const count = children.length;
                const fanArc = Math.min(Math.PI * 0.7, 0.4 * count);
                const step = count > 1 ? fanArc / (count - 1) : 0;
                const startAngle = baseAngle - fanArc / 2;
                const hopRadius = 65 + Math.min(count * 5, 80);

                children.forEach((nn, j) => {
                  const angle = count === 1 ? baseAngle : startAngle + j * step;
                  const jitter = (Math.random() - 0.5) * 10;
                  const px = parentPos.x + Math.cos(angle) * hopRadius + jitter;
                  const py = parentPos.y + Math.sin(angle) * hopRadius + jitter;
                  posMap.set(String(nn.id || nn.name), { x: px, y: py });
                  prevPositionsRef.current.set(String(nn.id), {
                    x: px,
                    y: py,
                    vx: 0,
                    vy: 0,
                  });
                  positionedNewNodes.push({
                    ...nn,
                    x: px,
                    y: py,
                    vx: 0,
                    vy: 0,
                  });
                });
              });
            }
          }

          // Identify unique new relationships
          const currentLinks = graphDataRef.current.edges || [];
          const existingRelKeys = new Set(
            currentLinks.map((e) => {
              const s = String(e.source?.id || e.source_id || e.source || "");
              const t = String(e.target?.id || e.target_id || e.target || "");
              const type = String(e.type || e.relation || e.label || "");
              return `${s}->${t}:${type}`;
            }),
          );

          const uniqueNewEdges = (relationships || []).filter((r) => {
            const s = String(r.source?.id || r.source_id || r.source || "");
            const t = String(r.target?.id || r.target_id || r.target || "");
            const type = String(r.type || r.relation || r.label || "");
            const key = `${s}->${t}:${type}`;
            const revKey = `${t}->${s}:${type}`;
            return !existingRelKeys.has(key) && !existingRelKeys.has(revKey);
          });

          if (positionedNewNodes.length > 0 || uniqueNewEdges.length > 0) {
            setDynamicallyExpandedData((prev) => {
              const pIds = new Set(prev.nodes.map((n) => String(n.id)));
              const pRelKeys = new Set(
                prev.edges.map(
                  (e) =>
                    `${e.source?.id || e.source}->${e.target?.id || e.target}:${e.type || e.relation}`,
                ),
              );
              const mergedNodes = [
                ...prev.nodes,
                ...positionedNewNodes.filter((n) => !pIds.has(String(n.id))),
              ];
              const mergedEdges = [
                ...prev.edges,
                ...uniqueNewEdges.filter((e) => {
                  const k = `${e.source?.id || e.source}->${e.target?.id || e.target}:${e.type || e.relation}`;
                  return !pRelKeys.has(k);
                }),
              ];
              return { nodes: mergedNodes, edges: mergedEdges };
            });

            setExpansionFeedback({
              nodeId: targetId,
              nodeName: selected_node?.name || selected_node?.label || targetId,
              addedNodes: positionedNewNodes.length,
              addedEdges: uniqueNewEdges.length,
              totalConnected: (connected_nodes || []).length,
              hops,
            });

            // Gently reheat D3 simulation to smoothly position new neighbors
            if (simulationRef.current) {
              simulationRef.current.alpha(0.35).restart();
            }

            // In Node-Centered Focus Mode: smoothly reframe the expanded neighborhood
            if (focusOnNeighborhoodRef.current) {
              setTimeout(() => {
                focusOnNeighborhoodRef.current(targetId, 85, 650);
              }, 120);
            }
          } else {
            setExpansionFeedback({
              nodeId: targetId,
              nodeName: selected_node?.name || selected_node?.label || targetId,
              addedNodes: 0,
              addedEdges: 0,
              totalConnected: (connected_nodes || []).length,
              hops,
              alreadyInGraph: true,
            });
          }
        }
      } catch (err) {
        console.warn(
          `Neo4j node multi-hop expansion failed for ${targetId}:`,
          err,
        );
      } finally {
        setIsExpandingNode(false);
      }
    },
    [expansionDepth, expansionDirection, expansionExcludedTypes],
  );

  useEffect(() => {
    expandSelectedNodeRef.current = expandSelectedNode;
  }, [expandSelectedNode]);

  // Combine raw entities from all active sources (preserving complete master data)
  const combinedRawData = useMemo(() => {
    let baseNodes;
    let baseEdges;

    if (propNodes && propNodes.length > 0) {
      baseNodes = propNodes;
      baseEdges = propEdges || [];
    } else if (contextIsQueryGraphActive && contextGraphNodes) {
      // Query graph is authoritative! Display query-relevant Neo4j subgraph atomically without old background graph mixing
      baseNodes = contextGraphNodes;
      baseEdges = contextGraphEdges || [];
    } else if (contextGraphNodes && contextGraphNodes.length > 0) {
      baseNodes = contextGraphNodes;
      baseEdges = contextGraphEdges || [];
    } else if (backendData?.nodes && backendData.nodes.length > 0) {
      baseNodes = backendData.nodes;
      baseEdges = backendData.relationships || backendData.edges || [];
    } else {
      baseNodes = [];
      baseEdges = [];
    }

    const mergedNodes = [...baseNodes];
    const mergedEdges = [...baseEdges];

    // Merge dynamically retrieved connected subgraph from Neo4j Aura (preserving existing nodes & edges)
    if (dynamicallyExpandedData.nodes.length > 0) {
      const existingNodeIds = new Set(
        mergedNodes.map((n) => String(n.id || n.name)),
      );
      dynamicallyExpandedData.nodes.forEach((dn) => {
        const nid = String(dn.id || dn.name);
        if (!existingNodeIds.has(nid)) {
          existingNodeIds.add(nid);
          mergedNodes.push(dn);
        }
      });
    }

    if (dynamicallyExpandedData.edges.length > 0) {
      const existingEdgeKeys = new Set(
        mergedEdges.map((e) => {
          const s = String(e.source?.id || e.source_id || e.source || "");
          const t = String(e.target?.id || e.target_id || e.target || "");
          const type = String(e.type || e.relation || e.label || "");
          return `${s}->${t}:${type}`;
        }),
      );
      dynamicallyExpandedData.edges.forEach((de) => {
        const s = String(de.source?.id || de.source_id || de.source || "");
        const t = String(de.target?.id || de.target_id || de.target || "");
        const type = String(de.type || de.relation || de.label || "");
        const key = `${s}->${t}:${type}`;
        const revKey = `${t}->${s}:${type}`;
        if (!existingEdgeKeys.has(key) && !existingEdgeKeys.has(revKey)) {
          existingEdgeKeys.add(key);
          mergedEdges.push(de);
        }
      });
    }

    // Only merge proof and evidence nodes if base query subgraph returned nodes from Neo4j
    if (baseNodes.length > 0) {
      if (contextProofNodes && contextProofNodes.length > 0) {
        const existingProofIds = new Set(mergedNodes.map((n) => String(n.id)));
        contextProofNodes.forEach((pn) => {
          if (!existingProofIds.has(String(pn.id))) {
            mergedNodes.push(pn);
          }
        });
        if (contextProofEdges && contextProofEdges.length > 0) {
          const existingProofEdgeIds = new Set(
            mergedEdges.map((e) => String(e.id)),
          );
          contextProofEdges.forEach((pe) => {
            if (!existingProofEdgeIds.has(String(pe.id))) {
              mergedEdges.push(pe);
            }
          });
        }
      }

      // When contextIsQueryGraphActive is true, graph nodes strictly originate from Neo4j!
      // Only merge synthetic evidence records if NOT in strict query graph mode
      if (
        !contextIsQueryGraphActive &&
        contextEvidenceRecords &&
        contextEvidenceRecords.length > 0
      ) {
        const existingIds = new Set(
          mergedNodes.map((n) => String(n.id || n.passageId || n.passage_id)),
        );
        contextEvidenceRecords.forEach((ev, idx) => {
          const pId = String(ev.passageId || ev.id);
          if (!existingIds.has(pId)) {
            const cId = String(ev.code || `E${idx + 1}`);
            mergedNodes.push({
              id: pId,
              code: cId,
              aliases: [cId, pId, `evidence_${idx + 1}`],
              label: `${cId}: ${ev.reference || pId}`,
              name: ev.reference || pId,
              tamilLabel: ev.tamilText || ev.text || ev.reference || pId,
              transliteration: ev.transliteration || "",
              type: "Evidence",
              category: "Evidence",
              isEvidenceRecord: true,
              text: ev.tamilText || ev.text || "",
              translation: ev.translation || "",
              confidence: ev.confidence || ev.relevanceScore || 0.9,
              source: ev.source || "Tolkāppiyam",
              citation: ev.reference || ev.source || "",
              properties: { ...ev },
            });
          }
        });
      }
    }

    return { nodes: mergedNodes, edges: mergedEdges };
  }, [
    propNodes,
    propEdges,
    backendData,
    dynamicallyExpandedData,
    contextIsQueryGraphActive,
    contextGraphNodes,
    contextGraphEdges,
    contextProofNodes,
    contextProofEdges,
    contextEvidenceRecords,
  ]);

  // Robust Data-Normalization Layer (Guarantees zero dropped entities or relationships)
  const normalizedData = useMemo(() => {
    return normalizeGraphData(combinedRawData);
  }, [combinedRawData]);

  // Dynamically derived filter options from normalized data
  const availableEntityTypes = useMemo(() => {
    const types = new Set();
    normalizedData.nodes.forEach((n) => {
      const t = n.type || n.category;
      if (t) types.add(t);
    });
    return Array.from(types).sort();
  }, [normalizedData]);

  const availableRelationshipTypes = useMemo(() => {
    const rels = new Set();
    normalizedData.links.forEach((l) => {
      const r = l.type || l.relation || l.predicate;
      if (r) rels.add(r);
    });
    return Array.from(rels).sort();
  }, [normalizedData]);

  const availableHierarchyLevels = useMemo(() => {
    const levels = new Set();
    normalizedData.nodes.forEach((n) => {
      const h = n.hierarchy_level || n.hierarchyLevel;
      if (h) levels.add(String(h).toUpperCase());
    });
    const order = ["L0", "L1", "L2", "L3", "L4", "L5"];
    return order.filter((lvl) => levels.has(lvl));
  }, [normalizedData]);

  // Pure Visualization-Layer Filtering (Leaves underlying application state 100% untouched)
  const { filteredNodes, filteredLinks, stats } = useMemo(() => {
    const query = searchText.trim().toLowerCase();
    const hasFilter =
      selectedEntityType !== "ALL" ||
      selectedRelationshipType !== "ALL" ||
      selectedSourceFilter !== "ALL" ||
      selectedHierarchyLevel !== "ALL" ||
      (activeCategoryFilter && activeCategoryFilter !== "ALL") ||
      hopDepth !== "ALL" ||
      query !== "";

    let nodes = [...normalizedData.nodes];
    let links = [...normalizedData.links];

    // 1. Filter by Entity Type
    if (selectedEntityType !== "ALL") {
      const typeLower = selectedEntityType.toLowerCase();
      nodes = nodes.filter(
        (n) =>
          String(n.type || "").toLowerCase() === typeLower ||
          String(n.category || "").toLowerCase() === typeLower,
      );
    }

    // 2. Filter by Category Filter (from context or interactive legend)
    if (activeCategoryFilter && activeCategoryFilter !== "ALL") {
      const catLower = activeCategoryFilter.toLowerCase();
      nodes = nodes.filter(
        (n) =>
          String(n.category || "").toLowerCase() === catLower ||
          String(n.type || "").toLowerCase() === catLower,
      );
    }

    // 3. Filter by Hierarchy Level (L0, L1, L2, L3, L4, L5)
    if (selectedHierarchyLevel !== "ALL") {
      const hLower = selectedHierarchyLevel.toLowerCase();
      nodes = nodes.filter((n) => {
        const h = String(
          n.hierarchy_level || n.hierarchyLevel || "",
        ).toLowerCase();
        return h === hLower;
      });
    }

    // 4. Filter by Source / Evidence Grounding
    if (selectedSourceFilter !== "ALL") {
      const srcLower = selectedSourceFilter.toLowerCase();
      nodes = nodes.filter((n) => {
        const s = String(n.source || n.citation || n.iyal || "").toLowerCase();
        const isEv = Boolean(n.isEvidenceRecord || n.type === "Evidence");
        return s.includes(srcLower) || (srcLower === "evidence" && isEv);
      });
    }

    // 5. Filter by Real-Time Search Query
    if (query) {
      nodes = nodes.filter((n) => {
        const lbl = String(n.label || "").toLowerCase();
        const tr = String(n.transliteration || "").toLowerCase();
        const nid = String(n.id || "").toLowerCase();
        const name = String(n.name || "").toLowerCase();
        const tamil = String(n.tamilLabel || n.tamil_label || "").toLowerCase();
        const desc = String(n.description || n.text || "").toLowerCase();
        const eng = String(n.english || "").toLowerCase();
        return (
          lbl.includes(query) ||
          tr.includes(query) ||
          nid.includes(query) ||
          name.includes(query) ||
          tamil.includes(query) ||
          desc.includes(query) ||
          eng.includes(query)
        );
      });
    }

    // 6. Filter by Relationship Type
    if (selectedRelationshipType !== "ALL") {
      const relQuery = selectedRelationshipType.toLowerCase();
      links = links.filter((l) => {
        const rel = String(
          l.type || l.relation || l.predicate || "",
        ).toLowerCase();
        const lbl = String(l.label || "").toLowerCase();
        return rel === relQuery || lbl.includes(relQuery);
      });
    }

    // 7. Graph Depth / Hops Filtering (BFS Neighborhood without dataset mutation)
    if (hopDepth !== "ALL" && typeof hopDepth === "number" && hopDepth >= 1) {
      const focalId = String(
        activeSelectedId || focusedCenterId || "mutalporul",
      );
      const focalExists = normalizedData.nodes.some(
        (n) => String(n.id) === focalId,
      );
      if (focalExists) {
        const visited = new Set([focalId]);
        let frontier = [focalId];
        for (let step = 0; step < hopDepth; step++) {
          const nextFrontier = [];
          frontier.forEach((currId) => {
            normalizedData.links.forEach((l) => {
              const sId = extractNodeId(l.source);
              const tId = extractNodeId(l.target);
              if (sId === currId && !visited.has(tId)) {
                visited.add(tId);
                nextFrontier.push(tId);
              } else if (tId === currId && !visited.has(sId)) {
                visited.add(sId);
                nextFrontier.push(sId);
              }
            });
          });
          frontier = nextFrontier;
        }
        nodes = nodes.filter((n) => visited.has(String(n.id)));
      }
    }

    // Preserve proof trace nodes if proof trace mode is active
    if (contextIsShowingProofTrace && contextProofNodes) {
      const proofIdSet = new Set(contextProofNodes.map((p) => String(p.id)));
      const extraProofNodes = normalizedData.nodes.filter((n) =>
        proofIdSet.has(String(n.id)),
      );
      const currentIds = new Set(nodes.map((n) => n.id));
      extraProofNodes.forEach((pn) => {
        if (!currentIds.has(pn.id)) nodes.push(pn);
      });
    }

    const visibleNodeIdSet = new Set(nodes.map((n) => String(n.id)));
    const visibleLinks = links.filter((l) => {
      const sId = extractNodeId(l.source);
      const tId = extractNodeId(l.target);
      return visibleNodeIdSet.has(sId) && visibleNodeIdSet.has(tId);
    });

    // Map visual styles from taxonomy
    const styledNodes = nodes.map((node) => {
      const category = node.type || node.category || "Concept";
      const style =
        CATEGORY_STYLES[category] ||
        CATEGORY_STYLES[node.type] ||
        CATEGORY_STYLES.Concept;

      return {
        ...node,
        color: style.stroke,
        bgColor: style.fill,
        textColor: style.text,
        shape: style.shape || "circle",
        radius: style.radius || 28,
        width: style.width || 56,
        height: style.height || 56,
      };
    });

    return {
      filteredNodes: styledNodes,
      filteredLinks: visibleLinks,
      stats: {
        backendNodeCount: normalizedData.stats.backendNodeCount,
        backendRelCount: normalizedData.stats.backendRelCount,
        totalEntities: normalizedData.nodes.length,
        totalEdges: normalizedData.links.length,
        renderedEntities: styledNodes.length,
        renderedEdges: visibleLinks.length,
        isFiltered: hasFilter,
        synthesizedEndpoints: normalizedData.stats.synthesizedNodeCount,
        duplicatesResolved: normalizedData.stats.duplicatesResolved,
        selfLoopCount: normalizedData.stats.selfLoopCount,
        multiEdgeCount: normalizedData.stats.multiEdgeCount,
        isolatedNodeCount: normalizedData.stats.isolatedNodeCount,
      },
    };
  }, [
    normalizedData,
    searchText,
    selectedEntityType,
    selectedRelationshipType,
    selectedSourceFilter,
    selectedHierarchyLevel,
    activeCategoryFilter,
    hopDepth,
    activeSelectedId,
    focusedCenterId,
    contextIsShowingProofTrace,
    contextProofNodes,
  ]);

  // Dedicated query context metadata derived strictly from the active query
  const queryContextMeta = useMemo(() => {
    const rawSources =
      contextQuerySubgraph?.literarySources ||
      contextQuerySubgraph?.metadata?.literary_sources ||
      [];
    const evidenceSources = contextEvidenceRecords
      ? contextEvidenceRecords
          .map((e) => e.source || e.work || e.reference)
          .filter(Boolean)
      : [];
    const allSources = Array.from(new Set([...rawSources, ...evidenceSources]));
    const sourcesDisplay =
      allSources.length > 0 ? allSources : ["Tolkāppiyam (தொல்காப்பியம்)"];

    const evidenceCount =
      contextQuerySubgraph?.evidenceCount ??
      contextQuerySubgraph?.metadata?.evidence_count ??
      (contextEvidenceRecords?.length || 0);

    const activeQuery = contextQueryString || contextQuerySubgraph?.query || "";
    const nodeCount = filteredNodes.length;
    const relCount = filteredLinks.length;

    return {
      activeQuery,
      nodeCount,
      relCount,
      sourcesDisplay,
      evidenceCount,
      isLiveQuery: Boolean(contextIsQueryGraphActive && activeQuery),
    };
  }, [
    contextQuerySubgraph,
    contextEvidenceRecords,
    contextQueryString,
    contextIsQueryGraphActive,
    filteredNodes.length,
    filteredLinks.length,
  ]);

  // Selected node computation
  const selectedNode = useMemo(() => {
    const targetId = activeSelectedId || clickedNodeData?.id;
    if (!targetId) return null;
    return (
      filteredNodes.find((n) => String(n.id) === String(targetId)) ||
      clickedNodeData
    );
  }, [filteredNodes, activeSelectedId, clickedNodeData]);

  // Comprehensive details & degree for selected node enriched with live Neo4j data
  const selectedNodeDetails = useMemo(() => {
    if (!selectedNode) return null;
    const sId = String(selectedNode.id);

    const inLinks = normalizedData.links.filter(
      (l) => extractNodeId(l.target) === sId,
    );
    const outLinks = normalizedData.links.filter(
      (l) => extractNodeId(l.source) === sId,
    );

    const liveData =
      nodeConnectedData &&
      String(
        nodeConnectedData?.selected_node?.id ||
          nodeConnectedData?.selected_node?.name,
      ) === sId
        ? nodeConnectedData.selected_node
        : null;

    return {
      ...selectedNode,
      ...(liveData || {}),
      inDegree: inLinks.length,
      outDegree: outLinks.length,
      totalDegree: inLinks.length + outLinks.length,
      inLinks,
      outLinks,
      tamilText:
        liveData?.tamil_text ||
        liveData?.tamil_name ||
        liveData?.original_text ||
        liveData?.text ||
        selectedNode.tamil_text ||
        selectedNode.tamilText ||
        selectedNode.tamilLabel ||
        selectedNode.tamil_name ||
        selectedNode.label ||
        selectedNode.name ||
        "",
      sourceCorpus:
        liveData?.source_corpus ||
        liveData?.source ||
        selectedNode.source_corpus ||
        selectedNode.sourceCorpus ||
        selectedNode.source ||
        "Tolkāppiyam",
      sourceReference:
        liveData?.source_reference ||
        liveData?.citation ||
        selectedNode.source_reference ||
        selectedNode.sourceReference ||
        selectedNode.citation ||
        "",
      validationLevel:
        liveData?.validation_level ||
        liveData?.validation_status ||
        selectedNode.validation_level ||
        selectedNode.validationLevel ||
        selectedNode.validation_status ||
        "corpus_validated",
      confidence:
        typeof liveData?.confidence === "number"
          ? liveData.confidence
          : typeof selectedNode.confidence === "number"
            ? selectedNode.confidence
            : 1.0,
      contextTinai:
        liveData?.tinai ||
        liveData?.context ||
        selectedNode.tinai ||
        selectedNode.context ||
        "",
      taxonomyType:
        liveData?.type ||
        (Array.isArray(liveData?.labels)
          ? liveData.labels.find((l) => l !== "KGNode")
          : null) ||
        selectedNode.type ||
        selectedNode.category ||
        "Entity",
    };
  }, [selectedNode, normalizedData.links, nodeConnectedData]);

  // Ref tracking current simulation elements
  const graphDataRef = useRef({ nodes: [], edges: [] });
  const transformRef = useRef(d3.zoomIdentity);

  // Fit View helper
  const fitView = useCallback((padding = 55, duration = 350) => {
    const svg = svgRef.current;
    const container = containerRef.current;
    if (!svg || !container || !zoomBehaviorRef.current) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    const currentNodes = graphDataRef.current.nodes;
    if (currentNodes.length === 0) return;

    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;
    currentNodes.forEach((n) => {
      const x = typeof n.x === "number" ? n.x : width / 2;
      const y = typeof n.y === "number" ? n.y : height / 2;
      const r = n.radius || 30;
      if (x - r < minX) minX = x - r;
      if (x + r > maxX) maxX = x + r;
      if (y - r < minY) minY = y - r;
      if (y + r > maxY) maxY = y + r;
    });

    const graphWidth = Math.max(1, maxX - minX);
    const graphHeight = Math.max(1, maxY - minY);

    const scaleX = (width - padding * 2) / graphWidth;
    const scaleY = (height - padding * 2) / graphHeight;
    const scale = Math.max(0.25, Math.min(2.5, Math.min(scaleX, scaleY)));

    const midX = (minX + maxX) / 2;
    const midY = (minY + maxY) / 2;
    const translateX = width / 2 - scale * midX;
    const translateY = height / 2 - scale * midY;

    const targetTransform = d3.zoomIdentity
      .translate(translateX, translateY)
      .scale(scale);

    const d3Svg = d3.select(svg);
    if (duration > 0) {
      d3Svg
        .transition()
        .duration(duration)
        .call(zoomBehaviorRef.current.transform, targetTransform);
    } else {
      d3Svg.call(zoomBehaviorRef.current.transform, targetTransform);
    }
  }, []);

  // Unified Clear Selection & Traversal Reset Handler
  const handleClearSelection = useCallback(() => {
    if (selectSynchronizedItemRef.current) {
      selectSynchronizedItemRef.current(null, "graph");
    } else if (setSelectedNodeIdRef.current) {
      setSelectedNodeIdRef.current(null);
    }
    setClickedNodeData(null);
    setSelectedEdgeData(null);
    setPopoverPos(null);
    setFocusedCenterId(null);
    setDynamicallyExpandedData({ nodes: [], edges: [] });
    setNodeConnectedData(null);
    setExpansionFeedback(null);
    fitView(55, 450);
  }, [fitView]);

  const handleClearSelectionRef = useRef(handleClearSelection);
  useEffect(() => {
    handleClearSelectionRef.current = handleClearSelection;
  }, [handleClearSelection]);

  const handleZoomIn = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(200)
        .call(zoomBehaviorRef.current.scaleBy, 1.25);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(200)
        .call(zoomBehaviorRef.current.scaleBy, 0.8);
    }
  }, []);

  const handleFit = useCallback(() => {
    fitView(55, 400);
  }, [fitView]);

  // Node-Centered Focus Mode State
  const [isFocusMode, setIsFocusMode] = useState(true);
  const focusOnNeighborhoodRef = useRef(null);

  // Automatically calculate selected node's neighborhood from Neo4j result and visually focus the graph
  const focusOnNeighborhood = useCallback(
    (centerId, padding = 75, duration = 650) => {
      const svg = svgRef.current;
      const container = containerRef.current;
      if (!svg || !container || !zoomBehaviorRef.current || !centerId) return;

      const width = container.clientWidth || 800;
      const height = container.clientHeight || 600;

      const { nodes, edges } = graphDataRef.current;
      if (!nodes || nodes.length === 0) return;

      const centerNode = findNodeByStableId(nodes, centerId);
      if (
        !centerNode ||
        typeof centerNode.x !== "number" ||
        typeof centerNode.y !== "number"
      )
        return;

      // Identify the neighborhood nodes (1-hop or multi-hop induced neighborhood)
      const effectiveHops = typeof hopDepth === "number" ? hopDepth : 1;
      const { visitedNodeIds, directNeighborIds } =
        getInducedSubgraphNeighborhood(centerNode.id, edges, effectiveHops);

      const neighborhoodNodes = nodes.filter(
        (n) =>
          String(n.id) === String(centerNode.id) ||
          directNeighborIds.has(String(n.id)) ||
          visitedNodeIds.has(String(n.id)),
      );

      if (neighborhoodNodes.length === 0) return;

      let minX = Infinity,
        maxX = -Infinity,
        minY = Infinity,
        maxY = -Infinity;

      neighborhoodNodes.forEach((n) => {
        const x = typeof n.x === "number" ? n.x : centerNode.x;
        const y = typeof n.y === "number" ? n.y : centerNode.y;
        const r = (n.radius || 28) + 20;
        if (x - r < minX) minX = x - r;
        if (x + r > maxX) maxX = x + r;
        if (y - r < minY) minY = y - r;
        if (y + r > maxY) maxY = y + r;
      });

      const boxWidth = Math.max(90, maxX - minX);
      const boxHeight = Math.max(90, maxY - minY);

      // Compute optimal zoom scale to fit neighborhood with comfortable margin
      const availWidth = Math.max(100, width - padding * 2);
      const availHeight = Math.max(100, height - padding * 2);
      const scaleX = availWidth / boxWidth;
      const scaleY = availHeight / boxHeight;
      const scale = Math.max(0.50, Math.min(1.60, Math.min(scaleX, scaleY)));

      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;
      const translateX = width / 2 - scale * midX;
      const translateY = height / 2 - scale * midY;

      const targetTransform = d3.zoomIdentity
        .translate(translateX, translateY)
        .scale(scale);

      d3.select(svg)
        .transition()
        .duration(duration)
        .ease(d3.easeCubicOut)
        .call(zoomBehaviorRef.current.transform, targetTransform);
    },
    [hopDepth],
  );

  useEffect(() => {
    focusOnNeighborhoodRef.current = focusOnNeighborhood;
  }, [focusOnNeighborhood]);

  const handleCenterSelected = useCallback(() => {
    const targetId = activeSelectedId || clickedNodeData?.id;
    if (!targetId) return;
    focusOnNeighborhood(targetId, 75, 600);
  }, [activeSelectedId, clickedNodeData, focusOnNeighborhood]);

  const toggleFullscreen = useCallback(() => {
    const container = containerRef.current;
    if (!container) return;

    if (!document.fullscreenElement) {
      if (container.requestFullscreen) {
        container.requestFullscreen();
      } else if (container.webkitRequestFullscreen) {
        container.webkitRequestFullscreen();
      }
      setIsFullscreen(true);
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
      }
      setIsFullscreen(false);
    }
  }, []);

  useEffect(() => {
    const handleFsChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener("fullscreenchange", handleFsChange);
    document.addEventListener("webkitfullscreenchange", handleFsChange);
    return () => {
      document.removeEventListener("fullscreenchange", handleFsChange);
      document.removeEventListener("webkitfullscreenchange", handleFsChange);
    };
  }, []);

  const handleResetAllFilters = useCallback(() => {
    setSearchText("");
    setSelectedEntityType("ALL");
    setSelectedRelationshipType("ALL");
    setSelectedSourceFilter("ALL");
    setSelectedHierarchyLevel("ALL");
    if (setActiveCategoryFilter) setActiveCategoryFilter(null);
    setHopDepth("ALL");
  }, [setActiveCategoryFilter, setHopDepth]);

  const handleShowAll = useCallback(() => {
    setSearchText("");
    setSelectedEntityType("ALL");
    setSelectedRelationshipType("ALL");
    setSelectedSourceFilter("ALL");
    setSelectedHierarchyLevel("ALL");
    if (setActiveCategoryFilter) setActiveCategoryFilter(null);
    setHopDepth("ALL");
    setClickedNodeData(null);
    setSelectedEdgeData(null);
    if (setSelectedNodeId) setSelectedNodeId(null);
    setFocusedCenterId(null);
    prevPositionsRef.current.clear();
    if (simulationRef.current) {
      simulationRef.current.nodes().forEach((n) => {
        n.fx = null;
        n.fy = null;
      });
      simulationRef.current.alpha(0.8).restart();
    }
    if (showAllTimerRef.current) clearTimeout(showAllTimerRef.current);
    showAllTimerRef.current = setTimeout(() => {
      fitView(55, 350);
    }, 60);
  }, [setActiveCategoryFilter, setSelectedNodeId, fitView, setHopDepth]);

  // Primary D3 Simulation & Rendering Lifecycle (Production Optimized)
  useEffect(() => {
    const container = containerRef.current;
    const svgEl = svgRef.current;
    if (!container || !svgEl) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    const nodeCount = filteredNodes.length;
    const isLargeGraph = nodeCount > 80;
    const isVeryLargeGraph = nodeCount > 250;

    // Halt and detach any lingering simulation before rebuilding
    if (simulationRef.current) {
      simulationRef.current.stop();
      simulationRef.current.on("tick", null);
      simulationRef.current.on("end", null);
      simulationRef.current = null;
    }

    const svg = d3.select(svgEl);

    // Defs: Markers & Glows - Initialize once to support smooth state transitions
    let defs = svg.select("defs");
    if (defs.empty()) {
      defs = svg.append("defs");

      // Standard arrow marker
      defs
        .append("marker")
        .attr("id", "d3-arrow-default")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", 7)
        .attr("markerHeight", 7)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M 0,-4 L 8,0 L 0,4")
        .attr("fill", "#64748b");

      // Highlighted edge arrow
      defs
        .append("marker")
        .attr("id", "d3-arrow-highlight")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", 7)
        .attr("markerHeight", 7)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M 0,-4 L 8,0 L 0,4")
        .attr("fill", "#6366f1");

      // Directly connected outgoing arrow marker
      defs
        .append("marker")
        .attr("id", "d3-arrow-connected")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M 0,-4 L 8,0 L 0,4")
        .attr("fill", "#4f46e5");

      // Directly connected incoming arrow marker
      defs
        .append("marker")
        .attr("id", "d3-arrow-connected-in")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M 0,-4 L 8,0 L 0,4")
        .attr("fill", "#059669");

      // Proof trace arrow
      defs
        .append("marker")
        .attr("id", "d3-arrow-proof")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 10)
        .attr("refY", 0)
        .attr("markerWidth", 8)
        .attr("markerHeight", 8)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M 0,-4 L 8,0 L 0,4")
        .attr("fill", "#d97706");

      // Node drop shadow filter
      const shadowFilter = defs
        .append("filter")
        .attr("id", "d3-node-shadow")
        .attr("x", "-20%")
        .attr("y", "-20%")
        .attr("width", "150%")
        .attr("height", "150%");
      shadowFilter
        .append("feDropShadow")
        .attr("dx", "0")
        .attr("dy", "1.5")
        .attr("stdDeviation", "2.5")
        .attr("flood-color", "#0f172a")
        .attr("flood-opacity", "0.08");

      // Proof glow filter
      const proofGlow = defs
        .append("filter")
        .attr("id", "d3-proof-glow")
        .attr("x", "-30%")
        .attr("y", "-30%")
        .attr("width", "160%")
        .attr("height", "160%");
      proofGlow
        .append("feDropShadow")
        .attr("dx", "0")
        .attr("dy", "0")
        .attr("stdDeviation", "6")
        .attr("flood-color", "#f59e0b")
        .attr("flood-opacity", "0.75");

      // Selected node glow filter
      const selectedGlow = defs
        .append("filter")
        .attr("id", "d3-selected-glow")
        .attr("x", "-35%")
        .attr("y", "-35%")
        .attr("width", "170%")
        .attr("height", "170%");
      selectedGlow
        .append("feDropShadow")
        .attr("dx", "0")
        .attr("dy", "0")
        .attr("stdDeviation", "5.5")
        .attr("flood-color", "#6366f1")
        .attr("flood-opacity", "0.75");

      // Direct neighbor glow filter
      const neighborGlow = defs
        .append("filter")
        .attr("id", "d3-neighbor-glow")
        .attr("x", "-30%")
        .attr("y", "-30%")
        .attr("width", "160%")
        .attr("height", "160%");
      neighborGlow
        .append("feDropShadow")
        .attr("dx", "0")
        .attr("dy", "0")
        .attr("stdDeviation", "4")
        .attr("flood-color", "#818cf8")
        .attr("flood-opacity", "0.55");
    }

    // Viewport Group - Initialize once to retain zoom coordinates and smooth transitions
    let g = svg.select("g.kg-viewport");
    if (g.empty()) {
      g = svg.append("g").attr("class", "kg-viewport");
      g.append("g").attr("class", "kg-links-group");
      g.append("g").attr("class", "kg-link-labels-group");
      g.append("g").attr("class", "kg-nodes-group");
      g.append("g").attr("class", "kg-node-labels-group");
    }

    // Separate SVG Groups: Links, Link Labels, Nodes, Node Labels
    const linksGroup = g.select("g.kg-links-group");
    const linkLabelsGroup = g.select("g.kg-link-labels-group");
    const nodesGroup = g.select("g.kg-nodes-group");
    const nodeLabelsGroup = g.select("g.kg-node-labels-group");

    // D3 Zoom Behavior with wide scale extent for large graph exploration
    const zoomBehavior = d3
      .zoom()
      .scaleExtent([0.15, 4.0])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
        transformRef.current = event.transform;
        setZoomLevelPercent(Math.round(event.transform.k * 100));
        if (isLargeGraph && !activeSelectedId && !focusedCenterId) {
          linkLabelsGroup.attr(
            "display",
            event.transform.k >= 1.15 ? null : "none",
          );
        } else {
          linkLabelsGroup.attr("display", null);
        }
      });
    zoomBehaviorRef.current = zoomBehavior;
    svg.call(zoomBehavior).on("dblclick.zoom", null);

    // Initial LoD state for link labels in large graphs
    if (isLargeGraph && !activeSelectedId && !focusedCenterId) {
      linkLabelsGroup.attr("display", "none");
    } else {
      linkLabelsGroup.attr("display", null);
    }

    // Canvas click clears selection, resets dynamic traversal state, and smoothly returns to full view
    svg.on("click", (event) => {
      if (event.target === svgEl) {
        if (handleClearSelectionRef.current) {
          handleClearSelectionRef.current();
        }
      }
    });

    // Prepare simulation nodes with coordinate preservation and smooth neighbor placement
    const prevPositions = prevPositionsRef.current;
    const simNodes = filteredNodes.map((n, idx) => {
      const existing = prevPositions.get(n.id);
      let initX = existing?.x ?? n.initialX;
      let initY = existing?.y ?? n.initialY;

      if (initX === undefined || initY === undefined) {
        // If node is connected to an existing node, place it near that neighbor to prevent jumping
        const connectedNeighbor = filteredLinks.find(
          (l) =>
            extractNodeId(l.source) === n.id ||
            extractNodeId(l.target) === n.id,
        );
        const neighborId = connectedNeighbor
          ? extractNodeId(connectedNeighbor.source) === n.id
            ? extractNodeId(connectedNeighbor.target)
            : extractNodeId(connectedNeighbor.source)
          : null;
        const neighborPos = neighborId ? prevPositions.get(neighborId) : null;

        if (neighborPos && typeof neighborPos.x === "number") {
          const jitterAngle = idx * 1.618 * 2 * Math.PI;
          initX = neighborPos.x + 45 * Math.cos(jitterAngle);
          initY = neighborPos.y + 45 * Math.sin(jitterAngle);
        } else {
          const angle = (2 * Math.PI * idx) / Math.max(1, filteredNodes.length);
          const r = 70 + (idx % 6) * 45;
          initX = width / 2 + r * Math.cos(angle);
          initY = height / 2 + r * Math.sin(angle);
        }
      }

      return {
        ...n,
        x: initX,
        y: initY,
        vx: existing?.vx ?? 0,
        vy: existing?.vy ?? 0,
      };
    });

    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks = filteredLinks
      .map((l) => {
        const sId = extractNodeId(l.source);
        const tId = extractNodeId(l.target);
        if (!nodeMap.has(sId) || !nodeMap.has(tId)) return null;
        return {
          ...l,
          source: nodeMap.get(sId),
          target: nodeMap.get(tId),
        };
      })
      .filter(Boolean);

    graphDataRef.current = { nodes: simNodes, edges: simLinks };

    // Precalculate adjacency lookup maps for rapid hover & selection highlighting
    const adjacencyMap = new Map();
    simNodes.forEach((n) => adjacencyMap.set(n.id, new Set()));
    const incidentLinksMap = new Map();
    simNodes.forEach((n) => incidentLinksMap.set(n.id, []));

    simLinks.forEach((link) => {
      const sId = extractNodeId(link.source);
      const tId = extractNodeId(link.target);
      adjacencyMap.get(sId)?.add(tId);
      adjacencyMap.get(tId)?.add(sId);
      incidentLinksMap.get(sId)?.push(link.id);
      incidentLinksMap.get(tId)?.push(link.id);
    });

    const effectiveLayout =
      currentLayout === "cose" || currentLayout === "cola"
        ? "force"
        : currentLayout === "circle"
          ? "radial"
          : currentLayout === "breadthfirst"
            ? "hierarchical"
            : currentLayout;

    // Layout configuration & simulation early stopping
    if (effectiveLayout === "radial") {
      const cx = width / 2;
      const cy = height / 2;
      const rootId = String(
        activeSelectedId || focusedCenterId || "mutalporul",
      );
      const rootNode = simNodes.find((n) => String(n.id) === rootId);
      if (rootNode) {
        rootNode.x = cx;
        rootNode.y = cy;
        rootNode.vx = 0;
        rootNode.vy = 0;
      }

      const others = simNodes.filter((n) => n !== rootNode);
      const inner = others.filter(
        (n) =>
          n.type === "Concept" ||
          n.hierarchy_level === "L4" ||
          n.type === "Section" ||
          n.type === "Work",
      );
      const outer = others.filter((n) => !inner.includes(n));

      const rInner = Math.min(width, height) * 0.25;
      const rOuter = Math.min(width, height) * 0.42;

      inner.forEach((n, idx) => {
        const angle =
          (2 * Math.PI * idx) / Math.max(1, inner.length) - Math.PI / 2;
        n.x = cx + rInner * Math.cos(angle);
        n.y = cy + rInner * Math.sin(angle);
        n.vx = 0;
        n.vy = 0;
        prevPositions.set(n.id, { x: n.x, y: n.y, vx: 0, vy: 0 });
      });

      outer.forEach((n, idx) => {
        const angle =
          (2 * Math.PI * idx) / Math.max(1, outer.length) - Math.PI / 2;
        n.x = cx + rOuter * Math.cos(angle);
        n.y = cy + rOuter * Math.sin(angle);
        n.vx = 0;
        n.vy = 0;
        prevPositions.set(n.id, { x: n.x, y: n.y, vx: 0, vy: 0 });
      });

      simulationRef.current = null;
      queueMicrotask(() => setIsSimulating(false));
    } else if (effectiveLayout === "hierarchical") {
      const getTier = (n) => {
        const h = String(
          n.hierarchy_level || n.hierarchyLevel || "",
        ).toUpperCase();
        if (h === "L0" || n.type === "Literature") return 0;
        if (h === "L1" || n.type === "Work") return 1;
        if (h === "L2" || n.type === "Section") return 2;
        if (h === "L3" || n.type === "Verse" || n.isEvidenceRecord) return 3;
        if (h === "L4" || n.type === "Concept") return 4;
        if (
          h === "L5" ||
          ["Person", "Object", "Event", "Entity"].includes(n.type)
        )
          return 5;
        if (["Premise", "Rule", "Inference", "Conclusion"].includes(n.type))
          return 6;
        return 4;
      };

      const tiers = [[], [], [], [], [], [], []];
      simNodes.forEach((n) => {
        tiers[getTier(n)].push(n);
      });

      const activeTiers = tiers
        .map((t, idx) => ({ tier: idx, nodes: t }))
        .filter((t) => t.nodes.length > 0);
      const tierCount = activeTiers.length;

      activeTiers.forEach((tObj, slotIdx) => {
        const y =
          height * (0.12 + 0.76 * (slotIdx / Math.max(1, tierCount - 1)));
        const count = tObj.nodes.length;
        tObj.nodes.forEach((n, i) => {
          n.x =
            count <= 1
              ? width / 2
              : ((i + 1) / (count + 1)) * (width - 120) + 60;
          n.y = y;
          n.vx = 0;
          n.vy = 0;
          prevPositions.set(n.id, { x: n.x, y: n.y, vx: 0, vy: 0 });
        });
      });

      simulationRef.current = null;
      queueMicrotask(() => setIsSimulating(false));
    } else if (effectiveLayout === "preset") {
      const cols = Math.ceil(Math.sqrt(simNodes.length * 1.5));
      const colWidth = 140;
      const rowHeight = 100;
      const startX = Math.max(60, (width - cols * colWidth) / 2);
      const startY = 80;

      simNodes.forEach((n, idx) => {
        if (typeof n.initialX === "number" && typeof n.initialY === "number") {
          n.x = n.initialX;
          n.y = n.initialY;
        } else {
          const col = idx % cols;
          const row = Math.floor(idx / cols);
          n.x = startX + col * colWidth;
          n.y = startY + row * rowHeight;
        }
        n.vx = 0;
        n.vy = 0;
        prevPositions.set(n.id, { x: n.x, y: n.y, vx: 0, vy: 0 });
      });

      simulationRef.current = null;
      queueMicrotask(() => setIsSimulating(false));
    } else {
      // Force simulations ("force", "cose", "cola")
      const linkDist = isLargeGraph ? 130 : 165;
      const chargeStrength = isVeryLargeGraph
        ? -300
        : isLargeGraph
          ? -380
          : -480;
      const alphaDecay = isVeryLargeGraph ? 0.08 : isLargeGraph ? 0.055 : 0.035;
      const alphaMinCutoff = isLargeGraph ? 0.007 : 0.003;
      queueMicrotask(() => setIsSimulating(true));

      const simulation = d3
        .forceSimulation(simNodes)
        .force(
          "link",
          d3
            .forceLink(simLinks)
            .id((d) => d.id)
            .distance(linkDist)
            .strength(0.7),
        )
        .force(
          "charge",
          d3
            .forceManyBody()
            .strength(chargeStrength)
            .distanceMax(isLargeGraph ? 480 : 600),
        )
        .force("center", d3.forceCenter(width / 2, height / 2).strength(0.08))
        .force("x", d3.forceX(width / 2).strength(0.04))
        .force("y", d3.forceY(height / 2).strength(0.04))
        .force(
          "collide",
          d3
            .forceCollide()
            .radius((d) => (d.radius || 28) + (isLargeGraph ? 16 : 26))
            .iterations(isLargeGraph ? 1 : 2),
        )
        .alpha(isLargeGraph ? 0.6 : 0.8)
        .alphaMin(alphaMinCutoff)
        .alphaDecay(alphaDecay);

      // Pre-warm headless iterations in memory to stabilize layout before painting
      const prewarmIterations = isVeryLargeGraph ? 35 : isLargeGraph ? 25 : 15;
      for (let i = 0; i < prewarmIterations; ++i) {
        simulation.tick();
      }

      simulation.on("end", () => {
        simNodes.forEach((n) => {
          prevPositionsRef.current.set(n.id, {
            x: n.x,
            y: n.y,
            vx: 0,
            vy: 0,
          });
        });
        simulation.stop();
        setIsSimulating(false);
      });

      simulationRef.current = simulation;
    }

    // 1. RENDER LINKS in kg-links-group as SVG Paths with smooth transitions
    const linkElements = linksGroup
      .selectAll("path.kg-edge")
      .data(simLinks, (d) => d.id)
      .join(
        (enter) =>
          enter
            .append("path")
            .attr(
              "class",
              "kg-edge transition-opacity duration-200 cursor-pointer",
            )
            .attr("fill", "none")
            .attr("stroke", (d) => {
              if (
                d.isProofTraceEdge ||
                d.contributed_to_reasoning ||
                d.contributedToReasoning
              )
                return "#d97706";
              if (
                d.contributed_to_evidence ||
                d.contributedToEvidence ||
                (Array.isArray(d.evidence_ids) && d.evidence_ids.length > 0)
              )
                return "#059669";
              return "#94a3b8";
            })
            .attr("stroke-width", (d) => {
              if (
                d.isProofTraceEdge ||
                d.contributed_to_reasoning ||
                d.contributedToReasoning
              )
                return 3.2;
              if (d.contributed_to_evidence || d.contributedToEvidence)
                return 2.4;
              return 1.8;
            })
            .attr("stroke-opacity", 0)
            .attr("marker-end", (d) =>
              d.isProofTraceEdge ||
              d.contributed_to_reasoning ||
              d.contributedToReasoning
                ? "url(#d3-arrow-proof)"
                : "url(#d3-arrow-default)",
            )
            .call((enter) =>
              enter.transition().duration(350).attr("stroke-opacity", 0.95),
            ),
        (update) =>
          update
            .attr("stroke", (d) => {
              if (
                d.isProofTraceEdge ||
                d.contributed_to_reasoning ||
                d.contributedToReasoning
              )
                return "#d97706";
              if (
                d.contributed_to_evidence ||
                d.contributedToEvidence ||
                (Array.isArray(d.evidence_ids) && d.evidence_ids.length > 0)
              )
                return "#059669";
              return "#94a3b8";
            })
            .attr("stroke-width", (d) => {
              if (
                d.isProofTraceEdge ||
                d.contributed_to_reasoning ||
                d.contributedToReasoning
              )
                return 3.2;
              if (d.contributed_to_evidence || d.contributedToEvidence)
                return 2.4;
              return 1.8;
            })
            .attr("marker-end", (d) =>
              d.isProofTraceEdge ||
              d.contributed_to_reasoning ||
              d.contributedToReasoning
                ? "url(#d3-arrow-proof)"
                : "url(#d3-arrow-default)",
            )
            .attr("stroke-opacity", 0.95),
        (exit) =>
          exit.call((exit) =>
            exit.transition().duration(250).attr("stroke-opacity", 0).remove(),
          ),
      );

    // 2. RENDER LINK LABELS in kg-link-labels-group
    const linkLabelElements = linkLabelsGroup
      .selectAll("g.kg-edge-label-group")
      .data(simLinks, (d) => d.id)
      .join(
        (enter) => {
          const gLabel = enter
            .append("g")
            .attr(
              "class",
              "kg-edge-label-group cursor-pointer select-none pointer-events-none",
            )
            .attr("opacity", 0);

          gLabel.each(function (d) {
            const el = d3.select(this);
            const labelText = d.label || d.type || "";
            const estimatedWidth = Math.max(26, labelText.length * 6.2 + 12);

            el.append("rect")
              .attr("rx", 4)
              .attr("ry", 4)
              .attr("fill", "#ffffff")
              .attr("stroke", d.isProofTraceEdge ? "#fde68a" : "#cbd5e1")
              .attr("stroke-width", 1)
              .attr("height", 14)
              .attr("y", -7)
              .attr("x", -estimatedWidth / 2)
              .attr("width", estimatedWidth);

            el.append("text")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("font-size", "9px")
              .attr("font-family", "system-ui, -apple-system, sans-serif")
              .attr("font-weight", "600")
              .attr("fill", d.isProofTraceEdge ? "#92400e" : "#1e293b")
              .text(labelText);
          });

          return gLabel.call((enter) =>
            enter.transition().duration(350).attr("opacity", 1),
          );
        },
        (update) => update.attr("opacity", 1),
        (exit) =>
          exit.call((exit) =>
            exit.transition().duration(250).attr("opacity", 0).remove(),
          ),
      );

    // 3. RENDER NODES in kg-nodes-group with smooth enter / update / exit transitions
    const nodeElements = nodesGroup
      .selectAll("g.kg-node")
      .data(simNodes, (d) => d.id)
      .join(
        (enter) => {
          const gNode = enter
            .append("g")
            .attr(
              "class",
              "kg-node cursor-pointer transition-opacity duration-200",
            )
            .attr("id", (d) => `d3-node-${d.id}`)
            .attr("opacity", 0)
            .attr("transform", (d) => `translate(${d.x}, ${d.y})`);

          // Selection ring
          gNode
            .append("circle")
            .attr("class", "node-selection-ring")
            .attr("r", (d) => (d.radius || 28) + 7)
            .attr("fill", "none")
            .attr("stroke", "#6366f1")
            .attr("stroke-width", 2.5)
            .attr("stroke-dasharray", "4 3")
            .attr("opacity", 0);

          // Node main shape
          gNode.each(function (d) {
            const el = d3.select(this);
            const isProof =
              d.isProofTraceNode ||
              d.contributed_to_reasoning ||
              d.contributedToReasoning;
            const isEvidence =
              d.contributed_to_evidence ||
              d.contributedToEvidence ||
              (Array.isArray(d.evidence_ids) && d.evidence_ids.length > 0);
            const strokeColor = isProof
              ? "#f59e0b"
              : isEvidence
                ? "#10b981"
                : d.color || "#4f46e5";
            const strokeWidth = isProof ? 3.5 : isEvidence ? 3.0 : 2.2;
            const filterAttr = isProof
              ? "url(#d3-proof-glow)"
              : isLargeGraph
                ? "none"
                : "url(#d3-node-shadow)";

            if (d.shape === "rect") {
              const w = d.width || 86;
              const h = d.height || 48;
              el.append("rect")
                .attr("class", "node-main-shape")
                .attr("x", -w / 2)
                .attr("y", -h / 2)
                .attr("width", w)
                .attr("height", h)
                .attr("rx", 10)
                .attr("ry", 10)
                .attr("fill", d.bgColor || "#ffffff")
                .attr("stroke", strokeColor)
                .attr("stroke-width", strokeWidth)
                .attr("filter", filterAttr);
            } else if (d.shape === "pill") {
              const w = d.width || 88;
              const h = d.height || 44;
              el.append("rect")
                .attr("class", "node-main-shape")
                .attr("x", -w / 2)
                .attr("y", -h / 2)
                .attr("width", w)
                .attr("height", h)
                .attr("rx", 16)
                .attr("ry", 16)
                .attr("fill", d.bgColor || "#ffffff")
                .attr("stroke", strokeColor)
                .attr("stroke-width", strokeWidth)
                .attr("filter", filterAttr);
            } else {
              const r = d.radius || 28;
              el.append("circle")
                .attr("class", "node-main-shape")
                .attr("r", r)
                .attr("fill", d.bgColor || "#ffffff")
                .attr("stroke", strokeColor)
                .attr("stroke-width", strokeWidth)
                .attr("filter", filterAttr);
            }
          });

          return gNode.call((enter) =>
            enter.transition().duration(400).attr("opacity", 1),
          );
        },
        (update) => update.attr("opacity", 1),
        (exit) =>
          exit.call((exit) =>
            exit.transition().duration(280).attr("opacity", 0).remove(),
          ),
      );

    // 4. RENDER NODE LABELS in kg-node-labels-group
    const nodeLabelElements = nodeLabelsGroup
      .selectAll("g.kg-node-label")
      .data(simNodes, (d) => d.id)
      .join(
        (enter) => {
          const gLabel = enter
            .append("g")
            .attr("class", "kg-node-label pointer-events-none select-none")
            .attr("opacity", 0)
            .attr("transform", (d) => `translate(${d.x}, ${d.y})`);

          gLabel.each(function (d) {
            const el = d3.select(this);
            const fullLabel = d.tamilLabel || d.label || d.id;
            const truncatedLabel =
              fullLabel.length > 14
                ? fullLabel.slice(0, 12) + "..."
                : fullLabel;

            el.append("text")
              .attr("class", "node-title-text tamil-font")
              .attr("text-anchor", "middle")
              .attr("dominant-baseline", "central")
              .attr("y", d.transliteration ? -4 : 0)
              .attr(
                "font-family",
                "'Noto Sans Tamil', 'Noto Serif Tamil', 'Mukta Malar', 'Latha', system-ui, sans-serif",
              )
              .attr("font-size", d.shape === "rect" ? "11px" : "10px")
              .attr("font-weight", "700")
              .attr("fill", d.textColor || "#0f172a")
              .attr("paint-order", "stroke fill")
              .attr("stroke", "#ffffff")
              .attr("stroke-width", "3.5px")
              .attr("stroke-linejoin", "round")
              .text(truncatedLabel);

            if (d.transliteration) {
              const tr =
                d.transliteration.length > 12
                  ? d.transliteration.slice(0, 10) + ".."
                  : d.transliteration;
              el.append("text")
                .attr("class", "node-sub-text")
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "central")
                .attr("y", 9)
                .attr("font-size", "8px")
                .attr("font-family", "ui-monospace, monospace")
                .attr("font-weight", "600")
                .attr("fill", "#334155")
                .attr("paint-order", "stroke fill")
                .attr("stroke", "#ffffff")
                .attr("stroke-width", "2.5px")
                .attr("stroke-linejoin", "round")
                .text(tr);
            }
          });

          return gLabel.call((enter) =>
            enter.transition().duration(400).attr("opacity", 1),
          );
        },
        (update) => update.attr("opacity", 1),
        (exit) =>
          exit.call((exit) =>
            exit.transition().duration(280).attr("opacity", 0).remove(),
          ),
      );

    // Dynamic edge path and label calculators
    const computeEdgePath = (d) => {
      const sx = d.source.x ?? 0;
      const sy = d.source.y ?? 0;
      const tx = d.target.x ?? 0;
      const ty = d.target.y ?? 0;
      const sRadius = d.source.radius || 28;
      const tRadius = d.target.radius || 28;

      // Self-referential loop
      if (d.source.id === d.target.id || d.isSelfReferential) {
        const loopIdx = d.linkIndex || 0;
        const loopR = sRadius + 8 + loopIdx * 12;
        return `M ${sx - sRadius * 0.4} ${sy - sRadius * 0.9} C ${sx - loopR * 1.6} ${sy - loopR * 2.3}, ${sx + loopR * 1.6} ${sy - loopR * 2.3}, ${sx + sRadius * 0.4} ${sy - sRadius * 0.9}`;
      }

      const dx = tx - sx;
      const dy = ty - sy;
      const dist = Math.hypot(dx, dy) || 1;
      const targetOffset = tRadius + 5;
      const endX = tx - (dx / dist) * targetOffset;
      const endY = ty - (dy / dist) * targetOffset;

      // Parallel multi-edges between same node pair
      if (d.totalParallelLinks && d.totalParallelLinks > 1) {
        const total = d.totalParallelLinks;
        const idx = d.linkIndex || 0;
        const curveOffset = (idx - (total - 1) / 2) * 26;
        const nx = -dy / dist;
        const ny = dx / dist;
        const mx = (sx + endX) / 2;
        const my = (sy + endY) / 2;
        const cx = mx + nx * curveOffset;
        const cy = my + ny * curveOffset;
        return `M ${sx} ${sy} Q ${cx} ${cy} ${endX} ${endY}`;
      }

      return `M ${sx} ${sy} L ${endX} ${endY}`;
    };

    const computeEdgeLabelTransform = (d) => {
      const sx = d.source.x ?? 0;
      const sy = d.source.y ?? 0;
      const tx = d.target.x ?? 0;
      const ty = d.target.y ?? 0;
      const sRadius = d.source.radius || 28;

      if (d.source.id === d.target.id || d.isSelfReferential) {
        const loopIdx = d.linkIndex || 0;
        const loopR = sRadius + 8 + loopIdx * 12;
        return `translate(${sx}, ${sy - loopR * 2.1})`;
      }

      if (d.totalParallelLinks && d.totalParallelLinks > 1) {
        const total = d.totalParallelLinks;
        const idx = d.linkIndex || 0;
        const curveOffset = (idx - (total - 1) / 2) * 26;
        const dx = tx - sx;
        const dy = ty - sy;
        const dist = Math.hypot(dx, dy) || 1;
        const nx = -dy / dist;
        const ny = dx / dist;
        const mx = (sx + tx) / 2;
        const my = (sy + ty) / 2;
        const cx = mx + nx * curveOffset;
        const cy = my + ny * curveOffset;
        const px = 0.25 * sx + 0.5 * cx + 0.25 * tx;
        const py = 0.25 * sy + 0.5 * cy + 0.25 * ty;
        return `translate(${px}, ${py})`;
      }

      const mx = (sx + tx) / 2;
      const my = (sy + ty) / 2;
      return `translate(${mx}, ${my})`;
    };

    // Drag behavior with event stopPropagation, threshold and bounded reheat
    const dragBehavior = d3
      .drag()
      .on("start", (event, d) => {
        if (event.sourceEvent) event.sourceEvent.stopPropagation();
        dragStartPosRef.current = { x: event.x, y: event.y, moved: false };
        d.fx = d.x;
        d.fy = d.y;
        if (simulationRef.current) {
          simulationRef.current.alphaTarget(0.12).restart();
          setIsSimulating(true);
        }
      })
      .on("drag", (event, d) => {
        const dx = event.x - dragStartPosRef.current.x;
        const dy = event.y - dragStartPosRef.current.y;
        if (Math.hypot(dx, dy) > 4) {
          dragStartPosRef.current.moved = true;
        }
        d.fx = event.x;
        d.fy = event.y;
        if (!simulationRef.current) {
          d.x = event.x;
          d.y = event.y;
          ticked();
        }
      })
      .on("end", (event, d) => {
        if (simulationRef.current) {
          simulationRef.current.alphaTarget(0);
          d.fx = null;
          d.fy = null;
        }
        prevPositionsRef.current.set(d.id, {
          x: d.x,
          y: d.y,
          vx: 0,
          vy: 0,
        });
      });

    nodeElements.call(dragBehavior);

    // Throttled Tick function using requestAnimationFrame to prevent DOM thrashing
    let tickAnimFrameId = null;
    const ticked = () => {
      if (tickAnimFrameId) return;
      tickAnimFrameId = requestAnimationFrame(() => {
        tickAnimFrameId = null;
        linkElements.attr("d", computeEdgePath);
        linkLabelElements.attr("transform", computeEdgeLabelTransform);
        nodeElements.attr("transform", (d) => `translate(${d.x}, ${d.y})`);
        nodeLabelElements.attr("transform", (d) => `translate(${d.x}, ${d.y})`);
      });
    };

    if (simulationRef.current) {
      simulationRef.current.on("tick", ticked);
    } else {
      ticked();
    }

    // Node click handler (reads stable refs without triggering re-render)
    nodeElements.on("click", (event, d) => {
      event.stopPropagation();
      if (dragStartPosRef.current.moved) return;
      const clickedId = d.id;

      setSelectedEdgeData(null);
      setFocusedCenterId(clickedId);
      setClickedNodeData(d);

      const rect = container.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;
      setPopoverPos(calculateClampedPos(clickX, clickY, 380, 320));

      // Node-Centered Focus Mode: visually focus and frame the selected node's neighborhood
      if (focusOnNeighborhoodRef.current) {
        focusOnNeighborhoodRef.current(clickedId, 75, 600);
      }

      // Trigger dynamic expansion for the selected node directly from Neo4j Aura
      if (expandSelectedNodeRef.current) {
        expandSelectedNodeRef.current(d);
      }

      // Synchronize seamlessly with Query Center results & ReasonerContext
      if (selectSynchronizedItemRef.current) {
        selectSynchronizedItemRef.current(d, "graph");
      } else {
        const evidenceRecords = evidenceRecordsRef.current;
        const setSelectedEvidenceId = setSelectedEvidenceIdRef.current;
        if (
          evidenceRecords &&
          evidenceRecords.length > 0 &&
          setSelectedEvidenceId
        ) {
          const matchedEv = evidenceRecords.find(
            (ev) =>
              String(ev.id) === String(clickedId) ||
              String(ev.passageId) === String(clickedId) ||
              String(ev.code) === String(clickedId),
          );
          if (matchedEv) {
            setSelectedEvidenceId(matchedEv.id);
          }
        }

        const setNodeId = setSelectedNodeIdRef.current;
        if (setNodeId) {
          setNodeId((prev) => (prev === clickedId ? null : clickedId));
        }
      }
    });

    // Edge click handler
    linkElements.on("click", (event, d) => {
      event.stopPropagation();
      if (setSelectedNodeIdRef.current) setSelectedNodeIdRef.current(null);
      setClickedNodeData(null);

      const rect = container.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;
      setPopoverPos(calculateClampedPos(clickX, clickY, 368, 260));

      setSelectedEdgeData({
        id: d.id,
        label: d.label,
        type: d.type || d.relation,
        relation: d.relation || d.type,
        sourceId: d.source.id,
        targetId: d.target.id,
        sourceLabel: d.source.label || d.source.id,
        targetLabel: d.target.label || d.target.id,
        confidence: d.confidence,
        validationLevel:
          d.properties?.validation_level ||
          d.validationLevel ||
          "corpus_validated",
        sourceReference:
          d.properties?.source_reference || d.sourceReference || "",
        sourceCorpus:
          d.properties?.source_corpus || d.sourceCorpus || "Tolkāppiyam",
        passageId: d.properties?.passage_id || d.passageId || "",
        metadata: d.properties || {},
      });
    });

    // Interactive Hover Highlighting
    nodeElements
      .on("mouseenter", function (event, hoveredNode) {
        const neighbors = adjacencyMap.get(hoveredNode.id) || new Set();
        const incidentEdges = new Set(
          incidentLinksMap.get(hoveredNode.id) || [],
        );

        nodeElements.attr("opacity", (d) => {
          if (d.id === hoveredNode.id || neighbors.has(d.id)) return 1;
          return 0.85;
        });

        nodeLabelElements.attr("opacity", (d) => {
          if (d.id === hoveredNode.id || neighbors.has(d.id)) return 1;
          return 0.85;
        });

        linkElements
          .attr("opacity", (d) => (incidentEdges.has(d.id) ? 1 : 0.75))
          .attr("stroke", (d) =>
            incidentEdges.has(d.id) ? "#4f46e5" : "#94a3b8",
          )
          .attr("stroke-width", (d) => (incidentEdges.has(d.id) ? 3.0 : 1.6))
          .attr("marker-end", (d) =>
            incidentEdges.has(d.id)
              ? "url(#d3-arrow-highlight)"
              : "url(#d3-arrow-default)",
          );

        linkLabelElements.attr("opacity", (d) =>
          incidentEdges.has(d.id) ? 1 : 0.8,
        );

        d3.select(this)
          .select(".node-main-shape")
          .attr("stroke-width", (n) => (n.isProofTraceNode ? 4.5 : 3.8));
      })
      .on("mouseleave", function () {
        d3.select(this)
          .select(".node-main-shape")
          .attr("stroke-width", (n) => (n.isProofTraceNode ? 3.5 : 2.2));
        if (syncHighlightsRef.current) {
          syncHighlightsRef.current();
        }
      });

    linkElements
      .on("mouseenter", function (event, hoveredLink) {
        const sId = extractNodeId(hoveredLink.source);
        const tId = extractNodeId(hoveredLink.target);
        nodeElements.attr("opacity", (d) => {
          if (d.id === sId || d.id === tId) return 1;
          return 0.85;
        });

        nodeLabelElements.attr("opacity", (d) => {
          if (d.id === sId || d.id === tId) return 1;
          return 0.85;
        });

        linkElements
          .attr("opacity", (d) => (d.id === hoveredLink.id ? 1 : 0.75))
          .attr("stroke", (d) =>
            d.id === hoveredLink.id ? "#4f46e5" : "#94a3b8",
          )
          .attr("stroke-width", (d) => (d.id === hoveredLink.id ? 3.2 : 1.6))
          .attr("marker-end", (d) =>
            d.id === hoveredLink.id
              ? "url(#d3-arrow-highlight)"
              : "url(#d3-arrow-default)",
          );

        linkLabelElements.attr("opacity", (d) =>
          d.id === hoveredLink.id ? 1 : 0.8,
        );
      })
      .on("mouseleave", function () {
        if (syncHighlightsRef.current) {
          syncHighlightsRef.current();
        }
      });

    // Initial centering and fit
    const fitTimer = setTimeout(() => {
      fitView(55, 300);
    }, 180);

    // Responsive Debounced ResizeObserver (prevents layout thrashing and jumpy UI on resize)
    let resizeTimer = null;
    const resizeObserver = new ResizeObserver((entries) => {
      if (!entries || entries.length === 0) return;
      const entry = entries[0];
      const { width: newW, height: newH } = entry.contentRect;
      if (newW <= 0 || newH <= 0) return;

      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => {
        if (simulationRef.current) {
          simulationRef.current.force(
            "center",
            d3.forceCenter(newW / 2, newH / 2).strength(0.08),
          );
        }
        fitView(55, 200);
      }, 120);
    });
    resizeObserver.observe(container);

    // Comprehensive Cleanup: halts simulation, detaches all listeners, cancels animations & timers
    return () => {
      if (tickAnimFrameId) cancelAnimationFrame(tickAnimFrameId);
      clearTimeout(fitTimer);
      clearTimeout(resizeTimer);
      resizeObserver.disconnect();
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current.on("tick", null);
        simulationRef.current.on("end", null);
        simulationRef.current = null;
      }
      zoomBehavior.on("zoom", null);
      svg.on("click", null);
      svg.on(".zoom", null);
      nodeElements
        .on(".drag", null)
        .on("mouseenter", null)
        .on("mouseleave", null)
        .on("click", null);
      linkElements
        .on("click", null)
        .on("mouseenter", null)
        .on("mouseleave", null);
    };
  }, [
    filteredNodes,
    filteredLinks,
    currentLayout,
    calculateClampedPos,
    fitView,
    activeSelectedId,
    focusedCenterId,
  ]);

  // Synchronize highlights, Proof Trace mode, and Multi-Hop BFS traversal
  useEffect(() => {
    const syncHighlights = () => {
      const svg = d3.select(svgRef.current);
      if (svg.empty()) return;

      const { nodes, edges } = graphDataRef.current;
      if (nodes.length === 0) return;

      const nodeSelection = svg.selectAll("g.kg-node");
      const nodeLabelSelection = svg.selectAll("g.kg-node-label");
      const linkSelection = svg.selectAll("path.kg-edge");
      const labelSelection = svg.selectAll("g.kg-edge-label-group");

      // Baseline: ALWAYS 100% clear, vibrant, and visible
      nodeSelection
        .attr("opacity", 1)
        .select(".node-main-shape")
        .attr("stroke-width", (d) => (d.isProofTraceNode ? 3.5 : 2.2))
        .attr("stroke", (d) =>
          d.isProofTraceNode ? "#f59e0b" : d.color || "#6366f1",
        )
        .attr("filter", (d) =>
          d.isProofTraceNode ? "url(#d3-proof-glow)" : "none",
        );
      nodeLabelSelection.attr("opacity", 1);
      linkSelection
        .attr("opacity", 0.95)
        .attr("stroke", (d) => (d.isProofTraceEdge ? "#d97706" : "#94a3b8"))
        .attr("stroke-width", (d) => (d.isProofTraceEdge ? 3.2 : 1.8))
        .attr("stroke-dasharray", "none")
        .classed("d3-active-link-dash", false)
        .attr("marker-end", (d) =>
          d.isProofTraceEdge
            ? "url(#d3-arrow-proof)"
            : "url(#d3-arrow-default)",
        );
      labelSelection.each(function (d) {
        const el = d3.select(this);
        const labelText = d.label || d.type || "";
        const textWidth = Math.max(26, labelText.length * 6.2 + 12);
        el.attr("opacity", 1);
        el.select("rect")
          .attr("fill", "#ffffff")
          .attr("stroke", d.isProofTraceEdge ? "#fde68a" : "#cbd5e1")
          .attr("stroke-width", 1)
          .attr("height", 14)
          .attr("y", -7)
          .attr("x", -textWidth / 2)
          .attr("width", textWidth)
          .attr("rx", 4)
          .attr("ry", 4)
          .attr("filter", "none");
        el.select("text")
          .attr("font-size", "9px")
          .attr("font-weight", "600")
          .attr("fill", d.isProofTraceEdge ? "#92400e" : "#1e293b")
          .text(labelText);
      });
      nodeSelection.selectAll(".node-selection-halo").attr("opacity", 0);
      nodeSelection.selectAll(".node-selection-ring").attr("opacity", 0);
      nodeSelection.selectAll(".node-neighbor-ring").attr("opacity", 0);

      // MODE 1: PROOF TRACE FOCUS
      if (contextIsShowingProofTrace) {
        const proofNodeIdSet = new Set(
          (contextProofNodes || []).map((n) => String(n.id)),
        );
        const proofEdgeIdSet = new Set(
          (contextProofEdges || []).map((e) => String(e.id)),
        );

        nodeSelection.attr("opacity", (d) =>
          proofNodeIdSet.has(String(d.id)) ? 1 : 0.85,
        );
        nodeLabelSelection.attr("opacity", (d) =>
          proofNodeIdSet.has(String(d.id)) ? 1 : 0.85,
        );

        linkSelection
          .attr("opacity", (d) => {
            const isProof =
              proofEdgeIdSet.has(String(d.id)) ||
              d.isProofTraceEdge ||
              (proofNodeIdSet.has(String(extractNodeId(d.source))) &&
                proofNodeIdSet.has(String(extractNodeId(d.target))));
            return isProof ? 1 : 0.75;
          })
          .attr("stroke", (d) => {
            const isProof =
              proofEdgeIdSet.has(String(d.id)) ||
              d.isProofTraceEdge ||
              (proofNodeIdSet.has(String(extractNodeId(d.source))) &&
                proofNodeIdSet.has(String(extractNodeId(d.target))));
            return isProof ? "#d97706" : "#94a3b8";
          })
          .attr("stroke-width", (d) => (d.isProofTraceEdge ? 3.5 : 1.8))
          .attr("marker-end", (d) =>
            d.isProofTraceEdge
              ? "url(#d3-arrow-proof)"
              : "url(#d3-arrow-default)",
          );

        labelSelection.attr("opacity", (d) =>
          proofEdgeIdSet.has(String(d.id)) || d.isProofTraceEdge ? 1 : 0.8,
        );

        if (activeSelectedId) {
          nodeSelection
            .filter((d) => String(d.id) === String(activeSelectedId))
            .selectAll(".node-selection-ring")
            .attr("opacity", 1);
        }
        return;
      }

      // MODE 2: EXPLICIT NODE SELECTION FOCUS (STRONG HIGHLIGHT, DIRECTIONAL ARROWS, AND EDGE LABELS)
      const centerNodeId = activeSelectedId || focusedCenterId;
      if (centerNodeId) {
        const centerNode = findNodeByStableId(nodes, centerNodeId);

        if (centerNode) {
          const effectiveHops = typeof hopDepth === "number" ? hopDepth : 1;
          const { visitedNodeIds, inducedEdgeIds, directNeighborIds } =
            getInducedSubgraphNeighborhood(centerNode.id, edges, effectiveHops);

          // Identify directly connected 1st-degree relationships & canonical directions
          const directEdgeIds = new Set();
          const outgoingEdgeIds = new Set();
          const incomingEdgeIds = new Set();
          edges.forEach((e) => {
            const s = String(e.source?.id || e.source_id || e.source || "");
            const t = String(e.target?.id || e.target_id || e.target || "");
            const cid = String(centerNode.id);
            if (s === cid) {
              directEdgeIds.add(String(e.id));
              outgoingEdgeIds.add(String(e.id));
            } else if (t === cid) {
              directEdgeIds.add(String(e.id));
              incomingEdgeIds.add(String(e.id));
            }
          });

          // 1. Highlight Nodes:
          // - Selected root: Prominent 5.0px stroke, filter selected-glow, halo + ring active, 100% opacity, raised
          // - Directly connected neighbors: 100% opacity, 3.4px vibrant category stroke, neighbor-ring active, neighbor-glow
          // - Multi-hop visited (if hops > 1): 0.88 opacity, 2.6px stroke
          // - Unrelated nodes: Visually de-emphasized at 0.18 opacity, 1.0px muted stroke, filter none
          nodeSelection
            .attr("opacity", (d) => {
              if (String(d.id) === String(centerNode.id)) return 1.0;
              if (directNeighborIds.has(String(d.id))) return 1.0;
              if (visitedNodeIds.has(String(d.id))) return 0.88;
              return 0.18;
            })
            .select(".node-main-shape")
            .attr("stroke-width", (d) => {
              if (String(d.id) === String(centerNode.id))
                return d.isProofTraceNode ? 5.8 : 5.0;
              if (directNeighborIds.has(String(d.id))) return 3.4;
              if (visitedNodeIds.has(String(d.id))) return 2.6;
              return 1.0;
            })
            .attr("stroke", (d) => {
              if (String(d.id) === String(centerNode.id))
                return d.isProofTraceNode ? "#f59e0b" : "#4338ca";
              if (directNeighborIds.has(String(d.id)))
                return d.isProofTraceNode ? "#f59e0b" : d.color || "#6366f1";
              if (visitedNodeIds.has(String(d.id))) return d.color || "#94a3b8";
              return "#cbd5e1";
            })
            .attr("filter", (d) => {
              if (String(d.id) === String(centerNode.id))
                return "url(#d3-selected-glow)";
              if (directNeighborIds.has(String(d.id)))
                return "url(#d3-neighbor-glow)";
              if (d.isProofTraceNode) return "url(#d3-proof-glow)";
              return "none";
            });

          // Rings and Halos
          nodeSelection
            .selectAll(".node-selection-halo")
            .attr("opacity", (d) =>
              String(d.id) === String(centerNode.id) ? 1.0 : 0,
            );

          nodeSelection
            .selectAll(".node-selection-ring")
            .attr("opacity", (d) =>
              String(d.id) === String(centerNode.id) ? 1.0 : 0,
            );

          nodeSelection
            .selectAll(".node-neighbor-ring")
            .attr("opacity", (d) =>
              directNeighborIds.has(String(d.id)) ? 1.0 : 0,
            );

          // Raise the selected node to the top of the SVG rendering stack so it remains visually prominent during interactions
          nodeSelection
            .filter((d) => String(d.id) === String(centerNode.id))
            .raise();

          // 2. Node Labels:
          nodeLabelSelection.attr("opacity", (d) => {
            if (String(d.id) === String(centerNode.id)) return 1.0;
            if (directNeighborIds.has(String(d.id))) return 1.0;
            if (visitedNodeIds.has(String(d.id))) return 0.85;
            return 0.14;
          });

          nodeLabelSelection
            .filter((d) => String(d.id) === String(centerNode.id))
            .raise();

          // 3. Relationships (Links):
          // - Directly connected relationships: 1.0 opacity, 3.8px stroke, animated dash flow, prominent directional arrowhead, raised
          // - Outgoing edges: Indigo stroke (#4f46e5) + #d3-arrow-connected marker
          // - Incoming edges: Emerald stroke (#059669) + #d3-arrow-connected-in marker
          // - Multi-hop induced edges: 0.75 opacity, 2.2px stroke
          // - Unrelated edges: 0.06 opacity, 0.8px thin line, no marker, no label
          linkSelection
            .attr("opacity", (d) => {
              if (directEdgeIds.has(String(d.id))) return 1.0;
              if (inducedEdgeIds.has(String(d.id))) return 0.75;
              return 0.06;
            })
            .attr("stroke", (d) => {
              if (outgoingEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge ? "#d97706" : "#4f46e5";
              }
              if (incomingEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge ? "#d97706" : "#059669";
              }
              if (inducedEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge ? "#d97706" : "#6366f1";
              }
              return "#cbd5e1";
            })
            .attr("stroke-width", (d) => {
              if (directEdgeIds.has(String(d.id))) return 3.8;
              if (inducedEdgeIds.has(String(d.id))) return 2.2;
              return 0.8;
            })
            .attr("stroke-dasharray", (d) => {
              if (directEdgeIds.has(String(d.id))) return "6 4";
              return "none";
            })
            .classed("d3-active-link-dash", (d) =>
              directEdgeIds.has(String(d.id)),
            )
            .attr("marker-end", (d) => {
              if (outgoingEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge
                  ? "url(#d3-arrow-proof)"
                  : "url(#d3-arrow-connected)";
              }
              if (incomingEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge
                  ? "url(#d3-arrow-proof)"
                  : "url(#d3-arrow-connected-in)";
              }
              if (inducedEdgeIds.has(String(d.id))) {
                return d.isProofTraceEdge
                  ? "url(#d3-arrow-proof)"
                  : "url(#d3-arrow-highlight)";
              }
              return null;
            });

          linkSelection
            .filter((d) => directEdgeIds.has(String(d.id)))
            .raise();

          // 4. Edge Labels:
          // - Direct edges: High-contrast white pill with colored border, bold text with directional arrow indicator (→ or ←)
          // - Induced edges: Subdued neutral pill
          // - Unrelated edges: Hidden completely (opacity 0)
          labelSelection.each(function (d) {
            const el = d3.select(this);
            const edgeIdStr = String(d.id);
            const isDirect = directEdgeIds.has(edgeIdStr);
            const isOutgoing = outgoingEdgeIds.has(edgeIdStr);
            const isIncoming = incomingEdgeIds.has(edgeIdStr);
            const isInduced = inducedEdgeIds.has(edgeIdStr);

            if (isDirect) {
              const rawType = d.label || d.type || d.relation || "";
              const directionalText = isOutgoing
                ? `${rawType} →`
                : isIncoming
                  ? `← ${rawType}`
                  : rawType;
              const textWidth = Math.max(34, directionalText.length * 6.5 + 16);

              el.attr("opacity", 1.0).raise();

              el.select("rect")
                .attr("fill", "#ffffff")
                .attr("stroke", isOutgoing ? "#4f46e5" : "#059669")
                .attr("stroke-width", 1.8)
                .attr("height", 18)
                .attr("y", -9)
                .attr("x", -textWidth / 2)
                .attr("width", textWidth)
                .attr("rx", 5)
                .attr("ry", 5)
                .attr("filter", "drop-shadow(0 1px 3px rgba(0,0,0,0.14))");

              el.select("text")
                .attr("font-size", "10px")
                .attr("font-weight", "700")
                .attr("fill", isOutgoing ? "#3730a3" : "#065f46")
                .text(directionalText);
            } else if (isInduced) {
              const labelText = d.label || d.type || "";
              const textWidth = Math.max(26, labelText.length * 6.2 + 12);
              el.attr("opacity", 0.75);
              el.select("rect")
                .attr("fill", "#ffffff")
                .attr("stroke", "#cbd5e1")
                .attr("stroke-width", 1)
                .attr("height", 14)
                .attr("y", -7)
                .attr("x", -textWidth / 2)
                .attr("width", textWidth)
                .attr("rx", 4)
                .attr("ry", 4)
                .attr("filter", "none");
              el.select("text")
                .attr("font-size", "9px")
                .attr("font-weight", "600")
                .attr("fill", "#475569")
                .text(labelText);
            } else {
              el.attr("opacity", 0);
            }
          });

          return;
        }
      }

      // MODE 3: CATEGORY FILTER
      if (activeCategoryFilter) {
        nodeSelection.attr("opacity", (d) =>
          d.category === activeCategoryFilter || d.type === activeCategoryFilter
            ? 1
            : 0.2,
        );
        nodeLabelSelection.attr("opacity", (d) =>
          d.category === activeCategoryFilter || d.type === activeCategoryFilter
            ? 1
            : 0.15,
        );

        linkSelection
          .attr("opacity", (d) => {
            const sCat = d.source?.category || d.source?.type;
            const tCat = d.target?.category || d.target?.type;
            return sCat === activeCategoryFilter ||
              tCat === activeCategoryFilter
              ? 1
              : 0.1;
          })
          .attr("stroke", (d) => {
            const sCat = d.source?.category || d.source?.type;
            const tCat = d.target?.category || d.target?.type;
            return sCat === activeCategoryFilter ||
              tCat === activeCategoryFilter
              ? "#4f46e5"
              : "#cbd5e1";
          });

        labelSelection.attr("opacity", (d) => {
          const sCat = d.source?.category || d.source?.type;
          const tCat = d.target?.category || d.target?.type;
          return sCat === activeCategoryFilter || tCat === activeCategoryFilter
            ? 1
            : 0;
        });
      }
    };

    syncHighlightsRef.current = syncHighlights;
    syncHighlights();
  }, [
    activeSelectedId,
    focusedCenterId,
    activeCategoryFilter,
    hopDepth,
    contextIsShowingProofTrace,
    contextProofNodes,
    contextProofEdges,
  ]);

  // Synchronize popover positioning and smooth camera auto-centering when activeSelectedId changes externally
  useEffect(() => {
    if (!activeSelectedId) {
      const frameId = requestAnimationFrame(() => {
        setClickedNodeData(null);
        setPopoverPos(null);
      });
      return () => cancelAnimationFrame(frameId);
    }

    const frameId = requestAnimationFrame(() => {
      const { nodes } = graphDataRef.current;
      const targetNode = findNodeByStableId(nodes, activeSelectedId);

      if (targetNode) {
        setClickedNodeData(targetNode);
        if (focusOnNeighborhoodRef.current) {
          focusOnNeighborhoodRef.current(activeSelectedId, 75, 600);
        }
      }
    });
    return () => cancelAnimationFrame(frameId);
  }, [activeSelectedId]);

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
                  Awaiting Query
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

              {/* Level of Detail Performance Acceleration Badge */}
              {stats.renderedEntities > 80 && (
                <span
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200"
                  title="Level of Detail optimizations active: filter drop-shadows and link labels streamlined for high entity count"
                >
                  <Zap className="w-2.5 h-2.5 text-emerald-600" />
                  <span>LoD Accelerated ({stats.renderedEntities} Nodes)</span>
                </span>
              )}

              {/* Simulation Stabilizing Activity Badge */}
              {isSimulating && (
                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 animate-pulse">
                  <RefreshCw className="w-2.5 h-2.5 animate-spin text-indigo-600" />
                  <span>Stabilizing Layout...</span>
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Toolbar Controls */}
      {showToolbar && (
        <div className="flex flex-col border-b border-slate-100 bg-slate-50/50 text-xs">
          {/* Unified Compact Toolbar: Search, Filters, Layout & Hops */}
          <div className="flex items-center justify-between px-4 sm:px-5 py-2 gap-2 flex-wrap border-b border-slate-100/80">
            <div className="flex items-center gap-2 flex-1 min-w-[200px] sm:min-w-[260px] flex-wrap">
              {/* Real-time Search Input */}

              {/* Filter 1: Entity Type Dropdown */}
              <div className="relative inline-flex items-center shrink-0">
                <Filter className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <select
                  value={selectedEntityType}
                  onChange={(e) => setSelectedEntityType(e.target.value)}
                  className="appearance-none text-[11px] font-semibold bg-white hover:bg-purple-50/50 text-purple-950 pl-7 pr-6 py-1.5 rounded-xl border border-purple-200/90 hover:border-purple-400 shadow-2xs focus:ring-2 focus:ring-purple-500/25 focus:border-purple-500 focus:outline-none transition-all cursor-pointer"
                  title="Filter by Entity Type"
                >
                  <option value="ALL" className="bg-white text-slate-800 py-1">
                    All Entity Types
                  </option>
                  {availableEntityTypes.map((type) => (
                    <option
                      key={type}
                      value={type}
                      className="bg-white text-slate-800 py-1"
                    >
                      {type}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-purple-500 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Filter 2: Relationship Type Dropdown */}
              <div className="relative inline-flex items-center shrink-0">
                <Share2 className="w-3.5 h-3.5 text-indigo-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <select
                  value={selectedRelationshipType}
                  onChange={(e) => setSelectedRelationshipType(e.target.value)}
                  className="appearance-none text-[11px] font-semibold bg-white hover:bg-indigo-50/50 text-indigo-950 pl-7 pr-6 py-1.5 rounded-xl border border-indigo-200/90 hover:border-indigo-400 shadow-2xs focus:ring-2 focus:ring-indigo-500/25 focus:border-indigo-500 focus:outline-none transition-all cursor-pointer max-w-[150px] truncate"
                  title="Filter by Relationship Type"
                >
                  <option value="ALL" className="bg-white text-slate-800 py-1">
                    All Relationships
                  </option>
                  {availableRelationshipTypes.map((rel) => (
                    <option
                      key={rel}
                      value={rel}
                      className="bg-white text-slate-800 py-1"
                    >
                      {rel}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-indigo-500 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Filter 3: Hierarchy Level Dropdown */}
              <div className="relative inline-flex items-center shrink-0">
                <Layers className="w-3.5 h-3.5 text-emerald-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <select
                  value={selectedHierarchyLevel}
                  onChange={(e) => setSelectedHierarchyLevel(e.target.value)}
                  className="appearance-none text-[11px] font-semibold bg-white hover:bg-emerald-50/50 text-emerald-950 pl-7 pr-6 py-1.5 rounded-xl border border-emerald-200/90 hover:border-emerald-400 shadow-2xs focus:ring-2 focus:ring-emerald-500/25 focus:border-emerald-500 focus:outline-none transition-all cursor-pointer"
                  title="Filter by Structural Hierarchy Level"
                >
                  <option value="ALL" className="bg-white text-slate-800 py-1">
                    All Hierarchy
                  </option>
                  {availableHierarchyLevels.map((lvl) => (
                    <option
                      key={lvl}
                      value={lvl}
                      className="bg-white text-slate-800 py-1"
                    >
                      {lvl}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3 h-3 text-emerald-500 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>
            </div>

            {/* Right: Layout selector, Hops, and Reset Filters */}
            <div className="flex items-center gap-2 shrink-0 flex-wrap">
              {/* Layout Selector Dropdown */}
              <div className="relative inline-flex items-center">
                <Compass className="w-3.5 h-3.5 text-purple-600 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
                <select
                  value={
                    currentLayout === "cose" || currentLayout === "cola"
                      ? "force"
                      : currentLayout === "breadthfirst"
                        ? "hierarchical"
                        : currentLayout === "circle"
                          ? "radial"
                          : currentLayout
                  }
                  onChange={(e) => setCurrentLayout(e.target.value)}
                  className="appearance-none text-[11px] font-semibold bg-white hover:bg-purple-50/60 text-purple-950 pl-7 pr-6 py-1.5 rounded-xl border border-slate-200/90 hover:border-purple-300 shadow-2xs focus:ring-2 focus:ring-purple-500/25 focus:border-purple-500 focus:outline-none transition-all cursor-pointer"
                  title="Select D3 Automatic Layout Algorithm"
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
                <ChevronDown className="w-3 h-3 text-purple-500 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none" />
              </div>

              {/* Configurable Graph Depth / Hops */}
              <div className="flex items-center gap-0.5 bg-white px-1.5 py-1 rounded-xl border border-slate-200/90 shadow-2xs">
                <GitBranch className="w-3 h-3 text-purple-600 mr-0.5" />
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider pr-0.5 hidden sm:inline">
                  Hops:
                </span>
                {[1, 2, 3, 4, 5].map((hops) => (
                  <button
                    key={hops}
                    type="button"
                    onClick={() => setHopDepth(hops)}
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold transition-colors cursor-pointer ${
                      hopDepth === hops
                        ? "bg-purple-600 text-white shadow-2xs"
                        : "text-slate-600 hover:bg-slate-100"
                    }`}
                    title={`Filter to ${hops}-hop neighborhood`}
                  >
                    {hops}
                  </button>
                ))}
          
              </div>

              {/* Reset Filters Action Pill (only appears when filtered) */}
              {stats.isFiltered && (
                <button
                  type="button"
                  onClick={handleResetAllFilters}
                  className="inline-flex items-center gap-1 text-[11px] font-bold text-rose-700 hover:text-rose-900 bg-rose-50 hover:bg-rose-100 px-2.5 py-1 rounded-xl border border-rose-200 shadow-2xs cursor-pointer transition-colors"
                  title="Reset all search queries and filters to default view"
                >
                  <RotateCcw className="w-3 h-3" />
                  <span>Reset</span>
                </button>
              )}
            </div>
          </div>

          {/* Selected Node Information HUD Strip */}
          {selectedNodeDetails && (
            <div className="px-4 sm:px-5 py-2 bg-purple-50/70 border-t border-purple-200/80 text-xs flex items-center justify-between gap-3 flex-wrap animate-in fade-in duration-150">
              <div className="flex items-center gap-2.5 flex-wrap min-w-0">
                <div className="flex items-center gap-1.5">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: selectedNodeDetails.color || "#7c3aed",
                    }}
                  />
                  <span className="font-bold text-slate-900 text-sm">
                    {selectedNodeDetails.tamilLabel ||
                      selectedNodeDetails.label}
                  </span>
                  {selectedNodeDetails.transliteration && (
                    <span className="text-slate-500 font-medium">
                      ({selectedNodeDetails.transliteration})
                    </span>
                  )}
                </div>

                <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-white text-purple-800 border border-purple-200">
                  {selectedNodeDetails.type ||
                    selectedNodeDetails.category ||
                    "Entity"}
                </span>

                {selectedNodeDetails.hierarchy_level && (
                  <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-white text-slate-700 border border-slate-200">
                    Level: {selectedNodeDetails.hierarchy_level}
                  </span>
                )}

                <span className="text-[11px] text-purple-950 font-medium">
                  Degree: <strong>{selectedNodeDetails.totalDegree}</strong> (
                  {selectedNodeDetails.inDegree} in,{" "}
                  {selectedNodeDetails.outDegree} out)
                </span>

                {selectedNodeDetails.description && (
                  <span className="text-slate-600 text-[11px] truncate max-w-md hidden md:inline">
                    — {selectedNodeDetails.description}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1.5 shrink-0 flex-wrap">
                {/* Traversal Depth Quick Selector */}
                <div className="flex items-center gap-0.5 bg-white px-1.5 py-0.5 rounded-lg border border-purple-200/90 shadow-2xs">
                  <span className="text-[10px] font-bold text-purple-900 mr-0.5">
                    Depth:
                  </span>
                  {[1, 2, 3, 4, 5].map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => {
                        setExpansionDepth(d);
                        expandSelectedNode(selectedNodeDetails, { hops: d });
                      }}
                      className={`px-1.5 py-0.5 rounded text-[10px] font-bold transition-colors cursor-pointer ${
                        expansionDepth === d
                          ? "bg-purple-600 text-white shadow-2xs"
                          : "text-purple-700 hover:bg-purple-100"
                      }`}
                      title={`Configure ${d}-hop traversal from Neo4j`}
                    >
                      {d}
                    </button>
                  ))}
                </div>

                {isExpandingNode ? (
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-semibold bg-purple-100 text-purple-800 border border-purple-300 animate-pulse">
                    <RefreshCw className="w-3 h-3 animate-spin text-purple-600" />
                    <span>Traversing Neo4j...</span>
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={() => expandSelectedNode(selectedNodeDetails)}
                    className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-lg text-[10px] font-semibold bg-purple-600 text-white hover:bg-purple-700 border border-purple-600 cursor-pointer transition-colors shadow-2xs"
                    title={`Retrieve bounded ${expansionDepth}-hop connected subgraph from Neo4j Aura`}
                  >
                    <GitBranch className="w-3 h-3" />
                    <span>Traverse ({expansionDepth} Hops)</span>
                  </button>
                )}
                {expansionFeedback && (
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10px] font-medium border ${
                      expansionFeedback.addedNodes > 0
                        ? "bg-emerald-50 text-emerald-800 border-emerald-200"
                        : "bg-slate-100 text-slate-700 border-slate-200"
                    }`}
                  >
                    {expansionFeedback.addedNodes > 0
                      ? `+${expansionFeedback.addedNodes} nodes (${expansionFeedback.hops || expansionDepth} hops)`
                      : "In graph"}
                  </span>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setHopDepth(1);
                    setFocusedCenterId(selectedNodeDetails.id);
                  }}
                  className="px-2 py-0.5 rounded-lg text-[10px] font-semibold bg-white text-purple-700 border border-purple-200 hover:bg-purple-100 cursor-pointer transition-colors"
                  title="Focus 1-hop direct neighbors"
                >
                  1-Hop Focus
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsFocusMode((prev) => !prev);
                    if (!isFocusMode && selectedNodeDetails) {
                      focusOnNeighborhood(selectedNodeDetails.id, 75, 600);
                    }
                  }}
                  className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold border cursor-pointer transition-colors ${
                    isFocusMode
                      ? "bg-blue-100 text-blue-900 border-blue-300"
                      : "bg-white text-slate-600 border-slate-200 hover:bg-slate-100"
                  }`}
                  title={
                    isFocusMode
                      ? "Focus Mode: Active (click to disable auto-framing)"
                      : "Focus Mode: Off (click to enable auto-framing)"
                  }
                >
                  <Crosshair className="w-3 h-3 text-blue-700" />
                  <span>{isFocusMode ? "Focus Mode ON" : "Focus Mode OFF"}</span>
                </button>
                <button
                  type="button"
                  onClick={handleCenterSelected}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold bg-white text-indigo-700 border border-indigo-200 hover:bg-indigo-50 cursor-pointer transition-colors shadow-2xs"
                  title="Focus and frame selected node's neighborhood"
                >
                  <Compass className="w-3 h-3 text-indigo-600" />
                  <span>Focus Neighborhood</span>
                </button>
                {dynamicallyExpandedData.nodes.length > 0 && (
                  <button
                    type="button"
                    onClick={() => {
                      setDynamicallyExpandedData({ nodes: [], edges: [] });
                      setNodeConnectedData(null);
                      setExpansionFeedback(null);
                      fitView(55, 400);
                    }}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-lg text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100 cursor-pointer transition-colors shadow-2xs"
                    title="Reset dynamically expanded traversal nodes and restore base query graph"
                  >
                    <RotateCcw className="w-3 h-3 text-rose-600" />
                    <span>Reset Traversal ({dynamicallyExpandedData.nodes.length})</span>
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleClearSelection}
                  className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white cursor-pointer transition-colors"
                  title="Deselect node & reset traversal"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}

          {/* Selected Edge Information HUD Strip (Docked cleanly above canvas without blocking graph) */}
          {selectedEdgeData && !selectedNodeDetails && (
            <div className="px-4 sm:px-5 py-2 bg-indigo-50/90 border-t border-indigo-200/80 text-xs flex items-center justify-between gap-3 flex-wrap animate-in fade-in duration-150">
              <div className="flex items-center gap-2 flex-wrap min-w-0">
                <span className="font-bold text-slate-900 tamil-font">
                  {selectedEdgeData.sourceLabel || selectedEdgeData.source}
                </span>
                <span className="inline-flex items-center gap-1 font-mono font-bold text-purple-700 bg-white px-2 py-0.5 rounded border border-purple-200 text-[10px] shadow-2xs">
                  <ArrowRight className="w-3 h-3 text-purple-500" />
                  <span>{selectedEdgeData.type || selectedEdgeData.relation}</span>
                  <ArrowRight className="w-3 h-3 text-purple-500" />
                </span>
                <span className="font-bold text-slate-900 tamil-font">
                  {selectedEdgeData.targetLabel || selectedEdgeData.target}
                </span>
                {selectedEdgeData.sourceReference && (
                  <span className="text-slate-600 text-[10px] font-mono bg-white px-2 py-0.5 rounded border border-slate-200">
                    Ref: {selectedEdgeData.sourceReference}
                  </span>
                )}
                {selectedEdgeData.confidence !== undefined && (
                  <span className="text-purple-700 text-[10px] font-mono font-bold bg-white px-2 py-0.5 rounded border border-purple-200">
                    Confidence: {Math.round(selectedEdgeData.confidence * 100)}%
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setSelectedEdgeData(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-white cursor-pointer transition-colors"
                title="Deselect edge"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Active Query-Relevant Subgraph Header Banner with Full Context Metadata */}
          {(contextIsQueryGraphActive || queryContextMeta.activeQuery) && (
            <div className="px-4 sm:px-5 py-2.5 bg-gradient-to-r from-purple-50/95 via-indigo-50/90 to-blue-50/95 border-t border-purple-200/80 text-xs flex flex-col gap-2 animate-in fade-in duration-200">
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                  <span className="flex h-2.5 w-2.5 relative shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-purple-600" />
                  </span>
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <span className="font-bold text-purple-900 text-[10px] uppercase tracking-wider bg-purple-100/80 text-purple-800 px-2 py-0.5 rounded-md border border-purple-200/60 shadow-2xs">
                      Active Query Subgraph
                    </span>
                    <span
                      className="font-bold text-slate-800 text-xs truncate max-w-xs sm:max-w-md md:max-w-lg lg:max-w-xl tamil-font"
                      title={queryContextMeta.activeQuery}
                    >
                      “{queryContextMeta.activeQuery}”
                    </span>
                  </div>
                </div>

                {/* Metadata Pills: Nodes, Relationships, Sources, Evidence Count */}
                <div className="flex items-center gap-1.5 flex-wrap shrink-0">
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white text-purple-800 border border-purple-200 shadow-2xs">
                    <Network className="w-3 h-3 text-purple-600" />
                    <span>{queryContextMeta.nodeCount} Nodes</span>
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white text-indigo-800 border border-indigo-200 shadow-2xs">
                    <GitBranch className="w-3 h-3 text-indigo-600" />
                    <span>{queryContextMeta.relCount} Relationships</span>
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-bold bg-white text-blue-800 border border-blue-200 shadow-2xs">
                    <Sparkles className="w-3 h-3 text-blue-600" />
                    <span>{queryContextMeta.evidenceCount} Evidence Count</span>
                  </span>
                  <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold bg-emerald-50 text-emerald-800 border border-emerald-200 shadow-2xs">
                    <BookOpen className="w-3 h-3 text-emerald-600" />
                    <span
                      className="truncate max-w-[180px] sm:max-w-[240px]"
                      title={queryContextMeta.sourcesDisplay.join(", ")}
                    >
                      {queryContextMeta.sourcesDisplay[0]}
                      {queryContextMeta.sourcesDisplay.length > 1
                        ? ` +${queryContextMeta.sourcesDisplay.length - 1}`
                        : ""}
                    </span>
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* D3 Canvas Container */}
      <div
        ref={containerRef}
        className="relative flex-1 min-h-[360px] sm:min-h-[420px] bg-[#fbfcfe] overflow-hidden select-none"
      >
        {/* Sleek Loading Overlay during Active Query Processing */}
        {(contextIsAnalyzing || contextIsLoadingGraph) && (
          <div className="absolute inset-0 z-30 bg-white/80 backdrop-blur-[2px] flex flex-col items-center justify-center p-4 transition-all animate-in fade-in duration-200">
            <div className="bg-white p-5 rounded-2xl shadow-xl border border-purple-200 max-w-sm w-full text-center space-y-3">
              <div className="mx-auto w-10 h-10 rounded-xl bg-purple-100 flex items-center justify-center text-purple-600 shadow-2xs">
                <RefreshCw className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Extracting Neo4j Subgraph
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Retrieving and normalizing grounded entities, concepts, and
                  relationships...
                </p>
              </div>
              <div className="w-full bg-slate-100 rounded-full h-1.5 overflow-hidden">
                <div
                  className="bg-purple-600 h-1.5 rounded-full transition-all duration-300"
                  style={{ width: `${contextWorkflowProgressPercent || 65}%` }}
                />
              </div>
            </div>
          </div>
        )}

        {/* Authoritative Neo4j Mutation & Synchronization Overlay */}
        {contextIsMutatingGraph && (
          <div className="absolute inset-0 z-30 bg-white/80 backdrop-blur-[2px] flex flex-col items-center justify-center p-4 transition-all animate-in fade-in duration-200">
            <div className="bg-white p-5 rounded-2xl shadow-xl border border-indigo-200 max-w-sm w-full text-center space-y-3">
              <div className="mx-auto w-10 h-10 rounded-xl bg-indigo-100 flex items-center justify-center text-indigo-600 shadow-2xs">
                <RefreshCw className="w-5 h-5 animate-spin" />
              </div>
              <div>
                <h4 className="text-sm font-bold text-slate-900">
                  Writing Mutation to Neo4j Aura
                </h4>
                <p className="text-xs text-slate-500 mt-0.5">
                  Committing changes to Neo4j database and retrieving fresh
                  updated subgraph...
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Mutation Error Alert Banner */}
        {contextMutationError && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-40 max-w-md w-full px-4 animate-in slide-in-from-top-2 duration-200">
            <div className="bg-red-50 border border-red-200 text-red-700 px-3.5 py-2.5 rounded-xl shadow-lg flex items-center justify-between text-xs">
              <div className="flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-red-500 shrink-0" />
                <span>{contextMutationError}</span>
              </div>
            </div>
          </div>
        )}

        {/* Subtle grid background pattern */}
        <div
          className="absolute inset-0 pointer-events-none opacity-40"
          style={{
            backgroundImage:
              "radial-gradient(#94a3b8 0.75px, transparent 0.75px)",
            backgroundSize: "24px 24px",
          }}
        />

        {/* D3 Interactive SVG Canvas Mount Target */}
        <svg
          ref={svgRef}
          className="w-full h-full cursor-grab active:cursor-grabbing block"
        />

        {/* Floating Glassmorphic Canvas Navigation HUD */}
        <div className="absolute bottom-3 right-3 z-20 bg-white/90 hover:bg-white/95 backdrop-blur-md border border-slate-200/90 shadow-md rounded-xl p-1 flex items-center gap-0.5 text-slate-700 transition-all">
          <button
            type="button"
            onClick={() => fitView(55, 350)}
            className="inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-semibold hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
            title="Fit graph to canvas view"
          >
            <RefreshCw className="w-3 h-3 text-slate-500" />
            <span className="hidden sm:inline text-[11px]">Fit View</span>
          </button>
          <div className="h-3.5 w-px bg-slate-200 mx-0.5" />
          <button
            type="button"
            onClick={handleZoomOut}
            className="p-1 rounded-lg hover:text-purple-700 hover:bg-slate-100 transition-colors cursor-pointer"
            title="Zoom Out"
          >
            <ZoomOut className="w-3.5 h-3.5" />
          </button>
          <span className="text-[10px] font-mono text-slate-500 px-1 font-semibold min-w-[34px] text-center select-none">
            {zoomLevelPercent}%
          </span>
          <button
            type="button"
            onClick={handleZoomIn}
            className="p-1 rounded-lg hover:text-purple-700 hover:bg-slate-100 transition-colors cursor-pointer"
            title="Zoom In"
          >
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <div className="h-3.5 w-px bg-slate-200 mx-0.5" />
          <button
            type="button"
            onClick={handleCenterSelected}
            disabled={!activeSelectedId && !clickedNodeData?.id}
            className={`p-1 rounded-lg transition-colors cursor-pointer ${
              activeSelectedId || clickedNodeData?.id
                ? "text-purple-600 hover:bg-purple-50"
                : "text-slate-300 cursor-not-allowed"
            }`}
            title={
              activeSelectedId || clickedNodeData?.id
                ? "Center Selected Node in View"
                : "Select a node to center"
            }
          >
            <Crosshair className="w-3.5 h-3.5" />
          </button>
          <button
            type="button"
            onClick={toggleFullscreen}
            className="p-1 rounded-lg hover:text-purple-700 hover:bg-slate-100 transition-colors cursor-pointer"
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? (
              <Minimize2 className="w-3.5 h-3.5" />
            ) : (
              <Maximize2 className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

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
          stats.renderedEntities === 0 && (
            <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center bg-slate-50/95">
              <div className="p-4 bg-purple-50 text-purple-600 rounded-2xl border border-purple-200/80 shadow-xs mb-3.5">
                <Network className="w-9 h-9 stroke-[1.5]" />
              </div>
              {!contextQueryString || !contextQueryString.trim() ? (
                <>
                  <h3 className="text-sm font-bold text-slate-800 tracking-tight">
                    Knowledge Graph Awaiting Query
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm mt-1.5 leading-relaxed">
                    The Knowledge Graph is dynamically grounded in Neo4j Aura.
                    Run a query in the Query Center above to extract and
                    visualize relevant entities, relationships, and epistemic
                    reasoning paths.
                  </p>
                </>
              ) : searchText ||
                selectedEntityType !== "ALL" ||
                selectedRelationshipType !== "ALL" ||
                selectedHierarchyLevel !== "ALL" ||
                selectedSourceFilter !== "ALL" ||
                hopDepth !== "ALL" ? (
                <>
                  <h3 className="text-sm font-bold text-slate-800">
                    No Matching Graph Entities
                  </h3>
                  <p className="text-xs text-slate-500 max-w-xs mt-1 mb-3.5">
                    {searchText
                      ? `No entities found matching "${searchText}". Try adjusting your search or clearing active filters.`
                      : "No entities match the selected filters for this query result."}
                  </p>
                  <button
                    type="button"
                    onClick={handleResetAllFilters}
                    className="px-3.5 py-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 rounded-lg border border-purple-200 transition-colors cursor-pointer"
                  >
                    Clear Filters
                  </button>
                </>
              ) : (
                <>
                  <h3 className="text-sm font-bold text-slate-800">
                    No Graph Entities Found
                  </h3>
                  <p className="text-xs text-slate-500 max-w-sm mt-1.5 leading-relaxed">
                    No matching entities or relationships were retrieved from
                    Neo4j Aura for the query:
                    <span className="block mt-1 font-mono text-purple-700 font-semibold text-[11px] truncate max-w-xs mx-auto">
                      "{contextQueryString}"
                    </span>
                  </p>
                </>
              )}
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
                verses are required to derive Vyāpti. Try refining the query
                with specific classical terms.
              </p>
            </div>
          </div>
        )}

      </div>

      {/* 5. Comprehensive Graph Notations & Ontological Legend Bar */}
      {showLegend && (
        <div className="border-t border-slate-200/90 bg-gradient-to-r from-slate-50 via-white to-slate-50 px-4 sm:px-5 py-3 text-xs shrink-0 select-none shadow-xs">
          <div className="flex items-center justify-between gap-2 mb-2 pb-1.5 border-b border-slate-200/70 flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-purple-900 bg-purple-100/90 px-2.5 py-0.5 rounded-md border border-purple-200 shadow-2xs">
                Graph Notations & Ontological Legend (குறிகள் விளக்கம்)
              </span>
              <span className="text-[11px] text-slate-500 hidden sm:inline">
                Entity taxonomy, canonical verse provenance paths, and Nyāya deduction edges
              </span>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-3">
            {/* Column A: Node Taxonomy & Symbols - 7 cols on lg */}
            <div className="lg:col-span-7 space-y-1.5">
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">
                Node Taxonomy (முனைய வகைகள்):
              </span>
              <div className="flex items-center gap-2 flex-wrap text-[11px]">
                {/* Verse / Sūtra */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-900 shadow-2xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 border border-emerald-600 shrink-0" />
                  <span className="font-bold">Verse / Sūtra</span>
                  <span className="text-[10px] text-emerald-700 tamil-font font-medium">(பாடல் / நூற்பா)</span>
                </div>

                {/* Mutalporuḷ / Primary Ground */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 border border-blue-300 text-blue-900 shadow-2xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-500 border border-blue-600 shrink-0" />
                  <span className="font-bold">Primary Ground</span>
                  <span className="text-[10px] text-blue-700 tamil-font font-medium">(முதற்பொருள் - நிலம்/பொழுது)</span>
                </div>

                {/* Concepts / Karu & Uri */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-50 border border-purple-300 text-purple-900 shadow-2xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-purple-500 border border-purple-600 shrink-0" />
                  <span className="font-bold">Concepts / Uri</span>
                  <span className="text-[10px] text-purple-700 tamil-font font-medium">(கருப்பொருள் / உரிப்பொருள்)</span>
                </div>

                {/* Entities & Deities */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-amber-50 border border-amber-300 text-amber-950 shadow-2xs">
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500 border border-amber-600 shrink-0" />
                  <span className="font-bold">Entity / Deity</span>
                  <span className="text-[10px] text-amber-800 tamil-font font-medium">(தெய்வம் / மாந்தர்)</span>
                </div>

                {/* Literature / Work */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100 border border-slate-300 text-slate-900 shadow-2xs">
                  <span className="w-2.5 h-2 rounded bg-slate-800 shrink-0" />
                  <span className="font-bold">Literature / Work</span>
                  <span className="text-[10px] text-slate-600 tamil-font font-medium">(தொல்காப்பியம் / நூல்)</span>
                </div>

                {/* Nyāya Rule / Inference */}
                <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-indigo-50 border border-indigo-300 text-indigo-950 shadow-2xs">
                  <span className="w-3.5 h-2 rounded-full bg-indigo-600 shrink-0" />
                  <span className="font-bold">Nyāya Rule / Step</span>
                  <span className="text-[10px] text-indigo-700 tamil-font font-medium">(நியாய விதி / ஏது)</span>
                </div>
              </div>
            </div>

            {/* Column B: Relationship & Edge Notations - 5 cols on lg */}
            <div className="lg:col-span-5 space-y-1.5 border-t md:border-t-0 md:border-l border-slate-200/80 md:pl-3">
              <span className="text-[10px] font-bold text-slate-600 uppercase tracking-wider block">
                Relationship & Edge Notations (இணைப்புக் குறிகள்):
              </span>
              <div className="flex items-center gap-2 flex-wrap text-[10px]">
                {/* Canonical Provenance (Solid green) */}
                <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-emerald-50/80 border border-emerald-200 font-mono text-emerald-950">
                  <span className="font-bold text-emerald-600">──▶</span>
                  <span className="font-bold">GROUNDED_IN</span>
                  <span className="text-emerald-700 font-sans font-medium">(சான்றுப் பிணைப்பு)</span>
                </div>

                {/* Landscape Association (Solid slate) */}
                <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 border border-slate-200 font-mono text-slate-800">
                  <span className="font-bold text-slate-600">──▶</span>
                  <span className="font-bold">MENTIONS / ASSOC</span>
                  <span className="text-slate-600 font-sans font-medium">(இயைபுத் தொடர்பு)</span>
                </div>

                {/* Nyāya Epistemic Inference (Dashed amber) */}
                <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-amber-50/80 border border-amber-200 font-mono text-amber-950">
                  <span className="font-bold text-amber-600">- -▶</span>
                  <span className="font-bold">DEFEASIBLE_RULE</span>
                  <span className="text-amber-800 font-sans font-medium">(அனுமான வழி)</span>
                </div>

                {/* Selection Ring */}
                <div className="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-purple-50/80 border border-purple-200 text-purple-900 font-sans">
                  <span className="w-2.5 h-2.5 rounded-full border-2 border-dashed border-indigo-600 shrink-0" />
                  <span className="font-medium text-[10px]">Selection Ring (தேர்ந்தெடுத்த முனையம்)</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Diagnostics HUD Popover for KnowledgeGraphViewer */}
      {isDiagnosticsOpen && (
        <div className="absolute bottom-12 right-4 z-40 bg-white/95 backdrop-blur-md rounded-xl border border-slate-200/90 shadow-xl p-3 text-[11px] font-mono text-slate-700 animate-in fade-in zoom-in-95 duration-150 space-y-1.5 min-w-[260px]">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-100 font-bold text-slate-900">
            <div className="flex items-center gap-1.5 text-purple-700">
              <Activity className="w-3.5 h-3.5" />
              <span>KG Pipeline Diagnostics</span>
            </div>
            <button
              type="button"
              onClick={() => setIsDiagnosticsOpen(false)}
              className="text-slate-400 hover:text-slate-600 cursor-pointer text-xs p-0.5"
              title="Close"
            >
              ✕
            </button>
          </div>
          <div className="grid grid-cols-2 gap-x-3 gap-y-1 pt-0.5">
            <span className="text-slate-500">Backend Nodes:</span>
            <span className="font-semibold text-slate-800">
              {stats.backendNodeCount || stats.totalEntities}
            </span>
            <span className="text-slate-500">Backend Edges:</span>
            <span className="font-semibold text-slate-800">
              {stats.backendRelCount || stats.totalEdges}
            </span>
            <span className="text-slate-500">Normalized Nodes:</span>
            <span className="font-semibold text-indigo-700">
              {stats.totalEntities}
            </span>
            <span className="text-slate-500">Normalized Links:</span>
            <span className="font-semibold text-indigo-700">
              {stats.totalEdges}
            </span>
            <span className="text-slate-500">Rendered Nodes:</span>
            <span className="font-bold text-emerald-700">
              {stats.renderedEntities}
            </span>
            <span className="text-slate-500">Rendered Links:</span>
            <span className="font-bold text-emerald-700">
              {stats.renderedEdges}
            </span>
            <span className="text-slate-500">Self-Loops:</span>
            <span className="text-amber-700">{stats.selfLoopCount || 0}</span>
            <span className="text-slate-500">Multi-Edges:</span>
            <span className="text-purple-700">{stats.multiEdgeCount || 0}</span>
            <span className="text-slate-500">Isolated Nodes:</span>
            <span className="text-blue-700">
              {stats.isolatedNodeCount || 0}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
