import pygame

class FontManager:
    def __init__(self):
        self.paths = {}
        self.cache = {}

    def load(self, name, path):
        self.paths[name] = path

    def get(self, name, size):
        key = (name, size)

        if key not in self.cache:
            path = self.paths[name]
            self.cache[key] = pygame.font.Font(path, size)

        return self.cache[key]