import json
from pathlib import Path


class StoryState:
    def __init__(self, event_manager):
        self.flags = set()
        self.event_rules = {}

        data_path = Path(__file__).parent / "data" / "story" / "story_events.json"

        self.load(data_path)

        # Subscribe once to each event type.
        for event_type in self.event_rules:
            event_manager.subscribe(
                event_type,
                self.handle_event,
            )

    def load(self, path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        for rule in data.get("events", []):
            event_type = rule.get("event")
            flag = rule.get("flag")

            if not event_type or not flag:
                raise ValueError(f"Invalid story event rule: {rule}")

            self.event_rules.setdefault(event_type, []).append(rule)

    def handle_event(self, event):
        event_type = event["type"]

        rules = self.event_rules.get(event_type, [])

        for rule in rules:
            conditions = rule.get("conditions", {})

            # Every configured condition must match.
            if all(event.get(key) == value for key, value in conditions.items()):
                self.set_flag(rule["flag"])

    def set_flag(self, flag):
        if flag not in self.flags:
            self.flags.add(flag)
            print(f"[STORY] Flag activated: {flag}")

    def remove_flag(self, flag):
        self.flags.discard(flag)

    def has_flag(self, flag):
        return flag in self.flags

    def reset(self):
        self.flags.clear()
