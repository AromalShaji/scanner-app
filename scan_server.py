"""
scan_server.py
--------------
DWT-like WebSocket scan server — Windows / macOS / Linux + ADF feeder.

Usage:
  python scan_server.py [--host 127.0.0.1] [--port 8765]

WebSocket JSON API
------------------
  { "cmd": "list_scanners" }
  { "cmd": "scan", "scanner": "...", "dpi": 300, "pixel_type": 2,
                   "use_adf": false, "duplex": false }
  { "cmd": "export_pdf", "pages": ["data:image/png;base64,..."], "output_path": "out.pdf" }
  { "cmd": "ping" }
"""

import asyncio
import websockets
import json
import base64
import platform
import argparse
import os
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    raise SystemExit("Pillow required: pip install Pillow")

try:
    from fpdf2 import FPDF
except ImportError:
    try:
        from fpdf import FPDF
    except ImportError:
        FPDF = None

from scanner_backend import get_backend, PIXEL_BW, PIXEL_GRAYSCALE, PIXEL_COLOR

PLATFORM = platform.system()

# ── helpers ───────────────────────────────────────────────────────────────────

def ok(event, **data):
    return json.dumps({"event": event, "success": True, **data})

def err(event, message):
    return json.dumps({"event": event, "success": False, "error": str(message)})

def log(msg):
    print(f"[scan_server] {msg}", flush=True)

def pil_to_data_url(img: Image.Image) -> str:
    buf = BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"

# ── lazy backend (initialised once per process) ───────────────────────────────
_backend = None

def backend():
    global _backend
    if _backend is None:
        _backend = get_backend()
        log(f"Scanner backend: {type(_backend).__name__} on {PLATFORM}")
    return _backend

# ── blocking scan ops (run in executor so async loop stays free) ──────────────

def _list_scanners():
    return backend().list_scanners()


def _scan_all_pages(scanner_name, dpi, pixel_type, use_adf, duplex):
    """
    Runs the full scan session and returns a list of page dicts.
    Runs in a thread pool — must be fully synchronous.
    """
    pages = []
    for img in backend().scan_pages(
        scanner_name,
        dpi=dpi,
        pixel_type=pixel_type,
        use_adf=use_adf,
        duplex=duplex,
    ):
        pages.append({
            "data_url": pil_to_data_url(img),
            "width":    img.width,
            "height":   img.height,
        })
    return pages


def _pages_to_pdf(data_urls, output_path):
    if FPDF is None:
        raise RuntimeError("fpdf2 not installed: pip install fpdf2")

    pdf = FPDF(unit="mm", format="A4")
    tmp_files = []
    try:
        for i, url in enumerate(data_urls):
            b64 = url.split(",", 1)[1] if "," in url else url
            raw = base64.b64decode(b64)
            img = Image.open(BytesIO(raw))

            tmp_path = f"_pdf_tmp_{i}.png"
            img.save(tmp_path)
            tmp_files.append(tmp_path)

            pdf.add_page()
            pw = pdf.w - 20
            ph = pdf.h - 20
            iw, ih = img.size
            px_per_mm = 96 / 25.4
            ratio = min(pw / (iw / px_per_mm), ph / (ih / px_per_mm))
            w_mm = (iw / px_per_mm) * ratio
            h_mm = (ih / px_per_mm) * ratio
            pdf.image(tmp_path, x=(pdf.w - w_mm) / 2, y=(pdf.h - h_mm) / 2,
                      w=w_mm, h=h_mm)
    finally:
        for f in tmp_files:
            try:
                os.remove(f)
            except OSError:
                pass

    pdf.output(output_path)
    with open(output_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ── WebSocket message handler ─────────────────────────────────────────────────

async def handle(websocket):
    remote = websocket.remote_address
    log(f"Client connected: {remote}")
    loop = asyncio.get_event_loop()

    try:
        async for raw in websocket:
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send(err("error", "Invalid JSON"))
                continue

            cmd = msg.get("cmd", "")
            log(f"<- {cmd}")

            # ── ping ───────────────────────────────────────────────────────
            if cmd == "ping":
                await websocket.send(ok("pong", platform=PLATFORM))

            # ── list scanners ──────────────────────────────────────────────
            elif cmd == "list_scanners":
                try:
                    scanners = await loop.run_in_executor(None, _list_scanners)
                    await websocket.send(ok("scanners", scanners=scanners,
                                           platform=PLATFORM))
                except Exception as e:
                    log(f"list_scanners error: {e}")
                    await websocket.send(err("scanners", e))

            # ── scan ───────────────────────────────────────────────────────
            elif cmd == "scan":
                scanner    = msg.get("scanner", "")
                dpi        = int(msg.get("dpi", 300))
                pixel_type = int(msg.get("pixel_type", PIXEL_COLOR))
                use_adf    = bool(msg.get("use_adf", False))
                duplex     = bool(msg.get("duplex", False))

                if not scanner:
                    await websocket.send(err("scan_result", "No scanner specified"))
                    continue

                mode_str = (
                    "ADF duplex" if use_adf and duplex
                    else "ADF" if use_adf
                    else "Flatbed"
                )
                await websocket.send(json.dumps({
                    "event":  "scan_status",
                    "status": "scanning",
                    "mode":   mode_str,
                }))

                try:
                    pages = await loop.run_in_executor(
                        None,
                        _scan_all_pages,
                        scanner, dpi, pixel_type, use_adf, duplex,
                    )

                    if not pages:
                        await websocket.send(err("scan_result",
                                                 "No pages acquired — check feeder or flatbed"))
                        continue

                    # stream each page back so the UI can show progress
                    for i, page in enumerate(pages):
                        await websocket.send(ok(
                            "scan_page",
                            page_index   = i,
                            total_so_far = i + 1,
                            data_url     = page["data_url"],
                            width        = page["width"],
                            height       = page["height"],
                        ))

                    await websocket.send(ok(
                        "scan_complete",
                        page_count = len(pages),
                    ))

                except Exception as e:
                    log(f"scan error: {e}")
                    await websocket.send(err("scan_result", e))

            # ── export PDF ─────────────────────────────────────────────────
            elif cmd == "export_pdf":
                data_urls   = msg.get("pages", [])
                output_path = msg.get("output_path", "scanned_document.pdf")

                if not data_urls:
                    await websocket.send(err("pdf_result", "No pages provided"))
                    continue

                try:
                    pdf_b64 = await loop.run_in_executor(
                        None, _pages_to_pdf, data_urls, output_path
                    )
                    await websocket.send(ok(
                        "pdf_result",
                        pdf_b64     = pdf_b64,
                        output_path = output_path,
                        page_count  = len(data_urls),
                    ))
                except Exception as e:
                    log(f"pdf error: {e}")
                    await websocket.send(err("pdf_result", e))

            else:
                await websocket.send(err("error", f"Unknown command: {cmd}"))

    except websockets.exceptions.ConnectionClosed:
        log(f"Client disconnected: {remote}")


# ── entry point ───────────────────────────────────────────────────────────────

async def main(host, port):
    log(f"Platform: {PLATFORM}")
    log(f"Starting on ws://{host}:{port}")
    async with websockets.serve(handle, host, port):
        log("Ready - waiting for connections...")
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cross-platform WebSocket scan server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    asyncio.run(main(args.host, args.port))