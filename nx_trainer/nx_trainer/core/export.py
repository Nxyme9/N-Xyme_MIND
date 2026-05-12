from pathlib import Path


class Exporter:
    def __init__(self, model_path: Path, output_path: Path, format: str = "hf", quantization: str = None):
        self.model_path = model_path
        self.output_path = output_path
        self.format = format
        self.quantization = quantization

    def export(self):
        print(f"Exporting {self.model_path} to {self.format} format")