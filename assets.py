import os
import pygame
from settings import ASSETS_DIR

_images, _missing = {}, set()


def load_image(name, size=None):
    """assets/ ішінен суретті кэшпен жүктейді. Табылмаса None қайтарады."""
    key = (name, size)
    if key not in _images:
        img = None
        try:
            img = pygame.image.load(os.path.join(ASSETS_DIR, name)).convert_alpha()
            if size:
                img = pygame.transform.smoothscale(img, size)
        except (FileNotFoundError, pygame.error):
            if name not in _missing:
                _missing.add(name)
                print(f"Сурет табылмады: assets/{name} — орнына фигура салынады")
        _images[key] = img
    return _images[key]


def blit_center(screen, img, pos):
    """Суретті центрі pos нүктесінде болатындай салады."""
    screen.blit(img, img.get_rect(center=(int(pos[0]), int(pos[1]))))


def load_frames(prefix, size=None):
    """assets/<prefix>_0.png, <prefix>_1.png ... кадрларын жүктейді."""
    frames, i = [], 0
    while os.path.exists(os.path.join(ASSETS_DIR, f"{prefix}_{i}.png")):
        img = load_image(f"{prefix}_{i}.png", size)
        if img:
            frames.append(img)
        i += 1
    if not frames:
        single = load_image(f"{prefix}.png", size)
        if single:
            frames.append(single)
    return frames


class Animation:
    """Кадрлар анимациясы."""

    def __init__(self, frames, delay, loop=True):
        self.frames, self.delay, self.loop = frames, delay, loop
        self.index, self.timer, self.done = 0, 0.0, False

    def update(self, dt):
        if len(self.frames) < 2 or self.done:
            return
        self.timer += dt
        while self.timer >= self.delay:
            self.timer -= self.delay
            self.index += 1
            if self.index >= len(self.frames):
                if self.loop:
                    self.index = 0
                else:
                    self.index, self.done = len(self.frames) - 1, True
                    return

    @property
    def image(self):
        return self.frames[self.index] if self.frames else None