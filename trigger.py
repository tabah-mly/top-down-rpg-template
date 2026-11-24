class Trigger:
    def __init__(self, shape, name, config=None):
        config = config or {}

        self.shape = shape
        self.name = name

        self.event = config.get("event", "enter")
        self.action = config.get("action", "print")
        self.message = config.get("message", "")
        self.once = config.get("once", False)

        self.target_map = config.get("target_map")
        self.target_spawn = config.get("target_spawn")

        # Quest integration
        self.quest_event = config.get("quest_event")
        self.quest_target = config.get("quest_target", name)

        self.inside = False
        self.activated = False

    def update(self, target_rect):
        is_inside = self.shape.collides(target_rect)

        entered = is_inside and not self.inside
        exited = self.inside and not is_inside

        activated = False

        if not (self.once and self.activated):
            if self.event == "enter" and entered:
                activated = True

            elif self.event == "exit" and exited:
                activated = True

            elif self.event == "stay" and is_inside:
                activated = True

        self.inside = is_inside

        if activated:
            self.activated = True

        return activated

    def draw_debug(self, surface, camera):
        self.shape.draw_debug(
            surface,
            camera,
            color=(255, 200, 0),
        )
