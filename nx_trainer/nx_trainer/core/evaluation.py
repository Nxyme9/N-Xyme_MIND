from pathlib import Path


class Evaluator:
    def __init__(self, model_path: Path, data_path: Path, batch_size: int = 16):
        self.model_path = model_path
        self.data_path = data_path
        self.batch_size = batch_size

    def evaluate(self):
        return {"loss": 0.0, "perplexity": 0.0, "accuracy": 0.0}