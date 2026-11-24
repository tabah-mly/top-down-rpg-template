import pygame


class OpeningSequence:
    def __init__(self, screen_width, screen_height, font_manager, prologue):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font_manager = font_manager

        self.title_font = self.font_manager.get("main", 64)
        self.font = self.font_manager.get("main", 28)
        self.prompt_font = self.font_manager.get("main", 18)

        self.title = prologue.get("title", "")
        self.pages = prologue["pages"]

        self.phase = "title"
        self.current_page = 0

        # Typewriter effect
        self.visible_characters = 0
        self.characters_per_second = 35
        self.typewriter_timer = 0

        # Fade transition
        self.transition_alpha = 255
        self.fade_speed = 400

        self.finished = False

        self.text_color = (225, 220, 205)
        self.prompt_color = (130, 125, 115)

        self.max_text_width = int(self.screen_width * 0.75)
        self.line_height = 42

    def update(self, dt):
        if self.finished:
            return

        # Fade out at the end of the opening.
        if self.phase == "fade_out":
            self.transition_alpha = min(
                255,
                self.transition_alpha + self.fade_speed * dt,
            )

            if self.transition_alpha >= 255:
                self.finished = True

            return

        # Fade in at the beginning of each screen.
        if self.transition_alpha > 0:
            self.transition_alpha = max(
                0,
                self.transition_alpha - self.fade_speed * dt,
            )

        # Typewriter effect only runs during the story.
        if self.phase != "story":
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

        if event.key != pygame.K_SPACE:
            return False

        if self.phase == "title":
            self.phase = "story"
            self.current_page = 0
            self.visible_characters = 0
            self.typewriter_timer = 0
            self.transition_alpha = 255
            return False

        if self.phase == "fade_out":
            return False

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
            self.phase = "fade_out"
            self.transition_alpha = 0

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

        if self.phase == "title":
            title_surface = self.title_font.render(
                self.title,
                True,
                self.text_color,
            )

            title_rect = title_surface.get_rect(
                center=(
                    self.screen_width // 2,
                    self.screen_height // 2,
                )
            )

            surface.blit(title_surface, title_rect)

            prompt = self.prompt_font.render(
                "SPACE  -  BEGIN",
                True,
                self.prompt_color,
            )

        else:
            current_text = self.pages[self.current_page]
            visible_text = current_text[:self.visible_characters]

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

        # Draw fade overlay last.
        if self.transition_alpha > 0:
            fade_surface = pygame.Surface(
                (self.screen_width, self.screen_height),
            )

            fade_surface.fill((0, 0, 0))
            fade_surface.set_alpha(round(self.transition_alpha))

            surface.blit(fade_surface, (0, 0))

    def reset(self):
        self.phase = "title"
        self.current_page = 0
        self.visible_characters = 0
        self.typewriter_timer = 0
        self.transition_alpha = 255
        self.finished = False