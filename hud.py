"""Minimal pixel-art gameplay HUD for the prologue."""

from pathlib import Path
import math
import pygame


class GameplayHUD:
    """Draw health, enemy defeats, and the War of Fallen Skies timer."""

    def __init__(self, font_manager, screen_width, screen_height):
        self.font_manager = font_manager
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)

        asset_dir = Path(__file__).resolve().parent / "assets" / "imgs" / "system"
        self.health_icon = pygame.image.load(str(asset_dir / "health.png")).convert_alpha()
        self.skull_icon = pygame.image.load(str(asset_dir / "skull.png")).convert_alpha()

        # Integer scaling keeps the source pixel art crisp.
        self.icon_scale = 2
        self.health_icon = pygame.transform.scale(
            self.health_icon,
            (self.health_icon.get_width() * self.icon_scale,
             self.health_icon.get_height() * self.icon_scale),
        )
        self.skull_icon = pygame.transform.scale(
            self.skull_icon,
            (self.skull_icon.get_width() * self.icon_scale,
             self.skull_icon.get_height() * self.icon_scale),
        )

        self.value_font = self.font_manager.get("main", 27)
        self.timer_font = self.font_manager.get("main", 38)

    @staticmethod
    def _draw_shadowed_text(surface, font, text, rect, color=(250, 248, 238)):
        shadow = font.render(str(text), True, (14, 17, 20))
        foreground = font.render(str(text), True, color)
        shadow_rect = shadow.get_rect(**rect)
        foreground_rect = foreground.get_rect(**rect)
        shadow_rect.move_ip(2, 2)
        surface.blit(shadow, shadow_rect)
        surface.blit(foreground, foreground_rect)
        return foreground_rect

    @staticmethod
    def format_timer(seconds):
        seconds = max(0, int(math.ceil(float(seconds))))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        remaining = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{remaining:02d}"

    def draw(
        self,
        surface,
        player,
        mission_id,
        wave_kills=0,
        wave_enemy_total=None,
        total_mission_kills=0,
        timer_remaining=None,
    ):
        top = 12
        left = 20
        icon_y = top

        # Health: top-left.
        health_rect = self.health_icon.get_rect(topleft=(left, icon_y))
        surface.blit(self.health_icon, health_rect)
        hp = max(0, int(player.stats.get("hp", 0)))
        max_hp = max(1, int(player.stats.get("max_hp", 1)))
        self._draw_shadowed_text(
            surface,
            self.value_font,
            f"{hp}/{max_hp}",
            {"midleft": (health_rect.right + 10, health_rect.centery - 1)},
        )

        # Enemy defeats: top-right. First Assault resets per wave; War of
        # Fallen Skies shows a cumulative mission total.
        if mission_id == "first_assault":
            if wave_enemy_total is None:
                counter = str(max(0, int(wave_kills)))
            else:
                counter = f"{max(0, int(wave_kills))}/{max(0, int(wave_enemy_total))}"
        elif mission_id == "war_battlefield":
            counter = str(max(0, int(total_mission_kills)))
        else:
            counter = None

        if counter is not None:
            counter_surface = self.value_font.render(counter, True, (250, 248, 238))
            icon_w = self.skull_icon.get_width()
            gap = 10
            right_padding = 22
            group_width = icon_w + gap + counter_surface.get_width()
            group_left = self.screen_width - right_padding - group_width
            skull_rect = self.skull_icon.get_rect(topleft=(group_left, icon_y - 2))
            surface.blit(self.skull_icon, skull_rect)
            self._draw_shadowed_text(
                surface,
                self.value_font,
                counter,
                {"midleft": (skull_rect.right + gap, skull_rect.centery)},
            )

        # The countdown is exclusive to War of Fallen Skies.
        if mission_id == "war_battlefield" and timer_remaining is not None:
            timer_text = self.format_timer(timer_remaining)
            timer_surface = self.timer_font.render(timer_text, True, (250, 248, 238))
            timer_rect = timer_surface.get_rect(midtop=(self.screen_width // 2, 7))
            shadow = self.timer_font.render(timer_text, True, (14, 17, 20))
            surface.blit(shadow, timer_rect.move(2, 2))
            surface.blit(timer_surface, timer_rect)
