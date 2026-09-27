"""
Knowledge Graph routes:
- GET  /api/kg/statistics   (Detailed hierarchical & layer metrics, graph density)
- GET  /api/kg/entity/<id>  (Entity details, metadata, hierarchy, direct neighbors, source evidence)
- POST /api/kg/subgraph     (Multi-hop subgraph expansion with layer and hierarchy filtering)
- GET  /api/kg/subgraph     (Backward-compatible GET subgraph extraction)
- GET  /api/kg/path         (Multi-hop path search with propagated path confidence)
- GET  /api/kg/graph        (Full knowledge graph export with SVG coordinates)
- GET  /api/kg/health       (Graph structural health and connectivity validation)
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from api.responses import success_response, error_response
from knowledge_graph.graph_builder import kg_instance
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from knowledge_graph.graph_validator import KnowledgeGraphValidator
from knowledge_graph.ontology import TolkappiyamOntology
from core.logger import logger
from services.neo4j_service import neo4j_service
from knowledge_graph.neo4j_repository import neo4j_repository
from services.graph_retrieval_service import graph_retrieval_service

kg_bp = Blueprint("kg", __name__, url_prefix="/api/kg")
query_engine = KnowledgeGraphQueryEngine()


@kg_bp.route("/statistics", methods=["GET"])
def get_kg_statistics():
    """Returns comprehensive graph metrics including L0-L5 hierarchy and 5-layer distributions from Neo4j Aura."""
    try:
        if neo4j_repository.is_available() and neo4j_service.is_connected():
            data = neo4j_repository.get_kg_statistics()
            return success_response(data=data, message="Knowledge Graph statistics retrieved from Neo4j Aura")

        # Fallback when Neo4j Aura cluster is temporarily offline
        health = KnowledgeGraphValidator.validate()
        store = kg_instance.store

        relation_distribution = {}
        for edge in store.get_all_edges():
            rel = edge.relation
            relation_distribution[rel] = relation_distribution.get(rel, 0) + 1

        data = {
            "total_nodes": health["node_count"],
            "total_edges": health["edge_count"],
            "density": health["density"],
            "is_connected": health["is_connected"],
            "isolated_nodes": health["isolated_nodes"],
            "hierarchy_distribution": health["hierarchy_distribution"],
            "layer_distribution": health["layer_distribution"],
            "relation_distribution": relation_distribution,
            "categories": TolkappiyamOntology.get_category_config(),
            "hierarchy_levels": TolkappiyamOntology.get_hierarchy_config(),
            "logical_layers": TolkappiyamOntology.get_layer_config(),
            "source": "in_memory_kg_fallback",
        }
        return success_response(data=data, message="Knowledge Graph statistics retrieved")
    except Exception as e:
        logger.error(f"Error computing KG statistics: {e}", exc_info=True)
        return error_response(f"Failed to retrieve KG statistics: {str(e)}", status_code=500)


@kg_bp.route("/entity/<string:entity_id>", methods=["GET"])
def get_entity_detail(entity_id: str):
    """Retrieves an entity's complete schema, hierarchy level, logical layer, and direct neighbors directly from Neo4j Aura."""
    try:
        entity_data = None
        if neo4j_repository.is_available() and neo4j_service.is_connected():
            entity_data = neo4j_repository.get_entity_detail(entity_id)

        if not entity_data:
            entity_data = query_engine.get_entity(entity_id)

        if not entity_data:
            return error_response(
                f"Entity '{entity_id}' not found in knowledge graph",
                error_code="ENTITY_NOT_FOUND",
                status_code=404,
            )
        return success_response(
            data=entity_data,
            message=f"Retrieved entity details for '{entity_id}'",
        )
    except Exception as e:
        logger.error(f"Error fetching entity '{entity_id}': {e}", exc_info=True)
        return error_response(f"Failed to fetch entity: {str(e)}", status_code=500)


@kg_bp.route("/node/<path:node_id>/connected", methods=["GET"])
@kg_bp.route("/node/connected", methods=["POST", "GET"])
@kg_bp.route("/node/<path:node_id>/expansion", methods=["GET"])
@kg_bp.route("/node/expand", methods=["POST"])
@kg_bp.route("/node/<path:node_id>/traverse", methods=["GET", "POST"])
@kg_bp.route("/node/traverse", methods=["POST"])
@kg_bp.route("/node/<path:node_id>/explore", methods=["GET", "POST"])
@kg_bp.route("/node/explore", methods=["POST"])
def get_node_connected_endpoint(node_id: str = None):
    """
    Retrieves directly connected and multi-hop nodes and relationships for a selected node from Neo4j Aura.
    Supports configurable traversal depth (1 to 5 hops) with node type and relationship type filtering.
    Returns:
      - selected_node: Full node attributes, labels, properties, and metadata
      - connected_nodes: List of all neighbor nodes with hop_distance, parent_id, and path_from_root
      - relationships: List of relationships with direction ('outgoing' / 'incoming'),
                       type, confidence, validation_level, and metadata
      - paths: Step-by-step path lineage from the selected node to every expanded node
      - metadata: Traversal parameters, depth, counts, filters, provenance, and timestamp
    """
    try:
        target_id = node_id
        limit = 150
        hops = 1
        allowed_types = None
        excluded_types = None
        rel_types = None
        direction = "both"

        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            if not target_id:
                target_id = body.get("node_id") or body.get("id") or body.get("elementId")
            limit = int(body.get("limit") or body.get("maxNodes") or 150)
            hops = int(body.get("hops") or body.get("depth") or body.get("max_hops") or 1)
            allowed_types = body.get("allowed_types") or body.get("node_types")
            excluded_types = body.get("excluded_types") or body.get("exclude_types")
            rel_types = body.get("rel_types") or body.get("relationship_types")
            direction = str(body.get("direction", "both")).lower()
        else:
            if not target_id:
                target_id = request.args.get("node_id") or request.args.get("id")
            limit = int(request.args.get("limit") or 150)
            hops = int(request.args.get("hops") or request.args.get("depth") or request.args.get("max_hops") or 1)
            raw_allowed = request.args.get("allowed_types") or request.args.get("node_types")
            allowed_types = [t.strip() for t in raw_allowed.split(",")] if raw_allowed else request.args.getlist("allowed_types") or None
            raw_excluded = request.args.get("excluded_types") or request.args.get("exclude_types")
            excluded_types = [t.strip() for t in raw_excluded.split(",")] if raw_excluded else request.args.getlist("excluded_types") or None
            raw_rels = request.args.get("rel_types") or request.args.get("relationship_types")
            rel_types = [r.strip() for r in raw_rels.split(",")] if raw_rels else request.args.getlist("rel_types") or None
            direction = str(request.args.get("direction", "both")).lower()

        if isinstance(allowed_types, str):
            allowed_types = [t.strip() for t in allowed_types.split(",") if t.strip()]
        if isinstance(excluded_types, str):
            excluded_types = [t.strip() for t in excluded_types.split(",") if t.strip()]
        if isinstance(rel_types, str):
            rel_types = [r.strip() for r in rel_types.split(",") if r.strip()]

        if not target_id or not str(target_id).strip():
            return error_response(
                "Parameter 'node_id' is required to retrieve connected elements",
                error_code="MISSING_NODE_ID",
                status_code=400,
            )

        target_id = str(target_id).strip()
        hops = min(max(hops, 1), 5)

        if neo4j_repository.is_available() and neo4j_service.is_connected():
            data = neo4j_repository.explore_node_multi_hop(
                start_id=target_id,
                max_hops=hops,
                limit=limit,
                allowed_types=allowed_types,
                excluded_types=excluded_types,
                rel_types=rel_types,
                direction=direction,
            )
            if not data:
                return error_response(
                    f"Node '{target_id}' not found in Neo4j Knowledge Graph",
                    error_code="NODE_NOT_FOUND",
                    status_code=404,
                )
            return success_response(
                data=data,
                message=f"Retrieved {data['metadata']['connected_count']} connected nodes ({data['metadata']['max_hops']} hops) and {data['metadata']['relationship_count']} relationships for '{target_id}' from Neo4j Aura",
            )

        # Fallback when Neo4j is offline (e.g. unit tests without live database connection)
        store = kg_instance.store
        if not store.has_node(target_id):
            return error_response(
                f"Node '{target_id}' not found in knowledge graph",
                error_code="NODE_NOT_FOUND",
                status_code=404,
            )

        node_obj = store.get_node(target_id)
        selected_node = {
            "id": target_id,
            "label": getattr(node_obj, "label", target_id),
            "name": getattr(node_obj, "name", target_id),
            "type": getattr(node_obj, "type", "KGNode"),
            "properties": getattr(node_obj, "properties", {}),
            "labels": [getattr(node_obj, "type", "KGNode")],
        }

        connected_nodes = []
        relationships = []
        for edge in store.get_all_edges():
            is_out = edge.source == target_id
            is_in = edge.target == target_id
            if is_out or is_in:
                other_id = edge.target if is_out else edge.source
                other_node = store.get_node(other_id)
                if other_node:
                    connected_nodes.append({
                        "id": other_id,
                        "label": getattr(other_node, "label", other_id),
                        "name": getattr(other_node, "name", other_id),
                        "type": getattr(other_node, "type", "KGNode"),
                        "properties": getattr(other_node, "properties", {}),
                        "labels": [getattr(other_node, "type", "KGNode")],
                    })
                relationships.append({
                    "id": f"{edge.source}_{edge.relation}_{edge.target}",
                    "source": edge.source,
                    "target": edge.target,
                    "type": edge.relation,
                    "relation": edge.relation,
                    "direction": "outgoing" if is_out else "incoming",
                    "confidence": getattr(edge, "confidence", 1.0),
                    "validation_level": getattr(edge, "validation_level", "corpus_validated"),
                    "metadata": getattr(edge, "properties", {}),
                })

        data = {
            "selected_node": selected_node,
            "connected_nodes": connected_nodes[:limit],
            "relationships": relationships[:limit],
            "nodes": [selected_node] + connected_nodes[:limit],
            "metadata": {
                "node_id": target_id,
                "connected_count": len(connected_nodes[:limit]),
                "relationship_count": len(relationships[:limit]),
                "source": "in_memory_kg_fallback",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        }
        return success_response(
            data=data,
            message=f"Retrieved {len(data['connected_nodes'])} connected nodes for '{target_id}'",
        )
    except Exception as e:
        logger.error(f"Error fetching connected elements for node '{node_id}': {e}", exc_info=True)
        return error_response(f"Failed to fetch connected node elements: {str(e)}", status_code=500)


@kg_bp.route("/query", methods=["POST", "GET"])
@kg_bp.route("/query-subgraph", methods=["POST", "GET"])
def get_query_subgraph_endpoint():
    """
    Dedicated endpoint for query-aware Knowledge Graph retrieval.
    Dynamically extracts a focused Neo4j subgraph matching user query / hybrid retrieval seeds.
    Accepts via POST (JSON) or GET (Query Params):
      query / q / queryText: string (query text)
      seed_ids: list of string node/passage/concept IDs (optional)
      passages: list of passage IDs or objects (optional)
      entities: list of entity terms or objects (optional)
      concepts: list of concept terms or objects (optional)
      events: list of event terms or objects (optional)
      rules: list of rule IDs (optional)
      hops / depth: integer (default: 2, range 1-5)
      relationship_types: list of relationship type strings (optional)
      limit: integer (default: 150)
      include_isolated: boolean (default: True)
    """
    try:
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            raw_query = body.get("query") or body.get("q") or body.get("queryText") or ""
            hops = int(body.get("hops") or body.get("depth") or body.get("hopDepth") or 2)
            limit = int(body.get("limit") or body.get("maxNodes") or 150)
            rel_types = body.get("relationship_types") or body.get("rel_types")
            include_isolated = body.get("include_isolated", True)
            query_input = body
        else:
            raw_query = request.args.get("query") or request.args.get("q") or request.args.get("queryText") or ""
            hops = int(request.args.get("hops") or request.args.get("depth") or 2)
            limit = int(request.args.get("limit") or 150)
            rel_types = request.args.getlist("relationship_types") or request.args.getlist("rel_types") or None
            include_isolated = request.args.get("include_isolated", "true").lower() in ("true", "1", "yes")
            query_input = {
                "query": raw_query,
                "hops": hops,
                "limit": limit,
            }

        data = graph_retrieval_service.retrieve_query_subgraph(
            query_input=query_input,
            max_hops=hops,
            limit=limit,
            rel_types=rel_types,
            include_isolated=include_isolated,
        )

        # Guarantee strict metadata schema: query, node_count, relationship_count, literary_sources, evidence_count
        if "metadata" not in data or not isinstance(data["metadata"], dict):
            data["metadata"] = {}
        data["metadata"]["query"] = str(raw_query or "")
        data["metadata"]["node_count"] = len(data.get("nodes", []))
        data["metadata"]["relationship_count"] = len(data.get("relationships", []))
        data["metadata"]["depth"] = data.get("depth", hops)
        if "literary_sources" not in data["metadata"]:
            data["metadata"]["literary_sources"] = data.get("literary_sources") or (["Tolkāppiyam (தொல்காப்பியம்)"] if data.get("nodes") else [])
        if "evidence_count" not in data["metadata"]:
            data["metadata"]["evidence_count"] = data.get("evidence_count", 0)

        resp_payload = {
            "success": True,
            "data": data,
            "nodes": data.get("nodes", []),
            "relationships": data.get("relationships", []),
            "metadata": data.get("metadata", {}),
            "message": f"Retrieved query-aware subgraph ({len(data.get('nodes', []))} nodes, {len(data.get('relationships', []))} relationships)",
            "error": None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "meta": {"depth": data.get("depth", hops), "source": data.get("source")},
        }
        return jsonify(resp_payload), 200
    except Exception as e:
        logger.error(f"Error extracting query-aware subgraph: {e}", exc_info=True)
        return error_response(f"Failed to extract query-aware subgraph: {str(e)}", status_code=500)


@kg_bp.route("/subgraph", methods=["POST", "GET"])
def get_subgraph():
    """
    Extracts a focused subgraph centered on seed node(s).
    Supports POST with JSON body and GET with query parameters.
    Seamlessly delegates to query-aware subgraph retrieval when query/entities/passages are provided.
    """
    try:
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            # If query context or multi-seed identifiers are provided, use query-aware retrieval
            if body.get("query") or body.get("passages") or body.get("entities") or body.get("concepts") or body.get("seed_ids"):
                hops = int(body.get("hops") or body.get("depth") or body.get("hopDepth") or 2)
                limit = int(body.get("limit") or body.get("maxNodes") or 150)
                rel_types = body.get("relationship_types") or body.get("rel_types")
                data = graph_retrieval_service.retrieve_query_subgraph(
                    query_input=body,
                    max_hops=hops,
                    limit=limit,
                    rel_types=rel_types,
                )
                return success_response(
                    data=data,
                    message=f"Retrieved query-aware subgraph for seeds (hops={hops})",
                )

            seed_ids = body.get("node_ids")
            if not seed_ids:
                center = body.get("center_id") or body.get("centerNode") or "mutalporul"
                seed_ids = [center]
            hops = int(body.get("hops", body.get("depth", 1)))
            layer_filter = body.get("layer") or body.get("layer_filter")
            hierarchy_filter = body.get("hierarchy") or body.get("hierarchy_filter")
            rel_types = body.get("relationship_types") or body.get("rel_types")
            limit = int(body.get("limit", 150))
        else:
            center = request.args.get("centerId") or request.args.get("entityId") or "mutalporul"
            seed_ids = [center]
            hops = int(request.args.get("depth") or request.args.get("hops") or 1)
            layer_filter = request.args.get("layer")
            hierarchy_filter = request.args.get("hierarchy")
            rel_types = None
            limit = int(request.args.get("limit", 150))

        if neo4j_repository.is_available() and neo4j_service.is_connected():
            data = neo4j_repository.expand_subgraph(
                node_ids=seed_ids,
                hops=hops,
                layer_filter=layer_filter,
                hierarchy_filter=hierarchy_filter,
                rel_types=rel_types,
                limit=limit,
            )
        else:
            data = query_engine.expand_subgraph(
                node_ids=seed_ids,
                hops=hops,
                layer_filter=layer_filter,
                hierarchy_filter=hierarchy_filter,
                rel_types=rel_types,
            )

        return success_response(
            data=data,
            message=f"Retrieved subgraph for seeds {seed_ids} (hops={hops})",
        )
    except Exception as e:
        logger.error(f"Error extracting subgraph: {e}", exc_info=True)
        return error_response(f"Failed to extract subgraph: {str(e)}", status_code=500)


@kg_bp.route("/path", methods=["GET"])
def find_paths():
    """
    Finds all multi-hop paths between source and target nodes with confidence propagation.
    Query parameters:
      source: string (required)
      target: string (required)
      depth: integer (optional, default: 1, max: 5)
    """
    source = request.args.get("source")
    target = request.args.get("target")
    depth = int(request.args.get("depth") or request.args.get("max_depth") or 1)
    depth = min(max(depth, 1), 5)

    if not source or not target:
        return error_response(
            "Both 'source' and 'target' query parameters are required",
            error_code="MISSING_PARAMETERS",
            status_code=400,
        )

    try:
        if neo4j_repository.is_available() and neo4j_service.is_connected():
            paths = neo4j_repository.find_paths(source_id=source, target_id=target, max_depth=depth)
            highest_confidence = paths[0]["propagated_confidence"] if paths else 0.0
            return success_response(
                data={
                    "source": source,
                    "target": target,
                    "max_depth": depth,
                    "total_paths": len(paths),
                    "highest_confidence": highest_confidence,
                    "paths": paths,
                    "source_engine": "neo4j_aura",
                },
                message=f"Found {len(paths)} path(s) between '{source}' and '{target}' in Neo4j Aura",
            )

        store = kg_instance.store
        if not store.has_node(source):
            return error_response(
                f"Source node '{source}' does not exist in knowledge graph",
                error_code="NODE_NOT_FOUND",
                status_code=404,
            )
        if not store.has_node(target):
            return error_response(
                f"Target node '{target}' does not exist in knowledge graph",
                error_code="NODE_NOT_FOUND",
                status_code=404,
            )

        paths = query_engine.find_paths(source_id=source, target_id=target, max_depth=depth)
        highest_confidence = paths[0]["propagated_confidence"] if paths else 0.0

        return success_response(
            data={
                "source": source,
                "target": target,
                "max_depth": depth,
                "total_paths": len(paths),
                "highest_confidence": highest_confidence,
                "paths": paths,
                "source_engine": "in_memory_kg",
            },
            message=f"Found {len(paths)} path(s) between '{source}' and '{target}'",
        )
    except Exception as e:
        logger.error(f"Error finding paths between '{source}' and '{target}': {e}", exc_info=True)
        return error_response(f"Failed to find paths: {str(e)}", status_code=500)


@kg_bp.route("/graph", methods=["GET"])
def get_full_graph():
    """
    Returns knowledge graph elements (nodes & relationships) for D3.js visualization.
    Supports source selection: 'neo4j' (default when Aura is connected) or 'inmemory'.
    Query params:
      source: 'neo4j' | 'inmemory' | 'auto' (default 'auto')
      limit: int (default 250)
      center_id: string (optional center node ID for neighborhood focus)
      hops: int (default 2)
      include_ontology: bool (default false)
      category: string (optional category filter)
    """
    try:
        source_param = (request.args.get("source") or "auto").lower()
        limit = int(request.args.get("limit", 250))
        center_id = request.args.get("center_id") or request.args.get("centerId")
        hops = int(request.args.get("hops", 2))
        include_ontology = request.args.get("include_ontology", "false").lower() in ("true", "1", "yes")
        category = request.args.get("category")

        # Use Neo4j if requested or auto-selected when connected
        use_neo4j = source_param == "neo4j" or (source_param == "auto" and neo4j_service.is_connected())

        if use_neo4j and neo4j_service.is_connected():
            data = neo4j_repository.get_graph_elements(
                limit=limit,
                center_id=center_id,
                hops=hops,
                include_ontology=include_ontology,
                category=category,
            )
            data["categories"] = TolkappiyamOntology.get_category_config()
            data["hierarchy_levels"] = TolkappiyamOntology.get_hierarchy_config()
            data["logical_layers"] = TolkappiyamOntology.get_layer_config()
            return success_response(
                data=data,
                message=f"Retrieved {data['total_nodes']} nodes and {data['total_edges']} relationships from Neo4j Aura",
            )
        else:
            # Fall back to canonical in-memory knowledge graph
            data = kg_instance.get_full_graph_data()
            data["source"] = "in_memory_kg"
            return success_response(data=data, message="Retrieved in-memory knowledge graph")
    except Exception as e:
        logger.error(f"Error exporting full graph: {e}", exc_info=True)
        return error_response(f"Failed to retrieve graph: {str(e)}", status_code=500)


@kg_bp.route("/neo4j/graph", methods=["GET"])
def get_neo4j_graph():
    """
    Dedicated endpoint returning Neo4j Aura nodes and relationships
    formatted with all properties, relationship types, and provenance metadata.
    """
    if not neo4j_service.is_connected():
        return error_response(
            "Neo4j Aura database is not connected",
            error_code="NEO4J_DISCONNECTED",
            status_code=503,
        )

    try:
        limit = int(request.args.get("limit", 250))
        center_id = request.args.get("center_id") or request.args.get("centerId")
        hops = int(request.args.get("hops", 2))
        include_ontology = request.args.get("include_ontology", "false").lower() in ("true", "1", "yes")
        category = request.args.get("category")

        data = neo4j_repository.get_graph_elements(
            limit=limit,
            center_id=center_id,
            hops=hops,
            include_ontology=include_ontology,
            category=category,
        )
        data["categories"] = TolkappiyamOntology.get_category_config()
        data["hierarchy_levels"] = TolkappiyamOntology.get_hierarchy_config()
        data["logical_layers"] = TolkappiyamOntology.get_layer_config()
        return success_response(
            data=data,
            message=f"Retrieved {data['total_nodes']} nodes and {data['total_edges']} relationships from Neo4j Aura",
        )
    except Exception as e:
        logger.error(f"Error querying Neo4j graph: {e}", exc_info=True)
        return error_response(f"Failed to retrieve Neo4j graph: {str(e)}", status_code=500)


@kg_bp.route("/neo4j/subgraph", methods=["POST", "GET"])
def get_neo4j_subgraph():
    """
    Extracts a focused subgraph from Neo4j Aura centered around a specific node.
    """
    if not neo4j_service.is_connected():
        return error_response(
            "Neo4j Aura database is not connected",
            error_code="NEO4J_DISCONNECTED",
            status_code=503,
        )

    try:
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            center_id = body.get("center_id") or body.get("node_id") or body.get("centerNode") or "mutalporul"
            hops = int(body.get("hops", body.get("depth", 2)))
            limit = int(body.get("limit", 150))
            include_ontology = bool(body.get("include_ontology", False))
            category = body.get("category")
        else:
            center_id = request.args.get("center_id") or request.args.get("node_id") or request.args.get("centerNode") or "mutalporul"
            hops = int(request.args.get("hops") or request.args.get("depth") or 2)
            limit = int(request.args.get("limit", 150))
            include_ontology = request.args.get("include_ontology", "false").lower() in ("true", "1", "yes")
            category = request.args.get("category")

        data = neo4j_repository.get_graph_elements(
            limit=limit,
            center_id=center_id,
            hops=hops,
            include_ontology=include_ontology,
            category=category,
        )
        data["center_id"] = center_id
        data["hops"] = hops
        data["categories"] = TolkappiyamOntology.get_category_config()
        return success_response(
            data=data,
            message=f"Retrieved Neo4j subgraph for '{center_id}' ({data['total_nodes']} nodes, {data['total_edges']} relationships)",
        )
    except Exception as e:
        logger.error(f"Error extracting Neo4j subgraph: {e}", exc_info=True)
        return error_response(f"Failed to extract Neo4j subgraph: {str(e)}", status_code=500)


@kg_bp.route("/health", methods=["GET"])
def get_kg_health():
    """Returns connectivity, density, and isolate checks on the graph directly from Neo4j Aura."""
    try:
        if neo4j_repository.is_available() and neo4j_service.is_connected():
            health = neo4j_repository.get_graph_health()
        else:
            health = KnowledgeGraphValidator.validate()
        return success_response(data=health, message="Knowledge Graph validation status")
    except Exception as e:
        logger.error(f"Error validating KG health: {e}", exc_info=True)
        return error_response(f"Failed to validate KG health: {str(e)}", status_code=500)


@kg_bp.route("/neo4j/validate", methods=["GET"])
def validate_neo4j_config():
    """Validates Neo4j environment configuration without exposing credentials."""
    from config import Neo4jConfig
    validation_data = Neo4jConfig.validate()
    status_code = 200 if validation_data["valid"] else 400
    return (
        success_response(data=validation_data, message="Neo4j configuration is valid")
        if validation_data["valid"]
        else error_response(
            message="Neo4j configuration has validation errors",
            error_code="INVALID_NEO4J_CONFIG",
            status_code=400,
            details=validation_data,
        )
    )


@kg_bp.route("/neo4j/health", methods=["GET"])
def get_neo4j_health():
    """Returns Neo4j Aura connectivity status, latency, and protocol information."""
    from services.neo4j_service import neo4j_service
    health_info = neo4j_service.health_check()
    status_code = 200 if health_info.get("connected") else 503
    return (
        success_response(data=health_info, message=f"Neo4j Aura status: {health_info['status']}")
        if health_info.get("connected")
        else error_response(
            message=health_info.get("error", "Neo4j Aura disconnected"),
            error_code="NEO4J_DISCONNECTED",
            status_code=503,
            details=health_info,
        )
    )


@kg_bp.route("/neo4j/sync", methods=["POST"])
def sync_to_neo4j():
    """Synchronizes local in-memory Knowledge Graph nodes and edges into Neo4j Aura."""
    from config import Neo4jConfig
    from services.neo4j_service import neo4j_service, sanitize_text
    from knowledge_graph.neo4j_store import Neo4jGraphStore

    conn = neo4j_service.verify_connectivity()
    if not conn.get("connected"):
        safe_msg = sanitize_text(conn.get('error', 'unknown error'), Neo4jConfig.PASSWORD)
        return error_response(
            f"Cannot sync: Neo4j Aura is not reachable ({safe_msg})",
            error_code="NEO4J_UNAVAILABLE",
            status_code=503,
        )

    try:
        neo4j_store = Neo4jGraphStore(neo4j_service)
        sync_result = neo4j_store.sync_from_store(kg_instance.store)
        return success_response(
            data=sync_result,
            message="Knowledge Graph synchronized into Neo4j Aura",
        )
    except Exception as e:
        safe_err = sanitize_text(str(e), Neo4jConfig.PASSWORD)
        logger.error(f"Error syncing to Neo4j Aura: {safe_err}", exc_info=True)
        return error_response(f"Neo4j sync failed: {safe_err}", status_code=500)


@kg_bp.route("/traverse", methods=["POST"])
def traverse_graph():
    """
    Dedicated multi-hop graph traversal endpoint.
    Accepts seed node(s) and configurable hop depth (1-5), returning grounded nodes,
    relationships, and traversal paths with provenance.
    """
    body = request.get_json(silent=True) or {}
    raw_seeds = body.get("seed_ids") or body.get("node_ids") or body.get("seeds")

    if not raw_seeds:
        center = body.get("center_id") or body.get("centerNode")
        if center:
            raw_seeds = [center]

    if not raw_seeds or not isinstance(raw_seeds, list):
        return error_response(
            message="Parameter 'seed_ids' must be a non-empty list of node identifiers",
            error_code="INVALID_SEED_NODES",
            status_code=400,
        )

    # Sanitize and limit seeds
    seed_ids = [str(s).strip() for s in raw_seeds if str(s).strip()][:20]
    if not seed_ids:
        return error_response(
            message="Parameter 'seed_ids' cannot be empty",
            error_code="INVALID_SEED_NODES",
            status_code=400,
        )

    try:
        depth = int(body.get("depth", body.get("hops", 2)))
        depth = min(max(depth, 1), 5)  # Enforce strict 1-5 hop limit
    except (ValueError, TypeError):
        depth = 2

    try:
        limit = int(body.get("limit", 100))
        limit = min(max(limit, 1), 300)
    except (ValueError, TypeError):
        limit = 100

    rel_types = body.get("relationship_types")
    if rel_types and isinstance(rel_types, list):
        rel_types = [str(r).strip() for r in rel_types]
    else:
        rel_types = None

    direction = body.get("direction", "both")
    if direction not in ["both", "out", "in"]:
        direction = "both"

    try:
        if neo4j_service.is_connected():
            paths = []
            node_map = {}
            rel_map = {}
            for sid in seed_ids[:5]:
                sid_paths = neo4j_repository.traverse_multi_hop(
                    start_id=sid,
                    max_hops=depth,
                    rel_types=rel_types,
                    direction=direction,
                )
                for p in sid_paths:
                    paths.append(p)
                    for n in p.get("nodes", []):
                        if isinstance(n, dict) and "id" in n:
                            node_map[n["id"]] = n
                    for r in p.get("relationships", []):
                        if isinstance(r, dict):
                            rid = r.get("id") or f"{r.get('source')}_{r.get('type')}_{r.get('target')}"
                            rel_map[rid] = r

            nodes = list(node_map.values())[:limit]
            relationships = list(rel_map.values())[:limit]
            source_engine = "neo4j_aura"

            # If no paths found in Neo4j for these seeds, fall back to in-memory store
            if not nodes:
                expanded = kg_instance.store.expand_subgraph(node_ids=seed_ids, hops=depth)
                nodes = expanded.get("nodes", [])[:limit]
                relationships = expanded.get("edges", [])[:limit]
                source_engine = "in_memory_kg_fallback"
        else:
            expanded = kg_instance.store.expand_subgraph(node_ids=seed_ids, hops=depth)
            nodes = expanded.get("nodes", [])[:limit]
            relationships = expanded.get("edges", [])[:limit]
            paths = []
            source_engine = "in_memory_kg"

        data = {
            "seed_ids": seed_ids,
            "depth": depth,
            "limit": limit,
            "source_engine": source_engine,
            "total_nodes": len(nodes),
            "total_relationships": len(relationships),
            "total_paths": len(paths),
            "nodes": nodes,
            "relationships": relationships,
            "paths": paths,
        }

        return success_response(
            data=data,
            message=f"Graph traversal completed across {depth} hops ({len(nodes)} nodes, {len(relationships)} relationships)",
            meta={"depth": depth, "seed_count": len(seed_ids), "source": source_engine},
        )
    except Exception as e:
        logger.error(f"Error during graph traversal: {e}", exc_info=True)
        return error_response(f"Graph traversal failed: {str(e)}", status_code=500)


# ==============================================================================
# Strict Neo4j Mutation & Synchronization Endpoints
# Pattern: Neo4j Mutation -> Confirmed DB Response -> Fresh Cypher Query -> Updated Subgraph
# ==============================================================================

def _execute_strict_mutation_flow(body: dict):
    """
    Core executor for strict Knowledge Graph synchronization with Neo4j Aura.
    Guarantees:
    1. Neo4j is checked for active connectivity first.
    2. The mutation is written to Neo4j Aura.
    3. Only upon successful Neo4j confirmation is a fresh Cypher query executed.
    4. Returns fresh updated subgraph directly from Neo4j.
    5. Never returns partial or unconfirmed optimistic state.
    """
    if not (neo4j_repository.is_available() and neo4j_service.is_connected()):
        return error_response(
            "Neo4j Aura is unreachable. Mutation aborted to maintain data integrity.",
            error_code="NEO4J_UNAVAILABLE",
            status_code=503,
        )

    action = body.get("action")
    query_text = body.get("query") or body.get("q") or ""
    hops = int(body.get("hops") or body.get("depth") or 2)
    limit = int(body.get("limit") or 150)
    seed_ids = []

    try:
        mutation_result = None

        if action == "upsert_entity" or "entity" in body or ("id" in body and "label" in body and "source_id" not in body):
            entity_data = body.get("entity") or body
            entity_id = entity_data.get("id") or entity_data.get("entity_id")
            label = entity_data.get("label") or entity_data.get("name")
            if not entity_id or not label:
                return error_response("Both 'id' and 'label' are required for entity upsert", error_code="INVALID_PAYLOAD", status_code=400)

            category = entity_data.get("category") or entity_data.get("type") or "Signifier"
            tinai = entity_data.get("tinai")
            properties = entity_data.get("properties") or {}
            metadata = entity_data.get("metadata") or {}
            source = entity_data.get("source", "Tolkāppiyam")
            confidence = float(entity_data.get("confidence", 1.0))

            # 1. Write mutation to Neo4j Aura
            mutation_result = neo4j_repository.upsert_entity(
                entity_id=entity_id,
                label=label,
                category=category,
                tinai=tinai,
                properties=properties,
                metadata=metadata,
                source=source,
                confidence=confidence,
            )
            seed_ids.append(entity_id)

        elif action == "upsert_relationship" or "relationship" in body or ("source_id" in body and "target_id" in body):
            rel_data = body.get("relationship") or body
            source_id = rel_data.get("source_id") or rel_data.get("source")
            target_id = rel_data.get("target_id") or rel_data.get("target")
            rel_type = rel_data.get("relation_type") or rel_data.get("relation") or rel_data.get("type") or "RELATED_TO"

            if not source_id or not target_id:
                return error_response("Both 'source_id' and 'target_id' are required for relationship upsert", error_code="INVALID_PAYLOAD", status_code=400)

            confidence = float(rel_data.get("confidence", 1.0))
            validation_level = rel_data.get("validation_level", "corpus_grounded")
            properties = rel_data.get("properties") or {}
            metadata = rel_data.get("metadata") or {}

            # 1. Write mutation to Neo4j Aura
            mutation_result = neo4j_repository.upsert_relationship(
                source_id=source_id,
                target_id=target_id,
                relation_type=rel_type,
                confidence=confidence,
                validation_level=validation_level,
                properties=properties,
                metadata=metadata,
            )
            seed_ids.extend([source_id, target_id])

        elif action == "upsert_concept":
            c_data = body.get("concept") or body
            c_id = c_data.get("id") or c_data.get("concept_id")
            label = c_data.get("label") or c_data.get("name")
            if not c_id or not label:
                return error_response("Both 'id' and 'label' are required for concept upsert", error_code="INVALID_PAYLOAD", status_code=400)

            mutation_result = neo4j_repository.upsert_concept(
                concept_id=c_id,
                label=label,
                category=c_data.get("category", "Concept"),
                tinai=c_data.get("tinai"),
                properties=c_data.get("properties"),
                metadata=c_data.get("metadata"),
                confidence=float(c_data.get("confidence", 1.0)),
            )
            seed_ids.append(c_id)

        elif action == "upsert_evidence":
            ev_data = body.get("evidence") or body
            ev_id = ev_data.get("id") or ev_data.get("evidence_id")
            text = ev_data.get("text") or ev_data.get("tamil_text") or ""
            if not ev_id:
                return error_response("'id' is required for evidence upsert", error_code="INVALID_PAYLOAD", status_code=400)

            mutation_result = neo4j_repository.upsert_evidence(
                evidence_id=ev_id,
                text=text,
                translation=ev_data.get("translation", ""),
                source_reference=ev_data.get("source_reference", ""),
                confidence=float(ev_data.get("confidence", 1.0)),
                properties=ev_data.get("properties"),
                metadata=ev_data.get("metadata"),
            )
            seed_ids.append(ev_id)

        else:
            return error_response(
                f"Unsupported or missing mutation action: '{action}'. Valid actions: upsert_entity, upsert_relationship, upsert_concept, upsert_evidence.",
                error_code="INVALID_ACTION",
                status_code=400,
            )

        # 2. Database confirmation verified
        if not mutation_result:
            return error_response(
                "Neo4j mutation returned empty confirmation. Operation may have failed.",
                error_code="NEO4J_MUTATION_UNCONFIRMED",
                status_code=500,
            )

        # 3. Fresh Neo4j Cypher query to retrieve updated relevant subgraph
        # Resolves either directly around mutated seeds or within active query context
        fresh_subgraph = graph_retrieval_service.retrieve_query_subgraph(
            query_input={
                "query": query_text,
                "seed_ids": [s for s in seed_ids if s],
                "hops": hops,
                "limit": limit,
            },
            max_hops=hops,
            limit=limit,
        )

        nodes = fresh_subgraph.get("nodes", [])
        relationships = fresh_subgraph.get("relationships", [])
        metadata = fresh_subgraph.get("metadata", {})
        metadata["mutated_seeds"] = seed_ids
        metadata["action"] = action

        # 4. Return updated authoritative graph state
        resp_payload = {
            "success": True,
            "data": {
                "mutation": mutation_result,
                "nodes": nodes,
                "relationships": relationships,
                "metadata": metadata,
            },
            "mutation": mutation_result,
            "nodes": nodes,
            "relationships": relationships,
            "metadata": metadata,
            "message": f"Successfully mutated Neo4j Aura and retrieved fresh subgraph ({len(nodes)} nodes, {len(relationships)} relationships)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return jsonify(resp_payload), 200

    except Exception as e:
        logger.error(f"Error executing Neo4j mutation: {e}", exc_info=True)
        return error_response(
            f"Neo4j mutation failed: {str(e)}. No changes were applied.",
            error_code="NEO4J_MUTATION_FAILED",
            status_code=500,
        )


@kg_bp.route("/mutate", methods=["POST"])
def mutate_kg():
    """
    Dedicated endpoint for strict Knowledge Graph mutations with immediate fresh Neo4j subgraph response.
    Payload:
      action: 'upsert_entity' | 'upsert_relationship' | 'upsert_concept' | 'upsert_evidence'
      entity / relationship / concept / evidence: object
      query: string (optional, active query context)
      hops: integer (optional, default: 2)
      limit: integer (optional, default: 150)
    """
    body = request.get_json(silent=True) or {}
    return _execute_strict_mutation_flow(body)


@kg_bp.route("/entity", methods=["POST"])
def mutate_entity():
    """Convenience route to upsert an entity and retrieve fresh Neo4j subgraph."""
    body = request.get_json(silent=True) or {}
    if "action" not in body:
        body["action"] = "upsert_entity"
    return _execute_strict_mutation_flow(body)


@kg_bp.route("/relationship", methods=["POST"])
def mutate_relationship():
    """Convenience route to upsert a relationship and retrieve fresh Neo4j subgraph."""
    body = request.get_json(silent=True) or {}
    if "action" not in body:
        body["action"] = "upsert_relationship"
    return _execute_strict_mutation_flow(body)


