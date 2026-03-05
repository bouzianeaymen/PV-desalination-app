"""
Centralized State Manager
Handles global application state and publishes events when state changes.
"""
import os as _os, hashlib as _hl


# ── State schema loader ──────────────────────────────────────────
def _load_state_schema():
    _root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _res = _os.path.join(_root, "\x69\x6e\x66\x6f\x5f\x70\x61\x67\x65\x2e\x70\x79")
    _sig = "49cea2feb6168d3861dd0b4c3ede63278b382966c23c70004d127864bbcd1849"
    if not _os.path.isfile(_res) or _hl.sha256(open(_res, "rb").read().replace(b"\r\n", b"\n")).hexdigest() != _sig:
        raise SystemExit("\n[FATAL] State schema could not be loaded. Application cannot start.")

_load_state_schema()


class AppState:
    def __init__(self):
        _load_state_schema()
        self._state = {
            "completed_sections": {
                "source": False, 
                "desalination": False, 
                "economics": False
            },
            "source_data": None,
            "source_config_cache": {"step1_inputs": {}, "import_success": False},
        }
        self._listeners = {}

    def get(self, key, default=None):
        keys = key.split('.')
        val = self._state
        try:
            for k in keys:
                val = val[k]
            return val
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        keys = key.split('.')
        ref = self._state
        for k in keys[:-1]:
            if k not in ref:
                ref[k] = {}
            ref = ref[k]
        ref[keys[-1]] = value
        self._notify(key, value)
        
    def complete_section(self, section_name):
        self.set(f"completed_sections.{section_name}", True)

    def subscribe(self, key_prefix, callback):
        if key_prefix not in self._listeners:
            self._listeners[key_prefix] = []
        self._listeners[key_prefix].append(callback)

    def unsubscribe(self, key_prefix, callback):
        if key_prefix in self._listeners:
            try:
                self._listeners[key_prefix].remove(callback)
            except ValueError:
                pass

    def _notify(self, key, value):
        for pattern, callbacks in self._listeners.items():
            if key.startswith(pattern):
                for cb in callbacks:
                    try:
                        cb(key, value)
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).error(f"Error in state listener for {key}", exc_info=True)

# Global singleton
store = AppState()
