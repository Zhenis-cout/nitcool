import math
import os
import random
import sys
from array import array

import pygame
from PIL import Image, ImageSequence

# папка с ресурсами (работает и в .py, и в .exe из PyInstaller)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


# ==================== settings.py ====================
W, H = 1920, 1080              # терезе өлшемі
WORLD_W, WORLD_H = 3840, 2160  # карта өлшемі (терезеден екі есе үлкен)
FPS = 60
LEVEL_PAUSE = 2.5              # деңгей аяқталған соңғы үзіліс (секунд)

# Деңгейлер. time — өту үшін аман қалу секундтары, speed — тас жылдамдығының еселеуіші,
# interval — тастардың шығу аралығы, armored/comet — сауытты тас пен комета ықтималдығы,
# ufo — НЛО келу аралығы (мин, макс) немесе None, rain — тас жаңбыры бар ма
LEVELS = [
    dict(name="1level", time=25, speed=0.8, interval=1.0, armored=0.0, comet=0.0, ufo=None, rain=False),
    dict(name="2level", time=45, speed=1.0, interval=0.9, armored=0.1, comet=0.1, ufo=None, rain=False),
    dict(name="3level", time=50, speed=1.2, interval=0.8, armored=0.15, comet=0.2, ufo=(25, 35), rain=False),
    dict(name="4level", time=67, speed=1.4, interval=0.7, armored=0.2, comet=0.25, ufo=(20, 30), rain=True),
    dict(name="5level", time=80, speed=1.6, interval=0.6, armored=0.25, comet=0.3, ufo=(15, 25), rain=True),
]

# ==================== LOCATIONS ====================
# Әр локацияның өз фоны және ойын кезіндегі қосымша әсері бар.
LOCATIONS = [
    {"name": "Космос", "top": (5, 5, 30), "bottom": (60, 40, 120), "speed": 1.0},
    {"name": "Марс", "top": (45, 8, 5), "bottom": (170, 65, 35), "speed": 1.10},
    {"name": "Ледяная планета", "top": (5, 30, 60), "bottom": (75, 165, 210), "speed": 0.90},
    {"name": "Галактика", "top": (20, 0, 45), "bottom": (105, 35, 155), "speed": 1.20},
]

FIRE_DELAY, SPLIT_SIZE, MAX_LIVES = 0.18, 34, 5
BULLET_SPEED, BULLET_R, SHIP_R, PICKUP_R = 22, 5, 28, 20
SHOT_SPEED, MARGIN = 9, 300    # НЛО оғының жылдамдығы; тастар терезеден MARGIN px тыс шығады

WHITE = (255, 255, 255)

# --- Спрайт корабля ---
SHIP_SPRITE = "ship.png"       # assets/ ішінде; gif те болады (анимация), мысалы "ship.gif"
SHIP_SIZE = (62, 100)           # размер корабля на экране (ширина, высота)
SHIP_ANIM_DELAY = 0.1          # секунд на один кадр анимации
SHIP_ROTATE = 0                # поворот спрайта в градусах (0, 90, -90, 180), если смотрит не вверх

# time — әсер ету уақыты (0 = бірінші соққыға дейін), weight — түсу жиілігі
BUFFS = {
    "triple": {"letter": "3", "color": (255, 160, 40), "name": "Үш ату", "time": 10, "weight": 3},
    "rapid": {"letter": "R", "color": (255, 90, 90), "name": "Жылдам ату", "time": 8, "weight": 3},
    "slow": {"letter": "Z", "color": (170, 120, 255), "name": "Баяу уақыт", "time": 6, "weight": 2},
    "life": {"letter": "+", "color": (90, 230, 120), "name": "Өмір +1", "time": 0, "weight": 1},
}

# size — өлшем аралығы, speed — жылдамдық еселеуіші, hp — бұзылғанға дейінгі соққы,
# points — ұпай, drop — бонус түсу ықтималдығы
KINDS = {
    "normal": dict(size=(22, 50), speed=1.0, hp=1, points=1, drop=0.08),
    "armored": dict(size=(50, 64), speed=0.7, hp=3, points=5, drop=0.6),
    "comet": dict(size=(16, 24), speed=1.8, hp=1, points=3, drop=0.2),
    "ufo": dict(hp=10, points=15, drop=1.0),  # НЛО әрқашан бонус тастайды
}

# spritecollide үшін соқтығысу функциясы: спрайттың rect центрі мен radius атрибуты бойынша шеңберлерді салыстырады
CIRCLE = pygame.sprite.collide_circle

SOUND_VOLUME = 0.6  # жалпы дыбыс деңгейі (0.0 – 1.0)


# ==================== sounds.py ====================
class SoundManager:
    """Дыбыстарды файлсыз, толқын формасын есептеп (синтез) жасайды және ойнатады.

    Дыбыс құрылғысы жоқ болса, ойын үнсіз жұмыс істей береді (enabled = False).
    """

    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 1, 512)
            self.rate, fmt, self.channels = pygame.mixer.get_init()
            if fmt != -16:  # тек 16 бит таңбалы форматты қолдаймыз
                return
        except pygame.error as e:
            print("Дыбыс қосылмады:", e)
            return

        self.enabled = True
        self.sounds = {
            "shoot": self._make([(900, 300, 0.12)], vol=0.15, square=True),
            "explosion": self._make([(300, 60, 0.35)], vol=0.45, noise=0.8),
            "pickup": self._make([(600, 1200, 0.15)], vol=0.3),
            "hit": self._make([(220, 80, 0.3)], vol=0.5, square=True, noise=0.3),
            "levelup": self._make([(523, 523, 0.12), (659, 659, 0.12), (784, 784, 0.25)], vol=0.3),
            "gameover": self._make([(392, 380, 0.3), (330, 320, 0.3), (262, 250, 0.3), (196, 150, 0.6)],
                                   vol=0.35, square=True),
            "win": self._make([(523, 523, 0.15), (659, 659, 0.15), (784, 784, 0.15), (1047, 1047, 0.5)],
                              vol=0.3),
        }
        for s in self.sounds.values():
            s.set_volume(SOUND_VOLUME)

    def _make(self, notes, vol=0.3, square=False, noise=0.0):
        """notes = [(бастапқы жиілік, соңғы жиілік, ұзақтығы с), ...] → pygame.mixer.Sound."""
        data = array("h")
        phase = 0.0
        for f0, f1, dur in notes:
            n = int(self.rate * dur)
            for i in range(n):
                t = i / n
                phase += math.tau * (f0 + (f1 - f0) * t) / self.rate
                s = math.sin(phase)
                if square:
                    s = 1.0 if s >= 0 else -1.0
                s = s * (1 - noise) + random.uniform(-1, 1) * noise
                env = (1 - t) ** 2 * min(1.0, i / 80)  # баяу сөну + кликсіз бастау
                v = int(32767 * vol * env * s)
                data.extend([v] * self.channels)  # моно/стерео үшін
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name):
        if self.enabled:
            self.sounds[name].play()


# ==================== assets.py ====================
ASSETS_DIR = os.path.join(BASE_DIR, "assets")  # барлық суреттер осы папкада
_images, _missing = {}, set()


def load_image(name, size=None):
    """assets/ ішінен суретті жүктейді (бір рет, кэшпен).

    Файл табылмаса None қайтарады — сонда нысан ескі фигурамен (көпбұрыш/шеңбер) салынады.
    """
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
    """assets/<prefix>_0.png, <prefix>_1.png, ... кадрларын ретімен жүктейді.

    Нөмірленген файл жоқ болса, <prefix>.png (бір кадр) алынады; ол да жоқ болса [] қайтады.
    """
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
    """Бірнеше суреттің (кадрдың) кезекпен ауысуы.

    delay — бір кадрдың ұзақтығы (с); loop=False болса, соңғы кадрда тоқтайды (done = True).
    """

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


# ==================== game_object.py ====================
class GameObject(pygame.sprite.Sprite):
    """Ойындағы барлық нысандардың ата-ана класы (pygame.sprite.Sprite-тан мұра алады).

    Балалар класс update(), draw(), hit(), on_destroy() әдістерін қайта анықтайды (override).
    Нысандар pygame.sprite.Group ішінде сақталады; жойылғанда kill() барлық топтан алып тастайды.
    """

    points = 0         # жойылғанда берілетін ұпай
    drop_chance = 0.0  # жойылғанда бонус түсу ықтималдығы

    def __init__(self, x, y, radius, hp=1):
        super().__init__()  # Sprite.__init__ — топтарға қосылуға мүмкіндік береді
        self.x, self.y = x, y
        self.radius = radius  # collide_circle осы атрибутты пайдаланады
        self.hp = hp
        d = max(2, int(radius * 2))
        self.rect = pygame.Rect(0, 0, d, d)  # Sprite үшін міндетті rect (соқтығысу өлшемі)
        self.sync_rect()

    def sync_rect(self):
        """rect центрін (x, y) нүктесімен сәйкестендіреді."""
        self.rect.center = (round(self.x), round(self.y))

    def update(self, game, dt):
        """Әр кадрда шақырылады. Әр класс өзінше жүзеге асырады."""

    def draw(self, screen, cam):
        """cam = (cx, cy) — камераның сол жақ жоғарғы бұрышы. Әр класс өзінше салады."""

    def screen_pos(self, cam):
        return self.x - cam[0], self.y - cam[1]

    def hit(self, damage=1):
        """Соққы алу. Нысан жойылса True қайтарады (және барлық топтан шығарады)."""
        self.hp -= damage
        if self.hp <= 0:
            self.kill()
            return True
        return False

    def on_destroy(self, game):
        """Нысан жойылғанда шақырылады (мысалы, тас бөлшектерге ыдырайды)."""

    def on_ship_collision(self):
        """Кеме осы нысанға соқтығысқанда не болатыны. Әдепкі: нысан жоғалады."""
        self.kill()


# ==================== bullet.py ====================
class Bullet(GameObject):
    """Кеменің оғы."""

    slowable = False  # «Баяу уақыт» бонусы әсер ете ме
    IMAGE, IMAGE_SIZE = "bullet.png", (16, 40)  # assets/bullet.png (оқ жоғарыға қараған болуы керек)

    def __init__(self, x, y, vx=0.0, vy=-BULLET_SPEED, radius=BULLET_R):
        super().__init__(x, y, radius)
        self.vx, self.vy = vx, vy
        self.image = self.make_image()  # ұшу бағытына бұрылған сурет (бір рет есептеледі)

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
        x, y = self.screen_pos(cam)  # сурет жоқ болса — ескі сызба
        n = math.hypot(self.vx, self.vy)
        pygame.draw.line(screen, (255, 200, 60), (x, y), (x - self.vx / n * 18, y - self.vy / n * 18), 6)
        pygame.draw.circle(screen, (255, 255, 220), (int(x), int(y)), self.radius)


class EnemyShot(Bullet):
    """НЛО-ның оғы: баяулатуға ұшырайды, басқаша түсті."""

    slowable = True
    IMAGE, IMAGE_SIZE = "enemy_shot.png", (30, 30)

    def __init__(self, x, y, vx, vy):
        super().__init__(x, y, vx, vy, radius=9)

    def draw(self, screen, cam):  # draw әдісін қайта анықтау
        if self.image:
            blit_center(screen, self.image, self.screen_pos(cam))
            return
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        pygame.draw.circle(screen, (255, 70, 200), pos, 10)
        pygame.draw.circle(screen, WHITE, pos, 4)


# ==================== pickup.py ====================
_font = None


class Pickup(GameObject):
    """Төмен түсетін бонус. Кеме алғанда әсер береді."""

    def __init__(self, kind, x, y):
        super().__init__(x, y, PICKUP_R + 6)
        self.kind = kind
        self.age = 0.0

    def update(self, game, dt):
        self.y += 3
        self.age += dt
        if self.y > game.cam_y + H + 30:
            self.kill()

    def apply(self, ship):
        ship.add_buff(self.kind)
        self.kill()

    def draw(self, screen, cam):
        global _font
        if _font is None:
            _font = pygame.font.SysFont("arial", 26, bold=True)
        info = BUFFS[self.kind]
        pos = (int(self.x - cam[0]), int(self.y - cam[1]))
        side = int(52 + 6 * math.sin(self.age * 6))  # «тыныс алады»
        img = load_image(f"pickup_{self.kind}.png", (side, side))  # assets/pickup_<түрі>.png
        if img:
            blit_center(screen, img, pos)
            return
        rad = int(PICKUP_R + 3 * math.sin(self.age * 6))
        pygame.draw.circle(screen, (20, 20, 50), pos, rad + 4)
        pygame.draw.circle(screen, info["color"], pos, rad)
        pygame.draw.circle(screen, WHITE, pos, rad, 3)
        label = _font.render(info["letter"], True, WHITE)
        screen.blit(label, label.get_rect(center=pos))


# ==================== ship.py ====================
_ship_frames = None


def load_ship_frames():
    """Загружает кадры гифки один раз. Если файла нет, возвращает [] (рисуем старый треугольник)."""
    global _ship_frames
    if _ship_frames is not None:
        return _ship_frames
    _ship_frames = []
    try:
        path = os.path.join(ASSETS_DIR, SHIP_SPRITE)  # assets/ ішінде
        if not os.path.exists(path):                  # ескі орын: ойынмен бір папка
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
    """Ойыншының кемесі. hp = өмір саны."""

    def __init__(self, x, y):
        super().__init__(x, y, SHIP_R, hp=3)  # ата-ана конструкторын шақыру
        self.speed = 9
        self.invincible = self.cooldown = 0.0
        self.shield = False  # қалқан бір соққыны жұтады
        self.buffs = dict.fromkeys(("triple", "rapid", "slow"), 0.0)
        # анимация спрайта
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
            self.buffs[kind] = BUFFS[kind]["time"]  # қайта алса таймер жаңарады

    def update(self, game, dt):  # override
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
            game.bullets.add(self.shoot())  # Group.add тізімді қабылдайды
            game.sounds.play("shoot")       # дыбыс: ату

        # смена кадров анимации
        if len(self.frames) > 1:
            self.anim_timer += dt
            if self.anim_timer >= SHIP_ANIM_DELAY:
                self.anim_timer = 0.0
                self.frame_index = (self.frame_index + 1) % len(self.frames)

    def shoot(self):
        self.cooldown = FIRE_DELAY * (0.4 if self.has("rapid") else 1.0)
        # dx, dy, vx — бүйір оқтар «Үш ату» бонусына арналған
        pattern = [(0, -30, 0), (-14, -20, -4), (14, -20, 4)]
        count = 3 if self.has("triple") else 1
        return [Bullet(self.x + dx, self.y + dy, vx) for dx, dy, vx in pattern[:count]]

    def hit(self, damage=1):  # override: қалқан және жеңілмейтін уақыт
        if self.invincible > 0:
            return False
        if self.shield:
            self.shield, self.invincible = False, 1.0
            return False
        self.invincible = 1.5
        return super().hit(damage)

    def draw(self, screen, cam):  # override
        x, y = self.screen_pos(cam)
        if self.shield:
            pygame.draw.circle(screen, BUFFS["shield"]["color"], (int(x), int(y)),
                               int(40 + 2 * math.sin(pygame.time.get_ticks() / 120)), 3)
        if self.invincible > 0 and int(self.invincible * 10) % 2 == 0:
            return  # соққыдан кейінгі жыпылықтау
        if self.frames:
            sprite = self.frames[self.frame_index]
            screen.blit(sprite, sprite.get_rect(center=(int(x), int(y))))
            return
        # запасной вариант: старый треугольник, если гифка не загрузилась
        pygame.draw.polygon(screen, (255, 150, 40),
                            [(x - 8, y + 14), (x + 8, y + 14), (x, y + 26 + random.randint(0, 14))])
        body = [(x, y - 30), (x + 22, y + 22), (x, y + 11), (x - 22, y + 22)]
        pygame.draw.polygon(screen, (90, 200, 255), body)
        pygame.draw.polygon(screen, (230, 250, 255), body, 3)
        pygame.draw.circle(screen, (20, 30, 80), (int(x), int(y - 6)), 5)


# ==================== rock.py ====================
class Rock(GameObject):
    """Құлап келе жатқан тас: қарапайым, сауытты немесе комета."""

    def __init__(self, mult, kind="normal", size=None, x=0.0, y=0.0, drift=None):
        info = KINDS[kind]
        size = size or random.randint(*info["size"])
        super().__init__(x, y, size * 0.85, hp=info["hp"])
        self.kind, self.size, self.mult = kind, size, mult
        self.points, self.drop_chance = info["points"], info["drop"]
        self.speed = random.uniform(4, 7) * mult * info["speed"]
        self.drift = drift if drift is not None else random.uniform(-1.5, 1.5)
        self.angle, self.spin = random.uniform(0, 360), random.uniform(-3, 3)
        self.shape = [random.uniform(0.7, 1.0) for _ in range(random.randint(8, 11))]
        # assets/rock.png, armored.png, comet.png — өлшемі тастың өлшеміне сай
        side = int(size * 2)
        self.base = load_image({"normal": "rock.png", "armored": "armored.png", "comet": "comet.png"}[kind],
                               (side, side))
        self._tinted = {}  # сауытты тастың hp-ға байланысты қызарған суреттері

    def aim_at(self, tx, ty):
        """Комета кеме қазір тұрған жерге ұшады."""
        frames = max(1.0, (ty - self.y) / self.speed)
        self.drift = max(-6.0, min(6.0, (tx - self.x) / frames))

    def update(self, game, dt):  # override
        scale = game.time_scale
        self.y += self.speed * scale
        self.x += self.drift * scale
        self.angle += self.spin * scale
        # төмен түсіп кеткен немесе шетке ұшып кеткен тас = +1 ұпай
        if self.y > game.cam_y + H + self.size or abs(self.x - game.cam_x - W / 2) > W / 2 + 2 * MARGIN:
            self.kill()
            game.score += 1

    def on_destroy(self, game):  # override: үлкен тас бөлшектерге ыдырайды
        if self.size < SPLIT_SIZE:
            return
        n = int(self.size * 0.6)
        for d in (-1, 1):
            game.rocks.add(Rock(self.mult, "normal", n, self.x + d * n, self.y, self.drift + 2 * d))

    def draw_tail(self, screen, x, y):
        """Комета құйрығы: ұшу бағытына қарсы."""
        length = math.hypot(self.drift, self.speed)
        dx, dy = self.drift / length, self.speed / length
        px, py = -dy * self.size * 0.7, dx * self.size * 0.7
        tail = (x - dx * self.size * 4, y - dy * self.size * 4)
        pygame.draw.polygon(screen, (255, 140, 50), [(x + px, y + py), (x - px, y - py), tail])

    def draw_image(self, screen, x, y):
        img = self.base
        if self.kind == "armored" and self.hp < 3:  # hp азайған сайын қызарады
            if self.hp not in self._tinted:
                img = img.copy()
                img.fill((70 * (3 - self.hp), 0, 0, 0), special_flags=pygame.BLEND_RGB_ADD)
                self._tinted[self.hp] = img
            img = self._tinted[self.hp]
        blit_center(screen, pygame.transform.rotate(img, -self.angle), (x, y))

    def draw(self, screen, cam):  # override
        x, y = self.screen_pos(cam)
        if self.kind == "comet":
            self.draw_tail(screen, x, y)
        if self.base is not None:  # сурет бар болса — сурет, әйтпесе көпбұрыш
            self.draw_image(screen, x, y)
            return
        if self.kind == "armored":
            fill = {3: (90, 105, 135), 2: (115, 100, 125), 1: (150, 90, 90)}[self.hp]
            edge, width = (170, 200, 240), 5
        elif self.kind == "comet":
            fill, edge, width = (200, 80, 60), (255, 200, 120), 3
        else:
            fill, edge, width = (125, 110, 100), (190, 175, 160), 3
        n = len(self.shape)
        angles = [math.radians(self.angle) + math.tau * i / n for i in range(n)]
        pts = [(x + self.size * k * math.cos(a), y + self.size * k * math.sin(a))
               for k, a in zip(self.shape, angles)]
        pygame.draw.polygon(screen, fill, pts)
        pygame.draw.polygon(screen, edge, pts, width)


# ==================== ufo.py ====================
class UFO(GameObject):
    """Кеменің үстінде қалқып, оған оқ атады және 20 секундтан кейін ұшып кетеді."""

    LIFE = 20

    def __init__(self, x, y):
        info = KINDS["ufo"]
        super().__init__(x, y, 42, hp=info["hp"])
        self.max_hp = info["hp"]
        self.points, self.drop_chance = info["points"], info["drop"]
        self.age, self.fire = 0.0, 1.5  # жасы; атуға дейінгі секунд
        # АНИМАЦИЯ: assets/ufo_0.png, ufo_1.png, ... кадрлары кезекпен ауысады (шамдар жыпылықтайды)
        self.anim = Animation(load_frames("ufo", (110, 70)), 0.12)

    def update(self, game, dt):  # override
        ship, scale = game.ship, game.time_scale
        self.age += dt * scale
        self.fire -= dt * scale
        self.anim.update(dt * scale)  # «Баяу уақыт» кезінде анимация да баяулайды (кадрлар ауысады)
        if self.age >= self.LIFE:
            self.kill()
            return
        leaving = self.age > self.LIFE - 3  # соңғы 3 с — жоғары ұшады, атпайды
        tx = max(60, min(WORLD_W - 60, ship.x + 350 * math.sin(self.age)))
        ty = -300 if leaving else (ship.y - 320 if ship.y >= 400 else ship.y + 320)
        self.x += max(-7, min(7, (tx - self.x) * 0.04)) * scale
        self.y += (ty - self.y) * 0.03 * scale
        if self.fire <= 0 and not leaving:
            self.fire = 1.4
            d = math.hypot(ship.x - self.x, ship.y - self.y) or 1
            game.shots.add(EnemyShot(self.x, self.y + 20,
                                     (ship.x - self.x) / d * SHOT_SPEED,
                                     (ship.y - self.y) / d * SHOT_SPEED))

    def on_ship_collision(self):  # override: НЛО кемеге тиіп жоғалмайды
        pass

    def draw(self, screen, cam):  # override
        x, y = int(self.x - cam[0]), int(self.y - cam[1])
        img = self.anim.image  # ағымдағы кадр
        if img:
            blit_center(screen, img, (x, y - 4))
        else:
            pygame.draw.ellipse(screen, (110, 230, 190), (x - 20, y - 28, 40, 34))  # күмбез
            pygame.draw.ellipse(screen, (150, 160, 185), (x - 44, y - 8, 88, 28))   # корпус
            pygame.draw.ellipse(screen, (220, 235, 255), (x - 44, y - 8, 88, 28), 3)
            blink = pygame.time.get_ticks() // 250
            for i, dx in enumerate((-28, 0, 28)):
                color = (255, 230, 90) if (blink + i) % 2 else (255, 120, 60)
                pygame.draw.circle(screen, color, (x + dx, y + 8), 4)
        pygame.draw.rect(screen, (90, 20, 20), (x - 30, y - 46, 60, 6))  # өмір жолағы
        pygame.draw.rect(screen, (255, 90, 90), (x - 30, y - 46, int(60 * max(self.hp, 0) / self.max_hp), 6))


# ==================== effects.py ====================
# Визуалды әсерлер де спрайттар: effects тобында тұрады, уақыты біткенде kill() арқылы жойылады.
EXPLOSION_COLORS = {
    "normal": [(190, 175, 160), (125, 110, 100), (255, 200, 120)],
    "armored": [(170, 200, 240), (90, 105, 135), (255, 255, 255)],
    "comet": [(255, 140, 50), (255, 220, 120), (200, 80, 60)],
    "ufo": [(110, 230, 190), (255, 230, 90), (255, 255, 255)],
    "ship": [(255, 150, 40), (255, 230, 120), (255, 255, 255)],
}
_fx_font = None


class Particle(GameObject):
    """Жарылыстың ұсақ бөлшегі: шашырап ұшады, кішірейіп, жоғалады."""

    def __init__(self, x, y, vx, vy, life, color, size):
        super().__init__(x, y, 1)
        self.vx, self.vy, self.life, self.color, self.size = vx, vy, life, color, size
        self.age = 0.0

    def update(self, game, dt):
        k = dt * FPS  # жылдамдық «кадр бойынша» берілген
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
    """Жарылыс анимациясы: assets/explosion_0.png ... кадрлары бір рет ойнатылады."""

    def __init__(self, x, y, size, duration=0.5):
        super().__init__(x, y, 1)
        self.size, self.duration, self.age = size, duration, 0.0
        side = max(32, int(size * 2.6) // 16 * 16)  # өлшемдерді дөңгелектеу — кэш аз толады
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
        t = self.age / self.duration  # сурет жоқ болса — кеңейетін шеңбер
        pygame.draw.circle(screen, (255, 170 - int(100 * t), 50), (int(pos[0]), int(pos[1])),
                           int(self.size * (0.4 + 1.4 * t)), max(1, int(8 * (1 - t))))


class FloatingText(GameObject):
    """Жоғары ұшып, бұлдырап жоғалатын жазу (мысалы, «+5» ұпай)."""

    def __init__(self, x, y, text, color=(255, 240, 120), life=0.9):
        super().__init__(x, y, 1)
        global _fx_font
        if _fx_font is None:
            _fx_font = pygame.font.SysFont("arial", 30, bold=True)
        shadow, label = _fx_font.render(text, True, (0, 0, 0)), _fx_font.render(text, True, color)
        self.image = pygame.Surface((label.get_width() + 2, label.get_height() + 2), pygame.SRCALPHA)
        self.image.blit(shadow, (2, 2))
        self.image.blit(label, (0, 0))
        self.life, self.age = life, 0.0

    def update(self, game, dt):
        self.y -= 70 * dt  # жоғары көтеріледі
        self.age += dt
        if self.age >= self.life:
            self.kill()

    def draw(self, screen, cam):
        self.image.set_alpha(int(255 * (1 - (self.age / self.life) ** 2)))
        blit_center(screen, self.image, self.screen_pos(cam))


# ==================== game.py ====================
def pick_buff(lives):
    """Өмір максимумда болса, «өмір» бонусы түспейді."""
    kinds = list(BUFFS)
    weights = [0 if k == "life" and lives >= MAX_LIVES else BUFFS[k]["weight"] for k in kinds]
    return random.choices(kinds, weights)[0]


class Game:
    """Ойынның басты класы: күй, цикл, деңгейлер, соқтығысулар, жеңу/жеңілу/қайта бастау."""

    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 1, 512)  # pygame.init()-тен бұрын: аз кідіріс
        pygame.init()
        self.sounds = SoundManager()
        self.screen = pygame.display.set_mode((W, H))
        pygame.display.set_caption("Тастардан жалтар!")
        self.clock = pygame.time.Clock()
        self.font, self.small_font, self.big_font = (
            pygame.font.SysFont("arial", s, bold=True) for s in (36, 26, 90))
        self.background = self._make_background()
        self.stars = [[random.randint(0, W), random.randint(0, H), random.randint(1, 3), random.uniform(0, 6.28)]
                      for _ in range(150)]  # x, y, радиус, фаза
        self.best = 0.0
        self.running = True
        self.selected_location = 0
        self.reset()

    # ------------------------------------------------------------ күй
    def _new_world(self):
        """Кеме мен барлық спрайт топтарын (pygame.sprite.Group) жаңадан жасайды."""
        self.ship = Ship(WORLD_W // 2, WORLD_H - 120)
        self.ship_group = pygame.sprite.GroupSingle(self.ship)
        self.rocks = pygame.sprite.Group()
        self.ufos = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.shots = pygame.sprite.Group()
        self.pickups = pygame.sprite.Group()
        self.effects = pygame.sprite.Group()  # жарылыс, бөлшектер, ұшатын жазулар
        self.shake = self.shake_total = self.shake_power = 0.0  # экран шайқалуы

    def reset(self):
        """Жаңа ойын бастау (қайта бастау осы әдісті шақырады)."""
        self._new_world()
        self.t = 0.0       # бүкіл ойын уақыты
        self.score = 0
        self.level = 0     # чтобы self.cfg не падал до start_level
        self.lt = 0.0
        self.banner = 0.0
        self.time_scale = 1.0
        self.rain = self.warning = False
        self.state = "menu"  # menu | play | level | won | lost
        self.over_delay = 0.0
        self.keys = pygame.key.get_pressed()
        self.cam_x = self.cam_y = 0.0
        self.update_camera()
        self.background = self._make_background(
            LOCATIONS[self.selected_location]["top"],
            LOCATIONS[self.selected_location]["bottom"]
        )

    def reset_game(self):
        """Таңдалған локацияда жаңа ойынды бастау."""
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
        """Ағымдағы деңгейдің баптаулары."""
        return LEVELS[self.level]

    def start_level(self, n):
        self.level = n
        self.lt = 0.0  # деңгей уақыты
        self.spawn_timer = 0.0
        self.next_ufo = random.uniform(*self.cfg["ufo"]) / 2 if self.cfg["ufo"] else None
        self.banner = 2.0  # «Деңгей N» жазуының көрсетілу уақыты
        self.state = "play"
        self.ship.invincible = max(self.ship.invincible, 1.0)

    @property
    def all_objects(self):
        """Барлық спрайт бір тізімде (сурет салу ретімен). Полиморфизм осы тізім арқылы."""
        return (self.rocks.sprites() + self.ufos.sprites() + self.shots.sprites()
                + self.pickups.sprites() + self.bullets.sprites() + self.ship_group.sprites()
                + self.effects.sprites())  # әсерлер ең үстінен салынады

    def update_camera(self):
        self.cam_x = max(0, min(WORLD_W - W, self.ship.x - W / 2))
        self.cam_y = max(0, min(WORLD_H - H, self.ship.y - H / 2))

    # ------------------------------------------------------------ негізгі цикл
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

    # ------------------------------------------------------------ жаңарту
    def update(self, dt):
        self.keys = pygame.key.get_pressed()
        self.update_stars()
        self.shake = max(0.0, self.shake - dt)
        if self.state == "menu":
            return
        if self.state in ("won", "lost"):
            self.over_delay -= dt
            self.update_effects(dt)  # ойын соңында да жарылыс ойнай береді
            return
        if self.state == "level":  # деңгейлер арасындағы үзіліс
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

        # Полиморфизм: бір тізім, бір цикл — әр спрайт өз update() әдісін орындайды.
        # all_objects — көшірме тізім, сондықтан цикл кезінде kill() қауіпсіз.
        for obj in self.all_objects:
            if obj.alive():  # Sprite.alive() — спрайт кемінде бір топта тұр ма
                obj.update(self, dt)
                obj.sync_rect()  # қозғалғаннан кейін rect-ті жаңарту (соқтығысу үшін)

        self.handle_collisions()
        self.update_camera()
        self.check_end()

    def update_effects(self, dt):
        for e in self.effects.sprites():
            e.update(self, dt)
            e.sync_rect()

    # ------------------------------------------------------------ әсерлер
    def spawn_burst(self, x, y, n, colors, speed=(2, 9), life=(0.3, 0.8), size=(3, 8)):
        """n ұсақ бөлшекті барлық бағытқа шашады."""
        for _ in range(n):
            a, s = random.uniform(0, math.tau), random.uniform(*speed)
            self.effects.add(Particle(x, y, math.cos(a) * s, math.sin(a) * s,
                                      random.uniform(*life), random.choice(colors), random.uniform(*size)))

    def explode(self, x, y, size, colors, n=14):
        """Жарылыс анимациясы + бөлшектер."""
        self.effects.add(Explosion(x, y, size))
        self.spawn_burst(x, y, n, colors)

    def add_shake(self, power, duration):
        """Экранды power пиксельге дейін duration секунд шайқайды (біртіндеп бәсеңдейді)."""
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
        mult = cfg["speed"] * location_speed * (1 + lt / 60)  # локация мен деңгейге қарай қиындайды
        interval = max(0.25, cfg["interval"] - lt * 0.005)
        self.rain = self.warning = False
        if cfg["rain"] and lt >= 12:  # әр 25 с сайын: ескерту (2 с), содан соң тас жаңбыры (6 с)
            phase = (lt - 12) % 25
            self.warning, self.rain = phase < 2, 2 <= phase < 8
        if self.rain:
            interval /= 2
        interval *= W / (W + 2 * MARGIN)  # тастар терезеден кеңірек шығады — тығыздықты сақтаймыз

        self.spawn_timer += dt
        while self.spawn_timer >= interval:
            self.spawn_timer -= interval
            self.rocks.add(self.make_rock(mult))
        if self.next_ufo is not None and lt >= self.next_ufo:  # НЛО терезенің жоғарысынан келеді
            self.ufos.add(UFO(self.cam_x + random.randint(200, W - 200), self.cam_y - 80))
            self.next_ufo = lt + random.uniform(*cfg["ufo"])

    def make_rock(self, mult):
        """Деңгейге қарай сауытты тастар мен кометалар жиірек шығады."""
        armored, comet = self.cfg["armored"], self.cfg["comet"]
        r = random.random()
        kind = "armored" if r < armored else "comet" if r < armored + comet else "normal"
        rock = Rock(mult, kind)
        rock.x = random.randint(int(self.cam_x) - MARGIN, int(self.cam_x) + W + MARGIN)
        rock.y = self.cam_y - rock.size
        rock.sync_rect()  # координата өзгерді — rect-ті жаңартамыз
        if kind == "comet":
            rock.aim_at(self.ship.x, self.ship.y)
        return rock

    # ------------------------------------------------------------ соқтығысулар
    def handle_collisions(self):
        ship = self.ship

        # оқ × тас және НЛО: spritecollide(спрайт, топ, dokill, collided) соқтыққандар тізімін қайтарады
        for b in self.bullets.sprites():
            hits = (pygame.sprite.spritecollide(b, self.rocks, False, CIRCLE)
                    or pygame.sprite.spritecollide(b, self.ufos, False, CIRCLE))
            if hits:
                target = hits[0]
                b.kill()
                if target.hit():  # hit() — полиморфты: жойылса True (kill() ішінде шақырылған)
                    self.on_destroyed(target)

        # кеме × бонус
        for p in pygame.sprite.spritecollide(ship, self.pickups, False, CIRCLE):
            info = BUFFS[p.kind]
            p.apply(ship)
            self.sounds.play("pickup")  # дыбыс: бонус алу
            self.effects.add(FloatingText(p.x, p.y - 30, info["name"], info["color"], life=1.2))  # әсер
            self.spawn_burst(p.x, p.y, 12, [info["color"], WHITE], speed=(1, 5), size=(2, 5))

        # кеме × тас, НЛО оғы, НЛО
        if ship.invincible <= 0:
            for group in (self.rocks, self.shots, self.ufos):
                hits = pygame.sprite.spritecollide(ship, group, False, CIRCLE)
                if hits:
                    hits[0].on_ship_collision()  # тас пен оқ жоғалады, НЛО қалады
                    hp_before = ship.hp
                    ship.hit()
                    self.sounds.play("hit")  # дыбыс: соқтығысу
                    if ship.hp < hp_before:  # кеме зақымданды: от бөлшектері + экран шайқалады
                        self.spawn_burst(ship.x, ship.y, 22, EXPLOSION_COLORS["ship"])
                        self.add_shake(14, 0.4)
                    else:                    # қалқан соққыны жұтты: көк ұшқындар
                        self.spawn_burst(ship.x, ship.y, 16, [BUFFS["shield"]["color"], WHITE], size=(2, 6))
                    break

    def on_destroyed(self, obj):
        self.score += obj.points
        self.sounds.play("explosion")  # дыбыс: ұпай алу (нысан жойылды)
        kind = getattr(obj, "kind", "ufo")  # тастың түрі; НЛО-да kind жоқ
        self.explode(obj.x, obj.y, obj.radius, EXPLOSION_COLORS[kind], int(6 + obj.radius * 0.3))
        self.effects.add(FloatingText(obj.x, obj.y - obj.radius, f"+{obj.points}"))  # ұпай жоғары ұшады
        if kind == "ufo":
            self.add_shake(8, 0.3)
        obj.on_destroy(self)  # тас бөлшектенеді, НЛО ештеңе істемейді
        if random.random() < obj.drop_chance:
            self.pickups.add(Pickup(pick_buff(self.ship.hp), obj.x, obj.y))

    # ------------------------------------------------------------ деңгей / жеңу / жеңілу
    def check_level_complete(self):
        """Деңгей өтті: осы деңгейдің уақыты бойы аман қалды."""
        return self.ship.alive() and self.lt >= self.cfg["time"]

    def check_win(self):
        """Жеңу: соңғы деңгей өтті."""
        return self.check_level_complete() and self.level == len(LEVELS) - 1

    def check_lose(self):
        """Жеңілу: барлық өмір таусылды (кеме топтан шығарылды)."""
        return not self.ship.alive()

    def check_end(self):
        if self.check_lose():
            self.finish("lost")
        elif self.check_win():
            self.finish("won")
        elif self.check_level_complete():
            self.finish_level()

    def finish_level(self):
        """Келесі деңгейге өту: қауіптерді тазалап, сыйға +1 өмір береміз."""
        for group in (self.rocks, self.ufos, self.bullets, self.shots):
            group.empty()
        self.ship.hp = min(MAX_LIVES, self.ship.hp + 1)
        self.state, self.over_delay = "level", LEVEL_PAUSE
        self.rain = self.warning = False
        self.sounds.play("levelup")  # дыбыс: деңгей өтті

    def finish(self, state):
        self.state = state
        self.over_delay = 0.8  # кездейсоқ басып қайта бастап жібермеу үшін
        self.best = max(self.best, self.t)
        self.sounds.play("win" if state == "won" else "gameover")  # дыбыс: ойын соңы
        if state == "lost":  # кеме жарылады
            self.explode(self.ship.x, self.ship.y, 60, EXPLOSION_COLORS["ship"], 40)
            self.add_shake(22, 0.8)

    def restart(self):
        """Қайта бастау: таңдалған локациядағы жаңа ойын."""
        self.reset_game()

    # ------------------------------------------------------------ сурет салу
    def draw(self):
        if self.state == "menu":
            self.draw_menu()
            return

        ox, oy = self.shake_offset()  # экран шайқалуы: камераны кездейсоқ жылжытамыз
        cam = (self.cam_x + ox, self.cam_y + oy)
        self.screen.blit(self.background, (0, 0))
        now = pygame.time.get_ticks() / 1000
        for x, y, r, ph in self.stars:  # параллакс: үлкен жұлдыздар жылдамырақ қозғалады
            c = int(170 + 85 * math.sin(now * 2 + ph))
            pos = (int((x - cam[0] * r * 0.1) % W), int((y - cam[1] * r * 0.1) % H))
            pygame.draw.circle(self.screen, (c, c, c), pos, r)
        pygame.draw.rect(self.screen, (255, 220, 60), (int(-cam[0]), int(-cam[1]), WORLD_W, WORLD_H), 4)

        # Полиморфизм: бір тізім, бір цикл — әр спрайт өзін өзі салады
        for obj in self.all_objects:
            obj.draw(self.screen, cam)

        self.draw_hud()
        if self.state == "level":
            self.draw_level_screen()
        elif self.state in ("won", "lost"):
            self.draw_end_screen()

    def draw_menu(self):
        """Басты мәзір және локация таңдау экраны."""
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
                    self.screen, (255, 220, 60),
                    (W // 2 - 300, y - 32, 600, 64), 3, border_radius=12
                )

        selected_location = LOCATIONS[self.selected_location]
        self.center(self.small_font, f"Скорость препятствий: x{selected_location['speed']:.2f}", 800, (180, 220, 255))
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

        # деңгей аяқталуына дейінгі прогресс-жолақ
        total = self.cfg["time"]
        bw, bx, by = 600, (W - 600) // 2, H - 70
        pygame.draw.rect(self.screen, (20, 20, 60), (bx, by, bw, 26), border_radius=8)
        pygame.draw.rect(self.screen, (120, 255, 150), (bx, by, int(bw * min(1, self.lt / total)), 26),
                         border_radius=8)
        pygame.draw.rect(self.screen, (255, 220, 60), (bx, by, bw, 26), 3, border_radius=8)
        self.center(self.small_font, f"Деңгей аяқталуына: {max(0, total - self.lt):.0f} с", by - 34, (180, 255, 200))

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
        pygame.draw.rect(self.screen, (150, 150, 200), (*m(self.cam_x, self.cam_y), int(W * k), int(H * k)), 1)
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

    # ------------------------------------------------------------ көмекші
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


# ==================== main.py ====================
def main():
    Game().run()


if __name__ == "__main__":
    main()
