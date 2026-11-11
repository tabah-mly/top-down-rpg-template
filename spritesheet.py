import pygame


class SpriteSheet:
    def __init__(self, sheet_path, frame_width, frame_height, scale=1):
        self.sheet = pygame.image.load(sheet_path).convert_alpha()

        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scale = scale

        self.frames = []
        self._generate_frames()

    def _generate_frames(self):
        sheet_width, sheet_height = self.sheet.get_size()

        columns = sheet_width // self.frame_width
        rows = sheet_height // self.frame_height

        for y in range(rows):
            for x in range(columns):
                frame = pygame.Surface(
                    (self.frame_width, self.frame_height), pygame.SRCALPHA
                )

                frame.blit(
                    self.sheet,
                    (0, 0),
                    (
                        x * self.frame_width,
                        y * self.frame_height,
                        self.frame_width,
                        self.frame_height,
                    ),
                )

                if self.scale != 1:
                    frame = pygame.transform.scale(
                        frame,
                        (self.frame_width * self.scale, self.frame_height * self.scale),
                    )

                self.frames.append(frame)

        return self.frames
