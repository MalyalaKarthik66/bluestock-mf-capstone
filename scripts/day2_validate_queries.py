"""
Day 2 SQL Query Validator.

Executes all SQL statements from sql/queries.sql against the SQLite database
and prints a short success summary with sample row counts.
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, text


def _extract_queries(sql_text: str) -> list[str]:
    """Split SQL script into executable statements, preserving query bodies."""
    chunks = [c.strip() for c in sql_text.split(";") if c.strip()]
    queries: list[str] = []

    for chunk in chunks:
        lines = [ln for ln in chunk.splitlines() if ln.strip()]
        filtered = [ln for ln in lines if not ln.strip().startswith("--")]
        statement = "\n".join(filtered).strip()
        if statement:
            queries.append(statement)

    return queries


def main() -> None:
    """Validate all Day 2 analytical SQL queries."""
    project_root = Path(__file__).resolve().parent.parent
    db_path = project_root / "data" / "db" / "bluestock_mf.db"
    queries_path = project_root / "sql" / "queries.sql"

    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    if not queries_path.exists():
        raise FileNotFoundError(f"Query file not found: {queries_path}")

    query_text = queries_path.read_text(encoding="utf-8")
    queries = _extract_queries(query_text)

    if len(queries) != 10:
        raise ValueError(f"Expected 10 queries, found {len(queries)}")

    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.connect() as conn:
        for idx, query in enumerate(queries, start=1):
            result = conn.execute(text(query))
            sample = result.fetchmany(3)
            print(f"Q{idx}: OK (sample rows fetched: {len(sample)})")

    print("All 10 queries validated successfully.")


if __name__ == "__main__":
    main()
