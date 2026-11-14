import pygame


class DialogWindow:
    def __init__(self, screen_width, screen_height, font_manager):
        self.image = pygame.image.load("assets/imgs/system/window_dialog.png").convert_alpha()

        # Keep the image's original aspect ratio.
        # self.width = screen_width - 80
        # self.height = round(
        #     self.width * self.image.get_height() / self.image.get_width()
        # )

        # self.image = pygame.transform.smoothscale(self.image, (self.width, self.height))

        # self.image = pygame.image.load(
        #     "assets/imgs/system/window.png"
        # ).convert_alpha()

        self.width, self.height = self.image.get_size()

        self.x = (screen_width - self.width) // 2
        self.y = screen_height - self.height - 32

        self.font_manager = font_manager
        self.font = self.font_manager.get("main", 22)
        self.prompt_font = self.font_manager.get("main", 20)

        # self.font = pygame.font.Font(None, 30)
        # self.prompt_font = pygame.font.Font(None, 22)

        self.active = False
        self.pages = []
        self.current_page = 0

        self.text_margin_x = 48
        self.text_margin_y = 35
        self.max_text_width = self.width - self.text_margin_x * 2

        self.line_height = 32
        self.max_lines = 3

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

    def open(self, message):
        lines = self.wrap_text(message)

        self.pages = [
            lines[i : i + self.max_lines] for i in range(0, len(lines), self.max_lines)
        ]

        if not self.pages:
            self.pages = [[]]

        self.current_page = 0
        self.active = True

    def advance(self):
        if not self.active:
            return

        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
        else:
            self.active = False

    def draw(self, surface):
        if not self.active:
            return

        surface.blit(self.image, (self.x, self.y))

        lines = self.pages[self.current_page]

        for i, line in enumerate(lines):
            # text_surface = self.font.render(line, True, (255, 255, 255))
            text_surface = self.font.render(line, False, (255, 255, 255))

            surface.blit(
                text_surface,
                (
                    self.x + self.text_margin_x,
                    self.y + self.text_margin_y + i * self.line_height,
                ),
            )

        prompt = self.prompt_font.render("SPACE / ENTER  >", True, (210, 210, 220))

        prompt_rect = prompt.get_rect(
            bottomright=(self.x + self.width - 42, self.y + self.height - 20)
        )

        surface.blit(prompt, prompt_rect)
