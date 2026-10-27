"""Canonical locations, derived from this file rather than the process cwd."""
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = STUDIO_ROOT.parent
PYTHON_ROOT = STUDIO_ROOT / "python"
WEB_ROOT = STUDIO_ROOT / "web"
DATA_ROOT = STUDIO_ROOT / "data"
DEEPMIMO_ROOT = DATA_ROOT / "deepmimo-scenes"
CITY_ROOT = DEEPMIMO_ROOT / "city-design"
CLASSIFICATION_ROOT = DEEPMIMO_ROOT / "classification"
PREVIEW_CACHE = CLASSIFICATION_ROOT / "cache/previews"
SOURCE_ROOT = DEEPMIMO_ROOT / "source"
SCENES_ROOT = DATA_ROOT / "scenes"
TEST_SCENE_ROOT = SCENES_ROOT / "test-4buildings"
RESEARCH_ROOT = REPO_ROOT / "docs/分析文档/LCMAgent"


def city_directory(size):
    """Keep the original 4 km root and independently designed smaller cities."""
    if size not in (1000, 2000, 4000):
        raise ValueError("city size must be 1000, 2000 or 4000 metres")
    return CITY_ROOT if size == 4000 else CITY_ROOT / f"city-{size // 1000}km"
