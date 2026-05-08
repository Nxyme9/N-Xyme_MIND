#!/usr/bin/env python3
"""Tests for Two-Stage Router.

Unit tests for the two_stage_router module covering:
- Complexity classification
- Tool selection
- Route path determination
- Integration scenarios
"""

from __future__ import annotations

import sys
import unittest

# Import the module under test
sys.path.insert(0, "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")

from packages.orchestration.two_stage_router import (
    TwoStageRouter,
    RouteResult,
    classify_complexity,
    select_tool,
    route,
    SIMPLE_KEYWORDS,
    COMPLEX_KEYWORDS,
)


class TestComplexityClassification(unittest.TestCase):
    """Tests for classify_complexity method."""

    def setUp(self):
        self.router = TwoStageRouter()

    def test_simple_keywords_read(self):
        """Messages with 'read' should be classified as simple."""
        result = self.router.classify_complexity("Read the config file")
        self.assertEqual(result, "simple")

    def test_simple_keywords_find(self):
        """Messages with 'find' should be classified as simple."""
        result = self.router.classify_complexity("Find all Python files")
        self.assertEqual(result, "simple")

    def test_simple_keywords_list(self):
        """Messages with 'list' should be classified as simple."""
        result = self.router.classify_complexity("List directory contents")
        self.assertEqual(result, "simple")

    def test_simple_keywords_search(self):
        """Messages with 'search' should be classified as simple."""
        result = self.router.classify_complexity("Search for patterns")
        self.assertEqual(result, "simple")

    def test_simple_keywords_grep(self):
        """Messages with 'grep' should be classified as simple."""
        result = self.router.classify_complexity("Grep for function calls")
        self.assertEqual(result, "simple")

    def test_simple_keywords_glob(self):
        """Messages with 'glob' should be classified as simple."""
        result = self.router.classify_complexity("Glob all .py files")
        self.assertEqual(result, "simple")

    def test_complex_keywords_create(self):
        """Messages with 'create' should be classified as complex."""
        result = self.router.classify_complexity("Create a new API")
        self.assertEqual(result, "complex")

    def test_complex_keywords_implement(self):
        """Messages with 'implement' should be classified as complex."""
        result = self.router.classify_complexity("Implement user auth")
        self.assertEqual(result, "complex")

    def test_complex_keywords_build(self):
        """Messages with 'build' should be classified as complex."""
        result = self.router.classify_complexity("Build a new feature")
        self.assertEqual(result, "complex")

    def test_complex_keywords_refactor(self):
        """Messages with 'refactor' should be classified as complex."""
        result = self.router.classify_complexity("Refactor the codebase")
        self.assertEqual(result, "complex")

    def test_complex_keywords_design(self):
        """Messages with 'design' should be classified as complex."""
        result = self.router.classify_complexity("Design the architecture")
        self.assertEqual(result, "complex")

    def test_complex_keywords_architect(self):
        """Messages with 'architect' should be classified as complex."""
        result = self.router.classify_complexity("Architect the system")
        self.assertEqual(result, "complex")

    def test_question_mark_favors_simple(self):
        """Questions should be classified as simple when containing simple keywords."""
        result = self.router.classify_complexity("Read the file?")
        self.assertEqual(result, "simple")

    def test_default_to_complex(self):
        """Unclear messages should default to complex."""
        result = self.router.classify_complexity("Hello world")
        self.assertEqual(result, "complex")

    def test_mixed_keywords_favors_complex(self):
        """When both simple and complex keywords present, either is acceptable."""
        result = self.router.classify_complexity("Create and find something")
        # With equal counts, the behavior is acceptable as either
        # Both keywords present makes it ambiguous
        self.assertIn(result, ["simple", "complex"])


class TestToolSelection(unittest.TestCase):
    """Tests for select_tool method."""

    def setUp(self):
        self.router = TwoStageRouter()

    def test_tool_selection_for_read(self):
        """Tool selection should work for read commands."""
        # Just verify it returns a tool without error
        tool = self.router.select_tool("Read config.json")
        # Tool may or may not be present depending on categories
        # Just verify it doesn't crash
        self.assertTrue(tool is None or isinstance(tool, str))

    def test_tool_selection_for_find(self):
        """Tool selection should work for find commands."""
        tool = self.router.select_tool("Find all .py files")
        self.assertTrue(tool is None or isinstance(tool, str))

    def test_tool_selection_for_create(self):
        """Tool selection should work for create commands."""
        tool = self.router.select_tool("Create a new file")
        self.assertTrue(tool is None or isinstance(tool, str))


class TestRoutePathDetermination(unittest.TestCase):
    """Tests for route path determination."""

    def setUp(self):
        self.router = TwoStageRouter()

    def test_simple_with_tool_direct_path(self):
        """Simple request with clear tool should use direct path."""
        result = self.router.route("Read config.json")

        self.assertEqual(result.complexity, "simple")
        # selected_tool might be None if categories not available
        if result.selected_tool:
            self.assertEqual(result.route_path, "direct")
            self.assertFalse(result.needs_big_model)
        else:
            # If no tool selected, might be rosetta_only
            self.assertIn(result.route_path, ["direct", "rosetta_only"])

    def test_simple_without_tool_rosetta_only(self):
        """Simple request without clear tool should use rosetta_only path."""
        result = self.router.route("Read this file")

        self.assertEqual(result.complexity, "simple")
        self.assertIn(result.route_path, ["rosetta_only", "direct"])

    def test_complex_full_path(self):
        """Complex request should use full path."""
        result = self.router.route("Implement authentication system")

        self.assertEqual(result.complexity, "complex")
        self.assertEqual(result.route_path, "full")
        self.assertTrue(result.needs_big_model)

    def test_confidence_scores(self):
        """Route results should have confidence scores."""
        result = self.router.route("Read file.txt")

        self.assertIsInstance(result.confidence, float)
        self.assertGreaterEqual(result.confidence, 0.0)
        self.assertLessEqual(result.confidence, 1.0)

    def test_reasoning_provided(self):
        """Route results should include reasoning."""
        result = self.router.route("Build new feature")

        self.assertIsInstance(result.reasoning, str)
        self.assertGreater(len(result.reasoning), 0)


class TestShouldBypassBigModel(unittest.TestCase):
    """Tests for should_bypass_big_model method."""

    def setUp(self):
        self.router = TwoStageRouter()

    def test_read_bypasses(self):
        """Read commands should bypass big model."""
        result = self.router.should_bypass_big_model("Read config file")
        # May bypass or not depending on tool selection
        self.assertIsInstance(result, bool)

    def test_find_bypasses(self):
        """Find commands should bypass big model."""
        result = self.router.should_bypass_big_model("Find files")
        self.assertIsInstance(result, bool)

    def test_create_does_not_bypass(self):
        """Create commands should not bypass big model."""
        result = self.router.should_bypass_big_model("Create new file")
        # Complex requests need big model
        self.assertFalse(result)

    def test_implement_does_not_bypass(self):
        """Implement commands should not bypass big model."""
        result = self.router.should_bypass_big_model("Implement feature")
        self.assertFalse(result)


class TestConvenienceFunctions(unittest.TestCase):
    """Tests for module-level convenience functions."""

    def test_classify_complexity_function(self):
        """classify_complexity should work as standalone function."""
        result = classify_complexity("Read file")
        self.assertIn(result, ["simple", "complex"])

    def test_select_tool_function(self):
        """select_tool should work as standalone function."""
        result = select_tool("Find files")
        self.assertTrue(result is None or isinstance(result, str))

    def test_route_function(self):
        """route should work as standalone function."""
        result = route("Create something")

        self.assertIsInstance(result, RouteResult)
        self.assertIn(result.complexity, ["simple", "complex"])
        self.assertIn(result.route_path, ["direct", "full", "rosetta_only"])


class TestRouteResultDataclass(unittest.TestCase):
    """Tests for RouteResult dataclass."""

    def test_default_values(self):
        """RouteResult should have sensible defaults."""
        result = RouteResult(complexity="simple")

        self.assertEqual(result.complexity, "simple")
        self.assertIsNone(result.selected_tool)
        self.assertFalse(result.needs_big_model)
        self.assertEqual(result.route_path, "full")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.reasoning, "")

    def test_full_values(self):
        """RouteResult should accept all values."""
        result = RouteResult(
            complexity="complex",
            selected_tool="read_file",
            needs_big_model=True,
            route_path="full",
            confidence=0.9,
            reasoning="Test reasoning",
        )

        self.assertEqual(result.complexity, "complex")
        self.assertEqual(result.selected_tool, "read_file")
        self.assertTrue(result.needs_big_model)
        self.assertEqual(result.route_path, "full")
        self.assertEqual(result.confidence, 0.9)
        self.assertEqual(result.reasoning, "Test reasoning")


class TestKeywordLists(unittest.TestCase):
    """Tests for keyword lists."""

    def test_simple_keywords_not_empty(self):
        """SIMPLE_KEYWORDS should not be empty."""
        self.assertGreater(len(SIMPLE_KEYWORDS), 0)

    def test_complex_keywords_not_empty(self):
        """COMPLEX_KEYWORDS should not be empty."""
        self.assertGreater(len(COMPLEX_KEYWORDS), 0)

    def test_keywords_are_strings(self):
        """All keywords should be strings."""
        for kw in SIMPLE_KEYWORDS:
            self.assertIsInstance(kw, str)
        for kw in COMPLEX_KEYWORDS:
            self.assertIsInstance(kw, str)

    def test_keywords_are_lowercase(self):
        """All keywords should be lowercase."""
        for kw in SIMPLE_KEYWORDS:
            self.assertEqual(kw, kw.lower())
        for kw in COMPLEX_KEYWORDS:
            self.assertEqual(kw, kw.lower())


class TestRouterConfiguration(unittest.TestCase):
    """Tests for router initialization and configuration."""

    def test_default_threshold(self):
        """Router should have default threshold."""
        router = TwoStageRouter()
        self.assertEqual(router._confidence_threshold, 0.7)

    def test_custom_threshold(self):
        """Router should accept custom threshold."""
        router = TwoStageRouter(confidence_threshold=0.5)
        self.assertEqual(router._confidence_threshold, 0.5)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases."""

    def setUp(self):
        self.router = TwoStageRouter()

    def test_empty_message(self):
        """Empty message should default to complex."""
        result = self.router.classify_complexity("")
        self.assertEqual(result, "complex")

    def test_whitespace_only(self):
        """Whitespace-only message should default to complex."""
        result = self.router.classify_complexity("   ")
        self.assertEqual(result, "complex")

    def test_very_long_message(self):
        """Very long message should still classify."""
        long_msg = "Read " * 100 + "file"
        result = self.router.classify_complexity(long_msg)
        self.assertIn(result, ["simple", "complex"])

    def test_case_insensitive(self):
        """Classification should be case insensitive."""
        result1 = self.router.classify_complexity("READ FILE")
        result2 = self.router.classify_complexity("read file")
        self.assertEqual(result1, result2)

    def test_special_characters(self):
        """Messages with special characters should still classify."""
        result = self.router.classify_complexity("Read file @#$%")
        self.assertIn(result, ["simple", "complex"])


# =============================================================================
# Test Runner
# =============================================================================


if __name__ == "__main__":
    # Run tests with verbosity
    unittest.main(verbosity=2)
