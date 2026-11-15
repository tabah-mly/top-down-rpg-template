
import json
from pathlib import Path


class EntityDatabase:
    def __init__(self):
        self.entities = {}

        data_dir = Path(__file__).parent / "data" / "entities"

        self.load_category("npc", data_dir / "npcs.json")
        self.load_category("enemy", data_dir / "enemies.json")
        self.load_category("boss", data_dir / "bosses.json")

    def load_category(self, category, path):
        with open(path, "r", encoding="utf-8") as file:
            self.entities[category] = json.load(file)

    def get(self, category, entity_id, overrides=None):
        definitions = self.entities.get(category, {})

        if entity_id not in definitions:
            raise ValueError(
                f"Unknown {category} entity: '{entity_id}'"
            )

        # Copy the definition so one map instance
        # cannot accidentally modify another.
        config = dict(definitions[entity_id])

        # Tiled properties override JSON values.
        if overrides:
            config.update(overrides)

        return config
