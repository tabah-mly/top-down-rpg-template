import json
from pathlib import Path


class QuestDatabase:
    def __init__(self):
        self.quests = {}

        data_path = Path(__file__).parent / "data" / "story" / "quests.json"

        self.load(data_path)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as file:
            self.quests = json.load(file)

    def get(self, quest_id):
        quest = self.quests.get(quest_id)

        if quest is None:
            raise ValueError(f"Unknown quest ID: '{quest_id}'")

        return quest
