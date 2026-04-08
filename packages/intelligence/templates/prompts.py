"""Prompt Template Library

Provides standardized prompt templates for common task types.
Ensures consistent delegation quality across the system.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger("prompt-templates")


@dataclass
class PromptTemplate:
    """A prompt template for a specific task type."""
    id: str
    name: str
    description: str
    category: str
    template: str
    variables: List[str] = field(default_factory=list)
    version: str = "1.0"
    effectiveness: float = 0.0
    usage_count: int = 0
    
    def render(self, **kwargs) -> str:
        """Render the template with provided variables."""
        prompt = self.template
        for var in self.variables:
            value = kwargs.get(var, f"[{var}]")
            prompt = prompt.replace(f"{{{var}}}", str(value))
        return prompt
    
    def record_usage(self, success: bool, learning_rate: float = 0.1):
        """Record template usage and update effectiveness."""
        self.usage_count += 1
        target = 1.0 if success else 0.0
        self.effectiveness = self.effectiveness + learning_rate * (target - self.effectiveness)


class PromptTemplateLibrary:
    """Library of prompt templates for delegation."""
    
    def __init__(self, templates_file: str = ".sisyphus/prompt_templates.json"):
        self.templates_file = Path(templates_file)
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load templates from file or initialize defaults."""
        if self.templates_file.exists():
            try:
                with open(self.templates_file) as f:
                    data = json.load(f)
                
                for template_id, template_data in data.items():
                    self._templates[template_id] = PromptTemplate(
                        id=template_id,
                        name=template_data.get('name', template_id),
                        description=template_data.get('description', ''),
                        category=template_data.get('category', 'general'),
                        template=template_data.get('template', ''),
                        variables=template_data.get('variables', []),
                        version=template_data.get('version', '1.0'),
                        effectiveness=template_data.get('effectiveness', 0.0),
                        usage_count=template_data.get('usage_count', 0)
                    )
            except Exception as e:
                logger.error(f"Error loading templates: {e}")
        
        # Initialize default templates if none loaded
        if not self._templates:
            self._initialize_default_templates()
    
    def _initialize_default_templates(self):
        """Initialize default prompt templates."""
        defaults = [
            PromptTemplate(
                id="code_implementation",
                name="Code Implementation",
                description="Template for implementing code changes",
                category="implementation",
                template="""I need you to implement the following task:

TASK: {task_description}

EXPECTED OUTCOME:
- {expected_outcome}

REQUIRED TOOLS: {required_tools}

MUST DO:
- {must_do}

MUST NOT DO:
- {must_not_do}

CONTEXT:
- Working directory: {working_directory}
- Existing patterns: {existing_patterns}
- Test location: {test_location}

Please implement this task following the above requirements.""",
                variables=["task_description", "expected_outcome", "required_tools", "must_do", "must_not_do", "working_directory", "existing_patterns", "test_location"]
            ),
            PromptTemplate(
                id="bug_fix",
                name="Bug Fix",
                description="Template for fixing bugs",
                category="fix",
                template="""I need you to fix the following bug:

BUG DESCRIPTION: {bug_description}

EXPECTED BEHAVIOR: {expected_behavior}

INVESTIGATION:
- First, investigate the root cause
- Check existing error handling patterns
- Verify the fix doesn't break existing functionality

FIX REQUIREMENTS:
- Minimal changes to fix the issue
- Follow existing code patterns
- Add tests if applicable
- Run existing tests to verify

CONTEXT:
- Error message: {error_message}
- Affected files: {affected_files}
- Related code: {related_code}

Please fix this bug following the above requirements.""",
                variables=["bug_description", "expected_behavior", "error_message", "affected_files", "related_code"]
            ),
            PromptTemplate(
                id="code_review",
                name="Code Review",
                description="Template for reviewing code",
                category="review",
                template="""Please review the following code:

CODE TO REVIEW: {code_snippet}

REVIEW CRITERIA:
- Code quality and readability
- Security vulnerabilities
- Performance implications
- Test coverage
- Documentation

REVIEW FORMAT:
1. Overall assessment
2. Strengths
3. Issues found (with severity)
4. Recommendations
5. Specific line-by-line comments

CONTEXT:
- Purpose: {code_purpose}
- Requirements: {requirements}
- Constraints: {constraints}

Please provide a comprehensive review.""",
                variables=["code_snippet", "code_purpose", "requirements", "constraints"]
            ),
            PromptTemplate(
                id="research_task",
                name="Research Task",
                description="Template for research and investigation",
                category="research",
                template="""I need you to research the following:

RESEARCH TOPIC: {research_topic}

RESEARCH GOALS:
- {research_goals}

SEARCH SCOPE:
- {search_scope}

OUTPUT FORMAT:
- Summary of findings
- Key patterns identified
- Recommendations
- References to existing code

CONTEXT:
- Project structure: {project_structure}
- Existing patterns: {existing_patterns}
- Constraints: {constraints}

Please conduct thorough research and provide actionable findings.""",
                variables=["research_topic", "research_goals", "search_scope", "project_structure", "existing_patterns", "constraints"]
            ),
            PromptTemplate(
                id="test_writing",
                name="Test Writing",
                description="Template for writing tests",
                category="testing",
                template="""I need you to write tests for the following:

CODE TO TEST: {code_to_test}

TEST REQUIREMENTS:
- {test_requirements}

TEST TYPES:
- Unit tests for individual functions
- Integration tests for component interactions
- Edge case coverage
- Error handling verification

TEST FRAMEWORK: {test_framework}
TEST LOCATION: {test_location}

CONTEXT:
- Existing test patterns: {existing_test_patterns}
- Mock requirements: {mock_requirements}
- Coverage target: {coverage_target}

Please write comprehensive tests following the above requirements.""",
                variables=["code_to_test", "test_requirements", "test_framework", "test_location", "existing_test_patterns", "mock_requirements", "coverage_target"]
            ),
            PromptTemplate(
                id="documentation",
                name="Documentation",
                description="Template for writing documentation",
                category="documentation",
                template="""I need you to write documentation for:

TOPIC: {documentation_topic}

DOCUMENTATION TYPE: {doc_type}

TARGET AUDIENCE: {target_audience}

DOCUMENTATION STRUCTURE:
- Overview
- Installation/Setup
- Usage Examples
- API Reference
- Troubleshooting

CONTEXT:
- Code location: {code_location}
- Existing docs: {existing_docs}
- Style guide: {style_guide}

Please write clear, comprehensive documentation.""",
                variables=["documentation_topic", "doc_type", "target_audience", "code_location", "existing_docs", "style_guide"]
            ),
        ]
        
        for template in defaults:
            self._templates[template.id] = template
        
        self._save_templates()
    
    def _save_templates(self):
        """Save templates to file."""
        data = {}
        for template_id, template in self._templates.items():
            data[template_id] = {
                'id': template.id,
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'template': template.template,
                'variables': template.variables,
                'version': template.version,
                'effectiveness': template.effectiveness,
                'usage_count': template.usage_count
            }
        
        with open(self.templates_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[PromptTemplate]:
        """Get all templates in a category."""
        return [t for t in self._templates.values() if t.category == category]
    
    def get_best_template(self, category: str) -> Optional[PromptTemplate]:
        """Get the most effective template for a category."""
        templates = self.get_templates_by_category(category)
        if not templates:
            return None
        return max(templates, key=lambda t: t.effectiveness)
    
    def render_template(self, template_id: str, **kwargs) -> Optional[str]:
        """Render a template with provided variables."""
        template = self.get_template(template_id)
        if not template:
            return None
        
        rendered = template.render(**kwargs)
        template.record_usage(True)  # Assume success for now
        self._save_templates()
        return rendered
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get template library statistics."""
        stats = {
            'total_templates': len(self._templates),
            'by_category': {},
            'most_used': None,
            'most_effective': None
        }
        
        # Count by category
        for template in self._templates.values():
            if template.category not in stats['by_category']:
                stats['by_category'][template.category] = 0
            stats['by_category'][template.category] += 1
        
        # Most used
        if self._templates:
            most_used = max(self._templates.values(), key=lambda t: t.usage_count)
            stats['most_used'] = {
                'id': most_used.id,
                'name': most_used.name,
                'usage_count': most_used.usage_count
            }
            
            # Most effective
            most_effective = max(self._templates.values(), key=lambda t: t.effectiveness)
            stats['most_effective'] = {
                'id': most_effective.id,
                'name': most_effective.name,
                'effectiveness': most_effective.effectiveness
            }
        
        return stats


# Global template library instance
_template_library = None

def get_prompt_template_library() -> PromptTemplateLibrary:
    """Get or create the global prompt template library."""
    global _template_library
    if _template_library is None:
        _template_library = PromptTemplateLibrary()
    return _template_library


def get_template(template_id: str) -> Optional[PromptTemplate]:
    """Get a template by ID (convenience function).
    
    Args:
        template_id: The template ID to retrieve.
    
    Returns:
        PromptTemplate if found, None otherwise.
    """
    library = get_prompt_template_library()
    return library.get_template(template_id)
