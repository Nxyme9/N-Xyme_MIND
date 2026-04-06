"""Template Manager — Project templates"""

import json, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

TEMPLATES = {
    "basic_project": {
        "name": "Basic Project",
        "files": ["README.md", "src/main.py", "requirements.txt"],
    },
    "web_app": {"name": "Web App", "files": ["index.html", "style.css", "app.js", "server.py"]},
    "api_service": {
        "name": "API Service",
        "files": ["main.py", "routes.py", "models.py", "config.py"],
    },
    "ml_project": {
        "name": "ML Project",
        "files": ["train.py", "model.py", "data_loader.py", "evaluate.py"],
    },
}


class TemplateManager:
    def __init__(self, template_dir: str = "data/templates"):
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def list_templates(self) -> List[str]:
        return list(TEMPLATES.keys()) + [f.stem for f in self.template_dir.glob("*.json")]

    def get_template(self, name: str) -> Dict:
        if name in TEMPLATES:
            return TEMPLATES[name]
        path = self.template_dir / f"{name}.json"
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def create_from_template(self, template_name: str, project_dir: str) -> Dict:
        template = self.get_template(template_name)
        if not template:
            return {"success": False, "error": "Template not found"}
        project = Path(project_dir)
        project.mkdir(parents=True, exist_ok=True)
        for filename in template.get("files", []):
            (project / filename).parent.mkdir(parents=True, exist_ok=True)
            (project / filename).write_text(f"# {filename}\n", encoding="utf-8")
        return {"success": True, "files": template.get("files", [])}
