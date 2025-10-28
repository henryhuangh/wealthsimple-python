#!/usr/bin/env python3
# extract_ws_from_har.py
import sys, json, csv, re, base64
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple
from urllib.parse import urlparse

# -------------------- Endpoint allowlist --------------------
ENDPOINTS = [
    {
        "name": "ws_graphql",
        "scheme": "https",
        "netloc": "my.wealthsimple.com",
        "path": "/graphql",      # allow optional trailing slash
        "allow_trailing": True,
    },
    {
        "name": "ws_oauth_token",
        "scheme": "https",
        "netloc": "api.production.wealthsimple.com",
        "path": "/v1/oauth/v2/token",  # exact
        "allow_trailing": False,
    },
]

# -------------------- Utilities --------------------
def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def safe_get(d: Any, *keys, default=None):
    cur = d
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def is_target_endpoint(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    try:
        u = urlparse(url)
    except Exception:
        return None
    for ep in ENDPOINTS:
        if u.scheme != ep["scheme"] or u.netloc != ep["netloc"]:
            continue
        path = (u.path or "")
        if ep["allow_trailing"]:
            if path.rstrip("/") == ep["path"]:
                return ep["name"]
        else:
            if path == ep["path"]:
                return ep["name"]
    return None

def decode_har_text(content: Dict) -> Optional[str]:
    """
    HAR response.content may have 'text' plus optional 'encoding' ('base64').
    """
    if not isinstance(content, dict):
        return None
    txt = content.get("text")
    if txt is None:
        return None
    enc = content.get("encoding")
    if enc and str(enc).lower() == "base64":
        try:
            return base64.b64decode(txt).decode("utf-8", errors="replace")
        except Exception:
            # Fall back to raw base64 if decode fails
            return f"[BASE64_NOT_DECODED] {txt[:120]}…"
    return txt

def coerce_text(x: Any) -> Optional[str]:
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
    return str(x)

# -------------------- Redaction --------------------
SENSITIVE_KEYS = {
    # bodies
    "password","pass","pwd","username","email","otp","otp_claim",
    "client_secret","clientSecret",
    "access_token","refresh_token","id_token","token",
    # headers
    "authorization","cookie","set-cookie",
}
TOKEN_PATTERN = re.compile(r"(?i)\b(bearer\s+[A-Za-z0-9._-]+|eyJ[0-9A-Za-z._-]+)\b")  # JWT/Bearer-like
LONG_ID = re.compile(r"([A-Za-z0-9]{24,})")

def redact_string(s: str) -> str:
    s = TOKEN_PATTERN.sub("[REDACTED_TOKEN]", s)
    s = LONG_ID.sub(lambda m: m.group(0)[:6] + "…[REDACTED]…", s)
    return s

def redact_scalar(v: Any, key_hint: Optional[str] = None) -> Any:
    if v is None or isinstance(v, (int, float, bool)):
        return v
    text = str(v)
    if key_hint and key_hint.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    return redact_string(text)

def redact_obj(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: redact_obj(v) if isinstance(v, (dict, list)) else redact_scalar(v, k) for k, v in obj.items()}
    if isinstance(obj, list):
        return [redact_obj(v) for v in obj]
    if isinstance(obj, str):
        return redact_string(obj)
    return obj

# -------------------- HAR accessors --------------------
def iter_har_entries(har: Dict) -> Iterable[Dict]:
    for e in safe_get(har, "log", "entries") or []:
        if isinstance(e, dict):
            yield e

def extract_request_body(req: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    """
    HAR requests often store body under postData.text (and/or params).
    """
    post = req.get("postData") or {}
    # If params present (list of {name,value}) turn into dict preview
    if isinstance(post.get("params"), list):
        try:
            as_dict = {kv.get("name"): kv.get("value") for kv in post["params"] if isinstance(kv, dict)}
            txt = json.dumps(as_dict, ensure_ascii=False, indent=2)
            return txt, as_dict
        except Exception:
            pass
    txt = post.get("text")
    if txt is None:
        return None, None
    # Try parse JSON if it looks like JSON
    parsed = None
    if isinstance(txt, str):
        s = txt.strip()
        if s.startswith("{") or s.startswith("["):
            try:
                parsed = json.loads(s)
            except Exception:
                parsed = None
    return txt, parsed

def extract_response_body(resp: Dict) -> Tuple[Optional[str], Optional[Dict]]:
    content = resp.get("content") or {}
    txt = decode_har_text(content)
    if txt is None:
        return None, None
    parsed = None
    s = txt.strip()
    if s.startswith("{") or s.startswith("["):
        try:
            parsed = json.loads(s)
        except Exception:
            parsed = None
    return txt, parsed

def headers_list_to_dict(headers: Any) -> Dict[str, Any]:
    out = {}
    if isinstance(headers, list):
        for h in headers:
            if isinstance(h, dict) and "name" in h:
                out[h["name"]] = h.get("value")
    return out

# -------------------- Main --------------------
def main(har_path: str, out_dir: str):
    in_path = Path(har_path)
    out_root = Path(out_dir) / "ws_har"
    ensure_dir(out_root)

    with in_path.open("r", encoding="utf-8") as f:
        har = json.load(f)

    # Prep endpoint folders
    ep_dirs = {}
    counters = {}
    for ep in ENDPOINTS:
        p = out_root / ep["name"]
        ensure_dir(p)
        ep_dirs[ep["name"]] = p
        counters[ep["name"]] = 0

    # CSV summary
    summary_path = out_root / "ws_summary.csv"
    ndjson_path = out_root / "raw_entries.ndjson"
    matches_redacted = []

    with summary_path.open("w", newline="", encoding="utf-8") as fcsv:
        writer = csv.writer(fcsv)
        writer.writerow([
            "idx","endpoint","startedDateTime","time_ms",
            "method","status","url","mimeType",
            "operationName","variables_preview"
        ])

        for e in iter_har_entries(har):
            req = e.get("request") or {}
            resp = e.get("response") or {}

            url = req.get("url")
            ep_name = is_target_endpoint(url)
            if not ep_name:
                continue

            counters[ep_name] += 1
            idx = f"{counters[ep_name]:04d}"
            base = f"{idx}_{ep_name}"
            ep_dir = ep_dirs[ep_name]

            # Headers (list->dict) + redact
            req_headers = redact_obj(headers_list_to_dict(req.get("headers")))
            resp_headers = redact_obj(headers_list_to_dict(resp.get("headers")))

            # Bodies
            req_text, req_parsed = extract_request_body(req)
            resp_text, resp_parsed = extract_response_body(resp)

            red_req_body = redact_obj(req_parsed if req_parsed is not None else req_text)
            red_resp_body = redact_obj(resp_parsed if resp_parsed is not None else resp_text)

            # Try GraphQL metadata
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

            # Write request JSON
            with (ep_dir / f"{base}.request.json").open("w", encoding="utf-8") as fr:
                json.dump({
                    "method": req.get("method"),
                    "url": url,
                    "httpVersion": req.get("httpVersion"),
                    "headers": req_headers,
                    "cookies": redact_obj(req.get("cookies")),
                    "queryString": redact_obj(req.get("queryString")),
                    "body": red_req_body,
                }, fr, ensure_ascii=False, indent=2)

            if req_text:
                with (ep_dir / f"{base}.request.body.txt").open("w", encoding="utf-8") as fb:
                    fb.write(coerce_text(redact_obj(req_text)) or "")

            # Write response JSON
            with (ep_dir / f"{base}.response.json").open("w", encoding="utf-8") as fr:
                json.dump({
                    "status": resp.get("status"),
                    "statusText": resp.get("statusText"),
                    "httpVersion": resp.get("httpVersion"),
                    "headers": resp_headers,
                    "cookies": redact_obj(resp.get("cookies")),
                    "mimeType": safe_get(resp, "content", "mimeType"),
                    "body": red_resp_body,
                }, fr, ensure_ascii=False, indent=2)

            if resp_text:
                with (ep_dir / f"{base}.response.body.txt").open("w", encoding="utf-8") as fb:
                    fb.write(coerce_text(redact_obj(resp_text)) or "")

            # CSV summary row
            writer.writerow([
                idx,
                ep_name,
                e.get("startedDateTime"),
                e.get("time"),
                req.get("method"),
                resp.get("status"),
                url,
                safe_get(resp, "content", "mimeType"),
                op_name,
                vars_preview,
            ])

            # Save redacted raw entry for NDJSON
            matches_redacted.append(redact_obj(e))

    with ndjson_path.open("w", encoding="utf-8") as fnd:
        for m in matches_redacted:
            fnd.write(json.dumps(m, ensure_ascii=False) + "\n")

    print(f"✅ Parsed HAR: {in_path}")
    for ep in ENDPOINTS:
        count = counters[ep["name"]]
        print(f"  • {ep['name']}: {count} request(s)")
    print(f"📄 Summary: {summary_path}")
    print(f"📦 Output root: {out_root}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python extract_ws_from_har.py <input.har> [output_dir]")
        sys.exit(1)
    har_file = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "./output"
    main(har_file, out_dir)