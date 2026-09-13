"""Retrieval package implementing FAISS, SentenceTransformers, Rank-BM25, and RAG retrieval."""
from .chunker import RetrievalChunk, PassageChunker
from .embeddings import (
    EmbeddingGenerator,
    DenseNgramEmbeddingGenerator,
    SentenceTransformerEmbeddingGenerator,
    cosine_similarity,
)
from .faiss_index import FAISSVectorIndex
from .bm25 import BM25Retriever
from .lexical_search import (
    LexicalSearchEngine,
    PassageDocument,
    LexicalSearchResult,
    lexical_search_engine,
)
from .semantic_search import (
    SemanticSearchEngine,
    SemanticPassageDocument,
    SemanticSearchResult,
    semantic_search_engine,
)
from .hybrid_search import (
    HybridSearchService,
    HybridSearchResult,
    hybrid_search_service,
)
from .vector_store import VectorStore
from .graph_retriever import GraphRetriever
from .hybrid_retriever import HybridRetriever
from .ranker import (
    EvidenceRanker,
    EvidenceRankingEngine,
    evidence_ranking_engine,
    EvidenceScoreComponents,
    EvidenceRankingExplanation,
    RankedEvidenceItem,
    EvidenceRankerConfig,
)
from .reranker import (
    PassageReranker,
    RerankedPassage,
    RerankScoreComponents,
    RerankExplanation,
    RerankerConfig,
    passage_reranker,
)
from .graph_hybrid_search import (
    GraphContext,
    GraphProvenanceStep,
    GraphAugmentedPassageResult,
    GraphHybridSearchService,
    graph_hybrid_search_service,
)
from .passage_embedding_pipeline import (
    PassageEmbeddingPipeline,
    passage_embedding_pipeline,
    PipelineReport,
    ValidatedPassage,
    SkippedPassage,
)
from .rag_service import RAGRetrievalEngine, rag_engine
from .hybrid_rag_pipeline import (
    HybridRAGPipeline,
    EvidenceItem,
    EvidenceCollection,
    hybrid_rag_pipeline,
)

__all__ = [
    "RetrievalChunk",
    "PassageChunker",
    "EmbeddingGenerator",
    "DenseNgramEmbeddingGenerator",
    "SentenceTransformerEmbeddingGenerator",
    "cosine_similarity",
    "FAISSVectorIndex",
    "BM25Retriever",
    "LexicalSearchEngine",
    "PassageDocument",
    "LexicalSearchResult",
    "lexical_search_engine",
    "SemanticSearchEngine",
    "SemanticPassageDocument",
    "SemanticSearchResult",
    "semantic_search_engine",
    "HybridSearchService",
    "HybridSearchResult",
    "hybrid_search_service",
    "PassageReranker",
    "RerankedPassage",
    "RerankScoreComponents",
    "RerankExplanation",
    "RerankerConfig",
    "passage_reranker",
    "GraphContext",
    "GraphProvenanceStep",
    "GraphAugmentedPassageResult",
    "GraphHybridSearchService",
    "graph_hybrid_search_service",
    "PassageEmbeddingPipeline",
    "passage_embedding_pipeline",
    "PipelineReport",
    "ValidatedPassage",
    "SkippedPassage",
    "VectorStore",
    "GraphRetriever",
    "HybridRetriever",
    "EvidenceRanker",
    "EvidenceRankingEngine",
    "evidence_ranking_engine",
    "EvidenceScoreComponents",
    "EvidenceRankingExplanation",
    "RankedEvidenceItem",
    "EvidenceRankerConfig",
    "RAGRetrievalEngine",
    "rag_engine",
    "HybridRAGPipeline",
    "EvidenceItem",
    "EvidenceCollection",
    "hybrid_rag_pipeline",
]
