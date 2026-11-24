import pygame


class OpeningSequence:
    def __init__(self, screen_width, screen_height, font_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font_manager = font_manager

        self.font = self.font_manager.get("main", 28)
        self.prompt_font = self.font_manager.get("main", 18)

        # Replace these with your actual story later.
        self.pages = [
            "Long before the kingdoms fell, the world lived in peace.",
            "Ancient powers watched over the lands, protecting all living things.",
            "But as time passed, mankind began to forget the old stories.",
            "And deep beneath the earth, something began to awaken...",
            "This is where our story begins.",
        ]

        self.current_page = 0

        # Typewriter effect
        self.visible_characters = 0
        self.characters_per_second = 35
        self.typewriter_timer = 0

        self.finished = False

        self.text_color = (225, 220, 205)
        self.prompt_color = (130, 125, 115)

        self.max_text_width = int(self.screen_width * 0.75)
        self.line_height = 42

    def update(self, dt):
        if self.finished:
            return

        current_text = self.pages[self.current_page]

        if self.visible_characters >= len(current_text):
            return

        self.typewriter_timer += dt * self.characters_per_second

        characters_to_show = int(self.typewriter_timer)

        if characters_to_show > 0:
            self.visible_characters = min(
                self.visible_characters + characters_to_show,
                len(current_text),
            )

            self.typewriter_timer -= characters_to_show

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return False

        if event.key == pygame.K_ESCAPE:
            self.finished = True
            return True

        if event.key == pygame.K_SPACE:
            current_text = self.pages[self.current_page]

            # First press: reveal the entire current passage.
            if self.visible_characters < len(current_text):
                self.visible_characters = len(current_text)
                return False

            # Second press: advance to the next passage.
            if self.current_page < len(self.pages) - 1:
                self.current_page += 1
                self.visible_characters = 0
                self.typewriter_timer = 0
            else:
                self.finished = True
                return True

        return False

    def wrap_text(self, text):
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = f"{current_line} {word}".strip()

            if self.font.size(test_line)[0] <= self.max_text_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)

                current_line = word

        if current_line:
            lines.append(current_line)

        return lines

    def draw(self, surface):
        surface.fill((0, 0, 0))

        current_text = self.pages[self.current_page]
        visible_text = current_text[: self.visible_characters]

        lines = self.wrap_text(visible_text)

        total_height = len(lines) * self.line_height

        start_y = (self.screen_height - total_height) // 2

        for index, line in enumerate(lines):
            text_surface = self.font.render(
                line,
                True,
                self.text_color,
            )

            text_rect = text_surface.get_rect(
                center=(
                    self.screen_width // 2,
                    start_y + index * self.line_height,
                )
            )

            surface.blit(text_surface, text_rect)

        # Continue prompt
        prompt = self.prompt_font.render(
            "SPACE  -  CONTINUE",
            True,
            self.prompt_color,
        )

        prompt_rect = prompt.get_rect(
            center=(
                self.screen_width // 2,
                self.screen_height - 55,
            )
        )

        surface.blit(prompt, prompt_rect)

    def reset(self):
        self.current_page = 0
        self.visible_characters = 0
        self.typewriter_timer = 0
        self.finished = False
