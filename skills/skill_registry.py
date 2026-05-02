import os
import json

# Skill registry to manage and store skills
class skill_registry:
    def __init__(self):
        # Get the absolute path of the directory containing this file
        self.skill_dir = os.path.dirname(os.path.abspath(__file__))
        self.skills = [f for f in os.listdir(self.skill_dir) if f.endswith('.md')]
        self.skill_descriptions = {}

    def register_skills(self):
        self.skill_descriptions = {}
        for skill in self.skills:
            skill_path = os.path.join(self.skill_dir, skill)
            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    line = f.readline().strip()
                    if line.startswith("DESCRIPTION:"):
                        line = line.replace("DESCRIPTION:", "").strip()
                    self.skill_descriptions[skill] = line
            except Exception as e:
                print(f"Error loading skill {skill}: {e}")

    def get_skill(self, skill_name):
        return self.skill_descriptions.get(skill_name, None)

    def list_skills(self):
        return self.skill_descriptions
    
    def get_skill_content(self, skill_name):
        if skill_name in self.skills:
            skill_path = os.path.join(self.skill_dir, skill_name)
            try:
                with open(skill_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Error reading skill file: {e}"
        return f"Skill '{skill_name}' not found."




