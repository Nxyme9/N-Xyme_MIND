"""Agent Skill Registry

Tracks agent capabilities and proficiency levels.
Matches tasks to agents based on required skills.
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field

logger = logging.getLogger("skill-registry")


@dataclass
class Skill:
    """A skill that agents can have."""
    name: str
    category: str
    description: str


@dataclass
class AgentSkills:
    """Skills and proficiency for an agent."""
    agent: str
    skills: Dict[str, float] = field(default_factory=dict)  # skill_name -> proficiency (0.0-1.0)
    total_tasks: int = 0
    success_count: int = 0
    
    def get_proficiency(self, skill_name: str) -> float:
        """Get proficiency level for a skill."""
        return self.skills.get(skill_name, 0.0)
    
    def update_proficiency(self, skill_name: str, success: bool, learning_rate: float = 0.1):
        """Update proficiency based on task outcome."""
        current = self.skills.get(skill_name, 0.5)
        target = 1.0 if success else 0.0
        self.skills[skill_name] = current + learning_rate * (target - current)
        self.total_tasks += 1
        if success:
            self.success_count += 1
    
    def get_match_score(self, required_skills: List[str]) -> float:
        """Get match score for required skills."""
        if not required_skills:
            return 0.5  # Default match
        
        scores = [self.get_proficiency(skill) for skill in required_skills]
        return sum(scores) / len(scores)


class SkillRegistry:
    """Registry of agent skills and capabilities."""
    
    def __init__(self, skills_file: str = ".sisyphus/skills.json"):
        self.skills_file = Path(skills_file)
        self.skills_file.parent.mkdir(parents=True, exist_ok=True)
        self._skills: Dict[str, Skill] = {}
        self._agent_skills: Dict[str, AgentSkills] = {}
        self._load_skills()
        self._load_agent_skills()
    
    def _load_skills(self):
        """Load skill taxonomy."""
        # Default skill taxonomy
        self._skills = {
            # Coding skills
            'python': Skill('python', 'coding', 'Python programming'),
            'javascript': Skill('javascript', 'coding', 'JavaScript programming'),
            'typescript': Skill('typescript', 'coding', 'TypeScript programming'),
            'sql': Skill('sql', 'coding', 'SQL database queries'),
            'api_design': Skill('api_design', 'coding', 'API design and implementation'),
            'testing': Skill('testing', 'coding', 'Writing and running tests'),
            'debugging': Skill('debugging', 'coding', 'Debugging and troubleshooting'),
            'refactoring': Skill('refactoring', 'coding', 'Code refactoring'),
            
            # Architecture skills
            'system_design': Skill('system_design', 'architecture', 'System architecture design'),
            'database_design': Skill('database_design', 'architecture', 'Database schema design'),
            'security': Skill('security', 'architecture', 'Security best practices'),
            'performance': Skill('performance', 'architecture', 'Performance optimization'),
            
            # Research skills
            'code_analysis': Skill('code_analysis', 'research', 'Code analysis and pattern recognition'),
            'documentation': Skill('documentation', 'research', 'Technical documentation'),
            'research': Skill('research', 'research', 'Research and investigation'),
            
            # Review skills
            'code_review': Skill('code_review', 'review', 'Code review and quality assessment'),
            'security_review': Skill('security_review', 'review', 'Security review'),
            'architecture_review': Skill('architecture_review', 'review', 'Architecture review'),
        }
    
    def _load_agent_skills(self):
        """Load agent skills from file or initialize defaults."""
        if self.skills_file.exists():
            try:
                with open(self.skills_file) as f:
                    data = json.load(f)
                
                for agent_name, agent_data in data.items():
                    self._agent_skills[agent_name] = AgentSkills(
                        agent=agent_name,
                        skills=agent_data.get('skills', {}),
                        total_tasks=agent_data.get('total_tasks', 0),
                        success_count=agent_data.get('success_count', 0)
                    )
            except Exception as e:
                logger.error(f"Error loading agent skills: {e}")
        
        # Initialize default agent skills if not loaded
        if not self._agent_skills:
            self._initialize_default_skills()
    
    def _initialize_default_skills(self):
        """Initialize default skills for all agents."""
        defaults = {
            'hephaestus': {
                'python': 0.9, 'javascript': 0.8, 'typescript': 0.8,
                'api_design': 0.8, 'testing': 0.7, 'debugging': 0.9,
                'refactoring': 0.8, 'sql': 0.7
            },
            'explore': {
                'code_analysis': 0.9, 'research': 0.9, 'documentation': 0.7,
                'debugging': 0.7, 'python': 0.7
            },
            'oracle': {
                'code_review': 0.9, 'architecture_review': 0.9, 'security_review': 0.8,
                'system_design': 0.8, 'security': 0.8
            },
            'momus': {
                'code_review': 0.8, 'security_review': 0.9, 'architecture_review': 0.8,
                'debugging': 0.7
            },
            'prometheus': {
                'system_design': 0.9, 'database_design': 0.8, 'api_design': 0.8,
                'performance': 0.7, 'security': 0.7
            },
            'metis': {
                'system_design': 0.9, 'architecture_review': 0.8, 'research': 0.8,
                'performance': 0.7
            },
            'sisyphus-junior': {
                'python': 0.6, 'documentation': 0.8, 'testing': 0.5
            },
            'librarian': {
                'research': 0.9, 'documentation': 0.8, 'code_analysis': 0.7
            }
        }
        
        for agent, skills in defaults.items():
            self._agent_skills[agent] = AgentSkills(
                agent=agent,
                skills=skills,
                total_tasks=0,
                success_count=0
            )
        
        self._save_agent_skills()
    
    def _save_agent_skills(self):
        """Save agent skills to file."""
        data = {}
        for agent_name, agent_skills in self._agent_skills.items():
            data[agent_name] = {
                'skills': agent_skills.skills,
                'total_tasks': agent_skills.total_tasks,
                'success_count': agent_skills.success_count
            }
        
        with open(self.skills_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_agent_skills(self, agent_name: str) -> Optional[AgentSkills]:
        """Get skills for an agent."""
        return self._agent_skills.get(agent_name)
    
    def update_agent_skill(self, agent_name: str, skill_name: str, success: bool, learning_rate: float = 0.1):
        """Update agent skill proficiency based on task outcome."""
        if agent_name not in self._agent_skills:
            self._agent_skills[agent_name] = AgentSkills(agent=agent_name)
        
        self._agent_skills[agent_name].update_proficiency(skill_name, success, learning_rate)
        self._save_agent_skills()
    
    def find_best_agent(self, required_skills: List[str]) -> Optional[str]:
        """Find the best agent for required skills."""
        if not required_skills:
            return 'hephaestus'  # Default
        
        best_agent = None
        best_score = -1
        
        for agent_name, agent_skills in self._agent_skills.items():
            score = agent_skills.get_match_score(required_skills)
            if score > best_score:
                best_score = score
                best_agent = agent_name
        
        return best_agent
    
    def get_all_skills(self) -> Dict[str, Skill]:
        """Get all available skills."""
        return self._skills.copy()
    
    def get_agent_summary(self) -> Dict[str, Any]:
        """Get summary of all agent skills."""
        summary = {}
        for agent_name, agent_skills in self._agent_skills.items():
            summary[agent_name] = {
                'skills': agent_skills.skills,
                'total_tasks': agent_skills.total_tasks,
                'success_rate': agent_skills.success_count / agent_skills.total_tasks if agent_skills.total_tasks > 0 else 0
            }
        return summary


# Global skill registry instance
_skill_registry = None

def get_skill_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _skill_registry
    if _skill_registry is None:
        _skill_registry = SkillRegistry()
    return _skill_registry
