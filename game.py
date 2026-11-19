import math
import random
import pygame
from effects import EXPLOSION_COLORS, Explosion, FloatingText, Particle
from pickup import Pickup
from rock import Rock
from settings import (
    BUFFS,
    CIRCLE,
    FPS,
    H,
    LEVEL_PAUSE,
    LEVELS,
    LOCATIONS,
    MARGIN,
    MAX_LIVES,
    W,
    WHITE,
    WORLD_H,
    WORLD_W,
)
from ship import Ship
from sounds import SoundManager
from ufo import UFO


def pick_buff(lives):
    kinds = [k for k in BUFFS if BUFFS[k]["weight"] > 0]
    weights = [0 if k == "life" and lives >= MAX_LIVES else BUFFS[k]["weight"] for k in kinds]
    return random.choices(kinds, weights)[0]


class Game:
    """Ойынның басты класы."""

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)
        pygame.init()
        self.sounds = SoundManager()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Тастардан жалтар!")
        self.clock = pygame.time.Clock()
        self.font, self.small_font, self.big_font = (
            pygame.font.SysFont("arial", s, bold=True) for s in (36, 26, 90)
        )
        self.background = self._make_background()
        self.stars = [
            [random.randint(0, W), random.randint(0, H), random.randint(1, 3), random.uniform(0, 6.28)]
            for _ in range(150)
        ]
        self.best = 0.0
        self.running = True
        self.selected_location = 0
        self.reset()

    def _new_world(self):
        self.ship = Ship(WORLD_W // 2, WORLD_H - 120)
        self.ship_group = pygame.sprite.GroupSingle(self.ship)
        self.rocks = pygame.sprite.Group()
        self.ufos = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.shots = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()
        self.shake = self.shake_total = self.shake_power = 0.0

    def reset(self):
        self._new_world()
        self.t = 0.0
        self.score = 0
        self.level = 0
        self.lt = 0.0
        self.banner = 0.0
        self.time_scale = 1.0
        self.rain = self.warning = False
        self.state = "menu"
        self.over_delay = 0.0
        self.keys = pygame.key.get_pressed()
        self.cam_x = self.cam_y = 0.0
        self.update_camera()
        self.background = self._make_background(
            LOCATIONS[self.selected_location]["top"],
            LOCATIONS[self.selected_location]["bottom"],
        )

    def reset_game(self):
        self._new_world()
        self.t = 0.0
        self.score = 0
        self.time_scale = 1.0
        self.rain = self.warning = False
        self.over_delay = 0.0
        self.cam_x = self.cam_y = 0.0
        self.update_camera()
        self.start_level(0)

    @property
    def cfg(self):
        return LEVELS[self.level]

    def start_level(self, n):
        self.level = n
        self.lt = 0.0
        self.spawn_timer = 0.0
        self.next_ufo = random.uniform(*self.cfg["ufo"]) / 2 if self.cfg["ufo"] else None
        self.banner = 2.0
        self.state = "play"
        self.ship.invincible = max(self.ship.invincible, 1.0)

    @property
    def all_objects(self):
        return (
            self.rocks.sprites()
            + self.ufos.sprites()
            + self.shots.sprites()
            + self.pickups.sprites()
            + self.bullets.sprites()
            + self.ship_group.sprites()
            + self.effects.sprites()
        )

    def update_camera(self):
        self.cam_x = max(0, min(WORLD_W - W, self.ship.x - W / 2))
        self.cam_y = max(0, min(WORLD_H - H, self.ship.y - H / 2))

    def run(self):
        dt = 1 / FPS
        while self.running:
            self.handle_events()
            self.update(dt)
            self.draw()
            pygame.display.flip()
            dt = min(self.clock.tick(FPS) / 1000, 0.05)
        pygame.quit()

    def handle_events(self):
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                self.running = False
                continue

            if e.type != pygame.KEYDOWN:
                continue

            if self.state == "menu":
                if e.key in (pygame.K_UP, pygame.K_w):
                    self.selected_location = (self.selected_location - 1) % len(LOCATIONS)
                elif e.key in (pygame.K_DOWN, pygame.K_s):
                    self.selected_location = (self.selected_location + 1) % len(LOCATIONS)
                elif e.key in (pygame.K_RETURN, pygame.K_SPACE):
                    location = LOCATIONS[self.selected_location]
                    self.background = self._make_background(location["top"], location["bottom"])
                    self.reset_game()
                elif e.key == pygame.K_ESCAPE:
                    self.running = False
                continue

            if e.key == pygame.K_ESCAPE:
                self.state = "menu"
                continue

            if e.key in (pygame.K_SPACE, pygame.K_r):
                if self.state in ("won", "lost") and self.over_delay <= 0:
                    self.restart()

    def update(self, dt):
        self.keys = pygame.key.get_pressed()
        self.update_stars()
        self.shake = max(0.0, self.shake - dt)
        if self.state == "menu":
            return
        if self.state in ("won", "lost"):
            self.over_delay -= dt
            self.update_effects(dt)
            return
        if self.state == "level":
            self.over_delay -= dt
            self.update_effects(dt)
            if self.over_delay <= 0:
                self.start_level(self.level + 1)
            return

        self.t += dt
        self.lt += dt
        self.banner = max(0.0, self.banner - dt)
        self.time_scale = 0.4 if self.ship.has("slow") else 1.0
        self.update_camera()
        self.spawn(dt)

        for obj in self.all_objects:
            if obj.alive():
                obj.update(self, dt)
                obj.sync_rect()

        self.handle_collisions()
        self.update_camera()
        self.check_end()

    def update_effects(self, dt):
        for e in self.effects.sprites():
            e.update(self, dt)
            e.sync_rect()

    def spawn_burst(self, x, y, n, colors, speed=(2, 9), life=(0.3, 0.8), size=(3, 8)):
        for _ in range(n):
            a, s = random.uniform(0, math.tau), random.uniform(*speed)
            self.effects.add(
                Particle(
                    x,
                    y,
                    math.cos(a) * s,
                    math.sin(a) * s,
                    random.uniform(*life),
                    random.choice(colors),
                    random.uniform(*size),
                )
            )

    def explode(self, x, y, size, colors, n=14):
        self.effects.add(Explosion(x, y, size))
        self.spawn_burst(x, y, n, colors)

    def add_shake(self, power, duration):
        if power * duration >= self.shake_power * self.shake:
            self.shake = self.shake_total = duration
            self.shake_power = power

    def shake_offset(self):
        if self.shake <= 0:
            return 0, 0
        amp = self.shake_power * self.shake / self.shake_total
        return random.randint(-int(amp), int(amp)), random.randint(-int(amp), int(amp))

    def update_stars(self):
        for s in self.stars:
            s[1] += s[2] * 0.8
            if s[1] > H:
                s[0], s[1] = random.randint(0, W), 0

    def spawn(self, dt):
        cfg, lt = self.cfg, self.lt
        location_speed = LOCATIONS[self.selected_location]["speed"]
        mult = cfg["speed"] * location_speed * (1 + lt / 60)
        interval = max(0.25, cfg["interval"] - lt * 0.005)
        self.rain = self.warning = False
        if cfg["rain"] and lt >= 12:
            phase = (lt - 12) % 25
            self.warning, self.rain = phase < 2, 2 <= phase < 8
        if self.rain:
            interval /= 2
        interval *= W / (W + 2 * MARGIN)

        self.spawn_timer += dt
        while self.spawn_timer >= interval:
            self.spawn_timer -= interval
            self.rocks.add(self.make_rock(mult))
        if self.next_ufo is not None and lt >= self.next_ufo:
            self.ufos.add(UFO(self.cam_x + random.randint(200, W - 200), self.cam_y - 80))
            self.next_ufo = lt + random.uniform(*cfg["ufo"])

    def make_rock(self, mult):
        armored, comet = self.cfg["armored"], self.cfg["comet"]
        r = random.random()
        kind = "armored" if r < armored else "comet" if r < armored + comet else "normal"
        rock = Rock(mult, kind)
        rock.x = random.randint(int(self.cam_x) - MARGIN, int(self.cam_x) + W + MARGIN)
        rock.y = self.cam_y - rock.size
        rock.sync_rect()
        if kind == "comet":
            rock.aim_at(self.ship.x, self.ship.y)
        return rock

    def handle_collisions(self):
        ship = self.ship

        for b in self.bullets.sprites():
            hits = (
                pygame.sprite.spritecollide(b, self.rocks, False, CIRCLE)
                or pygame.sprite.spritecollide(b, self.ufos, False, CIRCLE)
            )
            if hits:
                target = hits[0]
                b.kill()
                if target.hit():
                    self.on_destroyed(target)

        for p in pygame.sprite.spritecollide(ship, self.pickups, False, CIRCLE):
            info = BUFFS[p.kind]
            p.apply(ship)
            self.sounds.play("pickup")
            self.effects.add(FloatingText(p.x, p.y - 30, info["name"], info["color"], life=1.2))
            self.spawn_burst(p.x, p.y, 12, [info["color"], WHITE], speed=(1, 5), size=(2, 5))

        if ship.invincible <= 0:
            for group in (self.rocks, self.shots, self.ufos):
                hits = pygame.sprite.spritecollide(ship, group, False, CIRCLE)
                if hits:
                    hits[0].on_ship_collision()
                    hp_before = ship.hp
                    ship.hit()
                    self.sounds.play("hit")
                    if ship.hp < hp_before:
                        self.spawn_burst(ship.x, ship.y, 22, EXPLOSION_COLORS["ship"])
                        self.add_shake(14, 0.4)
                    else:
                        self.spawn_burst(ship.x, ship.y, 16, [BUFFS["shield"]["color"], WHITE], size=(2, 6))
                    break

    def on_destroyed(self, obj):
        self.score += obj.points
        self.sounds.play("explosion")
        kind = getattr(obj, "kind", "ufo")
        self.explode(obj.x, obj.y, obj.radius, EXPLOSION_COLORS[kind], int(6 + obj.radius * 0.3))
        self.effects.add(FloatingText(obj.x, obj.y - obj.radius, f"+{obj.points}"))
        if kind == "ufo":
            self.add_shake(8, 0.3)
        obj.on_destroy(self)
        if random.random() < obj.drop_chance:
            self.pickups.add(Pickup(pick_buff(self.ship.hp), obj.x, obj.y))

    def check_level_complete(self):
        return self.ship.alive() and self.lt >= self.cfg["time"]

    def check_win(self):
        return self.check_level_complete() and self.level == len(LEVELS) - 1

    def check_lose(self):
        return not self.ship.alive()

    def check_end(self):
        if self.check_lose():
            self.finish("lost")
        elif self.check_win():
            self.finish("won")
        elif self.check_level_complete():
            self.finish_level()

    def finish_level(self):
        for group in (self.rocks, self.ufos, self.bullets, self.shots):
            group.empty()
        self.ship.hp = min(MAX_LIVES, self.ship.hp + 1)
        self.state, self.over_delay = "level", LEVEL_PAUSE
        self.rain = self.warning = False
        self.sounds.play("levelup")

    def finish(self, state):
        self.state = state
        self.over_delay = 0.8
        self.best = max(self.best, self.t)
        self.sounds.play("win" if state == "won" else "gameover")
        if state == "lost":
            self.explode(self.ship.x, self.ship.y, 60, EXPLOSION_COLORS["ship"], 40)
            self.add_shake(22, 0.8)

    def restart(self):
        self.reset_game()

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
            return

        ox, oy = self.shake_offset()
        cam = (self.cam_x + ox, self.cam_y + oy)
        self.screen.blit(self.background, (0, 0))
        now = pygame.time.get_ticks() / 1000
        for x, y, r, ph in self.stars:
            c = int(170 + 85 * math.sin(now * 2 + ph))
            pos = (int((x - cam[0] * r * 0.1) % W), int((y - cam[1] * r * 0.1) % H))
            pygame.draw.circle(self.screen, (c, c, c), pos, r)
        pygame.draw.rect(self.screen, (255, 220, 60), (int(-cam[0]), int(-cam[1]), WORLD_W, WORLD_H), 4)

        for obj in self.all_objects:
            obj.draw(self.screen, cam)

        self.draw_hud()
        if self.state == "level":
            self.draw_level_screen()
        elif self.state in ("won", "lost"):
            self.draw_end_screen()

    def draw_menu(self):
        self.screen.blit(self.background, (0, 0))
        now = pygame.time.get_ticks() / 1000
        for x, y, r, ph in self.stars:
            c = int(150 + 80 * math.sin(now * 2 + ph))
            pygame.draw.circle(self.screen, (c, c, c), (x, y), r)

        self.center(self.big_font, "ТАСТАРДАН ЖАЛТАР!", 150, (255, 220, 60))
        self.center(self.font, "ЛОКАЦИЯНЫ ТАҢДАҢЫЗ", 310, WHITE)

        for i, location in enumerate(LOCATIONS):
            y = 410 + i * 90
            selected = i == self.selected_location
            color = (255, 220, 60) if selected else (220, 225, 245)
            label = self.font.render(location["name"], True, color)
            self.screen.blit(label, label.get_rect(center=(W // 2, y)))
            if selected:
                pygame.draw.rect(
                    self.screen,
                    (255, 220, 60),
                    (W // 2 - 300, y - 32, 600, 64),
                    3,
                    border_radius=12,
                )

        selected_location = LOCATIONS[self.selected_location]
        self.center(
            self.small_font,
            f"Кедергілер жылдамдығы: x{selected_location['speed']:.2f}",
            800,
            (180, 220, 255),
        )
        self.center(self.small_font, "UP / DOWN немесе W / S — таңдау", 870, WHITE)
        self.center(self.font, "ENTER — ОЙНАУ", 925, (120, 255, 150))
        self.center(self.small_font, "ESC — шығу", 985, (200, 200, 220))

    def draw_hud(self):
        pygame.draw.rect(self.screen, (20, 20, 60), (20, 20, 420, 150), border_radius=12)
        pygame.draw.rect(self.screen, (255, 220, 60), (20, 20, 420, 150), 3, border_radius=12)
        self.text(self.font, f"Деңгей: {self.level + 1}/{len(LEVELS)}  {self.cfg['name']}", (40, 30))
        self.text(self.font, f"Ұпай: {self.score}", (40, 75))
        self.text(self.font, f"Өмір: {max(self.ship.hp, 0)}", (40, 120), (255, 120, 120))
        self.draw_minimap()
        if self.state != "play":
            return

        ship = self.ship
        active = [("shield", BUFFS["shield"]["name"])] if ship.shield else []
        active += [(k, f"{BUFFS[k]['name']}: {ship.buffs[k]:.0f} с") for k in ship.buffs if ship.has(k)]
        for i, (kind, label) in enumerate(active):
            pygame.draw.circle(self.screen, BUFFS[kind]["color"], (36, 204 + 36 * i), 9)
            self.text(self.small_font, label, (56, 190 + 36 * i), BUFFS[kind]["color"])
        self.text(self.font, "Ату: ПРОБЕЛ", (40, H - 60), (180, 220, 255))

        total = self.cfg["time"]
        bw, bx, by = 600, (W - 600) // 2, H - 70
        pygame.draw.rect(self.screen, (20, 20, 60), (bx, by, bw, 26), border_radius=8)
        pygame.draw.rect(
            self.screen,
            (120, 255, 150),
            (bx, by, int(bw * min(1, self.lt / total)), 26),
            border_radius=8,
        )
        pygame.draw.rect(self.screen, (255, 220, 60), (bx, by, bw, 26), 3, border_radius=8)
        self.center(
            self.small_font,
            f"Деңгей аяқталуына: {max(0, total - self.lt):.0f} с",
            by - 34,
            (180, 255, 200),
        )

        if self.banner > 0:
            self.center(self.big_font, f"Деңгей {self.level + 1}: {self.cfg['name']}", 300, (255, 220, 60))
        elif self.warning and int(self.lt * 4) % 2 == 0:
            self.center(self.big_font, "Назар аударыңыз!", 120, (255, 200, 60))
        elif self.rain:
            self.center(self.font, "Тас жаңбыры!", 40, (255, 120, 120))

    def draw_minimap(self):
        ox, oy, k = W - 260, H - 155, 240 / WORLD_W
        m = lambda x, y: (int(ox + x * k), int(oy + y * k))
        pygame.draw.rect(self.screen, (20, 20, 60), (ox, oy, 240, 135))
        pygame.draw.rect(self.screen, (255, 220, 60), (ox, oy, 240, 135), 2)
        pygame.draw.rect(
            self.screen,
            (150, 150, 200),
            (*m(self.cam_x, self.cam_y), int(W * k), int(H * k)),
            1,
        )
        for p in self.pickups:
            pygame.draw.circle(self.screen, BUFFS[p.kind]["color"], m(p.x, p.y), 3)
        for u in self.ufos:
            pygame.draw.circle(self.screen, (255, 80, 80), m(u.x, u.y), 4)
        pygame.draw.circle(self.screen, (90, 200, 255), m(self.ship.x, self.ship.y), 3)

    def draw_level_screen(self):
        self.center(self.big_font, f"Деңгей {self.level + 1} өтті!", 300, (120, 255, 150))
        self.center(self.font, "Сыйлық: Өмір +1", 430, (255, 120, 120))
        self.center(self.font, "Келесі деңгейге дайындал...", 480, (180, 220, 255))

    def draw_end_screen(self):
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        if self.state == "won":
            self.center(self.big_font, "Жеңдіңіз!", 230, (120, 255, 150))
            self.center(self.font, f"Барлық {len(LEVELS)} деңгей өтті!", 380)
        else:
            self.center(self.big_font, "Ойын аяқталды!", 230, (255, 120, 120))
            self.center(self.font, f"Жеткен деңгей: {self.level + 1}/{len(LEVELS)}", 380)
        self.center(self.font, f"Уақыт: {self.t:.1f} с   Ұпай: {self.score}", 430)
        self.center(self.font, f"Рекорд: {self.best:.1f} с", 480, (255, 220, 60))
        self.center(self.font, "Қайта бастау: ПРОБЕЛ    Шығу: ESC", 580, (180, 220, 255))

    def text(self, font, s, pos, color=WHITE):
        self.screen.blit(font.render(s, True, (0, 0, 0)), (pos[0] + 2, pos[1] + 2))
        self.screen.blit(font.render(s, True, color), pos)

    def center(self, font, s, y, color=WHITE):
        self.text(font, s, ((W - font.size(s)[0]) // 2, y), color)

    @staticmethod
    def _make_background(top_color=(5, 5, 30), bottom_color=(60, 40, 120)):
        surf = pygame.Surface((W, H))
        for y in range(H):
            ratio = y / max(1, H - 1)
            color = [int(a + (b - a) * ratio) for a, b in zip(top_color, bottom_color)]
            pygame.draw.line(surf, color, (0, y), (W, y))
        return surf