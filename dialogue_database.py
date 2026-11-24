
import json
from pathlib import Path


class DialogueDatabase:
    def __init__(self):
        self.dialogues = {}

        data_path = (
            Path(__file__).parent
            / "data"
            / "story"
            / "dialogues.json"
        )

        self.load(data_path)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as file:
            self.dialogues = json.load(file)

    def get(self, dialogue_id):
        if not dialogue_id:
            return None

        dialogue = self.dialogues.get(dialogue_id)

        if dialogue is None:
            raise ValueError(
                f"Unknown dialogue ID: '{dialogue_id}'"
            )

        return dialogue
