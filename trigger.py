class Trigger:
    def __init__(
        self,
        shape,
        name="",
        event="enter",
        action="print",
        message="",
        once=False,
        target_map=None,
        target_spawn=None,
    ):
        self.shape = shape

        self.name = name
        self.event = event
        self.action = action
        self.message = message
        self.once = once

        self.target_map = target_map
        self.target_spawn = target_spawn

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
        self.shape.draw_debug(surface, camera, color=(255, 200, 0))
