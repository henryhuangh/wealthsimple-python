#!/usr/bin/env python3
# extract_ws_graphql.py
import sys
import json
import csv
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse

TARGET_SCHEME = "https"
TARGET_NETLOC = "my.wealthsimple.com"
TARGET_PATH = "/graphql"  # allow optional trailing slash

# --------- Helpers ---------
def safe_get(d: Dict, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def to_text(x: Any) -> Optional[str]:
    if x is None:
        return None
    if isinstance(x, (dict, list)):
        try:
            return json.dumps(x, ensure_ascii=False, indent=2)
        except Exception:
            return str(x)
    if isinstance(x, (bytes, bytearray)):
        try:
            return x.decode("utf-8", errors="replace")
        except Exception:
            return None
    if isinstance(x, str):
        return x
    return str(x)

def sanitize_filename(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", (s or "").strip())
    return s[:100] if len(s) > 100 else s

def is_target_endpoint(url: Optional[str]) -> bool:
    """Match exactly https://my.wealthsimple.com/graphql with optional trailing slash, any query/fragment."""
    if not url:
        return False
    try:
        u = urlparse(url)
    except Exception:
        return False
    if u.scheme != TARGET_SCHEME or u.netloc != TARGET_NETLOC:
        return False
    # normalize target path to allow optional trailing slash at endpoint
    path = (u.path or "").rstrip("/")
    return path == TARGET_PATH

def iter_network_records(data: Dict) -> Iterable[Dict]:
    for r in safe_get(data, "recording", "records") or []:
        if isinstance(r, dict) and r.get("type") == "timeline-record-type-network":
            yield r

def extract_req_body(entry: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    body_candidates = [
        safe_get(entry, "request", "postData", "text"),
        safe_get(entry, "request", "postData", "params"),
        safe_get(entry, "request", "body"),
        safe_get(entry, "requestBody"),
    ]
    for b in body_candidates:
        if b is None:
            continue
        txt = None
        parsed = None
        if isinstance(b, list):
            try:
                as_dict = {kv.get("name"): kv.get("value") for kv in b if isinstance(kv, dict) and "name" in kv}
                txt = json.dumps(as_dict, ensure_ascii=False, indent=2)
                parsed = as_dict
            except Exception:
                txt = to_text(b)
        else:
            txt = to_text(b)
            if isinstance(txt, str):
                try:
                    parsed = json.loads(txt)
                except Exception:
                    parsed = None
        if txt:
            return txt, parsed
    return None, None

def extract_resp_body(entry: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    body_candidates = [
        safe_get(entry, "response", "content", "text"),
        safe_get(entry, "response", "body"),
        safe_get(entry, "responseBody"),
        safe_get(entry, "content", "text"),
    ]
    for b in body_candidates:
        if b is None:
            continue
        txt = to_text(b)
        parsed = None
        if isinstance(txt, str):
            try:
                parsed = json.loads(txt)
            except Exception:
                parsed = None
        if txt:
            return txt, parsed
    return None, None

# --------- Core ---------
def main(in_path: str, out_dir: str):
    in_path = Path(in_path)
    out_root = Path(out_dir)
    out_group = out_root / "ws_graphql"
    ensure_dir(out_group)

    with in_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    matches = []
    for rec in iter_network_records(data):
        entry = rec.get("entry") or {}
        req = entry.get("request") or {}
        url = req.get("url")
        if not is_target_endpoint(url):
            continue

        matches.append({
            "url": url,
            "method": safe_get(req, "method"),
            "startedDateTime": safe_get(entry, "startedDateTime"),
            "time_ms": safe_get(entry, "time"),
            "status": safe_get(entry, "response", "status"),
            "req_headers": safe_get(req, "headers") or {},
            "resp_headers": safe_get(entry, "response", "headers") or {},
            "raw_entry": entry,
        })

    # Write CSV summary
    summary_path = out_group / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow([
            "idx", "startedDateTime", "time_ms",
            "method", "status", "url",
            "operationName", "variables_preview"
        ])

        for i, m in enumerate(matches, start=1):
            idx = f"{i:04d}"
            base = f"{idx}_{sanitize_filename('ws_graphql')}"
            req_json_path = out_group / f"{base}.request.json"
            resp_json_path = out_group / f"{base}.response.json"

            # Bodies
            req_text, req_parsed = extract_req_body(m["raw_entry"])
            resp_text, resp_parsed = extract_resp_body(m["raw_entry"])

            op_name = None
            vars_preview = None
            if isinstance(req_parsed, dict):
                op_name = req_parsed.get("operationName")
                variables = req_parsed.get("variables")
                if variables is not None:
                    try:
                        vars_preview = json.dumps(variables, ensure_ascii=False)[:200]
                    except Exception:
                        vars_preview = str(variables)[:200]

            # Request JSON
            with req_json_path.open("w", encoding="utf-8") as fr:
                json.dump({
                    "method": m["method"],
                    "url": m["url"],
                    "headers": m["req_headers"],
                    "body": req_parsed if req_parsed is not None else req_text,
                }, fr, ensure_ascii=False, indent=2)

            if req_text:
                with (out_group / f"{base}.request.body.txt").open("w", encoding="utf-8") as fb:
                    fb.write(req_text)

            # Response JSON
            with resp_json_path.open("w", encoding="utf-8") as fr:
                json.dump({
                    "status": m["status"],
                    "headers": m["resp_headers"],
                    "body": resp_parsed if resp_parsed is not None else resp_text,
                }, fr, ensure_ascii=False, indent=2)

            if resp_text:
                with (out_group / f"{base}.response.body.txt").open("w", encoding="utf-8") as fb:
                    fb.write(resp_text)

            writer.writerow([
                idx,
                m.get("startedDateTime"),
                m.get("time_ms"),
                m.get("method"),
                m.get("status"),
                m.get("url"),
                op_name,
                vars_preview,
            ])

    # NDJSON of raw entries for debugging
    ndjson_path = out_group / "raw_entries.ndjson"
    with ndjson_path.open("w", encoding="utf-8") as fnd:
        for m in matches:
            fnd.write(json.dumps(m["raw_entry"], ensure_ascii=False) + "\n")

    print(f"✅ Found {len(matches)} requests to {TARGET_SCHEME}://{TARGET_NETLOC}{TARGET_PATH}")
    print(f"📄 Summary: {summary_path}")
    print(f"📦 Files in: {out_group}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_ws_graphql.py <input_json> [output_dir]")
        sys.exit(1)
    in_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    main(in_file, out_dir)