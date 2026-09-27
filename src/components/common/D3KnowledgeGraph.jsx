import { useRef, useEffect, useState, useMemo, useCallback } from 'react';
import * as d3 from 'd3';
import {
  ZoomIn,
  ZoomOut,
  Maximize2,
  Minimize2,
  RefreshCw,
  Network,
  Crosshair,
  Search,
  X,
  ChevronRight,
  ChevronLeft,
  Info,
  ArrowRight,
  Activity,
} from 'lucide-react';
import { normalizeGraphData, extractNodeId, TAXONOMY_COLORS } from '../../services/graphNormalization';
import { graphApi } from '../../services/apiClient';

/**
 * Interactive Research-Grade D3.js Knowledge Graph Visualization Component.
 *
 * Features:
 * - Smooth zoom and pan using d3.zoom with bounded scale extent
 * - Smooth node dragging using d3.drag with alpha reheat and drag-vs-click conflict resolution
 * - Interactive hover highlighting: hovered node + incident links + neighbor nodes highlighted, others dimmed
 * - Selected-node highlighting with outer pulsing ring, connected edges, and dimming of unrelated elements
 * - Relationship click inspection popover with provenance, confidence, and metadata
 * - Controls: Zoom In, Zoom Out, Reset / Fit to View, Center Selected Node, Fullscreen toggle
 * - Search & Highlight function: locates nodes by label, ID, type, and properties with match navigation
 * - Adaptive zoom readability with SVG text halos (paint-order) preventing visual clutter
 * - React/D3 isolation: D3 handles fast SVG DOM transitions; React manages application state
 */
export default function D3KnowledgeGraph({
  data = null,
  nodes: propNodes = null,
  links: propLinks = null,
  width = '100%',
  height = '100%',
  className = '',
  isLoading = false,
  loadingMessage = 'Loading Knowledge Graph...',
  emptyMessage = 'No graph elements available to display.',
  selectedNodeId: controlledSelectedNodeId = null,
  selectedLinkId: controlledSelectedLinkId = null,
  highlightedNodeIds = null,
  highlightedLinkIds = null,
  dimmed = false,
  onNodeClick = null,
  onLinkClick = null,
  onBackgroundClick = null,
  showControls = true,
  showSearch = true,
  showDetailsPanel = true,
  linkDistance = 135,
  chargeStrength = -380,
  enableDragging = true,
  enableZooming = true,
  showLinkLabels = true,
  colorMap = TAXONOMY_COLORS,
  onZoomChange = null,
  enableDynamicExpansion = true,
  onNodeExpand = null,
}) {
  // DOM References
  const containerRef = useRef(null);
  const svgRef = useRef(null);
  const zoomBehaviorRef = useRef(null);
  const simulationRef = useRef(null);
  const currentNodesRef = useRef(new Map()); // id -> { x, y, vx, vy } for coordinate stability
  const gViewportRef = useRef(null);
  const dragStartPosRef = useRef({ x: 0, y: 0, moved: false });

  // Application / UI State
  const [internalSelectedNodeId, setInternalSelectedNodeId] = useState(null);
  const [internalSelectedLinkId, setInternalSelectedLinkId] = useState(null);
  const [activeEdgeData, setActiveEdgeData] = useState(null);
  const [activeNodeData, setActiveNodeData] = useState(null);
  const [zoomLevelPercent, setZoomLevelPercent] = useState(100);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [edgePopoverPos, setEdgePopoverPos] = useState(null);
  const [isDiagnosticsOpen, setIsDiagnosticsOpen] = useState(false);
  const [renderedCounts, setRenderedCounts] = useState({ nodes: 0, links: 0 });

  // Dynamic Neo4j Node Expansion State
  const [dynamicallyExpandedNodes, setDynamicallyExpandedNodes] = useState([]);
  const [dynamicallyExpandedLinks, setDynamicallyExpandedLinks] = useState([]);
  const [isExpandingNode, setIsExpandingNode] = useState(false);
  const [nodeConnectedData, setNodeConnectedData] = useState(null);
  const expandNodeFromNeo4jRef = useRef(null);
  // Reset dynamic expansion when base graph data changes
  const lastDataRef = useRef(data);
  useEffect(() => {
    if (lastDataRef.current !== data) {
      lastDataRef.current = data;
      setDynamicallyExpandedNodes([]);
      setDynamicallyExpandedLinks([]);
      setNodeConnectedData(null);
    }
  }, [data]);

  // Effective selection (controlled or internal)
  const activeSelectedNodeId = controlledSelectedNodeId !== null ? controlledSelectedNodeId : internalSelectedNodeId;
  const activeSelectedLinkId = controlledSelectedLinkId !== null ? controlledSelectedLinkId : internalSelectedLinkId;

  // 1. Data Normalization Layer
  const normalizedData = useMemo(() => {
    let raw;
    if (propNodes && (propLinks || data?.edges)) {
      raw = {
        nodes: [...propNodes, ...dynamicallyExpandedNodes],
        edges: [...(propLinks || data?.edges || []), ...dynamicallyExpandedLinks],
      };
    } else if (data) {
      raw = {
        nodes: [...(data.nodes || []), ...dynamicallyExpandedNodes],
        edges: [...(data.edges || data.relationships || []), ...dynamicallyExpandedLinks],
      };
    } else {
      raw = {
        nodes: dynamicallyExpandedNodes,
        edges: dynamicallyExpandedLinks,
      };
    }
    return normalizeGraphData(raw);
  }, [data, propNodes, propLinks, dynamicallyExpandedNodes, dynamicallyExpandedLinks]);

  const { nodes: graphNodes, links: graphLinks, stats } = normalizedData;
  const isVeryLargeGraph = graphNodes.length > 300;

  // Derived search matches across nodes
  const searchMatches = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return [];

    return graphNodes.filter((n) => {
      const idMatch = String(n.id).toLowerCase().includes(q);
      const labelMatch = String(n.label || '').toLowerCase().includes(q);
      const tamilMatch = String(n.tamilLabel || '').toLowerCase().includes(q);
      const typeMatch = String(n.type || '').toLowerCase().includes(q);
      const transMatch = String(n.transliteration || '').toLowerCase().includes(q);
      const propMatch =
        n.properties &&
        Object.values(n.properties).some((v) =>
          typeof v === 'string' && v.toLowerCase().includes(q)
        );

      return idMatch || labelMatch || tamilMatch || typeMatch || transMatch || propMatch;
    });
  }, [searchQuery, graphNodes]);

  // Fullscreen toggle
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

  // Listen for fullscreen change events from browser/ESC key
  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsFullscreen(Boolean(document.fullscreenElement));
    };
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    document.addEventListener('webkitfullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
      document.removeEventListener('webkitfullscreenchange', handleFullscreenChange);
    };
  }, []);

  // Fit view helper with transition
  const fitView = useCallback(
    (padding = 60, duration = 350) => {
      const svgEl = svgRef.current;
      const container = containerRef.current;
      if (!svgEl || !container || !zoomBehaviorRef.current) return;

      const currentW = container.clientWidth || 800;
      const currentH = container.clientHeight || 600;

      if (graphNodes.length === 0) return;

      let minX = Infinity,
        maxX = -Infinity,
        minY = Infinity,
        maxY = -Infinity;

      graphNodes.forEach((n) => {
        const x = typeof n.x === 'number' ? n.x : currentW / 2;
        const y = typeof n.y === 'number' ? n.y : currentH / 2;
        const r = (colorMap[n.type]?.radius || 26) + 12;
        if (x - r < minX) minX = x - r;
        if (x + r > maxX) maxX = x + r;
        if (y - r < minY) minY = y - r;
        if (y + r > maxY) maxY = y + r;
      });

      const graphW = Math.max(1, maxX - minX);
      const graphH = Math.max(1, maxY - minY);

      const scaleX = (currentW - padding * 2) / graphW;
      const scaleY = (currentH - padding * 2) / graphH;
      const scale = Math.max(0.2, Math.min(2.5, Math.min(scaleX, scaleY)));

      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;
      const tx = currentW / 2 - scale * midX;
      const ty = currentH / 2 - scale * midY;

      const transform = d3.zoomIdentity.translate(tx, ty).scale(scale);
      const d3Svg = d3.select(svgEl);

      if (duration > 0) {
        d3Svg
          .transition()
          .duration(duration)
          .ease(d3.easeCubicOut)
          .call(zoomBehaviorRef.current.transform, transform);
      } else {
        d3Svg.call(zoomBehaviorRef.current.transform, transform);
      }
    },
    [graphNodes, colorMap]
  );

  // Node-Centered Focus Mode State
  const [isFocusMode, setIsFocusMode] = useState(true);
  const focusOnNeighborhoodRef = useRef(null);

  // Automatically calculate selected node's neighborhood from Neo4j result and visually focus the graph
  const focusOnNeighborhood = useCallback(
    (centerId, padding = 75, duration = 650) => {
      const svgEl = svgRef.current;
      const container = containerRef.current;
      if (!svgEl || !container || !zoomBehaviorRef.current || !centerId) return;

      const centerNode = graphNodes.find((n) => String(n.id) === String(centerId));
      if (!centerNode || typeof centerNode.x !== 'number' || typeof centerNode.y !== 'number') return;

      const neighborNodes = [centerNode];
      const cid = String(centerNode.id);

      graphLinks.forEach((l) => {
        const sId = String(l.source?.id || l.source);
        const tId = String(l.target?.id || l.target);
        if (sId === cid) {
          const neighbor = graphNodes.find((n) => String(n.id) === tId);
          if (neighbor && typeof neighbor.x === 'number') neighborNodes.push(neighbor);
        } else if (tId === cid) {
          const neighbor = graphNodes.find((n) => String(n.id) === sId);
          if (neighbor && typeof neighbor.x === 'number') neighborNodes.push(neighbor);
        }
      });

      let minX = Infinity,
        maxX = -Infinity,
        minY = Infinity,
        maxY = -Infinity;

      neighborNodes.forEach((n) => {
        const x = n.x;
        const y = n.y;
        const r = (n.radius || 26) + 18;
        if (x - r < minX) minX = x - r;
        if (x + r > maxX) maxX = x + r;
        if (y - r < minY) minY = y - r;
        if (y + r > maxY) maxY = y + r;
      });

      const currentW = container.clientWidth || 800;
      const currentH = container.clientHeight || 600;

      const boxWidth = Math.max(90, maxX - minX);
      const boxHeight = Math.max(90, maxY - minY);

      const availWidth = Math.max(100, currentW - padding * 2);
      const availHeight = Math.max(100, currentH - padding * 2);
      const scaleX = availWidth / boxWidth;
      const scaleY = availHeight / boxHeight;
      const scale = Math.max(0.50, Math.min(1.60, Math.min(scaleX, scaleY)));

      const midX = (minX + maxX) / 2;
      const midY = (minY + maxY) / 2;
      const tx = currentW / 2 - scale * midX;
      const ty = currentH / 2 - scale * midY;

      const transform = d3.zoomIdentity.translate(tx, ty).scale(scale);

      d3.select(svgEl)
        .transition()
        .duration(duration)
        .ease(d3.easeCubicOut)
        .call(zoomBehaviorRef.current.transform, transform);
    },
    [graphNodes, graphLinks]
  );

  useEffect(() => {
    focusOnNeighborhoodRef.current = focusOnNeighborhood;
  }, [focusOnNeighborhood]);

  // Center on currently selected node's neighborhood
  const handleCenterSelected = useCallback(() => {
    if (activeSelectedNodeId) {
      focusOnNeighborhood(activeSelectedNodeId, 75, 550);
    }
  }, [activeSelectedNodeId, focusOnNeighborhood]);

  // Dynamic Neo4j Node Selection & Multi-Hop Traversal Expansion
  const expandNodeFromNeo4j = useCallback(
    async (nodeObj, options = {}) => {
      if (!nodeObj) return;
      const targetId = extractNodeId(nodeObj) || nodeObj.id || nodeObj.name;
      if (!targetId) return;

      setIsExpandingNode(true);
      const hops = options.hops || 2;
      const direction = options.direction || "both";
      const allowedTypes = options.allowedTypes || null;
      const excludedTypes = options.excludedTypes || null;

      try {
        const res = await graphApi.getNodeConnected(targetId, {
          hops,
          limit: 150,
          direction,
          allowedTypes,
          excludedTypes,
        });

        if (res && res.success && res.data) {
          const { selected_node, connected_nodes, relationships, paths, metadata } = res.data;
          setNodeConnectedData({
            selected_node,
            connected_nodes: connected_nodes || [],
            relationships: relationships || [],
            paths: paths || [],
            metadata: metadata || {},
          });

          if (onNodeExpand) {
            onNodeExpand(res.data);
          }

          const existingIds = new Set(graphNodes.map((n) => String(n.id)));
          const rawNewNodes = (connected_nodes || []).filter(
            (cn) => !existingIds.has(String(cn.id))
          );

          const selX = nodeObj.x ?? (containerRef.current?.clientWidth || 800) / 2;
          const selY = nodeObj.y ?? (containerRef.current?.clientHeight || 600) / 2;

          // Track positions for multi-hop hierarchy
          const posMap = new Map();
          graphNodes.forEach((n) => {
            if (typeof n.x === "number" && typeof n.y === "number") {
              posMap.set(String(n.id), { x: n.x, y: n.y });
            }
          });
          posMap.set(String(targetId), { x: selX, y: selY });

          // Group by hop_distance
          const nodesByHop = new Map();
          rawNewNodes.forEach((node) => {
            const h = node.hop_distance || 1;
            if (!nodesByHop.has(h)) nodesByHop.set(h, []);
            nodesByHop.get(h).push(node);
          });

          const positionedNewNodes = [];
          const sortedHops = Array.from(nodesByHop.keys()).sort((a, b) => a - b);

          for (const hop of sortedHops) {
            const hopNodes = nodesByHop.get(hop);

            if (hop === 1) {
              const radius = 68 + Math.min(hopNodes.length * 5, 120);
              const angleStep = (2 * Math.PI) / (hopNodes.length || 1);

              hopNodes.forEach((nn, i) => {
                const angle = i * angleStep;
                const jitter = (Math.random() - 0.5) * 15;
                const px = selX + Math.cos(angle) * radius + jitter;
                const py = selY + Math.sin(angle) * radius + jitter;
                posMap.set(String(nn.id), { x: px, y: py });
                currentNodesRef.current.set(String(nn.id), { x: px, y: py, vx: 0, vy: 0 });
                positionedNewNodes.push({
                  ...nn,
                  x: px,
                  y: py,
                  vx: 0,
                  vy: 0,
                });
              });
            } else {
              const byParent = new Map();
              hopNodes.forEach((n) => {
                const pid = n.parent_id ? String(n.parent_id) : "unknown";
                if (!byParent.has(pid)) byParent.set(pid, []);
                byParent.get(pid).push(n);
              });

              byParent.forEach((children, pid) => {
                const parentPos = posMap.get(pid) || { x: selX, y: selY };
                const baseAngle =
                  parentPos.x === selX && parentPos.y === selY
                    ? Math.random() * 2 * Math.PI
                    : Math.atan2(parentPos.y - selY, parentPos.x - selX);

                const count = children.length;
                const fanArc = Math.min(Math.PI * 0.7, 0.4 * count);
                const step = count > 1 ? fanArc / (count - 1) : 0;
                const startAngle = baseAngle - fanArc / 2;
                const hopRadius = 60 + Math.min(count * 5, 75);

                children.forEach((nn, j) => {
                  const angle = count === 1 ? baseAngle : startAngle + j * step;
                  const jitter = (Math.random() - 0.5) * 10;
                  const px = parentPos.x + Math.cos(angle) * hopRadius + jitter;
                  const py = parentPos.y + Math.sin(angle) * hopRadius + jitter;
                  posMap.set(String(nn.id), { x: px, y: py });
                  currentNodesRef.current.set(String(nn.id), { x: px, y: py, vx: 0, vy: 0 });
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

          const existingEdgeKeys = new Set(
            graphLinks.map(
              (l) =>
                `${extractNodeId(l.source)}->${extractNodeId(l.target)}:${l.type || l.relation}`
            )
          );
          const newLinks = (relationships || []).filter((r) => {
            const s = String(r.source?.id || r.source || "");
            const t = String(r.target?.id || r.target || "");
            const type = String(r.type || r.relation || "");
            const k = `${s}->${t}:${type}`;
            const rk = `${t}->${s}:${type}`;
            return !existingEdgeKeys.has(k) && !existingEdgeKeys.has(rk);
          });

          if (positionedNewNodes.length > 0 || newLinks.length > 0) {
            setDynamicallyExpandedNodes((prev) => {
              const prevIds = new Set(prev.map((n) => String(n.id)));
              return [...prev, ...positionedNewNodes.filter((n) => !prevIds.has(String(n.id)))];
            });
            setDynamicallyExpandedLinks((prev) => {
              const prevKeys = new Set(
                prev.map(
                  (l) =>
                    `${l.source?.id || l.source}->${l.target?.id || l.target}:${l.type || l.relation}`
                )
              );
              return [
                ...prev,
                ...newLinks.filter((l) => {
                  const k = `${l.source?.id || l.source}->${l.target?.id || l.target}:${l.type || l.relation}`;
                  return !prevKeys.has(k);
                }),
              ];
            });

            if (simulationRef.current) {
              simulationRef.current.alpha(0.35).restart();
            }

            if (isFocusMode && focusOnNeighborhoodRef.current) {
              setTimeout(() => {
                focusOnNeighborhoodRef.current(targetId, 85, 650);
              }, 120);
            }
          }
        }
      } catch (err) {
        console.warn("D3KnowledgeGraph dynamic expansion failed:", err);
      } finally {
        setIsExpandingNode(false);
      }
    },
    [graphNodes, graphLinks, onNodeExpand]
  );

  useEffect(() => {
    expandNodeFromNeo4jRef.current = expandNodeFromNeo4j;
  }, [expandNodeFromNeo4j]);

  // Navigate to match
  const handleCycleMatch = useCallback(
    (direction) => {
      if (searchMatches.length === 0) return;
      let nextIdx = currentMatchIndex + direction;
      if (nextIdx < 0) nextIdx = searchMatches.length - 1;
      if (nextIdx >= searchMatches.length) nextIdx = 0;

      setCurrentMatchIndex(nextIdx);
      const match = searchMatches[nextIdx];
      if (match) {
        setInternalSelectedNodeId(match.id);
        setActiveNodeData(match);
        centerNode(match.id, 1.4, 350);
      }
    },
    [searchMatches, currentMatchIndex, centerNode]
  );

  const handleZoomIn = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(220)
        .ease(d3.easeCubicOut)
        .call(zoomBehaviorRef.current.scaleBy, 1.28);
    }
  }, []);

  const handleZoomOut = useCallback(() => {
    if (svgRef.current && zoomBehaviorRef.current) {
      d3.select(svgRef.current)
        .transition()
        .duration(220)
        .ease(d3.easeCubicOut)
        .call(zoomBehaviorRef.current.scaleBy, 0.78);
    }
  }, []);

  // Compute boundary clamped popover coordinates
  const calculateClampedPos = useCallback((clickX, clickY, estWidth = 360, estHeight = 240) => {
    const container = containerRef.current;
    const cw = container?.clientWidth || 800;
    const ch = container?.clientHeight || 600;

    let left = clickX + 16;
    if (left + estWidth > cw - 12) {
      left = clickX - estWidth - 16;
    }
    left = Math.max(12, Math.min(left, cw - estWidth - 12));

    let top = clickY - 20;
    if (top + estHeight > ch - 12) {
      top = clickY - estHeight + 20;
    }
    top = Math.max(12, Math.min(top, ch - estHeight - 12));

    return { left: Math.round(left), top: Math.round(top), width: estWidth };
  }, []);

  // 2. Primary D3 Rendering and Simulation Lifecycle
  useEffect(() => {
    const container = containerRef.current;
    const svgEl = svgRef.current;
    if (!container || !svgEl) return;

    const w = container.clientWidth || 800;
    const h = container.clientHeight || 600;

    const svg = d3.select(svgEl);
    svg.selectAll('*').remove();

    // Setup Defs (Markers & Filters)
    const defs = svg.append('defs');

    // Default directed arrow marker
    defs
      .append('marker')
      .attr('id', 'kg-arrow-default')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0,-4 L 8,0 L 0,4')
      .attr('fill', '#94a3b8');

    // Highlighted directed arrow marker
    defs
      .append('marker')
      .attr('id', 'kg-arrow-highlight')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 7.5)
      .attr('markerHeight', 7.5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0,-4 L 8,0 L 0,4')
      .attr('fill', '#6366f1');

    // Directly connected outgoing arrow marker
    defs
      .append('marker')
      .attr('id', 'kg-arrow-connected')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0,-4 L 8,0 L 0,4')
      .attr('fill', '#4f46e5');

    // Directly connected incoming arrow marker
    defs
      .append('marker')
      .attr('id', 'kg-arrow-connected-in')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 8)
      .attr('markerHeight', 8)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0,-4 L 8,0 L 0,4')
      .attr('fill', '#059669');

    // Search match pulse arrow marker
    defs
      .append('marker')
      .attr('id', 'kg-arrow-match')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 10)
      .attr('refY', 0)
      .attr('markerWidth', 7.5)
      .attr('markerHeight', 7.5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M 0,-4 L 8,0 L 0,4')
      .attr('fill', '#d97706');

    // Node drop shadow filter
    if (!isVeryLargeGraph) {
      const shadow = defs
        .append('filter')
        .attr('id', 'kg-node-shadow')
        .attr('x', '-25%')
        .attr('y', '-25%')
        .attr('width', '150%')
        .attr('height', '150%');
      shadow
        .append('feDropShadow')
        .attr('dx', '0')
        .attr('dy', '1.5')
        .attr('stdDeviation', '2.5')
        .attr('flood-color', '#0f172a')
        .attr('flood-opacity', '0.08');

      // Glowing selection filter
      const glow = defs
        .append('filter')
        .attr('id', 'kg-selection-glow')
        .attr('x', '-35%')
        .attr('y', '-35%')
        .attr('width', '170%')
        .attr('height', '170%');
      glow
        .append('feDropShadow')
        .attr('dx', '0')
        .attr('dy', '0')
        .attr('stdDeviation', '5.5')
        .attr('flood-color', '#6366f1')
        .attr('flood-opacity', '0.65');

      // Glowing neighbor filter
      const neighborGlow = defs
        .append('filter')
        .attr('id', 'kg-neighbor-glow')
        .attr('x', '-30%')
        .attr('y', '-30%')
        .attr('width', '160%')
        .attr('height', '160%');
      neighborGlow
        .append('feDropShadow')
        .attr('dx', '0')
        .attr('dy', '0')
        .attr('stdDeviation', '4')
        .attr('flood-color', '#818cf8')
        .attr('flood-opacity', '0.5');
    }

    // Main viewport container
    const gViewport = svg.append('g').attr('class', 'kg-viewport');
    gViewportRef.current = gViewport;

    // Strict Layered SVG Groups Separation
    const linksGroup = gViewport.append('g').attr('class', 'kg-links-group');
    const linkLabelsGroup = gViewport.append('g').attr('class', 'kg-link-labels-group');
    const nodesGroup = gViewport.append('g').attr('class', 'kg-nodes-group');
    const nodeLabelsGroup = gViewport.append('g').attr('class', 'kg-node-labels-group');

    // Zoom setup
    if (enableZooming) {
      const zoom = d3
        .zoom()
        .scaleExtent([0.15, 4.0])
        .on('zoom', (event) => {
          gViewport.attr('transform', event.transform);
          const pct = Math.round(event.transform.k * 100);
          setZoomLevelPercent(pct);

          // Semantic zoom: adjust text readability or secondary label visibility at extreme scales
          if (pct < 45) {
            nodeLabelsGroup.selectAll('.kg-label-sub').attr('display', 'none');
          } else {
            nodeLabelsGroup.selectAll('.kg-label-sub').attr('display', null);
          }

          if (onZoomChange) onZoomChange(event.transform);
        });
      zoomBehaviorRef.current = zoom;
      svg.call(zoom).on('dblclick.zoom', null);
    }

    // Background click handler clears selection, dynamic traversal, and smoothly resets view
    svg.on('click', (event) => {
      if (event.target === svgEl) {
        setInternalSelectedNodeId(null);
        setInternalSelectedLinkId(null);
        setActiveNodeData(null);
        setActiveEdgeData(null);
        setEdgePopoverPos(null);
        setDynamicallyExpandedNodes([]);
        setDynamicallyExpandedLinks([]);
        setNodeConnectedData(null);
        fitView(55, 450);
        if (onBackgroundClick) onBackgroundClick(event);
      }
    });

    // Prepare simulation nodes & links (preserving previous coordinates for stability)
    const prevCoords = currentNodesRef.current;
    const simNodes = graphNodes.map((n, idx) => {
      const existing = prevCoords.get(n.id);
      let initX = existing?.x ?? n.initialX;
      let initY = existing?.y ?? n.initialY;

      if (initX === undefined || initY === undefined) {
        const angle = (2 * Math.PI * idx) / Math.max(1, graphNodes.length);
        const radius = 60 + (idx % 6) * 45;
        initX = w / 2 + radius * Math.cos(angle);
        initY = h / 2 + radius * Math.sin(angle);
      }

      const style = colorMap[n.type] || colorMap.Concept || {
        fill: '#faf5ff',
        stroke: '#9333ea',
        text: '#581c87',
        radius: 26,
        shape: 'circle',
      };

      return {
        ...n,
        x: initX,
        y: initY,
        vx: existing?.vx ?? 0,
        vy: existing?.vy ?? 0,
        radius: style.radius || 26,
        shape: style.shape || 'circle',
        style,
      };
    });

    const nodeLookup = new Map(simNodes.map((n) => [n.id, n]));

    const simLinks = graphLinks
      .map((l) => {
        const sId = extractNodeId(l.source);
        const tId = extractNodeId(l.target);
        if (!nodeLookup.has(sId) || !nodeLookup.has(tId)) return null;
        return {
          ...l,
          source: nodeLookup.get(sId),
          target: nodeLookup.get(tId),
        };
      })
      .filter(Boolean);

    setRenderedCounts({ nodes: simNodes.length, links: simLinks.length });

    // Precalculate adjacency lookup map for instant hover highlighting
    const adjacencyMap = new Map();
    simNodes.forEach((n) => adjacencyMap.set(n.id, new Set()));
    const incidentLinksMap = new Map();
    simNodes.forEach((n) => incidentLinksMap.set(n.id, []));

    simLinks.forEach((link) => {
      adjacencyMap.get(link.source.id)?.add(link.target.id);
      adjacencyMap.get(link.target.id)?.add(link.source.id);
      incidentLinksMap.get(link.source.id)?.push(link.id);
      incidentLinksMap.get(link.target.id)?.push(link.id);
    });

    // Stop previous simulation
    if (simulationRef.current) {
      simulationRef.current.stop();
      simulationRef.current = null;
    }

    // Force Simulation configuration
    const linkForceDistance = isVeryLargeGraph ? linkDistance * 0.85 : linkDistance;
    const repulsionStrength = isVeryLargeGraph ? chargeStrength * 0.75 : chargeStrength;

    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        'link',
        d3
          .forceLink(simLinks)
          .id((d) => d.id)
          .distance(linkForceDistance)
          .strength(0.7)
      )
      .force(
        'charge',
        d3
          .forceManyBody()
          .strength(repulsionStrength)
          .distanceMax(isVeryLargeGraph ? 400 : 550)
      )
      .force('center', d3.forceCenter(w / 2, h / 2).strength(0.06))
      .force('x', d3.forceX(w / 2).strength(0.04))
      .force('y', d3.forceY(h / 2).strength(0.04))
      .force(
        'collide',
        d3
          .forceCollide()
          .radius((d) => (d.radius || 26) + (isVeryLargeGraph ? 10 : 16))
          .iterations(isVeryLargeGraph ? 1 : 2)
      )
      .alpha(0.65)
      .alphaDecay(isVeryLargeGraph ? 0.05 : 0.032);

    simulationRef.current = simulation;

    // Helper: Compute SVG Path string supporting loops, parallel curved edges, and straight edges
    const computeLinkPath = (d) => {
      const sx = d.source.x ?? 0;
      const sy = d.source.y ?? 0;
      const tx = d.target.x ?? 0;
      const ty = d.target.y ?? 0;
      const sRadius = d.source.radius || 26;
      const tRadius = d.target.radius || 26;

      // 1. Self-referential loop (source === target)
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

      // 2. Parallel multi-edges between same node pair
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

      // 3. Single distinct edge
      return `M ${sx} ${sy} L ${endX} ${endY}`;
    };

    const computeLinkLabelTransform = (d) => {
      const sx = d.source.x ?? 0;
      const sy = d.source.y ?? 0;
      const tx = d.target.x ?? 0;
      const ty = d.target.y ?? 0;
      const sRadius = d.source.radius || 26;

      if (d.source.id === d.target.id || d.isSelfReferential) {
        const loopIdx = d.linkIndex || 0;
        const loopR = sRadius + 8 + loopIdx * 12;
        return `translate(${sx}, ${sy - (loopR * 2.1)})`;
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

    // 1. Render Links in kg-links-group with SVG Path
    const linkSelection = linksGroup
      .selectAll('path.kg-link')
      .data(simLinks, (d) => d.id)
      .join('path')
      .attr('class', 'kg-link transition-opacity duration-200 cursor-pointer')
      .attr('fill', 'none')
      .attr('id', (d) => `kg-link-${d.id}`)
      .attr('stroke', (d) => (d.id === activeSelectedLinkId ? '#6366f1' : '#cbd5e1'))
      .attr('stroke-width', (d) => (d.id === activeSelectedLinkId ? 2.8 : 1.6))
      .attr('stroke-opacity', 0.85)
      .attr('marker-end', (d) =>
        d.id === activeSelectedLinkId ? 'url(#kg-arrow-highlight)' : 'url(#kg-arrow-default)'
      );

    // 2. Render Link Labels in kg-link-labels-group
    let linkLabelSelection = null;
    if (showLinkLabels) {
      const labelGroups = linkLabelsGroup
        .selectAll('g.kg-link-label')
        .data(simLinks, (d) => d.id)
        .join('g')
        .attr('class', 'kg-link-label select-none pointer-events-none')
        .attr('id', (d) => `kg-link-label-${d.id}`);

      labelGroups
        .append('rect')
        .attr('rx', 3.5)
        .attr('ry', 3.5)
        .attr('fill', '#ffffff')
        .attr('stroke', '#e2e8f0')
        .attr('stroke-width', 0.8)
        .attr('height', 13)
        .attr('y', -6.5);

      labelGroups
        .append('text')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('font-size', '8.5px')
        .attr('font-family', 'ui-monospace, monospace')
        .attr('font-weight', '600')
        .attr('fill', '#64748b')
        .text((d) => d.label || d.type);

      labelGroups.each(function () {
        const textNode = d3.select(this).select('text').node();
        if (textNode) {
          const bbox = textNode.getBBox();
          d3.select(this)
            .select('rect')
            .attr('x', bbox.x - 3.5)
            .attr('width', bbox.width + 7);
        }
      });

      linkLabelSelection = labelGroups;
    }

    // 3. Render Nodes in kg-nodes-group
    const nodeSelection = nodesGroup
      .selectAll('g.kg-node')
      .data(simNodes, (d) => d.id)
      .join('g')
      .attr('class', 'kg-node cursor-grab active:cursor-grabbing transition-opacity duration-200')
      .attr('id', (d) => `kg-node-${d.id}`);

    // Selection ring
    nodeSelection
      .append('circle')
      .attr('class', 'kg-node-selection-ring')
      .attr('r', (d) => (d.radius || 26) + 7)
      .attr('fill', 'none')
      .attr('stroke', '#6366f1')
      .attr('stroke-width', 2.5)
      .attr('stroke-dasharray', '4 3')
      .attr('opacity', (d) => (d.id === activeSelectedNodeId ? 1 : 0));

    // Search match ring
    nodeSelection
      .append('circle')
      .attr('class', 'kg-node-match-ring')
      .attr('r', (d) => (d.radius || 26) + 11)
      .attr('fill', 'none')
      .attr('stroke', '#f59e0b')
      .attr('stroke-width', 2.5)
      .attr('opacity', 0);

    // Shape rendering based on entity taxonomy
    nodeSelection.each(function (d) {
      const gNode = d3.select(this);
      const isSelected = d.id === activeSelectedNodeId;

      if (d.shape === 'rect') {
        const rw = (d.radius || 32) * 2.2;
        const rh = (d.radius || 32) * 1.3;
        gNode
          .append('rect')
          .attr('class', 'kg-node-shape')
          .attr('x', -rw / 2)
          .attr('y', -rh / 2)
          .attr('width', rw)
          .attr('height', rh)
          .attr('rx', 8)
          .attr('ry', 8)
          .attr('fill', d.style.fill || '#ffffff')
          .attr('stroke', isSelected ? '#6366f1' : d.style.stroke || '#475569')
          .attr('stroke-width', isSelected ? 3 : 2)
          .attr('filter', isSelected ? 'url(#kg-selection-glow)' : !isVeryLargeGraph ? 'url(#kg-node-shadow)' : null);
      } else if (d.shape === 'pill') {
        const rw = (d.radius || 30) * 2.4;
        const rh = (d.radius || 30) * 1.2;
        gNode
          .append('rect')
          .attr('class', 'kg-node-shape')
          .attr('x', -rw / 2)
          .attr('y', -rh / 2)
          .attr('width', rw)
          .attr('height', rh)
          .attr('rx', 14)
          .attr('ry', 14)
          .attr('fill', d.style.fill || '#ffffff')
          .attr('stroke', isSelected ? '#6366f1' : d.style.stroke || '#7c3aed')
          .attr('stroke-width', isSelected ? 3 : 2.2)
          .attr('filter', isSelected ? 'url(#kg-selection-glow)' : !isVeryLargeGraph ? 'url(#kg-node-shadow)' : null);
      } else {
        gNode
          .append('circle')
          .attr('class', 'kg-node-shape')
          .attr('r', d.radius || 26)
          .attr('fill', d.style.fill || '#ffffff')
          .attr('stroke', isSelected ? '#6366f1' : d.style.stroke || '#9333ea')
          .attr('stroke-width', isSelected ? 3 : 2)
          .attr('filter', isSelected ? 'url(#kg-selection-glow)' : !isVeryLargeGraph ? 'url(#kg-node-shadow)' : null);
      }
    });

    // 4. Render Node Labels in kg-node-labels-group (guarantees text renders above all nodes & links)
    const nodeLabelsSelection = nodeLabelsGroup
      .selectAll('g.kg-node-label')
      .data(simNodes, (d) => d.id)
      .join('g')
      .attr('class', 'kg-node-label pointer-events-none select-none')
      .attr('id', (d) => `kg-node-label-${d.id}`);

    nodeLabelsSelection.each(function (d) {
      const gLabel = d3.select(this);
      const fullLabel = d.tamilLabel || d.label || d.id;
      const truncatedLabel =
        fullLabel.length > 14 ? fullLabel.slice(0, 12) + '...' : fullLabel;

      // Label text with SVG Halo (paint-order: stroke fill) for pristine readability
      gLabel
        .append('text')
        .attr('class', 'kg-label-title tamil-font')
        .attr('text-anchor', 'middle')
        .attr('dominant-baseline', 'central')
        .attr('y', d.transliteration ? -3.5 : 0)
        .attr('font-size', d.shape === 'rect' ? '10.5px' : '9.5px')
        .attr('font-weight', '700')
        .attr('fill', d.style.text || '#0f172a')
        .attr('paint-order', 'stroke fill')
        .attr('stroke', '#ffffff')
        .attr('stroke-width', '3px')
        .attr('stroke-linejoin', 'round')
        .text(truncatedLabel);

      if (d.transliteration) {
        const tr =
          d.transliteration.length > 11
            ? d.transliteration.slice(0, 9) + '..'
            : d.transliteration;
        gLabel
          .append('text')
          .attr('class', 'kg-label-sub')
          .attr('text-anchor', 'middle')
          .attr('dominant-baseline', 'central')
          .attr('y', 8)
          .attr('font-size', '7.5px')
          .attr('font-family', 'ui-monospace, monospace')
          .attr('font-weight', '500')
          .attr('fill', '#64748b')
          .attr('paint-order', 'stroke fill')
          .attr('stroke', '#ffffff')
          .attr('stroke-width', '2.5px')
          .attr('stroke-linejoin', 'round')
          .text(tr);
      }
    });

    // Helper: Reset dynamic hover highlights to persistent selection state
    const resetHighlights = () => {
      const isSelected = Boolean(activeSelectedNodeId);
      const neighborSet = isSelected ? adjacencyMap.get(activeSelectedNodeId) || new Set() : new Set();
      const incidentEdges = isSelected ? new Set(incidentLinksMap.get(activeSelectedNodeId) || []) : new Set();

      nodeSelection.attr('opacity', (d) => {
        if (!isSelected) return 1;
        if (d.id === activeSelectedNodeId || neighborSet.has(d.id)) return 1;
        return 0.15;
      });

      nodeLabelsSelection.attr('opacity', (d) => {
        if (!isSelected) return 1;
        if (d.id === activeSelectedNodeId || neighborSet.has(d.id)) return 1;
        return 0.15;
      });

      linkSelection
        .attr('opacity', (d) => {
          if (!isSelected) return 0.85;
          return incidentEdges.has(d.id) ? 1 : 0.08;
        })
        .attr('stroke', (d) => (incidentEdges.has(d.id) ? '#6366f1' : '#cbd5e1'))
        .attr('stroke-width', (d) => (incidentEdges.has(d.id) ? 2.6 : 1.6))
        .attr('marker-end', (d) => (incidentEdges.has(d.id) ? 'url(#kg-arrow-highlight)' : 'url(#kg-arrow-default)'));

      if (linkLabelSelection) {
        linkLabelSelection.attr('opacity', (d) => {
          if (!isSelected) return 0.85;
          return incidentEdges.has(d.id) ? 1 : 0.08;
        });
      }
    };

    // 5. Interactive Hover Highlighting
    nodeSelection
      .on('mouseenter', (event, hoveredNode) => {
        const neighbors = adjacencyMap.get(hoveredNode.id) || new Set();
        const incidentEdges = new Set(incidentLinksMap.get(hoveredNode.id) || []);

        // Highlight hovered node and immediate neighbors; dim others
        nodeSelection.attr('opacity', (d) => {
          if (d.id === hoveredNode.id || neighbors.has(d.id)) return 1;
          return 0.15;
        });

        nodeLabelsSelection.attr('opacity', (d) => {
          if (d.id === hoveredNode.id || neighbors.has(d.id)) return 1;
          return 0.15;
        });

        // Highlight incident links; dim others
        linkSelection
          .attr('opacity', (d) => (incidentEdges.has(d.id) ? 1 : 0.08))
          .attr('stroke', (d) => (incidentEdges.has(d.id) ? '#6366f1' : '#cbd5e1'))
          .attr('stroke-width', (d) => (incidentEdges.has(d.id) ? 2.8 : 1.4))
          .attr('marker-end', (d) => (incidentEdges.has(d.id) ? 'url(#kg-arrow-highlight)' : 'url(#kg-arrow-default)'));

        if (linkLabelSelection) {
          linkLabelSelection.attr('opacity', (d) => (incidentEdges.has(d.id) ? 1 : 0.08));
        }

        // Elevate hovered node
        d3.select(event.currentTarget)
          .select('.kg-node-shape')
          .attr('stroke-width', 3.5);
      })
      .on('mouseleave', (event, hoveredNode) => {
        d3.select(event.currentTarget)
          .select('.kg-node-shape')
          .attr('stroke-width', hoveredNode.id === activeSelectedNodeId ? 3 : 2);
        resetHighlights();
      });

    // Link Hover Highlighting
    linkSelection
      .on('mouseenter', (event, hoveredLink) => {
        nodeSelection.attr('opacity', (d) => {
          if (d.id === hoveredLink.source.id || d.id === hoveredLink.target.id) return 1;
          return 0.18;
        });

        nodeLabelsSelection.attr('opacity', (d) => {
          if (d.id === hoveredLink.source.id || d.id === hoveredLink.target.id) return 1;
          return 0.18;
        });

        linkSelection
          .attr('opacity', (d) => (d.id === hoveredLink.id ? 1 : 0.08))
          .attr('stroke', (d) => (d.id === hoveredLink.id ? '#6366f1' : '#cbd5e1'))
          .attr('stroke-width', (d) => (d.id === hoveredLink.id ? 3 : 1.4))
          .attr('marker-end', (d) => (d.id === hoveredLink.id ? 'url(#kg-arrow-highlight)' : 'url(#kg-arrow-default)'));

        if (linkLabelSelection) {
          linkLabelSelection.attr('opacity', (d) => (d.id === hoveredLink.id ? 1 : 0.08));
        }
      })
      .on('mouseleave', () => {
        resetHighlights();
      });

    // 6. Smooth Node Dragging with Drag-vs-Click Conflict Prevention
    if (enableDragging) {
      const drag = d3
        .drag()
        .on('start', (event, d) => {
          // Prevent zoom/pan while dragging node
          if (event.sourceEvent) event.sourceEvent.stopPropagation();

          dragStartPosRef.current = {
            x: event.x,
            y: event.y,
            moved: false,
          };

          if (!event.active && simulationRef.current) {
            simulationRef.current.alphaTarget(0.3).restart();
          }
          d.fx = d.x;
          d.fy = d.y;
        })
        .on('drag', (event, d) => {
          const dx = event.x - dragStartPosRef.current.x;
          const dy = event.y - dragStartPosRef.current.y;
          if (Math.hypot(dx, dy) > 4) {
            dragStartPosRef.current.moved = true;
          }

          d.fx = event.x;
          d.fy = event.y;
        })
        .on('end', (event, d) => {
          if (!event.active && simulationRef.current) {
            simulationRef.current.alphaTarget(0);
          }
          d.fx = null;
          d.fy = null;
        });

      nodeSelection.call(drag);
    }

    // 7. Node Click Handler (selects node & opens details)
    nodeSelection.on('click', (event, d) => {
      event.stopPropagation();
      // If user moved significantly during drag, ignore as click
      if (dragStartPosRef.current.moved) return;

      const isCurrent = d.id === activeSelectedNodeId;
      const nextId = isCurrent ? null : d.id;

      setInternalSelectedNodeId(nextId);
      setInternalSelectedLinkId(null);
      setActiveEdgeData(null);
      setEdgePopoverPos(null);
      setActiveNodeData(isCurrent ? null : d);

      if (!isCurrent && focusOnNeighborhoodRef.current) {
        focusOnNeighborhoodRef.current(d.id, 75, 600);
      }

      if (onNodeClick) onNodeClick(d, event);

      if (!isCurrent && enableDynamicExpansion && expandNodeFromNeo4jRef.current) {
        expandNodeFromNeo4jRef.current(d);
      }
    });

    // 8. Link Click Handler (selects relationship & displays popover)
    linkSelection.on('click', (event, d) => {
      event.stopPropagation();
      setInternalSelectedLinkId(d.id);
      setInternalSelectedNodeId(null);
      setActiveNodeData(null);

      const rect = container.getBoundingClientRect();
      const clickX = event.clientX - rect.left;
      const clickY = event.clientY - rect.top;
      setEdgePopoverPos(calculateClampedPos(clickX, clickY, 360, 240));

      const edgePayload = {
        id: d.id,
        label: d.label,
        type: d.type || d.relation,
        sourceId: d.source.id,
        targetId: d.target.id,
        sourceLabel: d.source.label || d.source.id,
        targetLabel: d.target.label || d.target.id,
        confidence: d.confidence,
        properties: d.properties || {},
      };
      setActiveEdgeData(edgePayload);

      if (onLinkClick) onLinkClick(d, event);
    });

    // Simulation tick handler
    simulation.on('tick', () => {
      simNodes.forEach((n) => {
        currentNodesRef.current.set(n.id, { x: n.x, y: n.y, vx: n.vx, vy: n.vy });
      });

      // Position links with dynamic path generator (loops, curves, lines)
      linkSelection.attr('d', computeLinkPath);

      if (linkLabelSelection) {
        linkLabelSelection.attr('transform', computeLinkLabelTransform);
      }

      nodeSelection.attr('transform', (d) => `translate(${d.x}, ${d.y})`);
      nodeLabelsSelection.attr('transform', (d) => `translate(${d.x}, ${d.y})`);
    });

    // Initial fit view
    const timer = setTimeout(() => {
      fitView(55, 300);
    }, 200);

    const ro = new ResizeObserver(() => {
      fitView(55, 0);
    });
    ro.observe(container);

    return () => {
      clearTimeout(timer);
      ro.disconnect();
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }
    };
  }, [
    graphNodes,
    graphLinks,
    linkDistance,
    chargeStrength,
    enableDragging,
    enableZooming,
    showLinkLabels,
    activeSelectedNodeId,
    activeSelectedLinkId,
    isVeryLargeGraph,
    colorMap,
    onNodeClick,
    onLinkClick,
    onBackgroundClick,
    onZoomChange,
    fitView,
    calculateClampedPos,
    enableDynamicExpansion,
  ]);

  // Synchronize dynamic search match rings
  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svg = d3.select(svgEl);

    const matchSet = new Set(searchMatches.map((m) => m.id));
    svg.selectAll('.kg-node-match-ring').attr('opacity', (d) => (matchSet.has(d.id) ? 1 : 0));
  }, [searchMatches]);

  // Synchronize selection & dimming states
  useEffect(() => {
    const svgEl = svgRef.current;
    if (!svgEl) return;
    const svg = d3.select(svgEl);

    const isSelected = Boolean(activeSelectedNodeId);
    const isLinkSelected = Boolean(activeSelectedLinkId);

    // Compute directly connected neighbor nodes and relationships for activeSelectedNodeId
    const directNeighborIds = new Set();
    const directLinkIds = new Set();
    const outgoingLinkIds = new Set();
    const incomingLinkIds = new Set();
    if (activeSelectedNodeId) {
      graphLinks.forEach((l) => {
        const s = String(l.source?.id || l.source);
        const t = String(l.target?.id || l.target);
        const sel = String(activeSelectedNodeId);
        if (s === sel) {
          directNeighborIds.add(t);
          directLinkIds.add(String(l.id));
          outgoingLinkIds.add(String(l.id));
        } else if (t === sel) {
          directNeighborIds.add(s);
          directLinkIds.add(String(l.id));
          incomingLinkIds.add(String(l.id));
        }
      });
    }

    const hasHighlighting =
      isSelected ||
      isLinkSelected ||
      (highlightedNodeIds && highlightedNodeIds.length > 0) ||
      (highlightedLinkIds && highlightedLinkIds.length > 0);

    const nodeSet = new Set(
      highlightedNodeIds || (activeSelectedNodeId ? [activeSelectedNodeId, ...Array.from(directNeighborIds)] : [])
    );
    const linkSet = new Set(
      highlightedLinkIds || (activeSelectedLinkId ? [activeSelectedLinkId] : Array.from(directLinkIds))
    );

    svg.selectAll('g.kg-node').attr('opacity', (d) => {
      if (!hasHighlighting && !dimmed) return 1;
      if (String(d.id) === String(activeSelectedNodeId)) return 1.0;
      if (directNeighborIds.has(String(d.id))) return 1.0;
      if (nodeSet.has(d.id)) return 1.0;
      return dimmed || hasHighlighting ? 0.18 : 1;
    })
    .select('.kg-node-shape')
    .attr('stroke-width', (d) => {
      if (String(d.id) === String(activeSelectedNodeId)) return 5.0;
      if (directNeighborIds.has(String(d.id))) return 3.4;
      return d.style?.strokeWidth || 2;
    })
    .attr('stroke', (d) => {
      if (String(d.id) === String(activeSelectedNodeId)) return '#4338ca';
      if (directNeighborIds.has(String(d.id))) return d.style?.stroke || '#6366f1';
      return hasHighlighting && !nodeSet.has(d.id) ? '#cbd5e1' : (d.style?.stroke || '#64748b');
    })
    .attr('filter', (d) => {
      if (String(d.id) === String(activeSelectedNodeId)) return 'url(#kg-selection-glow)';
      if (directNeighborIds.has(String(d.id))) return 'url(#kg-neighbor-glow)';
      return 'none';
    });

    // Raise selected node and its label to top
    if (activeSelectedNodeId) {
      svg.selectAll('g.kg-node').filter((d) => String(d.id) === String(activeSelectedNodeId)).raise();
      svg.selectAll('g.kg-node-label').filter((d) => String(d.id) === String(activeSelectedNodeId)).raise();
    }

    svg.selectAll('g.kg-node-label').attr('opacity', (d) => {
      if (!hasHighlighting && !dimmed) return 1;
      if (String(d.id) === String(activeSelectedNodeId) || directNeighborIds.has(String(d.id))) return 1.0;
      if (nodeSet.has(d.id)) return 1.0;
      return dimmed || hasHighlighting ? 0.14 : 1;
    });

    // Highlight direct relationships with directional arrows & stroke animations; subdue unrelated edges
    svg.selectAll('path.kg-link').attr('opacity', (d) => {
      if (!hasHighlighting && !dimmed) return 0.85;
      if (directLinkIds.has(String(d.id)) || linkSet.has(d.id)) {
        return 1.0;
      }
      return dimmed || hasHighlighting ? 0.06 : 0.85;
    })
    .attr('stroke', (d) => {
      if (outgoingLinkIds.has(String(d.id))) return '#4f46e5';
      if (incomingLinkIds.has(String(d.id))) return '#059669';
      if (directLinkIds.has(String(d.id)) || linkSet.has(d.id)) return '#6366f1';
      return hasHighlighting ? '#cbd5e1' : (d.color || '#cbd5e1');
    })
    .attr('stroke-width', (d) => {
      if (directLinkIds.has(String(d.id)) || linkSet.has(d.id)) return 3.8;
      return hasHighlighting ? 0.8 : (d.strokeWidth || 1.4);
    })
    .attr('stroke-dasharray', (d) => {
      if (directLinkIds.has(String(d.id))) return '6 4';
      return 'none';
    })
    .classed('d3-active-link-dash', (d) => directLinkIds.has(String(d.id)))
    .attr('marker-end', (d) => {
      if (outgoingLinkIds.has(String(d.id))) return 'url(#kg-arrow-connected)';
      if (incomingLinkIds.has(String(d.id))) return 'url(#kg-arrow-connected-in)';
      if (directLinkIds.has(String(d.id)) || linkSet.has(d.id)) return 'url(#kg-arrow-highlight)';
      return hasHighlighting ? null : 'url(#kg-arrow-default)';
    });

    if (activeSelectedNodeId) {
      svg.selectAll('path.kg-link').filter((d) => directLinkIds.has(String(d.id))).raise();
    }

    // Display relationship type pills with directional cues on highlighted edges
    svg.selectAll('g.kg-link-label').each(function (d) {
      const el = d3.select(this);
      const edgeId = String(d.id);
      const isDirect = directLinkIds.has(edgeId);
      const isOut = outgoingLinkIds.has(edgeId);
      const isIn = incomingLinkIds.has(edgeId);
      const isIncluded = isDirect || linkSet.has(d.id);

      if (!hasHighlighting && !dimmed) {
        el.attr('opacity', 0.85);
        el.select('rect')
          .attr('fill', '#ffffff')
          .attr('stroke', '#e2e8f0')
          .attr('stroke-width', 0.8)
          .attr('filter', 'none');
        el.select('text')
          .attr('fill', '#64748b')
          .attr('font-size', '8.5px')
          .attr('font-weight', '600')
          .text(d.label || d.type || '');
        return;
      }

      if (isDirect) {
        const rawType = d.label || d.type || d.relation || '';
        const directionalText = isOut ? `${rawType} →` : (isIn ? `← ${rawType}` : rawType);
        const textWidth = Math.max(34, directionalText.length * 6.5 + 16);

        el.attr('opacity', 1.0).raise();

        el.select('rect')
          .attr('fill', '#ffffff')
          .attr('stroke', isOut ? '#4f46e5' : '#059669')
          .attr('stroke-width', 1.8)
          .attr('height', 18)
          .attr('y', -9)
          .attr('x', -textWidth / 2)
          .attr('width', textWidth)
          .attr('rx', 5)
          .attr('ry', 5)
          .attr('filter', 'drop-shadow(0 1px 3px rgba(0,0,0,0.14))');

        el.select('text')
          .attr('font-size', '10px')
          .attr('font-weight', '700')
          .attr('fill', isOut ? '#3730a3' : '#065f46')
          .text(directionalText);
      } else if (isIncluded) {
        el.attr('opacity', 0.8);
        el.select('rect')
          .attr('fill', '#ffffff')
          .attr('stroke', '#cbd5e1')
          .attr('stroke-width', 1)
          .attr('filter', 'none');
        el.select('text')
          .attr('fill', '#475569')
          .text(d.label || d.type || '');
      } else {
        el.attr('opacity', 0);
      }
    });

    // Update selection ring visibility
    svg.selectAll('.kg-node-selection-ring').attr('opacity', (d) =>
      String(d.id) === String(activeSelectedNodeId) ? 1 : 0
    );

    // In Focus Mode: smoothly focus and frame the selected node's neighborhood
    if (activeSelectedNodeId && isFocusMode && focusOnNeighborhoodRef.current) {
      focusOnNeighborhoodRef.current(activeSelectedNodeId, 75, 600);
    }
  }, [
    activeSelectedNodeId,
    activeSelectedLinkId,
    highlightedNodeIds,
    highlightedLinkIds,
    dimmed,
    isFocusMode,
    graphLinks,
  ]);

  return (
    <div
      ref={containerRef}
      style={{ width, height }}
      className={`relative overflow-hidden select-none bg-[#fbfcfe] font-sans ${className}`}
    >
      {/* Subtle canvas grid pattern */}
      <div
        className="absolute inset-0 pointer-events-none opacity-35"
        style={{
          backgroundImage: 'radial-gradient(#94a3b8 0.75px, transparent 0.75px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Primary SVG Container */}
      <svg
        ref={svgRef}
        className="w-full h-full block cursor-grab active:cursor-grabbing"
      />

      {/* Top Floating Controls: Search & Controls Toolbar */}
      <div className="absolute top-3 right-3 flex items-center gap-2 z-20">
        {/* Research Search & Highlight Pill */}
        {showSearch && (
          <div className="flex items-center bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-xl px-2.5 py-1.5 shadow-sm transition-all duration-200">
            {isSearchOpen ? (
              <div className="flex items-center gap-1.5 animate-in fade-in zoom-in-95 duration-150">
                <Search className="w-3.5 h-3.5 text-purple-600 shrink-0" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search name, ID, type..."
                  className="text-xs bg-transparent border-none outline-none w-36 sm:w-48 text-slate-800 placeholder:text-slate-400 font-medium"
                  autoFocus
                />
                {searchMatches.length > 0 && (
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-50 text-purple-700 font-semibold border border-purple-200">
                    {currentMatchIndex + 1}/{searchMatches.length}
                  </span>
                )}
                {searchMatches.length > 1 && (
                  <div className="flex items-center">
                    <button
                      type="button"
                      onClick={() => handleCycleMatch(-1)}
                      className="p-0.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                      title="Previous match"
                    >
                      <ChevronLeft className="w-3.5 h-3.5" />
                    </button>
                    <button
                      type="button"
                      onClick={() => handleCycleMatch(1)}
                      className="p-0.5 text-slate-400 hover:text-slate-700 cursor-pointer"
                      title="Next match"
                    >
                      <ChevronRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => {
                    setSearchQuery('');
                    setIsSearchOpen(false);
                  }}
                  className="p-1 text-slate-400 hover:text-slate-600 rounded-md cursor-pointer"
                  title="Close search"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsSearchOpen(true)}
                className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-purple-700 font-medium cursor-pointer"
                title="Search and highlight entities"
              >
                <Search className="w-3.5 h-3.5 text-slate-500" />
                <span className="hidden sm:inline">Search KG</span>
              </button>
            )}
          </div>
        )}

        {/* Action Controls Toolbar */}
        {showControls && (
          <div className="flex items-center gap-1 bg-white/95 backdrop-blur-md border border-slate-200/90 rounded-xl p-1 shadow-sm">
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
              onClick={() => fitView(55, 350)}
              className="p-1.5 rounded-lg text-slate-600 hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
              title="Fit to Screen (Reset View)"
              aria-label="Fit to Screen"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={handleCenterSelected}
              disabled={!activeSelectedNodeId}
              className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                activeSelectedNodeId
                  ? 'text-purple-600 hover:bg-purple-50 hover:text-purple-800'
                  : 'text-slate-300 cursor-not-allowed'
              }`}
              title={activeSelectedNodeId ? 'Center Selected Node' : 'Select a node to center'}
              aria-label="Center Selected Node"
            >
              <Crosshair className="w-3.5 h-3.5" />
            </button>
            <button
              type="button"
              onClick={toggleFullscreen}
              className="p-1.5 rounded-lg text-slate-600 hover:text-purple-700 hover:bg-purple-50 transition-colors cursor-pointer"
              title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
              aria-label="Fullscreen Toggle"
            >
              {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
            <div className="h-4 w-px bg-slate-200 mx-0.5" />
            <span className="text-[10px] font-mono text-slate-500 px-1 font-semibold">
              {zoomLevelPercent}%
            </span>
          </div>
        )}
      </div>

      {/* Node Details Inspection Panel */}
      {showDetailsPanel && activeNodeData && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="absolute top-16 left-3 w-80 max-h-[85%] overflow-y-auto bg-white/95 backdrop-blur-md rounded-2xl border border-purple-200 shadow-xl p-4 z-20 animate-in fade-in slide-in-from-left-4 duration-200 text-xs"
        >
          <div className="flex items-start justify-between gap-2 pb-2 mb-2.5 border-b border-slate-100">
            <div>
              <div className="flex items-center gap-1.5 mb-1">
                <span className="px-2 py-0.5 rounded-full text-[10px] font-bold tracking-wide uppercase bg-purple-50 text-purple-700 border border-purple-200">
                  {activeNodeData.type || 'Entity'}
                </span>
                {activeNodeData.isSynthesized && (
                  <span className="px-1.5 py-0.5 rounded text-[9px] font-semibold bg-amber-50 text-amber-700 border border-amber-200">
                    Synthesized Endpoint
                  </span>
                )}
              </div>
              <h3 className="font-bold text-slate-900 text-sm leading-snug tamil-font">
                {activeNodeData.tamilLabel || activeNodeData.label || activeNodeData.id}
              </h3>
              {activeNodeData.transliteration && (
                <p className="text-[11px] font-mono text-slate-500 italic mt-0.5">
                  {activeNodeData.transliteration}
                </p>
              )}
            </div>
            <button
              type="button"
              onClick={() => {
                setActiveNodeData(null);
                setInternalSelectedNodeId(null);
              }}
              className="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
              title="Close Details Panel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Properties Grid */}
          <div className="space-y-1.5 bg-slate-50/80 p-2.5 rounded-xl border border-slate-200/80 mb-3 text-[11px]">
            <div className="flex items-center justify-between text-slate-600">
              <span className="font-semibold text-slate-700">Entity ID:</span>
              <span className="font-mono text-slate-800 truncate max-w-[60%]">{activeNodeData.id}</span>
            </div>
            {activeNodeData.properties &&
              Object.entries(activeNodeData.properties)
                .filter(([k]) => !['label', 'name', 'type', 'id'].includes(k))
                .slice(0, 7)
                .map(([key, val]) => (
                  <div key={key} className="flex items-start justify-between gap-1 text-slate-600">
                    <span className="font-semibold text-slate-700 capitalize">
                      {key.replace(/_/g, ' ')}:
                    </span>
                    <span className="text-right truncate max-w-[60%] text-slate-800">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
          </div>

          {/* Dynamic Neo4j Connected Neighbors Section */}
          <div className="mb-3 space-y-1.5">
            <div className="flex items-center justify-between text-[11px] font-semibold text-slate-700">
              <span className="flex items-center gap-1">
                <Network className="w-3.5 h-3.5 text-purple-600" />
                <span>Connected Neighbors (Neo4j):</span>
              </span>
              {isExpandingNode ? (
                <span className="text-[10px] text-purple-600 flex items-center gap-1 font-mono">
                  <RefreshCw className="w-3 h-3 animate-spin" /> Querying...
                </span>
              ) : (
                <span className="font-mono text-purple-700 font-bold">
                  {nodeConnectedData?.relationships?.length ?? 0}
                </span>
              )}
            </div>

            {nodeConnectedData?.relationships && nodeConnectedData.relationships.length > 0 ? (
              <div className="max-h-36 overflow-y-auto space-y-1 pr-1">
                {nodeConnectedData.relationships.map((rel, idx) => {
                  const isOut = rel.direction === "outgoing";
                  const neighborId = isOut ? rel.target : rel.source;
                  const neighborNode =
                    (nodeConnectedData.connected_nodes || []).find((cn) => cn.id === neighborId) || {};
                  const neighborName = neighborNode.name || neighborNode.label || neighborId;

                  return (
                    <div
                      key={idx}
                      className="p-1.5 rounded-lg bg-slate-50 border border-slate-200/90 text-[10px] flex items-center justify-between gap-1"
                    >
                      <span
                        className={`px-1 py-0.5 rounded font-mono font-bold text-[8px] border ${
                          isOut
                            ? "bg-blue-50 text-blue-700 border-blue-200"
                            : "bg-emerald-50 text-emerald-700 border-emerald-200"
                        }`}
                      >
                        {isOut ? "OUT →" : "← IN"}
                      </span>
                      <span className="font-mono text-purple-800 font-bold truncate max-w-[100px]" title={rel.type}>
                        {rel.type}
                      </span>
                      <span className="text-slate-800 font-medium truncate max-w-[90px] tamil-font" title={neighborName}>
                        {neighborName}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : !isExpandingNode ? (
              <p className="text-[10px] text-slate-400 italic">No first-degree neighbors in Neo4j.</p>
            ) : null}
          </div>

          <div className="flex items-center justify-between gap-2">
            <button
              type="button"
              onClick={() => centerNode(activeNodeData.id, 1.4, 350)}
              className="flex-1 flex items-center justify-center gap-1.5 py-1.5 rounded-xl bg-purple-50 hover:bg-purple-100 border border-purple-200 text-purple-900 font-semibold text-xs transition-colors cursor-pointer"
            >
              <Crosshair className="w-3.5 h-3.5 text-purple-600" />
              <span>Center in View</span>
            </button>
            <button
              type="button"
              onClick={() => expandNodeFromNeo4j(activeNodeData)}
              disabled={isExpandingNode}
              className="px-3 py-1.5 rounded-xl bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs transition-colors cursor-pointer disabled:opacity-50 flex items-center gap-1 shadow-2xs"
              title="Query Neo4j Aura for connected first-degree nodes"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isExpandingNode ? "animate-spin" : ""}`} />
              <span>Expand</span>
            </button>
          </div>
        </div>
      )}

      {/* Relationship Provenance Inspection Popover */}
      {activeEdgeData && edgePopoverPos && (
        <div
          style={{
            left: `${edgePopoverPos.left}px`,
            top: `${edgePopoverPos.top}px`,
            width: `${edgePopoverPos.width}px`,
          }}
          onClick={(e) => e.stopPropagation()}
          className="absolute bg-white/95 backdrop-blur-md rounded-xl border border-purple-200 shadow-2xl p-3 z-30 animate-in fade-in zoom-in-95 duration-150 text-xs"
        >
          <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-slate-100">
            <div className="flex items-center gap-1.5 font-bold text-slate-900">
              <Info className="w-3.5 h-3.5 text-purple-600" />
              <span>RELATIONSHIP PROVENANCE</span>
            </div>
            <button
              type="button"
              onClick={() => {
                setActiveEdgeData(null);
                setEdgePopoverPos(null);
                setInternalSelectedLinkId(null);
              }}
              className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-100 cursor-pointer"
              title="Close"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="flex items-center justify-between bg-slate-50 p-2 rounded-lg border border-slate-200 text-[11px] mb-2">
            <span className="font-semibold text-slate-800 truncate max-w-[38%]">
              {activeEdgeData.sourceLabel}
            </span>
            <div className="flex items-center gap-1 font-mono text-purple-700 font-bold text-[10px] px-1.5 py-0.5 bg-purple-50 rounded border border-purple-200 shrink-0">
              <ArrowRight className="w-3 h-3 text-purple-500" />
              <span>{activeEdgeData.type || activeEdgeData.label}</span>
              <ArrowRight className="w-3 h-3 text-purple-500" />
            </div>
            <span className="font-semibold text-slate-800 truncate max-w-[38%]">
              {activeEdgeData.targetLabel}
            </span>
          </div>

          <div className="space-y-1 bg-slate-50 rounded-lg p-2 border border-slate-200 text-[10px] text-slate-600">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-slate-700">Link ID:</span>
              <span className="font-mono text-slate-800 truncate">{activeEdgeData.id}</span>
            </div>
            {activeEdgeData.confidence !== undefined && (
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-700">Confidence:</span>
                <span className="font-mono text-emerald-700 font-bold">
                  {Math.round(activeEdgeData.confidence * 100)}%
                </span>
              </div>
            )}
            {activeEdgeData.properties &&
              Object.entries(activeEdgeData.properties)
                .slice(0, 4)
                .map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between">
                    <span className="font-semibold text-slate-700 capitalize">
                      {k.replace(/_/g, ' ')}:
                    </span>
                    <span className="font-mono text-slate-800 truncate max-w-[60%]">
                      {String(v)}
                    </span>
                  </div>
                ))}
          </div>
        </div>
      )}

      {/* Real-time Development Diagnostics HUD Panel */}
      <div className="absolute bottom-2 left-3 z-20 flex flex-col items-start gap-1">
        {isDiagnosticsOpen ? (
          <div className="bg-white/95 backdrop-blur-md rounded-xl border border-slate-200/90 shadow-lg p-2.5 text-[11px] font-mono text-slate-700 animate-in fade-in zoom-in-95 duration-150 space-y-1 min-w-[240px]">
            <div className="flex items-center justify-between pb-1 border-b border-slate-100 font-bold text-slate-900">
              <div className="flex items-center gap-1 text-purple-700">
                <Activity className="w-3.5 h-3.5" />
                <span>KG Pipeline Diagnostics</span>
              </div>
              <button
                type="button"
                onClick={() => setIsDiagnosticsOpen(false)}
                className="text-slate-400 hover:text-slate-600 cursor-pointer text-xs p-0.5"
                title="Collapse Diagnostics"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 pt-0.5">
              <span className="text-slate-500">Backend Nodes:</span>
              <span className="font-semibold text-slate-800">{stats.backendNodeCount || stats.nodeCount}</span>
              <span className="text-slate-500">Backend Rels:</span>
              <span className="font-semibold text-slate-800">{stats.backendRelCount || stats.linkCount}</span>
              <span className="text-slate-500">Normalized Nodes:</span>
              <span className="font-semibold text-indigo-700">{stats.nodeCount}</span>
              <span className="text-slate-500">Normalized Links:</span>
              <span className="font-semibold text-indigo-700">{stats.linkCount}</span>
              <span className="text-slate-500">Rendered Nodes:</span>
              <span className="font-bold text-emerald-700">{renderedCounts.nodes}</span>
              <span className="text-slate-500">Rendered Links:</span>
              <span className="font-bold text-emerald-700">{renderedCounts.links}</span>
              <span className="text-slate-500">Self-Loops:</span>
              <span className="text-amber-700">{stats.selfLoopCount || 0}</span>
              <span className="text-slate-500">Multi-Edges:</span>
              <span className="text-purple-700">{stats.multiEdgeCount || 0}</span>
              <span className="text-slate-500">Isolated Nodes:</span>
              <span className="text-blue-700">{stats.isolatedNodeCount || 0}</span>
            </div>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setIsDiagnosticsOpen(true)}
            className="flex items-center gap-1.5 text-[10px] font-mono text-slate-600 hover:text-purple-700 bg-white/85 hover:bg-white backdrop-blur-md px-2.5 py-1 rounded-lg border border-slate-200/80 shadow-xs cursor-pointer transition-all"
            title="Open Pipeline Diagnostics"
          >
            <Activity className="w-3 h-3 text-purple-600" />
            <span>
              {renderedCounts.nodes} nodes • {renderedCounts.links} edges
            </span>
            <span className="text-[9px] text-slate-400 font-semibold px-1 rounded bg-slate-100">HUD</span>
          </button>
        )}
      </div>

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 z-30 bg-white/80 backdrop-blur-xs flex flex-col items-center justify-center p-6 text-center animate-in fade-in duration-150">
          <div className="p-3 bg-purple-100/90 text-purple-700 rounded-2xl border border-purple-200/80 shadow-md mb-3 animate-pulse">
            <RefreshCw className="w-6 h-6 animate-spin text-purple-600" />
          </div>
          <h4 className="text-xs font-bold text-slate-800 tracking-tight">
            {loadingMessage}
          </h4>
        </div>
      )}

      {/* Empty State Overlay */}
      {!isLoading && graphNodes.length === 0 && (
        <div className="absolute inset-0 z-20 flex flex-col items-center justify-center p-6 text-center bg-slate-50/90">
          <div className="p-3 bg-slate-100 text-slate-400 rounded-2xl border border-slate-200 shadow-2xs mb-2.5">
            <Network className="w-7 h-7 stroke-[1.5]" />
          </div>
          <h4 className="text-xs font-bold text-slate-700">{emptyMessage}</h4>
        </div>
      )}
    </div>
  );
}
