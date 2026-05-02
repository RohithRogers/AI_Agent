import os
from tools.registry import tool
from skills.skill_registry import skill_registry

# Initialize skill registry
skills = skill_registry()
skills.register_skills()

@tool(
    name="get_skill_content",
    description="Retrieves the detailed content/process flow of a specific skill to help with task execution.",
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {
                "type": "string",
                "description": "The name of the skill file (e.g., 'pdf_skill.md', 'read_codebase.md')."
            }
        },
        "required": ["skill_name"]
    }
)
def get_skill_content(skill_name: str):
    """Returns the content of the specified skill."""
    # Refresh skills list in case new ones were added
    skills.register_skills()
    return skills.get_skill_content(skill_name)
