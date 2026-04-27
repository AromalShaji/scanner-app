"""
scanner_backend.py
------------------
Cross-platform scanner abstraction layer.

Platform dispatch:
  Windows  → TWAIN via pytwain
  macOS    → ImageCaptureCore via pyinsane2 (fallback: subprocess ICA bridge)
  Linux    → SANE via python-sane

Each backend exposes:
  list_scanners()                     → [str, ...]
  scan_pages(name, dpi, pixel_type,   → generator yielding PIL.Image per page
             use_adf, duplex)
"""

import sys
import os
import time
import platform
from io import BytesIO

try:
    from PIL import Image
except ImportError:
    raise RuntimeError("Pillow is required: pip install Pillow")

PLATFORM = platform.system()   # 'Windows' | 'Darwin' | 'Linux'

# ─────────────────────────────────────────────────────────────────────────────
# Pixel type constants (shared across callers)
# ─────────────────────────────────────────────────────────────────────────────
PIXEL_BW        = 0
PIXEL_GRAYSCALE = 1
PIXEL_COLOR     = 2

# ─────────────────────────────────────────────────────────────────────────────
# Windows — TWAIN
# ─────────────────────────────────────────────────────────────────────────────
class TwainBackend:
    """pytwain backend for Windows."""

    def __init__(self):
        try:
            import twain
            self._twain = twain
        except ImportError:
            raise RuntimeError(
                "pytwain not installed. Run: pip install twain"
            )

    def list_scanners(self):
        tw = self._twain
        sm = tw.SourceManager(0)
        try:
            return list(sm.GetSourceList())
        finally:
            sm.destroy()

    def scan_pages(self, scanner_name, dpi=300, pixel_type=PIXEL_COLOR,
                   use_adf=False, duplex=False):
        tw = self._twain
        sm = tw.SourceManager(0)
        source = None
        try:
            source = sm.OpenSource(scanner_name)
            if not source:
                raise RuntimeError(f"Cannot open: {scanner_name}")

            # resolution
            source.SetCapability(tw.ICAP_XRESOLUTION, tw.TWTY_FIX32, float(dpi))
            source.SetCapability(tw.ICAP_YRESOLUTION, tw.TWTY_FIX32, float(dpi))

            # pixel type
            source.SetCapability(tw.ICAP_PIXELTYPE, tw.TWTY_UINT16, pixel_type)

            # ADF
            if use_adf:
                try:
                    # TWAIN ICAP_FEEDERENABLED = 4115 (0x1013)
                    source.SetCapability(4115, tw.TWTY_BOOL, True)
                    source.SetCapability(tw.CAP_FEEDERENABLED, tw.TWTY_BOOL, True)
                except Exception:
                    pass  # scanner may not support it

            # Duplex
            if duplex:
                try:
                    source.SetCapability(tw.CAP_DUPLEXENABLED, tw.TWTY_BOOL, True)
                except Exception:
                    pass

            source.RequestAcquire(0, 0)
            time.sleep(1)

            while True:
                result = source.XferImageNatively()
                if not result:
                    break
                handle, remaining = result

                tmp = "_twain_tmp.bmp"
                tw.dib_to_bm_file(handle, tmp)
                img = Image.open(tmp).copy()
                os.remove(tmp)

                yield img

                if remaining == 0:
                    break
        finally:
            if source:
                for method in ("destroy", "reset"):
                    if hasattr(source, method):
                        try:
                            getattr(source, method)()
                        except Exception:
                            pass
            try:
                sm.destroy()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# macOS — pyinsane2  (brew install sane-backends  +  pip install pyinsane2)
# ─────────────────────────────────────────────────────────────────────────────
class InsaneBackend:
    """
    pyinsane2 backend — works on macOS and Linux.
    macOS: brew install sane-backends && pip install pyinsane2
    Linux: sudo apt install libsane-dev && pip install pyinsane2
    """

    # map our pixel_type int → pyinsane2 mode string
    MODE_MAP = {
        PIXEL_BW:        "Black & White",
        PIXEL_GRAYSCALE: "Gray",
        PIXEL_COLOR:     "Color",
    }

    def __init__(self):
        try:
            import pyinsane2
            pyinsane2.init()
            self._pi = pyinsane2
        except ImportError:
            raise RuntimeError(
                "pyinsane2 not installed.\n"
                "macOS: brew install sane-backends && pip install pyinsane2\n"
                "Linux: sudo apt install libsane-dev && pip install pyinsane2"
            )

    def list_scanners(self):
        devices = self._pi.get_devices()
        return [d.name for d in devices]

    def _get_device(self, name):
        for d in self._pi.get_devices():
            if d.name == name:
                return d
        raise RuntimeError(f"Scanner not found: {name}")

    def _set_opt(self, device, key, value):
        try:
            device.options[key].value = value
        except Exception:
            pass   # option not supported on this scanner

    def scan_pages(self, scanner_name, dpi=300, pixel_type=PIXEL_COLOR,
                   use_adf=False, duplex=False):
        device = self._get_device(scanner_name)

        self._set_opt(device, "resolution", dpi)
        self._set_opt(device, "mode", self.MODE_MAP.get(pixel_type, "Color"))

        if use_adf:
            self._set_opt(device, "source", "ADF" if not duplex else "ADF Duplex")
        else:
            self._set_opt(device, "source", "Flatbed")

        try:
            self._pi.set_max_scan_area(device)
        except Exception:
            pass

        scan_session = device.scan(multiple=use_adf)
        try:
            while True:
                try:
                    scan_session.scan.read()
                except self._pi.StopIteration:
                    break
                img = scan_session.images[-1]
                yield img
        except Exception as e:
            raise RuntimeError(f"Scan error: {e}")
        finally:
            try:
                scan_session.scan.cancel()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Linux — python-sane
# ─────────────────────────────────────────────────────────────────────────────
class SaneBackend:
    """
    python-sane backend — Linux native.
    sudo apt install libsane-dev python3-sane
    or: pip install python-sane
    """

    MODE_MAP = {
        PIXEL_BW:        "Lineart",
        PIXEL_GRAYSCALE: "Gray",
        PIXEL_COLOR:     "Color",
    }

    def __init__(self):
        try:
            import sane
            sane.init()
            self._sane = sane
        except ImportError:
            raise RuntimeError(
                "python-sane not installed.\n"
                "Run: sudo apt install libsane-dev && pip install python-sane"
            )

    def list_scanners(self):
        devices = self._sane.get_devices()
        # returns list of (name, vendor, model, type)
        return [d[0] for d in devices]

    def scan_pages(self, scanner_name, dpi=300, pixel_type=PIXEL_COLOR,
                   use_adf=False, duplex=False):
        dev = self._sane.open(scanner_name)
        try:
            dev.resolution = dpi
            dev.mode = self.MODE_MAP.get(pixel_type, "Color")

            if use_adf:
                try:
                    dev.source = "ADF Duplex" if duplex else "ADF"
                except Exception:
                    try:
                        dev.source = "Automatic Document Feeder"
                    except Exception:
                        pass

            if use_adf:
                # multi-page loop
                while True:
                    try:
                        dev.start()
                        img = dev.snap()
                        yield img.convert("RGB") if pixel_type == PIXEL_COLOR else img
                    except Exception as e:
                        msg = str(e).lower()
                        if "no documents" in msg or "end of feeder" in msg or "jammed" in msg:
                            break
                        raise
            else:
                dev.start()
                img = dev.snap()
                yield img.convert("RGB") if pixel_type == PIXEL_COLOR else img
        finally:
            try:
                dev.close()
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────────────
# Factory — pick the right backend automatically
# ─────────────────────────────────────────────────────────────────────────────
def get_backend():
    """
    Return the best available backend for the current platform.
    Tries in order:
      Windows  → TwainBackend
      macOS    → InsaneBackend (pyinsane2 over SANE/ICA)
      Linux    → SaneBackend, fallback InsaneBackend
    """
    if PLATFORM == "Windows":
        return TwainBackend()

    if PLATFORM == "Darwin":
        # macOS: try pyinsane2 first, then python-sane
        try:
            return InsaneBackend()
        except RuntimeError:
            try:
                return SaneBackend()
            except RuntimeError:
                raise RuntimeError(
                    "No scanner backend found on macOS.\n"
                    "Install: brew install sane-backends && pip install pyinsane2"
                )

    # Linux
    try:
        return SaneBackend()
    except RuntimeError:
        try:
            return InsaneBackend()
        except RuntimeError:
            raise RuntimeError(
                "No scanner backend found on Linux.\n"
                "Install: sudo apt install libsane-dev && pip install python-sane"
            )