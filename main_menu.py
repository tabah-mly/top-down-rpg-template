import pygame


class MainMenu:
    def __init__(self, screen_width, screen_height, font_manager):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.font_manager = font_manager

        self.background = self._load_background("assets/imgs/system/screen.png")

        self.overlay = pygame.Surface(
            (self.screen_width, self.screen_height),
            pygame.SRCALPHA,
        )
        self.overlay.fill((0, 0, 0, 110))

        self.options = [
            {"label": "New Game", "action": "new_game", "enabled": True},
            {"label": "Continue", "action": "continue", "enabled": False},
            {"label": "Exit", "action": "exit", "enabled": True},
        ]

        self.selected_index = 0
        self.button_rects = []

        self.title_font = self.font_manager.get("main", 76)
        self.option_font = self.font_manager.get("main", 36)

        self._create_layout()

    def _load_background(self, path):
        image = pygame.image.load(path).convert()

        image_width, image_height = image.get_size()

        # Scale to cover the entire screen
        scale = max(
            self.screen_width / image_width,
            self.screen_height / image_height,
        )

        new_width = int(image_width * scale)
        new_height = int(image_height * scale)

        image = pygame.transform.smoothscale(
            image,
            (new_width, new_height),
        )

        # Crop the center
        crop_x = (new_width - self.screen_width) // 2
        crop_y = (new_height - self.screen_height) // 2

        image = image.subsurface(
            pygame.Rect(
                crop_x,
                crop_y,
                self.screen_width,
                self.screen_height,
            )
        ).copy()

        return image

    def _create_layout(self):
        self.button_rects.clear()

        button_width = 300
        button_height = 58
        spacing = 18

        total_height = (
            len(self.options) * button_height + (len(self.options) - 1) * spacing
        )

        start_y = (self.screen_height + 100 - total_height) // 2

        for index, option in enumerate(self.options):
            rect = pygame.Rect(
                (self.screen_width - button_width) // 2,
                start_y + index * (button_height + spacing),
                button_width,
                button_height,
            )

            self.button_rects.append(rect)

    def _move_selection(self, direction):
        index = self.selected_index

        for _ in range(len(self.options)):
            index = (index + direction) % len(self.options)

            if self.options[index]["enabled"]:
                self.selected_index = index
                return

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._move_selection(-1)

            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._move_selection(1)

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                option = self.options[self.selected_index]

                if option["enabled"]:
                    return option["action"]

        elif event.type == pygame.MOUSEMOTION:
            for index, rect in enumerate(self.button_rects):
                if rect.collidepoint(event.pos):
                    if self.options[index]["enabled"]:
                        self.selected_index = index

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for index, rect in enumerate(self.button_rects):
                    if rect.collidepoint(event.pos):
                        option = self.options[index]

                        if option["enabled"]:
                            self.selected_index = index
                            return option["action"]

        return None

    def draw(self, surface):
        # surface.fill((18, 20, 32))

        # Background image
        surface.blit(self.background, (0, 0))

        # Dark overlay
        surface.blit(self.overlay, (0, 0))

        # Title
        title = self.title_font.render("Top Down RPG", True, (235, 220, 180))

        title_rect = title.get_rect(
            center=(self.screen_width // 2, self.screen_height // 3)
        )

        surface.blit(title, title_rect)

        # Menu options
        for index, option in enumerate(self.options):
            rect = self.button_rects[index]

            selected = index == self.selected_index
            enabled = option["enabled"]

            if not enabled:
                background = (35, 37, 47)
                text_color = (95, 95, 105)
            elif selected:
                background = (100, 75, 55)
                text_color = (255, 240, 205)
            else:
                background = (42, 46, 62)
                text_color = (205, 205, 210)

            # Transparent button background
            button_surface = pygame.Surface(
                rect.size,
                pygame.SRCALPHA,
            )
            button_surface.fill(background)
            surface.blit(button_surface, rect.topleft)

            # pygame.draw.rect(
            #     surface,
            #     background,
            #     rect,
            #     border_radius=6,
            # )

            if selected and enabled:
                pygame.draw.rect(
                    surface,
                    (225, 190, 125),
                    rect,
                    width=2,
                    border_radius=6,
                )

            text = self.option_font.render(
                option["label"],
                True,
                text_color,
            )

            text_rect = text.get_rect(center=rect.center)
            surface.blit(text, text_rect)
