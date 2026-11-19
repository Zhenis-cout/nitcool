import math
import pygame
from assets import blit_center, load_image
from game_object import GameObject
from settings import BULLET_R, BULLET_SPEED, H, W, WHITE


class Bullet(GameObject):
    """Кеменің оғы."""

    slowable = False
    IMAGE, IMAGE_SIZE = "bullet.png", (16, 40)

    def __init__(self, x, y, vx=0.0, vy=-BULLET_SPEED, radius=BULLET_R):
        super().__init__(x, y, radius)
        self.vx, self.vy = vx, vy
        self.image = self.make_image()

    def make_image(self):
        img = load_image(self.IMAGE, self.IMAGE_SIZE)
        if img is None:
            return None
        return pygame.transform.rotate(img, math.degrees(math.atan2(-self.vx, -self.vy)))

    def update(self, game, dt):
        scale = game.time_scale if self.slowable else 1.0
        self.x += self.vx * scale
        self.y += self.vy * scale
        cx, cy = game.cam_x, game.cam_y
        if not (-100 <= self.x - cx <= W + 100 and -100 <= self.y - cy <= H + 100):
            self.kill()

    def draw(self, screen, cam):
        if self.image:
            blit_center(screen, self.image, self.screen_pos(cam))
            return
        x, y = self.screen_pos(cam)
        n = math.hypot(self.vx, self.vy) or 1
        pygame.draw.line(screen, (255, 200, 60), (x, y), (x - self.vx / n * 18, y - self.vy / n * 18), 6)
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), self.radius)


class EnemyShot(Bullet):
    """НЛО-ның оғы."""

    slowable = True
    IMAGE, IMAGE_SIZE = "enemy_shot.png", (30, 30)

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y, vx, vy, radius=9)

    def draw(self, screen, cam):
        if self.image:
            blit_center(screen, self.image, self.screen_pos(cam))
            return
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        pygame.draw.circle(screen, (255, 70, 200), pos, 10)
        pygame.draw.circle(screen, WHITE, pos, 4)