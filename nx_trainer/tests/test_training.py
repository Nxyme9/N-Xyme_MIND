"""Tests for Rosetta Stone Trainer."""

import json
import tempfile
from pathlib import Path

import pytest

from nx_trainer.config import LoRAConfig, TrainingConfig, OllamaConfig
from nx_trainer.data_generator import DataGenerator
from nx_trainer.evaluator import Evaluator
from nx_trainer.trainer import Trainer


class TestDataGenerator:
    """Tests for DataGenerator class."""

    def test_init_default_tools(self):
        """Test initialization with default tools."""
        generator = DataGenerator()
        assert generator.tools is not None
        assert len(generator.tools) > 0

    def test_init_custom_tools(self):
        """Test initialization with custom tools."""
        custom_tools = {
            "custom_tool": {"arg1": "str"},
        }
        generator = DataGenerator(tools=custom_tools)
        assert generator.tools == custom_tools

    def test_generate_returns_list(self):
        """Test that generate returns a list."""
        generator = DataGenerator()
        result = generator.generate(num_variations=2)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_generate_output_format(self):
        """Test that generate returns properly formatted output."""
        generator = DataGenerator()
        result = generator.generate(num_variations=1)

        item = result[0]
        assert "input" in item
        assert "output" in item
        assert "tool" in item
        assert "args" in item

        # Check output format
        assert "[TOOL_CALL]" in item["output"]
        assert "[/TOOL_CALL]" in item["output"]

    def test_generate_with_output_path(self):
        """Test generate saves to file."""
        generator = DataGenerator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            result = generator.generate(num_variations=2, output_path=output_path)

            assert output_path.exists()
            with open(output_path) as f:
                loaded = [json.loads(line) for line in f]

            assert len(loaded) == len(result)
        finally:
            output_path.unlink(missing_ok=True)

    def test_save_method(self):
        """Test save method."""
        generator = DataGenerator()
        data = [{"input": "test", "output": "result", "tool": "test_tool", "args": {}}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            generator.save(data, output_path)
            assert output_path.exists()
        finally:
            output_path.unlink(missing_ok=True)

    def test_load_method(self):
        """Test load method."""
        generator = DataGenerator()
        data = [{"input": "test", "output": "result", "tool": "test_tool", "args": {}}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)
            for item in data:
                f.write(json.dumps(item) + "\n")

        try:
            loaded = generator.load(output_path)
            assert loaded == data
        finally:
            output_path.unlink(missing_ok=True)

    def test_prepare_for_fine_tuning(self):
        """Test prepare_for_fine_tuning converts to correct format."""
        generator = DataGenerator()
        data = [{"input": "test", "output": "result", "tool": "test_tool", "args": {}}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            input_path = Path(f.name)
            for item in data:
                f.write(json.dumps(item) + "\n")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            formatted = generator.prepare_for_fine_tuning(input_path, output_path)

            assert len(formatted) == 1
            assert "messages" in formatted[0]
            assert len(formatted[0]["messages"]) == 3  # system, user, assistant

            # Check message roles
            roles = [m["role"] for m in formatted[0]["messages"]]
            assert "system" in roles
            assert "user" in roles
            assert "assistant" in roles
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)


class TestEvaluator:
    """Tests for Evaluator class."""

    def test_parse_tool_call_basic(self):
        """Test basic tool call parsing."""
        evaluator = Evaluator()
        output = '[TOOL_CALL]{tool => "memory_search", args => { --query "security" }}[/TOOL_CALL]'

        result = evaluator.parse_tool_call(output)

        assert result is not None
        assert result["tool"] == "memory_search"
        assert result["args"]["query"] == "security"

    def test_parse_tool_call_no_args(self):
        """Test tool call with no arguments."""
        evaluator = Evaluator()
        output = '[TOOL_CALL]{tool => "get_active_context", args => { }}[/TOOL_CALL]'

        result = evaluator.parse_tool_call(output)

        assert result is not None
        assert result["tool"] == "get_active_context"
        assert result["args"] == {}

    def test_parse_tool_call_invalid(self):
        """Test parsing invalid output."""
        evaluator = Evaluator()
        output = "This is just text"

        result = evaluator.parse_tool_call(output)

        assert result is None

    def test_evaluate_output_correct(self):
        """Test evaluation when output is correct."""
        evaluator = Evaluator()
        output = '[TOOL_CALL]{tool => "memory_search", args => { --query "security" }}[/TOOL_CALL]'

        result = evaluator.evaluate_output(output, "memory_search")

        assert result["correct"] is True
        assert result["tool_match"] is True

    def test_evaluate_output_incorrect_tool(self):
        """Test evaluation when wrong tool."""
        evaluator = Evaluator()
        output = '[TOOL_CALL]{tool => "read_file", args => { --path "test" }}[/TOOL_CALL]'

        result = evaluator.evaluate_output(output, "memory_search")

        assert result["correct"] is False
        assert result["tool_match"] is False

    def test_default_test_cases(self):
        """Test default test cases."""
        evaluator = Evaluator()
        test_cases = evaluator.default_test_cases

        assert len(test_cases) > 0
        assert all(isinstance(tc, tuple) and len(tc) == 2 for tc in test_cases)


class TestTrainer:
    """Tests for Trainer class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        trainer = Trainer()

        assert trainer.lora_config is not None
        assert trainer.training_config is not None
        assert trainer.ollama_config is not None

    def test_init_custom_configs(self):
        """Test initialization with custom configs."""
        lora_config = LoRAConfig(r=8, alpha=16)
        training_config = TrainingConfig(num_train_epochs=5)
        ollama_config = OllamaConfig(model_name="llama2:7b")

        trainer = Trainer(
            lora_config=lora_config,
            training_config=training_config,
            ollama_config=ollama_config,
        )

        assert trainer.lora_config.r == 8
        assert trainer.training_config.num_train_epochs == 5
        assert trainer.ollama_config.model_name == "llama2:7b"

    def test_check_unsloth_available(self):
        """Test Unsloth availability check."""
        result = Trainer.check_unsloth_available()
        assert isinstance(result, bool)

    def test_check_ollama_available(self):
        """Test Ollama availability check."""
        result = Trainer.check_ollama_available()
        assert isinstance(result, bool)


class TestLoRAConfig:
    """Tests for LoRAConfig."""

    def test_default_values(self):
        """Test default values."""
        config = LoRAConfig()

        assert config.r == 32  # Updated to higher rank for more capacity
        assert config.alpha == 64
        assert config.dropout == 0.05  # Slight dropout for regularization
        assert config.bias == "none"

    def test_custom_values(self):
        """Test custom values."""
        config = LoRAConfig(r=8, alpha=16, dropout=0.1)

        assert config.r == 8
        assert config.alpha == 16
        assert config.dropout == 0.1


class TestTrainingConfig:
    """Tests for TrainingConfig."""

    def test_default_values(self):
        """Test default values."""
        config = TrainingConfig()

        # Note: model defaults to 1.5B for better tool-calling capacity
        assert "Qwen/Qwen2.5-" in config.model_name
        assert config.max_seq_length == 2048  # Increased for tool definitions
        assert config.num_train_epochs == 3


class TestDataGeneratorMultiTurn:
    """Tests for multi-turn conversation generation."""

    def test_generate_multi_turn_conversation(self):
        """Test multi-turn conversation generation."""
        generator = DataGenerator()
        conversations = generator.generate_multi_turn_conversation(
            num_conversations=2,
            turns_per_conversation=3,
        )

        assert len(conversations) == 2
        for conv in conversations:
            assert "conversation_id" in conv
            assert "scenario" in conv
            assert "turns" in conv
            assert len(conv["turns"]) == 3

            # Check turn structure
            for turn in conv["turns"]:
                assert "turn_id" in turn
                assert "input" in turn
                assert "output" in turn
                assert "tool" in turn
                assert "[TOOL_CALL]" in turn["output"]

    def test_generate_multi_turn_with_output_path(self):
        """Test multi-turn saves to file."""
        generator = DataGenerator()

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            output_path = Path(f.name)

        try:
            conversations = generator.generate_multi_turn_conversation(
                num_conversations=2,
                output_path=output_path,
            )

            assert output_path.exists()
            with open(output_path) as f:
                loaded = [json.loads(line) for line in f]

            assert len(loaded) == len(conversations)
        finally:
            output_path.unlink(missing_ok=True)

    def test_prepare_multi_turn_for_fine_tuning(self):
        """Test multi-turn conversion to fine-tuning format."""
        generator = DataGenerator()

        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            input_path = Path(f.name)

        conversations = generator.generate_multi_turn_conversation(
            num_conversations=1,
            turns_per_conversation=2,
        )

        with open(input_path, "w") as f:
            for conv in conversations:
                f.write(json.dumps(conv) + "\n")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            output_path = Path(f.name)

        try:
            formatted = generator.prepare_multi_turn_for_fine_tuning(input_path, output_path)

            assert len(formatted) >= 2  # At least 2 turns
            assert "messages" in formatted[0]
            assert "ground_truth" in formatted[0]
            assert "conversation_id" in formatted[0]
        finally:
            input_path.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)


class TestBatchInferrer:
    """Tests for BatchInferrer class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        from nx_trainer.batch_inferrer import BatchInferrer

        inferrer = BatchInferrer()

        assert inferrer.max_batch_size == 8
        assert inferrer.max_queue_size == 100
        assert inferrer.timeout_seconds == 30.0

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        from nx_trainer.batch_inferrer import BatchInferrer

        inferrer = BatchInferrer(
            max_batch_size=4,
            max_queue_size=50,
            timeout_seconds=10.0,
        )

        assert inferrer.max_batch_size == 4
        assert inferrer.max_queue_size == 50
        assert inferrer.timeout_seconds == 10.0

    def test_get_stats(self):
        """Test get_stats returns correct structure."""
        from nx_trainer.batch_inferrer import BatchInferrer

        inferrer = BatchInferrer(model_name="test-model")
        stats = inferrer.get_stats()

        assert "running" in stats
        assert "queue_size" in stats
        assert "max_batch_size" in stats
        assert "model_name" in stats
        assert stats["model_name"] == "test-model"


class TestStreamingInferrer:
    """Tests for StreamingInferrer class."""

    def test_init(self):
        """Test initialization."""
        from nx_trainer.batch_inferrer import StreamingInferrer

        inferrer = StreamingInferrer()

        assert inferrer._model is None
        assert inferrer._tokenizer is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
