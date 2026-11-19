import pygame


class GameObject(pygame.sprite.Sprite):
    """Ойындағы барлық нысандардың базалық класы."""

    points = 0
    drop_chance = 0.0

    def __init__(self, x, y, radius, hp=1):
        super().__init__()
        self.x, self.y = x, y
        self.radius = radius
        self.hp = hp
        d = max(2, int(radius * 2))
        self.rect = pygame.Rect(0, 0, d, d)
        self.sync_rect()

    def sync_rect(self):
        self.rect.center = (round(self.x), round(self.y))

    def update(self, game, dt):
        pass

    def draw(self, screen, cam):
        pass

    def screen_pos(self, cam):
        return self.x - cam[0], self.y - cam[1]

    def hit(self, damage=1):
        self.hp -= damage
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def on_destroy(self, game):
        pass

    def on_ship_collision(self):
        self.kill()