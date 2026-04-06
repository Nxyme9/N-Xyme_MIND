#!/usr/bin/env python3
"""System Registry — Self-aware module catalog with AST-based discovery"""

import ast
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional


@dataclass
class ModuleCapability:
    name: str
    classes: List[str] = field(default_factory=list)
    functions: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    docstring: str = ""
    line_count: int = 0


class CapabilityExtractor(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = []
        self.docstring = ""

    def visit_Module(self, node):
        self.docstring = ast.get_docstring(node) or ""
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        self.classes.append({"name": node.name, "methods": methods})
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        if node.col_offset == 0:
            self.functions.append(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        if node.col_offset == 0:
            self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            self.imports.append(alias.name)

    def visit_ImportFrom(self, node):
        if node.module:
            for alias in node.names:
                self.imports.append(f"{node.module}.{alias.name}")


class SystemRegistry:
    def __init__(self, src_dir: str = "src"):
        self.src_dir = Path(src_dir)
        self.capabilities: Dict[str, ModuleCapability] = {}
        self.graph: Dict[str, Set[str]] = {}
        self.reverse: Dict[str, Set[str]] = {}

    def full_scan(self) -> int:
        count = 0
        for py_file in self.src_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or "__init__" in py_file.name:
                continue
            try:
                module_name = self._to_module_name(py_file)
                source = py_file.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source)

                extractor = CapabilityExtractor()
                extractor.visit(tree)

                internal_imports = {
                    imp for imp in extractor.imports
                    if imp.startswith("src.") or imp.split(".")[0] in ["brain", "api", "tui"]
                }

                cap = ModuleCapability(
                    name=module_name,
                    classes=[c["name"] for c in extractor.classes],
                    functions=extractor.functions,
                    imports=list(internal_imports),
                    docstring=extractor.docstring[:200],
                    line_count=len(source.splitlines()),
                )

                self.capabilities[module_name] = cap
                self.graph[module_name] = internal_imports
                for dep in internal_imports:
                    self.reverse.setdefault(dep, set()).add(module_name)

                count += 1
            except Exception:
                pass
        return count

    def discover(self, query: str) -> List[ModuleCapability]:
        query_lower = query.lower()
        results = []
        for cap in self.capabilities.values():
            if query_lower in cap.name.lower():
                results.append(cap)
            elif query_lower in cap.docstring.lower():
                results.append(cap)
            elif any(query_lower in c.lower() for c in cap.classes):
                results.append(cap)
            elif any(query_lower in f.lower() for f in cap.functions):
                results.append(cap)
        return results

    def who_can(self, capability: str) -> List[str]:
        return [cap.name for cap in self.discover(capability)]

    def impact_analysis(self, module: str) -> Dict:
        return {
            "module": module,
            "depends_on": list(self.graph.get(module, set())),
            "depended_by": list(self.reverse.get(module, set())),
        }

    def get_stats(self) -> Dict:
        return {
            "modules": len(self.capabilities),
            "total_classes": sum(len(c.classes) for c in self.capabilities.values()),
            "total_functions": sum(len(c.functions) for c in self.capabilities.values()),
            "dependency_edges": sum(len(v) for v in self.graph.values()),
        }

    def _to_module_name(self, path: Path) -> str:
        rel = path.relative_to(self.src_dir)
        return str(rel.with_suffix("")).replace("\\", ".").replace("/", ".")
