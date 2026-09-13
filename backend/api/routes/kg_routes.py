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
from flask import Blueprint, request
from api.responses import success_response, error_response
from knowledge_graph.graph_builder import kg_instance
from knowledge_graph.graph_query import KnowledgeGraphQueryEngine
from knowledge_graph.graph_validator import KnowledgeGraphValidator
from knowledge_graph.ontology import TolkappiyamOntology
from core.logger import logger
from services.neo4j_service import neo4j_service
from knowledge_graph.neo4j_repository import neo4j_repository

kg_bp = Blueprint("kg", __name__, url_prefix="/api/kg")
query_engine = KnowledgeGraphQueryEngine()


@kg_bp.route("/statistics", methods=["GET"])
def get_kg_statistics():
    """Returns comprehensive graph metrics including L0-L5 hierarchy and 5-layer distributions."""
    try:
        health = KnowledgeGraphValidator.validate()
        store = kg_instance.store

        # Compute relation distribution
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
        }
        return success_response(data=data, message="Knowledge Graph statistics retrieved")
    except Exception as e:
        logger.error(f"Error computing KG statistics: {e}", exc_info=True)
        return error_response(f"Failed to retrieve KG statistics: {str(e)}", status_code=500)


@kg_bp.route("/entity/<string:entity_id>", methods=["GET"])
def get_entity_detail(entity_id: str):
    """Retrieves an entity's complete schema, hierarchy level, logical layer, and direct neighbors."""
    try:
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


@kg_bp.route("/subgraph", methods=["POST", "GET"])
def get_subgraph():
    """
    Extracts a focused subgraph centered on seed node(s).
    Supports POST with JSON body and GET with query parameters.
    """
    try:
        if request.method == "POST":
            body = request.get_json(silent=True) or {}
            seed_ids = body.get("node_ids")
            if not seed_ids:
                center = body.get("center_id") or body.get("centerNode") or "mutalporul"
                seed_ids = [center]
            hops = int(body.get("hops", body.get("depth", 1)))
            layer_filter = body.get("layer") or body.get("layer_filter")
            hierarchy_filter = body.get("hierarchy") or body.get("hierarchy_filter")
        else:
            center = request.args.get("centerId") or request.args.get("entityId") or "mutalporul"
            seed_ids = [center]
            hops = int(request.args.get("depth") or request.args.get("hops") or 1)
            layer_filter = request.args.get("layer")
            hierarchy_filter = request.args.get("hierarchy")

        data = query_engine.expand_subgraph(
            node_ids=seed_ids,
            hops=hops,
            layer_filter=layer_filter,
            hierarchy_filter=hierarchy_filter,
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

    try:
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
            },
            message=f"Found {len(paths)} path(s) between '{source}' and '{target}'",
        )
    except Exception as e:
        logger.error(f"Error finding paths between '{source}' and '{target}': {e}", exc_info=True)
        return error_response(f"Failed to find paths: {str(e)}", status_code=500)


@kg_bp.route("/graph", methods=["GET"])
def get_full_graph():
    """
    Returns knowledge graph elements (nodes & relationships) for Cytoscape visualization.
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
    """Returns connectivity, density, and isolate checks on the graph."""
    try:
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

