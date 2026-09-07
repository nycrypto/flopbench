"""Canonical JSON, safe offline HTML, and terminal report renderers."""

from __future__ import annotations

import html
import json

from .canonical import canonical_bytes
from .models import ReportExport


def render_json(export: ReportExport) -> bytes:
    return canonical_bytes(export.model_dump(mode="json", by_alias=True))


def render_terminal(export: ReportExport) -> str:
    payload = export.document.payload
    lines = [
        "FlopBench community report (unofficial)",
        f"Schema: {payload.schema_id}",
        f"Privacy: {export.document.privacy_level.value}",
        f"Digest: sha256:{export.digest.value}",
        "Authenticity: unverified local observations; not proof of eligibility or rewards.",
    ]
    return "\n".join(lines)


def render_html(export: ReportExport) -> bytes:
    """Render a standalone document with no scripts or external resources."""

    serialized = json.dumps(
        export.document.payload.model_dump(mode="json", by_alias=True),
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    )
    escaped = html.escape(serialized, quote=True)
    title = html.escape(f"FlopBench {export.document.payload.schema_id}", quote=True)
    privacy = html.escape(export.document.privacy_level.value, quote=True)
    digest = html.escape(export.digest.value, quote=True)
    markup = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>{title}</title><style>
body{{margin:2rem auto;max-width:72rem;padding:0 1rem;font:16px/1.5 system-ui;
color:#18202a;background:#f5f1e8}}
main{{background:#fff;padding:2rem;border:1px solid #18202a}}
code,pre{{font-family:ui-monospace,monospace}} pre{{overflow:auto;padding:1rem;background:#f0eee7}}
.warning{{border-left:.4rem solid #b74a22;padding-left:1rem}}
</style></head><body><main><h1>{title}</h1>
<p class="warning">Unofficial community output. It does not prove FLOP eligibility,
identity, or rewards.</p>
<dl><dt>Privacy</dt><dd>{privacy}</dd><dt>JCS SHA-256</dt><dd><code>{digest}</code></dd></dl>
<h2>Payload</h2><pre>{escaped}</pre></main></body></html>"""
    return markup.encode("utf-8")
