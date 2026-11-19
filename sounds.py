import math
import random
from array import array
import pygame
from settings import SOUND_VOLUME


class SoundManager:
    """Дыбыстарды файлсыз синтездейді және ойнатады."""

    def __init__(self):
        self.sounds = {}
        self.enabled = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(44100, -16, 1, 512)
            self.rate, fmt, self.channels = pygame.mixer.get_init()
            if fmt != -16:
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
            "gameover": self._make(
                [(392, 380, 0.3), (330, 320, 0.3), (262, 250, 0.3), (196, 150, 0.6)],
                vol=0.35, square=True
            ),
            "win": self._make(
                [(523, 523, 0.15), (659, 659, 0.15), (784, 784, 0.15), (1047, 1047, 0.5)],
                vol=0.3
            ),
        }
        for s in self.sounds.values():
            s.set_volume(SOUND_VOLUME)

    def _make(self, notes, vol=0.3, square=False, noise=0.0):
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
                env = (1 - t) ** 2 * min(1.0, i / 80)
                v = int(32767 * vol * env * s)
                data.extend([v] * self.channels)
        return pygame.mixer.Sound(buffer=data.tobytes())

    def play(self, name):
        if self.enabled and name in self.sounds:
            self.sounds[name].play()