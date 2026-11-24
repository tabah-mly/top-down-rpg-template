import json
from pathlib import Path


class StoryDatabase:
    def __init__(self):
        self.prologues = {}

        data_path = Path(__file__).parent / "data" / "story" / "prologue.json"

        self.load_prologues(data_path)

    def load_prologues(self, path):
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        prologue_id = data.get("id")

        if not prologue_id:
            raise ValueError("Prologue is missing an ID!")

        pages = data.get("pages")

        if not isinstance(pages, list) or not pages:
            raise ValueError(f"Prologue '{prologue_id}' has no valid pages!")

        if not all(isinstance(page, str) and page.strip() for page in pages):
            raise ValueError(f"Prologue '{prologue_id}' contains an invalid page!")

        self.prologues[prologue_id] = data

    def get_prologue(self, prologue_id):
        prologue = self.prologues.get(prologue_id)

        if prologue is None:
            raise ValueError(f"Unknown prologue ID: '{prologue_id}'")

        return prologue
