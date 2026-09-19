from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .analysis import analyze_observation


def build_sqlite_index(canonical: dict, output_path: Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(output_path)
    try:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS entities (entity_id TEXT PRIMARY KEY, kind TEXT, identity_json TEXT, attributes_json TEXT);
        CREATE TABLE IF NOT EXISTS edges (from_id TEXT, role TEXT, ordinal INTEGER, property_key TEXT, to_id TEXT, resolution TEXT);
        CREATE TABLE IF NOT EXISTS anomalies (code TEXT, severity TEXT, entity_id TEXT, evidence_json TEXT);
        CREATE TABLE IF NOT EXISTS signatures (entity_id TEXT, signature_kind TEXT, algorithm_version TEXT, digest TEXT);
        CREATE INDEX IF NOT EXISTS idx_entities_kind ON entities(kind);
        CREATE INDEX IF NOT EXISTS idx_edges_role ON edges(role);
        CREATE INDEX IF NOT EXISTS idx_signatures_digest ON signatures(digest);
        """)
        db.execute("DELETE FROM meta"); db.execute("DELETE FROM entities"); db.execute("DELETE FROM edges"); db.execute("DELETE FROM anomalies"); db.execute("DELETE FROM signatures")
        db.executemany("INSERT INTO meta VALUES (?, ?)", [("canonicalVersion", str(canonical.get("canonicalVersion", ""))), ("rawSha256", str(canonical.get("provenance", {}).get("rawSha256", "")))])
        db.executemany("INSERT INTO entities VALUES (?, ?, ?, ?)", [(x["id"], x["kind"], json.dumps(x.get("identity"), sort_keys=True), json.dumps(x.get("attributes", {}), sort_keys=True)) for x in canonical["observed"].get("entities", [])])
        db.executemany("INSERT INTO edges VALUES (?, ?, ?, ?, ?, ?)", [(x.get("from"), x.get("role"), x.get("ordinal"), x.get("property"), x.get("to"), str(x.get("resolved", "UNKNOWN"))) for x in canonical["observed"].get("edges", [])])
        db.executemany("INSERT INTO anomalies VALUES (?, ?, ?, ?)", [(x.get("code"), x.get("severity"), x.get("entity"), json.dumps(x.get("evidence", {}), sort_keys=True)) for x in canonical["observed"].get("anomalies", [])])
        analysis = analyze_observation(canonical)
        rows = []
        for kind, values in (("prefab", analysis["prefabSignatures"]), ("skeleton", analysis["skeletonSignatures"]), ("mesh", analysis["meshSignatures"])):
            source_map = analysis.get("signatureSources", {}).get(kind, {})
            rows.extend((source_map.get(entity_id, entity_id), kind, value.get("algorithmVersion", ""), value.get("digest", "")) for entity_id, value in values.items())
        db.executemany("INSERT INTO signatures VALUES (?, ?, ?, ?)", rows)
        db.commit()
    finally:
        db.close()
    return output_path
