"""
Skill Registry.
"""
from typing import Dict, List, Type, Any
from src.core.skills.base import Skill
from src.core.skills.definitions import (
    ExploreProject, 
    ViewFile, 
    SearchCode, 
    EditFile, 
    RunTests,
    DeleteResource
)

class SkillRegistry:
    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._register_defaults()

    def _register_defaults(self):
        self.register(ExploreProject())
        self.register(ViewFile())
        self.register(SearchCode())
        self.register(EditFile())
        self.register(RunTests())
        self.register(DeleteResource())

    def register(self, skill: Skill):
        self._skills[skill.name] = skill

    def get_skill(self, name: str) -> Skill:
        if name not in self._skills:
            raise ValueError(f"Skill '{name}' not found.")
        return self._skills[name]

    def list_skills(self) -> List[Skill]:
        return list(self._skills.values())

    def get_schemas(self) -> List[Dict[str, Any]]:
        return [skill.to_schema() for skill in self._skills.values()]

registry = SkillRegistry()
