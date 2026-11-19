import os
import sys
import pygame

# Ресурстар папкасы (.py және PyInstaller .exe үшін бірдей жұмыс істейді)
BASE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

W, H = 1920, 1080              # терезе өлшемі
WORLD_W, WORLD_H = 3840, 2160  # карта өлшемі (терезеден екі есе үлкен)
FPS = 60
LEVEL_PAUSE = 2.5              # деңгей аяқталған соңғы үзіліс (секунд)

# Деңгейлер: time — өту уақыты (с), speed — тас жылдамдығы, interval — шығу аралығы,
# armored/comet — сауытты тас пен комета ықтималдығы, ufo — НЛО аралығы, rain — тас жаңбыры
LEVELS = [
    dict(name="1level", time=25, speed=0.8, interval=1.0, armored=0.0, comet=0.0, ufo=None, rain=False),
    dict(name="2level", time=45, speed=1.0, interval=0.9, armored=0.1, comet=0.1, ufo=None, rain=False),
    dict(name="3level", time=50, speed=1.2, interval=0.8, armored=0.15, comet=0.2, ufo=(25, 35), rain=False),
    dict(name="4level", time=67, speed=1.4, interval=0.7, armored=0.2, comet=0.25, ufo=(20, 30), rain=True),
    dict(name="5level", time=80, speed=1.6, interval=0.6, armored=0.25, comet=0.3, ufo=(15, 25), rain=True),
]

# Локациялар
LOCATIONS = [
    {"name": "Космос", "top": (5, 5, 30), "bottom": (60, 40, 120), "speed": 1.0},
    {"name": "Марс", "top": (45, 8, 5), "bottom": (170, 65, 35), "speed": 1.10},
    {"name": "Ледяная планета", "top": (5, 30, 60), "bottom": (75, 165, 210), "speed": 0.90},
    {"name": "Галактика", "top": (20, 0, 45), "bottom": (105, 35, 155), "speed": 1.20},
]

FIRE_DELAY, SPLIT_SIZE, MAX_LIVES = 0.18, 34, 5
BULLET_SPEED, BULLET_R, SHIP_R, PICKUP_R = 22, 5, 28, 20
SHOT_SPEED, MARGIN = 9, 300

WHITE = (255, 255, 255)

# Кеме спрайты
SHIP_SPRITE = "ship.png"
SHIP_SIZE = (62, 100)
SHIP_ANIM_DELAY = 0.1
SHIP_ROTATE = 0

# Бонустар / бафтар
BUFFS = {
    "triple": {"letter": "3", "color": (255, 160, 40), "name": "Үш ату", "time": 10, "weight": 3},
    "rapid": {"letter": "R", "color": (255, 90, 90), "name": "Жылдам ату", "time": 8, "weight": 3},
    "slow": {"letter": "Z", "color": (170, 120, 255), "name": "Баяу уақыт", "time": 6, "weight": 2},
    "life": {"letter": "+", "color": (90, 230, 120), "name": "Өмір +1", "time": 0, "weight": 1},
    "shield": {"letter": "S", "color": (80, 180, 255), "name": "Қалқан", "time": 0, "weight": 0},
}

# Тас түрлері мен НЛО
KINDS = {
    "normal": dict(size=(22, 50), speed=1.0, hp=1, points=1, drop=0.08),
    "armored": dict(size=(50, 64), speed=0.7, hp=3, points=5, drop=0.6),
    "comet": dict(size=(16, 24), speed=1.8, hp=1, points=3, drop=0.2),
    "ufo": dict(hp=10, points=15, drop=1.0),
}

CIRCLE = pygame.sprite.collide_circle
SOUND_VOLUME = 0.6