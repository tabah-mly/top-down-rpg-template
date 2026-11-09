import pygame


class SpriteSheet:
    def __init__(self, sheet_path, frame_width, frame_height, scale=5, speed=0.2):
        self.speed = speed
        self.scale = scale

        self.sheet = pygame.image.load(sheet_path).convert_alpha()
        self.sheet_width, self.sheet_height = self.sheet.get_size()

        self.frame_width = frame_width
        self.frame_height = frame_height

        self.frame_count = self.sheet_width // self.frame_width

        self.frames = []
        self._generate_frames()

        self.frame_index = 0
        self.image = self.frames[0]
        self.timer = 0

        self.masks = [pygame.mask.from_surface(frame) for frame in self.frames]

    def _generate_frames(self):
        for i in range(self.frame_count):
            frame = pygame.Surface(
                (self.frame_width, self.frame_height),
                pygame.SRCALPHA,
            )

            frame.blit(
                self.sheet,
                (0, 0),
                (i * self.frame_width, 0, self.frame_width, self.frame_height),
            )

            frame = pygame.transform.scale(
                frame, (self.frame_width * self.scale, self.frame_height * self.scale)
            )

            self.frames.append(frame)

    def update(self, dt):
        self.timer += dt

        if self.timer >= self.speed:
            self.timer -= self.speed
            self.frame_index = (self.frame_index + 1) % len(self.frames)
            self.image = self.frames[self.frame_index]

    def reset(self):
        self.frame_index = 0
        self.timer = 0
        self.image = self.frames[0]

    @property
    def mask(self):
        return self.masks[self.frame_index]
