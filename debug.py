"""Central debug drawing switch for the game.

Set DEBUG = False to hide all collision and attack debug overlays.
"""

DEBUG = True

# Debug overlay colors (RGB)
BODY_COLLISION_COLOR = (0, 255, 100)       # Green
HURTBOX_COLOR = (255, 0, 220)              # Magenta
PLAYER_MELEE_HITBOX_COLOR = (255, 65, 65)  # Red
ENEMY_ATTACK_RANGE_COLOR = (255, 145, 0)  # Orange
PROJECTILE_HITBOX_COLOR = (255, 225, 0)   # Yellow
MAP_RECT_COLOR = (255, 0, 0)              # Red (shape default)
MAP_ELLIPSE_COLOR = (0, 180, 255)         # Cyan
MAP_POLYGON_COLOR = (0, 255, 100)         # Lime
