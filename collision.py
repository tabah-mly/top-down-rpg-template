import pygame


class CollisionShape:
    def __init__(self, shape_type, rect=None, points=None):
        self.shape_type = shape_type
        self.rect = pygame.Rect(rect) if rect else None
        self.points = [pygame.Vector2(point) for point in points] if points else []

    def collides(self, target_rect):
        if self.shape_type == "rect":
            return self.rect.colliderect(target_rect)

        if self.shape_type == "ellipse":
            return self._ellipse_collision(target_rect)

        if self.shape_type == "polygon":
            return self._polygon_collision(target_rect)

        return False

    def _ellipse_collision(self, target_rect):
        center_x = self.rect.centerx
        center_y = self.rect.centery

        radius_x = self.rect.width / 2
        radius_y = self.rect.height / 2

        if radius_x == 0 or radius_y == 0:
            return False

        # Find the closest point on the player rectangle
        closest_x = max(target_rect.left, min(center_x, target_rect.right))

        closest_y = max(target_rect.top, min(center_y, target_rect.bottom))

        dx = (closest_x - center_x) / radius_x
        dy = (closest_y - center_y) / radius_y

        return dx * dx + dy * dy <= 1

    def _polygon_collision(self, target_rect):
        if len(self.points) < 3:
            return False

        rect_points = [
            pygame.Vector2(target_rect.topleft),
            pygame.Vector2(target_rect.topright),
            pygame.Vector2(target_rect.bottomright),
            pygame.Vector2(target_rect.bottomleft),
        ]

        # Axes from both polygons
        axes = [
            pygame.Vector2(1, 0),
            pygame.Vector2(0, 1),
        ]

        for polygon in (self.points, rect_points):
            for i in range(len(polygon)):
                current = polygon[i]
                next_point = polygon[(i + 1) % len(polygon)]

                edge = next_point - current
                normal = pygame.Vector2(-edge.y, edge.x)

                if normal.length_squared() > 0:
                    axes.append(normal.normalize())

        # Separating Axis Theorem
        for axis in axes:
            polygon_projection = [point.dot(axis) for point in self.points]

            rect_projection = [point.dot(axis) for point in rect_points]

            if max(polygon_projection) < min(rect_projection) or max(
                rect_projection
            ) < min(polygon_projection):
                return False

        return True

    def draw_debug(self, surface, camera, color=None):
        if color is None:
            if self.shape_type == "rect":
                color = (255, 0, 0)
            elif self.shape_type == "ellipse":
                color = (0, 180, 255)
            elif self.shape_type == "polygon":
                color = (0, 255, 100)

        if self.shape_type == "rect":
            pygame.draw.rect(surface, color, camera.apply(self.rect), 2)

        elif self.shape_type == "ellipse":
            pygame.draw.ellipse(surface, color, camera.apply(self.rect), 2)

        elif self.shape_type == "polygon":
            screen_points = [
                camera.apply(pygame.Rect(round(point.x), round(point.y), 0, 0)).topleft
                for point in self.points
            ]

            pygame.draw.polygon(surface, color, screen_points, 2)


class CollisionBox:
    def __init__(self, width, height, offset=(0, 0)):
        self.width = width
        self.height = height
        self.offset = pygame.Vector2(offset)

        self.rect = pygame.Rect(0, 0, width, height)

    def update(self, anchor):
        position = pygame.Vector2(anchor) + self.offset
        self.rect.center = round(position.x), round(position.y)

    def collides(self, other):
        return self.rect.colliderect(other.rect)

    def draw_debug(self, surface, camera, color):
        pygame.draw.rect(surface, color, camera.apply(self.rect), 2)
