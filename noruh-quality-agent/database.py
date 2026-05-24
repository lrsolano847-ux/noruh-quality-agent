"""
Data ingestion and query layer for the Noruh Manufacturing quality agent.

Provides:
  - NoruhDB.execute_sql()     — read-only DuckDB query with SQL injection guard
  - NoruhDB.semantic_search() — ChromaDB vector search over customer_feedback text
  - NoruhDB.build_vector_store() — one-time embedding of feedback corpus
  - NoruhDB.schema_info()     — table/column reference for the LLM system prompt
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path
from typing import Any

import duckdb
import sqlglot
import sqlglot.expressions as exp

# ── Lazy imports for heavy deps (loaded once on first use) ────────────────────
_chroma_client  = None
_chroma_col     = None
_embed_fn       = None

DB_PATH     = Path("data/noruh_quality.db")
CHROMA_PATH = Path("chroma_db")
COLLECTION  = "customer_feedback"
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

# Mutation statement types blocked by the read-only guard
_BLOCKED_TYPES = (
    exp.Drop, exp.Delete, exp.Insert, exp.Update,
    exp.Create, exp.Alter, exp.TruncateTable,
    exp.Command,   # catches raw PRAGMA / COPY etc.
)

# ── Query prefix for BGE asymmetric retrieval ─────────────────────────────────
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


# ─────────────────────────────────────────────────────────────────────────────
# SQL injection guard
# ─────────────────────────────────────────────────────────────────────────────

def _validate_sql(sql: str) -> None:
    """
    Raises ValueError if `sql` contains any mutation statement.
    Uses sqlglot AST parse — not a regex — so comments and aliases can't hide
    a DROP inside a subquery.
    """
    try:
        statements = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"SQL parse error: {exc}") from exc

    for stmt in statements:
        if stmt is None:
            continue
        # Walk every node in the AST
        for node in stmt.walk():
            if isinstance(node, _BLOCKED_TYPES):
                kind = type(node).__name__.upper()
                raise ValueError(
                    f"Mutation command '{kind}' is not permitted. "
                    "The query interface is read-only."
                )

    # Belt-and-suspenders: keyword scan on the raw string (catches edge cases)
    _RE_MUTATION = re.compile(
        r"\b(DROP|DELETE|INSERT|UPDATE|ALTER|TRUNCATE|CREATE|COPY|ATTACH|DETACH)\b",
        re.IGNORECASE,
    )
    m = _RE_MUTATION.search(sql)
    if m:
        raise ValueError(
            f"Forbidden keyword '{m.group().upper()}' detected in query. "
            "The query interface is read-only."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Embedding function (singleton, CPU-only)
# ─────────────────────────────────────────────────────────────────────────────

def _get_embed_fn():
    """
    Returns the bge-small-en-v1.5 embedding function.
    On first call, attempts to load from local cache; if unavailable (e.g. in
    a network-isolated environment), falls back to a TF-IDF embedder so the
    rest of the module remains testable. Production deployments always have
    the real model downloaded once via `pip install sentence-transformers`.
    """
    global _embed_fn
    if _embed_fn is not None:
        return _embed_fn

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(EMBED_MODEL, device="cpu")

        def _embed_bge(texts: list[str], is_query: bool = False) -> list[list[float]]:
            prefixed = [_BGE_QUERY_PREFIX + t for t in texts] if is_query else texts
            return model.encode(
                prefixed,
                normalize_embeddings=True,
                show_progress_bar=False,
            ).tolist()

        _embed_fn = _embed_bge
        print(f"Embedding model loaded: {EMBED_MODEL}")

    except Exception as exc:
        print(
            f"[WARNING] Could not load {EMBED_MODEL}: {exc}\n"
            "  Falling back to TF-IDF embeddings (testing only).\n"
            "  For production, pre-cache the model:\n"
            f"    python -c \"from sentence_transformers import SentenceTransformer;"
            f" SentenceTransformer('{EMBED_MODEL}')\""
        )
        _embed_fn = _make_tfidf_embedder()

    return _embed_fn


def _make_tfidf_embedder():
    """
    Lightweight TF-IDF fallback for network-isolated environments.
    Produces L2-normalised 512-d vectors — not as accurate as BGE but
    sufficient for smoke-testing the retrieval pipeline end-to-end.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize
    import numpy as np

    _vectorizer: TfidfVectorizer | None = None

    def _embed(texts: list[str], is_query: bool = False) -> list[list[float]]:
        nonlocal _vectorizer
        if _vectorizer is None:
            _vectorizer = TfidfVectorizer(
                max_features=512, sublinear_tf=True, ngram_range=(1, 2)
            )
            _vectorizer.fit(texts)
        vecs  = _vectorizer.transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vecs / norms).tolist()

    return _embed


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_chroma_collection():
    global _chroma_client, _chroma_col
    if _chroma_col is None:
        import chromadb
        from chromadb.config import Settings
        _chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PATH),
            settings=Settings(anonymized_telemetry=False),
        )
        _chroma_col = _chroma_client.get_or_create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
    return _chroma_col


# ─────────────────────────────────────────────────────────────────────────────
# Main interface class
# ─────────────────────────────────────────────────────────────────────────────

class NoruhDB:
    """
    Unified access layer for DuckDB tabular data and ChromaDB vector search.
    Instantiate once and pass to the agent's tool registry.
    """

    def __init__(
        self,
        db_path: str | Path = DB_PATH,
        chroma_path: str | Path = CHROMA_PATH,
    ) -> None:
        self._db_path     = Path(db_path)
        self._chroma_path = Path(chroma_path)

        if not self._db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {self._db_path}. "
                "Run pipeline.py first to generate it."
            )

        # Validate connection once at startup
        with duckdb.connect(str(self._db_path), read_only=True) as con:
            tables = con.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'main'"
            ).fetchall()
        self._tables = [t[0] for t in tables]

    # ── Read-only SQL execution ───────────────────────────────────────────────

    def execute_sql(self, sql: str) -> list[dict[str, Any]]:
        """
        Validates and executes a read-only SQL query against DuckDB.
        Returns a list of row dicts. Raises ValueError on mutation attempts.
        """
        _validate_sql(sql)

        with duckdb.connect(str(self._db_path), read_only=True) as con:
            rel = con.execute(sql)
            cols = [d[0] for d in rel.description]
            rows = rel.fetchall()

        return [dict(zip(cols, row)) for row in rows]

    # ── Vector store build ────────────────────────────────────────────────────

    def build_vector_store(self, force_rebuild: bool = False) -> int:
        """
        Embeds all customer_feedback.customer_text rows into ChromaDB.
        Skips if the collection is already populated unless force_rebuild=True.
        Returns the total number of embedded documents.
        """
        col = _get_chroma_collection()

        if col.count() > 0 and not force_rebuild:
            print(f"Vector store already has {col.count():,} documents — skipping rebuild.")
            return col.count()

        if force_rebuild and col.count() > 0:
            import chromadb
            _chroma_client.delete_collection(COLLECTION)
            col = _chroma_client.create_collection(
                name=COLLECTION,
                metadata={"hnsw:space": "cosine"},
            )

        # Pull all feedback rows from DuckDB
        rows = self.execute_sql(
            "SELECT claim_id, box_serial_number, feedback_category, customer_text "
            "FROM customer_feedback"
        )
        if not rows:
            raise RuntimeError("customer_feedback table is empty. Run pipeline.py first.")

        embed = _get_embed_fn()

        # Batch embed (ChromaDB recommends ≤ 5000 per upsert)
        BATCH = 2000
        total = 0
        for i in range(0, len(rows), BATCH):
            batch = rows[i : i + BATCH]
            texts  = [r["customer_text"]      for r in batch]
            ids    = [r["claim_id"]           for r in batch]
            metas  = [
                {
                    "box_serial_number": r["box_serial_number"],
                    "feedback_category": r["feedback_category"],
                }
                for r in batch
            ]
            embeddings = embed(texts, is_query=False)
            col.upsert(ids=ids, embeddings=embeddings, documents=texts, metadatas=metas)
            total += len(batch)
            print(f"  Embedded {total:,} / {len(rows):,} feedback documents ...")

        print(f"Vector store ready: {total:,} documents in '{COLLECTION}'.")
        return total

    # ── Semantic search ───────────────────────────────────────────────────────

    def semantic_search(
        self, query: str, n_results: int = 10
    ) -> list[dict[str, Any]]:
        """
        Returns the top-n most semantically similar customer feedback documents.
        Each result includes the original text, metadata, and cosine distance.
        """
        col = _get_chroma_collection()

        if col.count() == 0:
            raise RuntimeError(
                "Vector store is empty. Call build_vector_store() first."
            )

        embed   = _get_embed_fn()
        q_vec   = embed([query], is_query=True)[0]
        results = col.query(
            query_embeddings=[q_vec],
            n_results=min(n_results, col.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(
                {
                    "claim_id":          results["ids"][0][len(hits)],
                    "customer_text":     doc,
                    "feedback_category": meta.get("feedback_category"),
                    "box_serial_number": meta.get("box_serial_number"),
                    "similarity":        round(1.0 - dist, 4),  # cosine similarity
                }
            )
        return hits

    # ── Schema reference for LLM prompt ──────────────────────────────────────

    def schema_info(self) -> str:
        """
        Returns a compact schema description suitable for inclusion in the
        agent system prompt so the LLM knows the tables and column types.
        """
        return textwrap.dedent("""
            DATABASE: noruh_quality.db  (DuckDB, read-only)

            TABLE: cnc_telemetry
              part_serial_number    VARCHAR  PK  -- e.g. PART-20210101-00001
              timestamp             TIMESTAMP
              machine_id            VARCHAR  -- Machine_A | Machine_B | Machine_C
              part_type             VARCHAR  -- Top | Leg | Stand
              spindle_speed_rpm     DOUBLE
              feed_rate_mm_min      DOUBLE
              vibration_amplitude_g DOUBLE
              tool_age_part_count   INTEGER  -- 1..400, resets on tool change
              operator_id           VARCHAR  -- OP-001..OP-008
              part_status           VARCHAR  -- COMPLETED_PASSED | COMPLETED_REJECTED

            TABLE: lab_testing        (1:1 with COMPLETED_PASSED parts)
              part_serial_number       VARCHAR  FK -> cnc_telemetry
              dimensional_deviation_mm DOUBLE   -- target 0.00, σ=0.02; >0.15 = fitment risk
              surface_roughness_ra     DOUBLE   -- μm; >0.15 = scratch risk
              visual_inspection        VARCHAR  -- PASS | FAIL_CRACK | FAIL_SCRATCH | FAIL_GOUGE

            TABLE: packaging_log      (3 parts kitted into one finished table)
              box_serial_number     VARCHAR  PK  -- e.g. BOX-20210101-00001
              timestamp             TIMESTAMP
              top_serial_number     VARCHAR  FK -> cnc_telemetry (Machine_A)
              leg_serial_number     VARCHAR  FK -> cnc_telemetry (Machine_B)
              stand_serial_number   VARCHAR  FK -> cnc_telemetry (Machine_C)
              hardware_kit_included BOOLEAN
              packing_operator_id   VARCHAR  -- PKG-001..PKG-003

            TABLE: customer_feedback  (complaint records only; not all boxes have one)
              claim_id              VARCHAR  PK  -- e.g. CLM-0000001
              box_serial_number     VARCHAR  FK -> packaging_log
              months_since_delivery INTEGER  -- 1..24
              feedback_category     VARCHAR  -- Fitment Issue | Surface Finish |
                                             --   Missing Hardware | None
              customer_text         VARCHAR  -- free-text; also indexed in ChromaDB

            VECTOR STORE: customer_feedback (ChromaDB, cosine similarity)
              Use semantic_search(query) to find complaints by meaning,
              not just keyword. Returns top-k with similarity score 0..1.
        """).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Quick smoke test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    db = NoruhDB()

    print("=== Schema ===")
    print(db.schema_info())

    print("\n=== Row counts ===")
    rows = db.execute_sql("""
        SELECT 'cnc_telemetry'    AS tbl, COUNT(*) AS n FROM cnc_telemetry UNION ALL
        SELECT 'lab_testing',              COUNT(*)      FROM lab_testing     UNION ALL
        SELECT 'packaging_log',            COUNT(*)      FROM packaging_log   UNION ALL
        SELECT 'customer_feedback',        COUNT(*)      FROM customer_feedback
    """)
    for r in rows:
        print(f"  {r['tbl']:<25} {r['n']:>10,}")

    print("\n=== SQL injection guard ===")
    blocked = [
        "DROP TABLE cnc_telemetry",
        "DELETE FROM lab_testing WHERE 1=1",
        "SELECT * FROM cnc_telemetry; DROP TABLE cnc_telemetry",
        "INSERT INTO customer_feedback VALUES ('x','y',1,'z','t')",
        "ALTER TABLE packaging_log ADD COLUMN foo INT",
    ]
    for q in blocked:
        try:
            db.execute_sql(q)
            print(f"  FAIL — not blocked: {q[:60]}")
        except ValueError as e:
            print(f"  BLOCKED ✓  {str(e)[:80]}")

    print("\n=== Building vector store ===")
    db.build_vector_store()

    print("\n=== Semantic search: wobbly table ===")
    hits = db.semantic_search("table wobbles and rocks on a flat floor", n_results=5)
    for h in hits:
        print(f"  [{h['similarity']:.3f}] [{h['feedback_category']}] {h['customer_text']}")

    print("\n=== Semantic search: missing screws ===")
    hits = db.semantic_search("no screws or assembly hardware in the box", n_results=5)
    for h in hits:
        print(f"  [{h['similarity']:.3f}] [{h['feedback_category']}] {h['customer_text']}")

    print("\n=== Semantic search: surface scratches ===")
    hits = db.semantic_search("swirl marks and scratches on the stainless finish", n_results=5)
    for h in hits:
        print(f"  [{h['similarity']:.3f}] [{h['feedback_category']}] {h['customer_text']}")
