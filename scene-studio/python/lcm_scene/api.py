"""Lazy, cwd-independent execution API for the studio's top-level run.py."""
import importlib
import sys
from .paths import city_directory

LEGACY_MODULES = {
    "fetch_deepmimo_geometry": "lcm_scene.sources.fetch_deepmimo_geometry",
    "audit_deepmimo_scenarios": "lcm_scene.sources.audit_deepmimo_scenarios",
    "audit_deepmimo_path_states": "lcm_scene.sources.audit_deepmimo_path_states",
    "export_deepmimo_gallery": "lcm_scene.exporters.export_deepmimo_gallery",
    "export_verified": "lcm_scene.exporters.export_verified",
    "inspect_candidates": "lcm_scene.city.inspect_candidates",
    "screen_city_sources": "lcm_scene.city.screen_city_sources",
}


def run_module(module, args=()):
    """Call a module's main with scoped argv; restore the caller's arguments."""
    old = sys.argv
    try:
        sys.argv = [module, *map(str, args)]
        return importlib.import_module(module).main()
    finally:
        sys.argv = old


def generate(size):
    """Explicit generation only; importing this API never rewrites snapshots."""
    city_directory(size)  # Reject unsupported sizes before loading dependencies.
    if size == 4000:
        return run_module("lcm_scene.city.assemble_city")
    return run_module("lcm_scene.city.design_city_variants", ["--size", size])


def validate_exports(write_report=True):
    from .city.validate_city_variants import validate
    return {size: validate(city_directory(size), write_report=write_report)
            for size in (1000, 2000, 4000)}


def verify_test():
    return run_module("lcm_scene.verification.verify")


def run_legacy(name, args=()):
    try:
        module = LEGACY_MODULES[name.removesuffix(".py")]
    except KeyError as error:
        raise ValueError(f"Unknown legacy script: {name}") from error
    return run_module(module, args)
