import math
import pygame
from assets import Animation, blit_center, load_frames
from bullet import EnemyShot
from game_object import GameObject
from settings import KINDS, SHOT_SPEED, WORLD_W


class UFO(GameObject):
    """Кеменің үстінде қалқып, оған оқ атады және 20 секундтан кейін ұшып кетеді."""

    LIFE = 20

    def __init__(self, x, y):
        info = KINDS["ufo"]
        super().__init__(x, y, 42, hp=info["hp"])
        self.max_hp = info["hp"]
        self.points, self.drop_chance = info["points"], info["drop"]
        self.age, self.fire = 0.0, 1.5
        self.anim = Animation(load_frames("ufo", (110, 70)), 0.12)

    def update(self, game, dt):
        ship, scale = game.ship, game.time_scale
        self.age += dt * scale
        self.fire -= dt * scale
        self.anim.update(dt * scale)
        if self.age >= self.LIFE:
            self.kill()
            return
        leaving = self.age > self.LIFE - 3
        tx = max(60, min(WORLD_W - 60, ship.x + 350 * math.sin(self.age)))
        ty = -300 if leaving else (ship.y - 320 if ship.y >= 400 else ship.y + 320)
        self.x += max(-7, min(7, (tx - self.x) * 0.04)) * scale
        self.y += (ty - self.y) * 0.03 * scale
        if self.fire <= 0 and not leaving:
            self.fire = 1.4
            d = math.hypot(ship.x - self.x, ship.y - self.y) or 1
            game.shots.add(
                EnemyShot(
                    self.x,
                    self.y + 20,
                    (ship.x - self.x) / d * SHOT_SPEED,
                    (ship.y - self.y) / d * SHOT_SPEED,
                )
            )

    def on_ship_collision(self):
        pass

    def draw(self, screen, cam):
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        img = self.anim.image
        if img:
            blit_center(screen, img, (x, y - 4))
        else:
            pygame.draw.ellipse(screen, (110, 230, 190), (x - 20, y - 28, 40, 34))
            pygame.draw.ellipse(screen, (150, 160, 185), (x - 44, y - 8, 88, 28))
            pygame.draw.ellipse(screen, (220, 235, 255), (x - 44, y - 8, 88, 28), 3)
            blink = pygame.time.get_ticks() // 250
            for i, dx in enumerate((-28, 0, 28)):
                color = (255, 230, 90) if (blink + i) % 2 else (255, 120, 60)
                pygame.draw.circle(screen, color, (x + dx, y + 8), 4)
        pygame.draw.rect(screen, (90, 20, 20), (x - 30, y - 46, 60, 6))
        pygame.draw.rect(screen, (255, 90, 90), (x - 30, y - 46, int(60 * max(self.hp, 0) / self.max_hp), 6))