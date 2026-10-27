"""Compatibility entry point; implementation lives in scene-visualizer/python."""
import runpy
import sys
from pathlib import Path

STUDIO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "python/lcm_scene").is_dir())
sys.path.insert(0, str(STUDIO_ROOT / "python"))
if __name__ == "__main__":
    runpy.run_module("lcm_scene.sources.audit_deepmimo_path_states", run_name="__main__")
