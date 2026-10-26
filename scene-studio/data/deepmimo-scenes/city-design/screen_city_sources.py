"""Compatibility entry point; implementation lives in scene-studio/python."""
import runpy
import sys
from pathlib import Path

STUDIO_ROOT = next(p for p in Path(__file__).resolve().parents if p.name == "scene-studio")
sys.path.insert(0, str(STUDIO_ROOT / "python"))
if __name__ == "__main__":
    runpy.run_module("lcm_scene.city.screen_city_sources", run_name="__main__")
