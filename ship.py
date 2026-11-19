import math
import os
import random
import pygame
from PIL import Image, ImageSequence
from bullet import Bullet
from game_object import GameObject
from settings import (
    ASSETS_DIR,
    BASE_DIR,
    BUFFS,
    FIRE_DELAY,
    MAX_LIVES,
    SHIP_ANIM_DELAY,
    SHIP_R,
    SHIP_ROTATE,
    SHIP_SIZE,
    SHIP_SPRITE,
    WORLD_H,
    WORLD_W,
)

_ship_frames = None


def load_ship_frames():
    global _ship_frames
    if _ship_frames is not None:
        return _ship_frames
    _ship_frames = []
    try:
        path = os.path.join(ASSETS_DIR, SHIP_SPRITE)
        if not os.path.exists(path):
            path = os.path.join(BASE_DIR, SHIP_SPRITE)
        img = Image.open(path)
        for frame in ImageSequence.Iterator(img):
            f = frame.convert("RGBA")
            surf = pygame.image.fromstring(f.tobytes(), f.size, "RGBA").convert_alpha()
            surf = pygame.transform.smoothscale(surf, SHIP_SIZE)
            if SHIP_ROTATE:
                surf = pygame.transform.rotate(surf, SHIP_ROTATE)
            _ship_frames.append(surf)
    except (FileNotFoundError, OSError) as e:
        print("Спрайт корабля не загружен:", e)
    return _ship_frames


class Ship(GameObject):
    """Ойыншының кемесі."""

    def __init__(self, x, y):
        super().__init__(x, y, SHIP_R, hp=3)
        self.speed = 9
        self.invincible = self.cooldown = 0.0
        self.shield = False
        self.buffs = dict.fromkeys(("triple", "rapid", "slow"), 0.0)
        self.frames = load_ship_frames()
        self.frame_index = 0
        self.anim_timer = 0.0

    def has(self, kind):
        return self.buffs[kind] > 0

    def add_buff(self, kind):
        if kind == "shield":
            self.shield = True
        elif kind == "life":
            self.hp = min(MAX_LIVES, self.hp + 1)
        else:
            self.buffs[kind] = BUFFS[kind]["time"]

    def update(self, game, dt):
        keys = game.keys
        held = lambda *ks: any(keys[k] for k in ks)
        self.x += self.speed * (held(pygame.K_RIGHT, pygame.K_d) - held(pygame.K_LEFT, pygame.K_a))
        self.y += self.speed * (held(pygame.K_DOWN, pygame.K_s) - held(pygame.K_UP, pygame.K_w))
        self.x = max(25, min(WORLD_W - 25, self.x))
        self.y = max(40, min(WORLD_H - 40, self.y))
        self.invincible = max(0.0, self.invincible - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        for k in self.buffs:
            self.buffs[k] = max(0.0, self.buffs[k] - dt)
        if keys[pygame.K_SPACE] and self.cooldown <= 0:
            game.bullets.add(self.shoot())
            game.sounds.play("shoot")

        if len(self.frames) > 1:
            self.anim_timer += dt
            if self.anim_timer >= SHIP_ANIM_DELAY:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(self.frames)

    def shoot(self):
        self.cooldown = FIRE_DELAY * (0.4 if self.has("rapid") else 1.0)
        pattern = [(0, -30, 0), (-14, -20, -4), (14, -20, 4)]
        count = 3 if self.has("triple") else 1
        return [Bullet(self.x + dx, self.y + dy, vx) for dx, dy, vx in pattern[:count]]

    def hit(self, damage=1):
        if self.invincible > 0:
            return False
        if self.shield:
            self.shield, self.invincible = False, 1.0
            return False
        self.invincible = 1.5
        return super().hit(damage)

    def draw(self, screen, cam):
        x, y = self.screen_pos(cam)
        if self.shield:
            pygame.draw.circle(
                screen,
                BUFFS["shield"]["color"],
                (int(x), int(y)),
                int(40 + 2 * math.sin(pygame.time.get_ticks() / 120)),
                3,
            )
        if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
            return
        if self.frames:
            sprite = self.frames[self.frame_index]
            screen.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
            return
        pygame.draw.polygon(
            screen,
            (255, 150, 40),
            [(x - 8, y + 14), (x + 8, y + 14), (x, y + 26 + random.randint(0, 14))],
        )
        body = [(x, y - 30), (x + 22, y + 22), (x, y + 11), (x - 22, y + 22)]
        pygame.draw.polygon(screen, (90, 200, 255), body)
        pygame.draw.polygon(screen, (230, 250, 255), body, 3)
        pygame.draw.circle(screen, (20, 30, 80), (int(x), int(y - 6)), 5)