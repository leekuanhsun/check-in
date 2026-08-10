import json

import pytest

from company_map import list_companies, load_company_map, resolve_company_targets

SAMPLE_MAP = {
    "NVIDIA": {
        "aliases": ["輝達", "NVDA"],
        "targets": [
            {"url": "https://site-a.example/nvda", "category": "輝達概念股"},
            {"url": "https://site-b.example/nvda", "category": "輝達概念股"},
        ],
    },
    "APPLE": {
        "aliases": ["蘋果", "AAPL"],
        "targets": [{"url": "https://site-a.example/aapl", "category": "蘋果概念股"}],
    },
}


@pytest.fixture
def company_map_file(tmp_path):
    path = tmp_path / "company_map.json"
    path.write_text(json.dumps(SAMPLE_MAP, ensure_ascii=False), encoding="utf-8")
    return str(path)


def test_load_company_map(company_map_file):
    loaded = load_company_map(company_map_file)
    assert loaded == SAMPLE_MAP


@pytest.mark.parametrize("query", ["NVIDIA", "nvidia", "輝達", "NVDA", "nvda"])
def test_resolve_company_targets_matches_name_or_alias_case_insensitive(query):
    targets = resolve_company_targets(SAMPLE_MAP, query)
    assert targets == SAMPLE_MAP["NVIDIA"]["targets"]


def test_resolve_company_targets_unknown_company_returns_none():
    assert resolve_company_targets(SAMPLE_MAP, "TESLA") is None


def test_list_companies_sorted():
    assert list_companies(SAMPLE_MAP) == ["APPLE", "NVIDIA"]
