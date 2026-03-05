"""
PV Desalination System — Application Entry Point
Initializes system configuration and validates runtime environment.
"""
import sys
import os
import hashlib
import runpy
import threading

# ─── System Configuration Constants ──────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Runtime asset manifest — required system resources
_ASSET_MANIFEST = {
    os.path.join(_BASE_DIR, "info_page.py"): "49cea2feb6168d3861dd0b4c3ede6326ce709d219ba0ce96919316b3a1c80b77",
}

_CORE_MODULE = os.path.join(_BASE_DIR, "_protected_core.py")
_MONITOR_INTERVAL = 30  # seconds


# ─── System Resource Validation ──────────────────────────────────────────────
def _compute_resource_sig(filepath):
    """Compute resource signature for asset validation."""
    with open(filepath, "rb") as fh:
        content = fh.read().replace(b"\r\n", b"\n")
        return hashlib.sha256(content).hexdigest()


def _sys_cfg_validate():
    """Validate system configuration and required resources at startup."""
    # Verify all required assets exist and are intact
    for asset_path, expected_sig in _ASSET_MANIFEST.items():
        basename = os.path.basename(asset_path)

        if not os.path.isfile(asset_path):
            _abort_with_diagnostic(
                f"CRITICAL ERROR: Required system resource '{basename}' is missing.\n\n"
                f"The application cannot function without this component.\n"
                f"Please restore the original application files and try again.\n\n"
                f"Application will now terminate."
            )

        actual_sig = _compute_resource_sig(asset_path)
        if actual_sig != expected_sig:
            _abort_with_diagnostic(
                f"CRITICAL ERROR: System resource '{basename}' failed integrity check.\n\n"
                f"This file has been modified or corrupted.\n"
                f"The application cannot run with altered system files.\n\n"
                f"Please restore the original application files and try again.\n"
                f"Application will now terminate."
            )

    # Verify core application module
    if not os.path.isfile(_CORE_MODULE):
        _abort_with_diagnostic(
            f"CRITICAL ERROR: Core application module is missing.\n\n"
            f"The application cannot start without its core module.\n"
            f"Please reinstall the application.\n\n"
            f"Application will now terminate."
        )


def _abort_with_diagnostic(diagnostic_msg):
    """Handle fatal configuration errors with user notification."""
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(diagnostic_msg, file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)
    try:
        import tkinter as _tk
        import tkinter.messagebox as _tmb
        _r = _tk.Tk()
        _r.withdraw()
        _tmb.showerror("Application Error — Cannot Start", diagnostic_msg)
        _r.destroy()
    except Exception:
        pass
    sys.exit(1)


# ─── Runtime Environment Monitor ─────────────────────────────────────────────
class _RuntimeMonitor(threading.Thread):
    """Background thread that periodically validates system resources."""

    def __init__(self):
        super().__init__(daemon=True, name="SysCfgMonitor")
        self._stop_evt = threading.Event()

    def run(self):
        while not self._stop_evt.wait(_MONITOR_INTERVAL):
            try:
                for asset_path, expected_sig in _ASSET_MANIFEST.items():
                    if not os.path.isfile(asset_path):
                        self._trigger_runtime_fault(
                            f"Required system resource '{os.path.basename(asset_path)}' "
                            f"was removed while the application was running.\n\n"
                            f"The application must shut down."
                        )
                        return

                    actual_sig = _compute_resource_sig(asset_path)
                    if actual_sig != expected_sig:
                        self._trigger_runtime_fault(
                            f"System resource '{os.path.basename(asset_path)}' "
                            f"was altered while the application was running.\n\n"
                            f"The application must shut down."
                        )
                        return
            except Exception:
                pass  # File busy / transient — retry next cycle

    @staticmethod
    def _trigger_runtime_fault(msg):
        print(f"\n{'=' * 60}", file=sys.stderr)
        print(f"RUNTIME FAULT: {msg}", file=sys.stderr)
        print(f"{'=' * 60}\n", file=sys.stderr)
        try:
            import tkinter as _tk
            import tkinter.messagebox as _tmb
            _r = _tk.Tk()
            _r.withdraw()
            _tmb.showerror("Runtime Error — Application Shutting Down", msg)
            _r.destroy()
        except Exception:
            pass
        os._exit(1)

    def stop(self):
        self._stop_evt.set()


# ─── Application Entry Point ─────────────────────────────────────────────────
if __name__ == "__main__":
    # Phase 1: Validate system configuration
    _sys_cfg_validate()

    # Phase 2: Start runtime environment monitor
    _monitor = _RuntimeMonitor()
    _monitor.start()

    # Phase 3: Launch core application
    runpy.run_path(_CORE_MODULE, run_name="__main__")
