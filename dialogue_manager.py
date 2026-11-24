import json
from pathlib import Path


class DialogueManager:
    def __init__(self, dialogue_database):
        self.dialogue_database = dialogue_database
        self.routes = {}

        data_path = Path(__file__).parent / "data" / "story" / "npc_dialogues.json"

        self.load(data_path)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as file:
            self.routes = json.load(file)

    def get_dialogue(self, npc, quest_manager, story_state):
        rules = self.routes.get(npc.entity_id, [])

        # First matching rule wins.
        for rule in rules:
            conditions = rule.get("conditions", [])

            if self.conditions_met(conditions, quest_manager, story_state):
                dialogue_id = rule["dialogue_id"]

                return {
                    "id": dialogue_id,
                    "content": self.dialogue_database.get(dialogue_id),
                }

        # If this NPC has configured routes but none match,
        # don't fall back to its static dialogue.
        if npc.entity_id in self.routes:
            return None

        # Backward compatibility for NPCs without configured routes.
        if npc.dialogue_id:
            return {
                "id": npc.dialogue_id,
                "content": self.dialogue_database.get(npc.dialogue_id),
            }

        return None

    def conditions_met(self, conditions, quest_manager, story_state):
        # Every condition in a rule must pass (AND logic).
        for condition in conditions:
            condition_type = condition.get("type")

            if condition_type == "quest_active":
                if quest_manager.active_quest_id != condition.get("quest_id"):
                    return False

                objective_id = condition.get("objective_id")

                if objective_id:
                    objective = quest_manager.current_objective

                    if not objective:
                        return False

                    if objective.get("id") != objective_id:
                        return False

            elif condition_type == "quest_completed":
                quest_id = condition.get("quest_id")

                if quest_id not in quest_manager.completed_quests:
                    return False

            elif condition_type == "story_flag":
                flag = condition.get("flag")
                expected_value = condition.get("value", True)

                if story_state.has_flag(flag) != expected_value:
                    return False

            else:
                raise ValueError(
                    f"Unknown dialogue condition: '{condition_type}'"
                )

        return True