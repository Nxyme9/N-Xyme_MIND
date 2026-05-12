from __future__ import annotations
import logging
import time
from dataclasses import dataclass
from typing import Optional

from .core.engine import DictationEngine, DictationConfig
import numpy as np

logger = logging.getLogger("nxyme_dictate.dual_pipeline")


@dataclass
class PipelineConfig:
    fast_model: str = "tiny"
    accurate_model: str = "large-v3-turbo"
    fast_threshold_ms: int = 500
    auto_switch: bool = True


class DualModelPipeline:
    def __init__(self, config: Optional[PipelineConfig] = None):
        self._config = config or PipelineConfig()
        self._fast_engine: Optional[DictationEngine] = None
        self._accurate_engine: Optional[DictationEngine] = None
        self._current_engine = None
        self._use_fast = True
        self._initialized = False

    def initialize(self) -> bool:
        try:
            logger.info("Initializing dual-model pipeline...")

            fast_config = DictationConfig(
                model=self._config.fast_model,
                device="cuda",
                compute_type="float16",
            )
            self._fast_engine = DictationEngine(fast_config)
            if not self._fast_engine.load():
                logger.warning("Fast model failed to load")
                return False
            logger.info(f"Fast model loaded: {self._config.fast_model}")

            accurate_config = DictationConfig(
                model=self._config.accurate_model,
                device="cuda",
                compute_type="float16",
            )
            self._accurate_engine = DictationEngine(accurate_config)
            if not self._accurate_engine.load():
                logger.warning("Accurate model failed to load")
            else:
                logger.info(f"Accurate model loaded: {self._config.accurate_model}")

            self._current_engine = self._fast_engine
            self._use_fast = True
            self._initialized = True

            logger.info("Dual-model pipeline ready")
            return True

        except Exception as e:
            logger.error(f"Dual-pipeline init failed: {e}")
            return False

    def transcribe(
        self,
        audio: np.ndarray,
        use_fast: bool = None,
    ) -> tuple[str, str]:
        if not self._initialized:
            return "[Pipeline not initialized]", "none"

        if use_fast is None:
            use_fast = self._use_fast

        engine = self._fast_engine if use_fast else self._accurate_engine
        model_name = self._config.fast_model if use_fast else self._config.accurate_model

        start = time.time()
        result = engine.transcribe(audio)
        latency_ms = int((time.time() - start) * 1000)

        logger.info(f"Transcribed with {model_name} in {latency_ms}ms")
        return result, model_name

    def transcribe_with_verification(
        self,
        audio: np.ndarray,
    ) -> tuple[str, str]:
        fast_result, fast_model = self.transcribe(audio, use_fast=True)

        if len(fast_result) < 50 and not fast_result.startswith("["):
            return fast_result, fast_model

        if self._accurate_engine and self._config.auto_switch:
            accurate_result, accurate_model = self.transcribe(audio, use_fast=False)

            if len(accurate_result) > len(fast_result):
                return accurate_result, accurate_model

        return fast_result, fast_model

    def switch_to_fast(self):
        self._use_fast = True
        self._current_engine = self._fast_engine
        logger.info("Switched to fast model")

    def switch_to_accurate(self):
        if self._accurate_engine:
            self._use_fast = False
            self._current_engine = self._accurate_engine
            logger.info("Switched to accurate model")

    @property
    def current_model(self) -> str:
        return self._config.fast_model if self._use_fast else self._config.accurate_model

    @property
    def is_fast_mode(self) -> bool:
        return self._use_fast

    def unload(self):
        if self._fast_engine:
            self._fast_engine.unload()
        if self._accurate_engine:
            self._accurate_engine.unload()
        logger.info("Dual-model pipeline unloaded")


def create_dual_pipeline(config: Optional[PipelineConfig] = None) -> DualModelPipeline:
    return DualModelPipeline(config)
