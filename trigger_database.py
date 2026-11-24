import json
from pathlib import Path


class TriggerDatabase:
    def __init__(self):
        self.triggers = {}

        data_path = Path(__file__).parent / "data" / "story" / "triggers.json"

        self.load(data_path)

    def load(self, path):
        with open(path, "r", encoding="utf-8") as file:
            self.triggers = json.load(file)

    def get_map_triggers(self, map_id):
        return self.triggers.get(map_id, {})

    def get(self, map_id, trigger_id):
        map_triggers = self.get_map_triggers(map_id)

        return map_triggers.get(trigger_id)
