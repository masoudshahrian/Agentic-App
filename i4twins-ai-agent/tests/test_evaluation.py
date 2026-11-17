import json

import pytest

from evaluation.evaluate import DATASET, main
from evaluation.metrics import Record, compute_metrics


def test_dataset_is_well_formed():
    cases = json.loads(DATASET.read_text(encoding="utf-8"))
    assert len(cases) == 15
    for case in cases:
        assert {"id", "prompt", "expected_skills", "expected_language", "clarification_required",
                "explanation"} <= set(case)
        assert len(case["expected_skills"]) <= 2
    assert any(c["expected_language"] == "fa" for c in cases)
    assert any(len(c["expected_skills"]) == 2 for c in cases)
    assert any(c["clarification_required"] for c in cases)


def test_metrics_hand_computed():
    records = [
        Record(("calculator",), ("calculator",), False, False, "en"),
        Record(("translator",), ("summarizer",), False, False, "fa"),
        Record(("summarizer", "translator"), ("summarizer", "translator"), False, False, "fa"),
        Record(("translator",), ("translator",), True, False, "en"),
    ]
    m = compute_metrics(records)
    assert m["exact_skill_set_accuracy"] == 0.75
    assert m["multi_skill_detection_accuracy"] == 1.0
    assert m["clarification_accuracy"] == 0.75
    assert m["persian_routing_accuracy"] == 0.5
    assert m["per_skill"]["calculator"]["f1"] == 1.0
    assert m["per_skill"]["summarizer"]["precision"] == 0.5     # 1 TP, 1 FP
    assert m["per_skill"]["translator"]["recall"] == pytest.approx(2 / 3)
    assert m["per_skill"]["general_chat"]["precision"] is None  # undefined, not faked


def test_offline_evaluation_runs_without_api_key(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("evaluation.evaluate.RESULTS", tmp_path)
    assert main(["--offline"]) == 0
    report = json.loads((tmp_path / "offline_baseline.json").read_text(encoding="utf-8"))
    assert report["metrics"]["n"] == 15 and report["mode"] == "offline"


def test_live_evaluation_without_key_exits_cleanly(monkeypatch, capsys):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr("app.config.load_dotenv", lambda *a, **k: None)
    assert main([]) == 2
    assert "not run" in capsys.readouterr().err
