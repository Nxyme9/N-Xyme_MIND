"""Tests for complexity_scorer.py."""

import pytest
from src.intelligence.complexity_scorer import score_complexity, ComplexityScorer


class TestScoreComplexity:
    def test_empty_input_defaults_to_l2(self):
        result = score_complexity("")
        assert result.level == 2
        assert result.confidence == 0.5
        assert "empty input" in result.reason

    def test_none_input_defaults_to_l2(self):
        result = score_complexity("")
        assert result.level == 2

    def test_l1_typo(self):
        result = score_complexity("fix typo in config")
        assert result.level == 1

    def test_l1_update_version(self):
        result = score_complexity("update version number to 2.0.0")
        assert result.level == 1

    def test_l1_rename_variable(self):
        result = score_complexity("rename variable x to y")
        assert result.level == 1

    def test_l2_fix_bug(self):
        result = score_complexity("fix bug in code")
        assert result.level == 2

    def test_l2_add_feature(self):
        result = score_complexity("add new feature to dashboard")
        assert result.level == 2

    def test_l3_refactor(self):
        result = score_complexity("refactor database connection pooling")
        assert result.level == 3

    def test_l3_auth(self):
        result = score_complexity("add JWT authentication to API")
        assert result.level == 3

    def test_l4_architecture(self):
        result = score_complexity("design microservices architecture")
        assert result.level == 4

    def test_l4_new_module(self):
        result = score_complexity("build new notification system from scratch")
        assert result.level == 4

    def test_l5_rewrite(self):
        result = score_complexity("rewrite entire codebase in TypeScript")
        assert result.level == 5

    def test_l5_overhaul(self):
        result = score_complexity("overhaul the entire system")
        assert result.level == 5

    def test_file_count_override_large(self):
        result = score_complexity("update 25 files in the project")
        assert result.level >= 4

    def test_file_count_override_medium(self):
        result = score_complexity("fix 12 files")
        assert result.level >= 3

    def test_file_count_override_small(self):
        result = score_complexity("do something with 7 items")
        assert result.level >= 2

    def test_global_scope_override(self):
        result = score_complexity("fix all the things in the entire codebase")
        assert result.level >= 4

    def test_global_scope_every(self):
        result = score_complexity("update every file in the system")
        assert result.level >= 4

    def test_confidence_single_reason(self):
        result = score_complexity("fix typo")
        assert result.confidence == 0.7

    def test_confidence_multiple_reasons(self):
        result = score_complexity("refactor all auth middleware and endpoints")
        assert result.confidence == 0.9

    def test_highest_wins_logic(self):
        result = score_complexity("fix typo and rewrite the entire system")
        assert result.level == 5

    def test_to_dict_format(self):
        result = score_complexity("fix typo")
        d = result.to_dict()
        assert "level" in d
        assert "confidence" in d
        assert "reason" in d

    def test_to_json_valid(self):
        import json

        result = score_complexity("fix typo")
        parsed = json.loads(result.to_json())
        assert parsed["level"] == 1


class TestComplexityScorerClass:
    def test_static_score(self):
        result = ComplexityScorer.score("fix bug")
        assert result.level == 2
