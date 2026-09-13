"""
Swagger UI and OpenAPI 3.0 interactive testing documentation route.
Exposes:
- GET /docs (Interactive Swagger UI testing console)
- GET /docs/
- GET /docs/openapi.json
- GET /docs/swagger.json
"""
from flask import Blueprint, jsonify, render_template_string

docs_bp = Blueprint("docs", __name__, url_prefix="/docs")

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Nyāya-Inspired Neuro-Symbolic Reasoner for Classical Tamil Literary Knowledge",
        "description": (
            "Interactive REST API testing console for Classical Tamil epistemology, "
            "*Tolkāppiyam* ontology retrieval, Knowledge Graph traversal, 5-stage "
            "Pañcāvayava deduction, and epistemic dataset validation."
        ),
        "version": "2.4.0",
        "contact": {
            "name": "Classical Tamil NLP & Epistemic Reasoning Lab",
            "url": "https://github.com/example/summer-intern",
        },
        "license": {
            "name": "Academic Research & Educational Use",
        },
    },
    "servers": [
        {
            "url": "http://127.0.0.1:5000",
            "description": "Local Development Server",
        },
        {
            "url": "http://localhost:5000",
            "description": "Localhost Alias",
        },
    ],
    "tags": [
        {
            "name": "System & Health",
            "description": "Readiness, runtime environment, and corpus status",
        },
        {
            "name": "Epistemic Query Analysis",
            "description": "Classical Tamil query parsing, Tiṇai detection, and neuro-symbolic reasoning",
        },
        {
            "name": "Corpus & Datasets",
            "description": "Sūtras, Atikāram breakdown, dataset profiling, and schema validation",
        },
        {
            "name": "Knowledge Graph",
            "description": "NetworkX ontology graph, k-hop subgraphs, and topological health",
        },
        {
            "name": "Nyāya Reasoning Engine",
            "description": "5-stage Pañcāvayava syllogism and Hetvābhāsa fallacy validator",
        },
        {
            "name": "Analytics & Benchmarks",
            "description": "Inference latency benchmarks, Pramāṇa distribution, and system telemetry",
        },
        {
            "name": "Semantic Knowledge Extraction",
            "description": "Extensible knowledge extraction: entities, controlled relations, structured events, and discourse context",
        },
        {
            "name": "RAG Retrieval Infrastructure",
            "description": "Source-traceable RAG retrieval using FAISS vector search, SentenceTransformers embeddings, and BM25 lexical search",
        },
    ],
    "paths": {
        "/api/health": {
            "get": {
                "tags": ["System & Health"],
                "summary": "System Health & Engine Status",
                "description": "Returns operational status, loaded corpus metadata, and active reasoning engine components.",
                "responses": {
                    "200": {
                        "description": "Backend service is fully operational",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "data": {
                                        "status": "HEALTHY",
                                        "service": "Nyāya-Inspired Neuro-Symbolic Reasoner for Classical Tamil Literary Knowledge",
                                        "version": "2.4.0",
                                        "corpus": "Tolkāppiyam",
                                        "indexed_sutras": 1610,
                                        "total_sutras": 1610,
                                        "knowledge_graph": "Active (NetworkX)",
                                        "reasoning_engine": "Pañcāvayava Syllogism (5-Stage Nyāya)",
                                        "validation_engine": "Hetvābhāsa Defeasible Logic",
                                        "neo4j": {
                                            "connected": True,
                                            "connection_status": "connected",
                                            "database_status": "online",
                                            "database": "neo4j",
                                            "message": "Neo4j Aura database is healthy, reachable, and operational.",
                                        },
                                    },
                                    "message": "Backend service is fully operational",
                                }
                            }
                        },
                    }
                },
            }
        },
        "/api/health/neo4j": {
            "get": {
                "tags": ["System & Health"],
                "summary": "Dedicated Neo4j Connectivity Health Check",
                "description": "Verifies that the backend can successfully communicate with the configured Neo4j Aura database. Returns connection status, database status, round-trip latency, and a safe human-readable message without exposing credentials or internal stack traces.",
                "responses": {
                    "200": {
                        "description": "Neo4j Aura database is connected and operational",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "connection_status": "connected",
                                    "database_status": "online",
                                    "message": "Neo4j Aura database is healthy, reachable, and operational.",
                                    "database": "neo4j",
                                    "latency_ms": 12.45,
                                    "server_agent": "Neo4j/5.27-aura",
                                    "protocol_version": "6.1",
                                }
                            }
                        },
                    },
                    "503": {
                        "description": "Neo4j Aura database is disconnected, unreachable, timed out, or unauthenticated",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": False,
                                    "connection_status": "disconnected",
                                    "database_status": "unreachable",
                                    "message": "Neo4j database is currently unreachable or paused.",
                                    "database": "neo4j",
                                    "latency_ms": None,
                                    "server_agent": None,
                                    "protocol_version": None,
                                }
                            }
                        },
                    },
                },
            }
        },
        "/api/query/analyze": {
            "post": {
                "tags": ["Epistemic Query Analysis"],
                "summary": "Execute End-to-End Neuro-Symbolic Query Analysis",
                "description": (
                    "Analyzes a Classical Tamil inquiry across language detection, Tiṇai classification, "
                    "hybrid retrieval (BM25 + Dense TF-IDF + KG), 5-stage Pañcāvayava deduction, "
                    "Hetvābhāsa fallacy validation, and dual-language synthesis."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["queryText"],
                                "properties": {
                                    "queryText": {
                                        "type": "string",
                                        "example": "குறிஞ்சி நிலத்தின் முதற்பொருள், கருப்பொருள், உரிப்பொருள் தொடர்பு எவ்வாறு அக ஒழுக்கத்தை உணர்த்துகிறது?",
                                        "description": "Classical Tamil research question or inquiry",
                                    },
                                    "depth": {
                                        "type": "integer",
                                        "default": 3,
                                        "minimum": 1,
                                        "maximum": 5,
                                        "description": "Subgraph expansion depth (1 to 5 hops)",
                                    },
                                    "focus": {
                                        "type": "string",
                                        "default": "Relationship",
                                        "example": "Relationship",
                                        "description": "Analysis focus area (e.g. Relationship, Grounding, Deity)",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Complete epistemic reasoning analysis result",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "data": {
                                        "queryId": "QRY-2026-091101",
                                        "detectedTinai": "Kuṟiñci",
                                        "landscape": "Puṇartalum Puṇartal Nimittamum",
                                        "epistemicConfidence": 0.96,
                                        "evidenceRecords": [
                                            {
                                                "id": "E1",
                                                "sutraId": "TK-PORUL-005",
                                                "tinai": "Kuṟiñci",
                                                "tamilText": "மாயோன் மேய காடுறை உலகமும் சேயோன் மேய மைவரை உலகமும்...",
                                                "score": 0.942,
                                            }
                                        ],
                                        "reasoningStages": [
                                            {"stage": "Pratijñā", "tamilTerm": "மேற்கோள் (Thesis)", "statement": "Kuṟiñci grounds clandestine union"},
                                            {"stage": "Hetu", "tamilTerm": "ஏது (Epistemic Reason)", "statement": "Due to isolated mountain habitat"},
                                            {"stage": "Udāharaṇa", "tamilTerm": "எடுத்துக்காட்டு (Universal Rule & Exemplar)", "statement": "Whenever mountainous ecology exists, clandestine union occurs"},
                                            {"stage": "Upanaya", "tamilTerm": "உபநயம் (Application)", "statement": "Kuṟiñci exemplifies this ecological co-presence"},
                                            {"stage": "Nigamana", "tamilTerm": "நிகமணம் (Conclusion)", "statement": "Therefore, Kuṟiñci validly grounds clandestine union"}
                                        ],
                                        "proofNodes": [
                                            {"id": "E1", "label": "Evidence E1", "type": "evidence"},
                                            {"id": "P1", "label": "Premise P1", "type": "premise"},
                                            {"id": "C1", "label": "Conclusion C1", "type": "conclusion"}
                                        ],
                                        "validationResults": {
                                            "soundnessScore": 0.96,
                                            "hetvabhasaPassed": True,
                                            "fallacyCount": 0,
                                        },
                                        "finalAnswer": {
                                            "tamilAnswer": "குறிஞ்சித் திணை புணர்தல் ஒழுக்கத்தை நிலவியலோடு பிணைக்கிறது.",
                                            "englishAnswer": "Kuṟiñci landscape canonically grounds clandestine love in mountain seclusion.",
                                        },
                                    },
                                    "message": "Neuro-symbolic analysis completed successfully",
                                }
                            }
                        },
                    },
                    "422": {
                        "description": "Validation Error (e.g., empty query string)",
                    },
                },
            }
        },
        "/api/query/examples": {
            "get": {
                "tags": ["Epistemic Query Analysis"],
                "summary": "List Canonical Research Query Examples",
                "description": "Returns pre-curated Classical Tamil scholarly inquiries with pre-configured parameters.",
                "responses": {
                    "200": {
                        "description": "List of curated query examples",
                    }
                },
            }
        },
        "/api/corpus/info": {
            "get": {
                "tags": ["Corpus & Datasets"],
                "summary": "Corpus Overview & Sūtra Counts",
                "description": "Returns total sūtra count, chapter breakdown across 3 canonical books (Eḻuttu, Col, Poruḷ), and Tiṇai distributions.",
                "responses": {
                    "200": {
                        "description": "Corpus metadata and Atikāram breakdown",
                    }
                },
            }
        },
        "/api/corpus/statistics": {
            "get": {
                "tags": ["Corpus & Datasets"],
                "summary": "Dataset Ingestion & Profiling Statistics",
                "description": (
                    "Returns comprehensive column profiling, null value distributions, uniqueness metrics, "
                    "Tamil Unicode character counts, and referential integrity between Ontology and Query_Mapping."
                ),
                "responses": {
                    "200": {
                        "description": "Dataset profiling statistics and version metadata",
                    }
                },
            }
        },
        "/api/corpus/validate": {
            "post": {
                "tags": ["Corpus & Datasets"],
                "summary": "Validate Ingested Datasets",
                "description": "Performs explicit schema and data validation on Ontology, Query_Mapping, or both datasets.",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "dataset_name": {
                                        "type": "string",
                                        "enum": ["all", "ontology", "query_mapping"],
                                        "default": "all",
                                        "description": "Dataset to validate",
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Validation results matching required schema contract",
                        "content": {
                            "application/json": {
                                "example": {
                                    "success": True,
                                    "data": [
                                        {
                                            "dataset_name": "ontology",
                                            "rows": 1000,
                                            "columns": ["ID", "Main Theme", "English_Label", "Tamil_Label"],
                                            "missing_values": {"Synonyms_Tamil": 66, "Parent_Concept": 3},
                                            "duplicates": 0,
                                            "validation_status": "valid",
                                        }
                                    ],
                                    "message": "Dataset validation completed (all)",
                                }
                            }
                        },
                    },
                    "400": {
                        "description": "Invalid dataset name specified",
                    },
                },
            }
        },
        "/api/corpus/sutras": {
            "get": {
                "tags": ["Corpus & Datasets"],
                "summary": "List Sūtras with Filters",
                "description": "Retrieves sūtras with optional filtering by Tiṇai or Atikāram chapter.",
                "parameters": [
                    {
                        "name": "tinai",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "enum": ["All", "Kuṟiñci", "Mullai", "Marutam", "Neytal", "Pālai"],
                            "default": "All",
                        },
                        "description": "Filter by Classical Tiṇai landscape",
                    },
                    {
                        "name": "atikaram",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                        },
                        "description": "Filter by Atikāram chapter name (e.g. 'Akattiṇai Iyal')",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Filtered array of canonical sūtras",
                    }
                },
            }
        },
        "/api/corpus/sutras/{sutra_id}": {
            "get": {
                "tags": ["Corpus & Datasets"],
                "summary": "Get Single Sūtra by ID",
                "description": "Retrieves full sūtra text, translation, commentary, and extracted ontological triples.",
                "parameters": [
                    {
                        "name": "sutra_id",
                        "in": "path",
                        "required": True,
                        "schema": {
                            "type": "string",
                            "example": "TK-PORUL-001",
                        },
                        "description": "Canonical sūtra identifier",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Sūtra details and triples",
                    },
                    "404": {
                        "description": "Sūtra ID not found",
                    },
                },
            }
        },
        "/api/kg/graph": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Get Full Ontological Knowledge Graph",
                "description": "Returns full NetworkX graph nodes with pre-computed 2D SVG canvas layout coordinates, categories, and typed edges.",
                "responses": {
                    "200": {
                        "description": "Complete Knowledge Graph with layout coordinates",
                    }
                },
            }
        },
        "/api/kg/subgraph": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Extract k-Hop Focused Subgraph",
                "description": "Extracts topological neighborhood around a focal concept up to specified hop depth.",
                "parameters": [
                    {
                        "name": "center",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "string",
                            "default": "Tolkāppiyam",
                            "example": "Kuṟiñci",
                        },
                        "description": "Root focal node identifier or label",
                    },
                    {
                        "name": "depth",
                        "in": "query",
                        "required": False,
                        "schema": {
                            "type": "integer",
                            "default": 2,
                            "minimum": 1,
                            "maximum": 5,
                        },
                        "description": "k-hop neighborhood distance",
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Focused subgraph nodes and edges",
                    }
                },
            }
        },
        "/api/kg/health": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Knowledge Graph Topological Health",
                "description": "Returns NetworkX graph metrics including connectivity, density, node/edge counts, and isolate checks.",
                "responses": {
                    "200": {
                        "description": "Knowledge Graph health metrics",
                    }
                },
            }
        },
        "/api/kg/statistics": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Hierarchical Knowledge Graph Statistics",
                "description": "Returns detailed metrics across 6 hierarchy levels (L0-L5), 5 logical layers, relation distributions, density, and connectivity.",
                "responses": {
                    "200": {
                        "description": "Comprehensive graph hierarchy and layer statistics",
                    }
                },
            }
        },
        "/api/kg/entity/{entity_id}": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Get Entity Details and Neighbors",
                "description": "Retrieves an entity's complete schema, hierarchy level (L0-L5), logical layer, direct neighbors, and source evidence.",
                "parameters": [
                    {
                        "name": "entity_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "example": "ceyon"},
                        "description": "Unique identifier of the entity or concept",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Entity details with neighbors and evidence",
                    },
                    "404": {
                        "description": "Entity not found",
                    }
                },
            }
        },
        "/api/kg/path": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Find Multi-Hop Paths with Confidence Propagation",
                "description": "Finds all paths between source and target entities up to depth with propagated Bayesian path confidence.",
                "parameters": [
                    {
                        "name": "source",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "example": "ceyon"},
                        "description": "Starting node identifier",
                    },
                    {
                        "name": "target",
                        "in": "query",
                        "required": True,
                        "schema": {"type": "string", "example": "uriporul"},
                        "description": "Destination node identifier",
                    },
                    {
                        "name": "depth",
                        "in": "query",
                        "required": False,
                        "schema": {"type": "integer", "default": 3, "minimum": 1, "maximum": 5},
                        "description": "Maximum path search depth",
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Paths found with propagated confidence scores",
                    },
                    "400": {
                        "description": "Missing parameters",
                    },
                    "404": {
                        "description": "Source or target node not found",
                    }
                },
            }
        },
        "/api/kg/neo4j/validate": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Validate Neo4j Environment Configuration",
                "description": "Validates Neo4j environment configuration, URI schemes, and connection pool settings without exposing sensitive credentials.",
                "responses": {
                    "200": {"description": "Neo4j configuration is valid and ready"},
                    "400": {"description": "Neo4j configuration has missing or invalid parameters"}
                }
            }
        },
        "/api/kg/neo4j/health": {
            "get": {
                "tags": ["Knowledge Graph"],
                "summary": "Check Neo4j Aura Connectivity & Health",
                "description": "Returns Neo4j Aura cloud database connectivity status, round-trip latency, server agent version, and protocol information.",
                "responses": {
                    "200": {"description": "Neo4j Aura instance is healthy and connected"},
                    "503": {"description": "Neo4j Aura is unreachable or authentication failed"}
                }
            }
        },
        "/api/kg/neo4j/sync": {
            "post": {
                "tags": ["Knowledge Graph"],
                "summary": "Synchronize Local KG into Neo4j Aura",
                "description": "Synchronizes all local Knowledge Graph nodes and relationships into the Neo4j Aura cloud database.",
                "responses": {
                    "200": {"description": "Synchronization completed successfully"},
                    "503": {"description": "Neo4j Aura service is not available"}
                }
            }
        },
        "/api/reasoning/deduce": {
            "post": {
                "tags": ["Nyāya Reasoning Engine"],
                "summary": "Execute 5-Stage Pañcāvayava Deduction",
                "description": "Generates a structured Nyāya deduction sequence (Pratijñā, Hetu, Udāharaṇa, Upanaya, Nigamana) from given locus and thesis.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["locus", "thesis"],
                                "properties": {
                                    "locus": {
                                        "type": "string",
                                        "example": "Kuṟiñci",
                                        "description": "Pakṣa (Locus/Subject)",
                                    },
                                    "thesis": {
                                        "type": "string",
                                        "example": "Clandestine love (Puṇartal) is epistemically grounded in mountainous topography",
                                        "description": "Sādhya (Property to be proven)",
                                    },
                                    "grounds": {
                                        "type": "string",
                                        "example": "Mountain ecology creates ecological isolation conducive to courtship",
                                        "description": "Optional explicit Hetu (Reason)",
                                    },
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "5-stage Pañcāvayava deduction sequence",
                    }
                },
            }
        },
        "/api/reasoning/validate-fallacies": {
            "post": {
                "tags": ["Nyāya Reasoning Engine"],
                "summary": "Check Hetvābhāsa Fallacies",
                "description": (
                    "Validates deduction stages against 5 classical Nyāya fallacies: "
                    "Savyabhicāra (Erratic), Viruddha (Contradictory), Satpratipakṣa (Counterbalanced), "
                    "Asiddha (Unproven), and Bādhita (Incongruous)."
                ),
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "stages": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "stage": {"type": "string", "example": "Pratijñā"},
                                                "content": {"type": "string", "example": "Kuṟiñci grounds clandestine union"},
                                            },
                                        },
                                    }
                                },
                            }
                        }
                    },
                },
                "responses": {
                    "200": {
                        "description": "Hetvābhāsa validation report and soundness score",
                    }
                },
            }
        },
        "/api/analytics/benchmark": {
            "get": {
                "tags": ["Analytics & Benchmarks"],
                "summary": "Performance Benchmarks & Latency Breakdown",
                "description": "Returns component-level execution latencies (Query Decomposer, Hybrid Retriever, Graph Engine, Nyāya Reasoner, Fallacy Validator).",
                "responses": {
                    "200": {
                        "description": "Latency breakdown and benchmark metrics",
                    }
                },
            }
        },
        "/api/analytics/metrics": {
            "get": {
                "tags": ["Analytics & Benchmarks"],
                "summary": "System Telemetry & Epistemic KPIs",
                "description": "Returns overall query throughput, Pramāṇa distribution (Pratyakṣa, Anumāna, Śabda, Upamāna), and cache hit ratios.",
                "responses": {
                    "200": {
                        "description": "System telemetry metrics",
                    }
                },
            }
        },
        "/api/corpus/preprocess": {
            "post": {
                "tags": ["Corpus & Datasets"],
                "summary": "Preprocess Classical Tamil Corpus",
                "description": "Transforms raw literary sūtras into traceable ProcessedPassage structures with NFC normalization, sentence/verse/passage segmentation, and lemmatization.",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "sutra_id": {
                                        "type": "string",
                                        "example": "tol-porul-akam-005",
                                        "description": "Optional single sūtra identifier",
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Corpus preprocessing statistics or single ProcessedPassage",
                    }
                }
            }
        },
        "/api/extraction/extract": {
            "post": {
                "tags": ["Semantic Knowledge Extraction"],
                "summary": "Extract Structured Knowledge from Sūtra or Text",
                "description": "Extracts typed entities (PERSON, PLACE, OBJECT, EVENT, CONCEPT, INSTITUTION, LITERARY_CONCEPT, ETHICAL_CONCEPT), controlled relations, structured events, and discourse context.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "sutra_id": {
                                        "type": "string",
                                        "example": "tol-porul-akam-005",
                                        "description": "Canonical sūtra identifier to load and extract",
                                    },
                                    "text": {
                                        "type": "string",
                                        "example": "சேயோன் மேய மைவரை உலகமும்",
                                        "description": "Direct Classical Tamil text to extract from",
                                    },
                                    "tinai": {
                                        "type": "string",
                                        "example": "Kuṟiñci",
                                        "description": "Optional Tiṇai context",
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Extracted knowledge entities, relations, events, and provenance",
                    }
                }
            }
        },
        "/api/extraction/batch": {
            "post": {
                "tags": ["Semantic Knowledge Extraction"],
                "summary": "Batch Extract Knowledge from Entire Corpus",
                "description": "Executes semantic extraction pipeline across canonical sūtras with aggregation of entities, controlled relations, and events.",
                "requestBody": {
                    "required": False,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "sutra_ids": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "example": ["tol-porul-akam-003", "tol-porul-akam-005"],
                                        "description": "Optional subset of sūtra identifiers",
                                    }
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Batch extraction results and summary statistics",
                    }
                }
            }
        },
        "/api/extraction/relation-types": {
            "get": {
                "tags": ["Semantic Knowledge Extraction"],
                "summary": "List Controlled Relation Vocabulary",
                "description": "Returns the controlled relation vocabulary supported by the extractor (e.g., accused_of, judged, presides_over, grounds_in, etc.).",
                "responses": {
                    "200": {
                        "description": "List of controlled relation types with descriptions",
                    }
                }
            }
        },
        "/api/extraction/entity-categories": {
            "get": {
                "tags": ["Semantic Knowledge Extraction"],
                "summary": "List Supported Entity Categories",
                "description": "Returns all 8 supported entity categories (PERSON, PLACE, OBJECT, EVENT, CONCEPT, INSTITUTION, LITERARY_CONCEPT, ETHICAL_CONCEPT).",
                "responses": {
                    "200": {
                        "description": "List of entity categories with definitions",
                    }
                }
            }
        },
        "/api/retrieval/semantic": {
            "post": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Semantic Vector Search via FAISS",
                "description": "Executes dense semantic vector similarity retrieval using FAISS IndexFlatIP and SentenceTransformers embeddings with cosine similarity.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {"type": "string", "example": "குறிஞ்சி நிலத்தின் தெய்வம்"},
                                    "top_k": {"type": "integer", "default": 5}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Retrieved chunks with cosine similarity and full source citation"}
                }
            }
        },
        "/api/retrieval/bm25": {
            "post": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Lexical Keyword Search via BM25Okapi",
                "description": "Executes keyword search over tokenized literary chunks with normalized BM25 scores.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {"type": "string", "example": "சேயோன் மைவரை"},
                                    "top_k": {"type": "integer", "default": 5}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Retrieved chunks with BM25 scores and source citation"}
                }
            }
        },
        "/api/retrieval/hybrid": {
            "post": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Hybrid Dense + Lexical Search (RRF)",
                "description": "Fuses FAISS dense semantic relevance with BM25 lexical scores using Reciprocal Rank Fusion.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["query"],
                                "properties": {
                                    "query": {"type": "string", "example": "மாயோன் மேய காடுறை"},
                                    "top_k": {"type": "integer", "default": 5},
                                    "semantic_weight": {"type": "number", "default": 0.6},
                                    "bm25_weight": {"type": "number", "default": 0.4}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Fused ranked chunks with full source traceability"}
                }
            }
        },
        "/api/retrieval/by-source/{source_id}": {
            "get": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Retrieve Evidence by Source ID",
                "description": "Retrieves all chunks originating from a specific canonical sūtra or document ID.",
                "parameters": [
                    {
                        "name": "source_id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "example": "tol-porul-akam-005"},
                        "description": "Document or Sūtra identifier"
                    }
                ],
                "responses": {
                    "200": {"description": "List of evidence chunks originating from source"},
                    "404": {"description": "Source not found"}
                }
            }
        },
        "/api/retrieval/by-entity/{entity}": {
            "get": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Retrieve Evidence by Entity",
                "description": "Retrieves all chunks referencing or associated with an entity.",
                "parameters": [
                    {
                        "name": "entity",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string", "example": "Cēyōṉ"},
                        "description": "Entity name (Tamil or transliteration)"
                    }
                ],
                "responses": {
                    "200": {"description": "List of evidence chunks matching entity"}
                }
            }
        },
        "/api/retrieval/statistics": {
            "get": {
                "tags": ["RAG Retrieval Infrastructure"],
                "summary": "Get Retrieval Engine Statistics",
                "description": "Returns chunk count, vector dimension, FAISS index size, and embedding model status.",
                "responses": {
                    "200": {"description": "RAG retrieval diagnostics and metrics"}
                }
            }
        },
    },
}

SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Swagger UI - Nyāya Epistemic Reasoner API</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
  <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5/favicon-32x32.png" sizes="32x32" />
  <link rel="icon" type="image/png" href="https://unpkg.com/swagger-ui-dist@5/favicon-16x16.png" sizes="16x16" />
  <style>
    html {
      box-sizing: border-box;
      overflow: -moz-scrollbars-vertical;
      overflow-y: scroll;
    }
    *, *:before, *:after {
      box-sizing: inherit;
    }
    body {
      margin: 0;
      background: #fafafa;
    }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>

  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js" charset="UTF-8"></script>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-standalone-preset.js" charset="UTF-8"></script>
  <script>
    window.onload = function() {
      const ui = SwaggerUIBundle({
        url: "/docs/openapi.json",
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIStandalonePreset
        ],
        plugins: [
          SwaggerUIBundle.plugins.DownloadUrl
        ],
        layout: "StandaloneLayout",
        defaultModelsExpandDepth: 1,
        defaultModelExpandDepth: 1,
        docExpansion: "list",
        filter: true,
        showExtensions: true,
        showCommonExtensions: true,
        tryItOutEnabled: true
      });
      window.ui = ui;
    };
  </script>
</body>
</html>
"""


@docs_bp.route("", methods=["GET"])
@docs_bp.route("/", methods=["GET"])
def swagger_ui():
    """Renders interactive Swagger UI testing console."""
    return render_template_string(SWAGGER_UI_HTML)


@docs_bp.route("/openapi.json", methods=["GET"])
@docs_bp.route("/swagger.json", methods=["GET"])
def get_openapi_spec():
    """Returns OpenAPI 3.0 JSON specification."""
    return jsonify(OPENAPI_SPEC)
