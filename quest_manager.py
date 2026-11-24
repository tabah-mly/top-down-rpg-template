class QuestManager:
    def __init__(self, quest_database, event_manager):
        self.quest_database = quest_database
        self.event_manager = event_manager

        self.active_quest_id = None
        self.completed_quests = set()

        self.objective_index = 0
        self.active = False

        self.event_manager.subscribe(
            "location_entered",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "npc_interacted",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "item_collected",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "enemy_defeated",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "trigger_activated",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "dialogue_completed",
            self.handle_event,
        )

        self.event_manager.subscribe(
            "cutscene_completed",
            self.handle_event,
        )

    @property
    def current_quest(self):
        if not self.active_quest_id:
            return None

        return self.quest_database.get(self.active_quest_id)

    @property
    def current_objective(self):
        quest = self.current_quest

        if not quest or not self.active:
            return None

        objectives = quest["objectives"]

        if self.objective_index >= len(objectives):
            return None

        return objectives[self.objective_index]

    def start_quest(self, quest_id):
        if self.active:
            raise RuntimeError("Another quest is already active.")

        if quest_id in self.completed_quests:
            return False

        self.quest_database.get(quest_id)

        self.active_quest_id = quest_id
        self.objective_index = 0
        self.active = True

        self.event_manager.emit(
            "quest_started",
            quest_id=quest_id,
        )

        self.check_objective()

        return True

    def handle_event(self, event):
        if not self.active:
            return

        objective = self.current_objective

        if not objective:
            return

        expected_event = objective.get("event")
        expected_target = objective.get("target")

        if event["type"] != expected_event:
            return

        if expected_target is not None:
            if event.get("target") != expected_target:
                return

        self.complete_objective()

    def complete_objective(self):
        objective = self.current_objective

        if not objective:
            return

        quest_id = self.active_quest_id
        objective_id = objective["id"]

        self.event_manager.emit(
            "objective_completed",
            quest_id=quest_id,
            objective_id=objective_id,
        )

        self.objective_index += 1

        if self.current_objective is None:
            self.complete_quest()
        else:
            self.check_objective()

        print(f"[QUEST] Objective completed: {objective_id}")

    def check_objective(self):
        objective = self.current_objective

        if objective:
            self.event_manager.emit(
                "objective_started",
                quest_id=self.active_quest_id,
                objective_id=objective["id"],
                description=objective["description"],
            )
            print(f"[QUEST] {self.active_quest_id}: " f"{objective['description']}")

    def complete_quest(self):
        quest_id = self.active_quest_id

        self.active = False
        self.completed_quests.add(quest_id)

        self.event_manager.emit(
            "quest_completed",
            quest_id=quest_id,
        )

        self.active_quest_id = None
        self.objective_index = 0

    def reset(self):
        self.active_quest_id = None
        self.completed_quests.clear()
        self.objective_index = 0
        self.active = False
