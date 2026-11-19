import pygame
from assets import Animation, blit_center, load_frames
from game_object import GameObject
from settings import FPS

EXPLOSION_COLORS = {
    "normal": [(190, 175, 160), (125, 110, 100), (255, 200, 120)],
    "armored": [(170, 200, 240), (90, 105, 135), (255, 255, 255)],
    "comet": [(255, 140, 50), (255, 220, 120), (200, 80, 60)],
    "ufo": [(110, 230, 190), (255, 230, 90), (255, 255, 255)],
    "ship": [(255, 150, 40), (255, 230, 120), (255, 255, 255)],
}
_fx_font = None


class Particle(GameObject):
    """Жарылыстың ұсақ бөлшегі."""

    def __init__(self, x, y, vx, vy, life, color, size):
        super().__init__(x, y, 1)
        self.vx, self.vy, self.life, self.color, self.size = vx, vy, life, color, size
        self.age = 0.0

    def update(self, game, dt):
        k = dt * FPS
        self.x += self.vx * k
        self.y += self.vy * k
        self.vx *= 0.97
        self.vy *= 0.97
        self.age += dt
        if self.age >= self.life:
            self.kill()

    def draw(self, screen, cam):
        x, y = self.screen_pos(cam)
        r = max(1, int(self.size * (1 - self.age / self.life)))
        pygame.draw.circle(screen, self.color, (int(x), int(y)), r)


class Explosion(GameObject):
    """Жарылыс анимациясы."""

    def __init__(self, x, y, size, duration=0.5):
        super().__init__(x, y, 1)
        self.size, self.duration, self.age = size, duration, 0.0
        side = max(32, int(size * 2.6) // 16 * 16)
        frames = load_frames("explosion", (side, side))
        self.anim = Animation(frames, duration / max(1, len(frames)), loop=False)

    def update(self, game, dt):
        self.age += dt
        self.anim.update(dt)
        if self.age >= self.duration:
            self.kill()

    def draw(self, screen, cam):
        pos = self.screen_pos(cam)
        img = self.anim.image
        if img:
            blit_center(screen, img, pos)
            return
        t = self.age / self.duration
        pygame.draw.circle(
            screen,
            (255, 170 - int(100 * t), 50),
            (int(pos[0]), int(pos[1])),
            int(self.size * (0.4 + 1.4 * t)),
            max(1, int(8 * (1 - t))),
        )


class FloatingText(GameObject):
    """Жоғары ұшып жоғалатын жазу."""

    def __init__(self, x, y, text, color=(255, 240, 120), life=0.9):
        super().__init__(x, y, 1)
        global _fx_font
        if _fx_font is None:
            _fx_font = pygame.font.SysFont("arial", 30, bold=True)
        shadow = _fx_font.render(text, True, (0, 0, 0))
        label = _fx_font.render(text, True, color)
        self.image = pygame.Surface((label.get_width() + 2, label.get_height() + 2), pygame.SRCALPHA)
        self.image.blit(shadow, (2, 2))
        self.image.blit(label, (0, 0))
        self.life, self.age = life, 0.0

    def update(self, game, dt):
        self.y -= 70 * dt
        self.age += dt
        if self.age >= self.life:
            self.kill()

    def draw(self, screen, cam):
        self.image.set_alpha(int(255 * (1 - (self.age / self.life) ** 2)))
        blit_center(screen, self.image, self.screen_pos(cam))