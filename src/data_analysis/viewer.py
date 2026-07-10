"""Local results gallery — watch analysis outputs appear live in the browser.

Run alongside the MCP server/client:

    python -m data_analysis.viewer            # http://127.0.0.1:8400
    python -m data_analysis.viewer --port 9000
    data-analysis-viewer                      # when installed via pip

Serves the configured MCP_OUTPUT_DIR as an auto-refreshing gallery:
PNG charts render in a grid, interactive Plotly HTML files open in a new
tab. Standard library only — no extra dependencies. Binds to localhost.
"""
import argparse
import json
import mimetypes
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from . import config

_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")

PAGE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Data-Analyze-MCP · Results</title>
<style>
:root{--bg:#f6f7f9;--card:#fff;--ink:#1b2430;--muted:#5c6b7a;--accent:#1f77b4;--line:#e2e6eb}
@media (prefers-color-scheme:dark){:root{--bg:#14171c;--card:#1c2129;--ink:#e8ecf1;--muted:#93a1b0;--accent:#5ba3d6;--line:#2a313b}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:"Apple SD Gothic Neo","Malgun Gothic",system-ui,sans-serif}
header{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);padding:14px 24px;display:flex;align-items:baseline;gap:14px}
h1{font-size:16px;margin:0}
h1 b{color:var(--accent)}
#status{font-size:12px;color:var(--muted);font-family:ui-monospace,monospace}
main{max-width:1200px;margin:0 auto;padding:20px;display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;overflow:hidden;display:flex;flex-direction:column}
.card img{width:100%;height:auto;display:block;background:#fff}
.meta{display:flex;justify-content:space-between;gap:8px;padding:9px 12px;font-size:12px;color:var(--muted);font-family:ui-monospace,monospace}
.meta .name{color:var(--ink);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.htmlcard{padding:18px 12px;text-align:center}
.htmlcard a{color:var(--accent);font-weight:600;text-decoration:none;font-size:14px}
.empty{grid-column:1/-1;text-align:center;color:var(--muted);padding:60px 0}
</style>
</head>
<body>
<header>
  <h1><b>Data-Analyze-MCP</b> 결과 갤러리</h1>
  <span id="status">연결 중…</span>
</header>
<main id="grid"></main>
<script>
let last = "";
async function refresh(){
  try{
    const res = await fetch("/api/files");
    const data = await res.json();
    document.getElementById("status").textContent =
      data.files.length + "개 결과물 · " + data.output_dir + " · 3초마다 갱신";
    const sig = JSON.stringify(data.files.map(f => f.name + f.modified));
    if(sig === last) return;
    last = sig;
    const grid = document.getElementById("grid");
    grid.innerHTML = "";
    if(!data.files.length){
      grid.innerHTML = '<div class="empty">아직 결과물이 없습니다 — 분석을 실행하면 여기 바로 나타납니다.</div>';
      return;
    }
    for(const f of data.files){
      const card = document.createElement("div");
      card.className = "card";
      if(f.image){
        card.innerHTML = `<a href="/files/${encodeURIComponent(f.name)}" target="_blank">
            <img src="/files/${encodeURIComponent(f.name)}?v=${f.modified}" alt="${f.name}" loading="lazy"></a>
          <div class="meta"><span class="name">${f.name}</span><span>${f.modified.slice(11,19)}</span></div>`;
      }else{
        card.innerHTML = `<div class="htmlcard">
            <a href="/files/${encodeURIComponent(f.name)}" target="_blank">🔍 ${f.name}</a>
            <div style="font-size:12px;color:var(--muted);margin-top:6px">인터랙티브 차트 — 새 탭에서 열기</div></div>
          <div class="meta"><span class="name">${(f.size_kb/1024).toFixed(1)} MB</span><span>${f.modified.slice(11,19)}</span></div>`;
      }
      grid.appendChild(card);
    }
  }catch(e){
    document.getElementById("status").textContent = "서버 연결 끊김 — 재시도 중…";
  }
}
refresh();
setInterval(refresh, 3000);
</script>
</body>
</html>"""


def _files_payload() -> dict:
    out = config.OUTPUT_DIR
    files = []
    if out.exists():
        for f in sorted(out.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if not f.is_file():
                continue
            st = f.stat()
            files.append(
                {
                    "name": f.name,
                    "image": f.suffix.lower() in _IMAGE_SUFFIXES,
                    "size_kb": round(st.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                }
            )
    return {"output_dir": str(out.resolve()), "files": files}


class GalleryHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):  # keep the terminal quiet
        pass

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802 (http.server API)
        if self.path == "/" or self.path.startswith("/index"):
            self._send(200, PAGE.encode(), "text/html; charset=utf-8")
        elif self.path.startswith("/api/files"):
            self._send(200, json.dumps(_files_payload()).encode(), "application/json")
        elif self.path.startswith("/files/"):
            # basename-only lookup inside OUTPUT_DIR — no path traversal
            raw = self.path.split("/files/", 1)[1].split("?")[0]
            name = Path(unquote(raw)).name
            target = config.OUTPUT_DIR / name
            if not target.is_file():
                self._send(404, b"not found", "text/plain")
                return
            ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self._send(200, target.read_bytes(), ctype)
        else:
            self._send(404, b"not found", "text/plain")


def main() -> None:
    parser = argparse.ArgumentParser(description="Data-Analyze-MCP results gallery")
    parser.add_argument("--port", type=int, default=8400)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), GalleryHandler)
    print(f"📊 결과 갤러리: http://{args.host}:{args.port}  (감시 대상: {config.OUTPUT_DIR.resolve()})")
    print("   Ctrl+C 로 종료")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
