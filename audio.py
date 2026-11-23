"""
AUDIO — Synthesized sound effects and ambient music.
Only sounds with a live call site are generated: jump, land, wrong, hurt, click, check, level.
"""
import math
import pygame


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def make_tone(frequency=440, duration=0.12, volume=0.18, kind="sine", slide=0.0):
    """Generate a short tone with attack/release envelope."""
    if not pygame.mixer.get_init():
        return None
    rate = 22050
    count = max(1, int(rate * duration))
    samples = bytearray()
    phase = 0.0
    for i in range(count):
        progress = i / count
        phase += 2 * math.pi * (frequency + slide * progress) / rate
        env = min(1.0, i / max(1, count * 0.06)) * (1.0 - progress) ** 1.4
        if kind == "triangle":
            wave = (2.0 / math.pi) * math.asin(math.sin(phase))
        elif kind == "bell":
            wave = (math.sin(phase) * 0.68 + math.sin(phase * 2.0) * 0.22
                    + math.sin(phase * 3.0) * 0.10)
        else:
            wave = math.sin(phase)
        val = int(_clamp(32767 * volume * env * wave, -32768, 32767))
        samples.extend(val.to_bytes(2, "little", signed=True))
    try:
        return pygame.mixer.Sound(buffer=bytes(samples))
    except pygame.error:
        return None


def make_chord(freqs, step_dur=0.065, volume=0.16):
    """Generate an arpeggiated chord from a list of frequencies."""
    if not pygame.mixer.get_init():
        return None
    rate = 22050
    samples = bytearray()
    for idx, freq in enumerate(freqs):
        count = max(1, int(rate * step_dur * (1.8 if idx == len(freqs) - 1 else 1.0)))
        for i in range(count):
            t = i / rate
            env = min(1.0, i / max(1, count * 0.08)) * ((1.0 - i / count) ** 1.25)
            w = math.sin(2 * math.pi * freq * t) * 0.72 + math.sin(4 * math.pi * freq * t) * 0.28
            val = int(_clamp(32767 * volume * env * w, -32768, 32767))
            samples.extend(val.to_bytes(2, "little", signed=True))
    try:
        return pygame.mixer.Sound(buffer=bytes(samples))
    except pygame.error:
        return None


def make_ambient_music():
    """Generate a looping ambient chord progression (12 seconds)."""
    if not pygame.mixer.get_init():
        return None
    rate = 22050
    chords = [(110.00, 164.81, 220.00, 329.63), (130.81, 196.00, 246.94, 392.00),
              (146.83, 220.00, 261.63, 329.63), (98.00, 146.83, 196.00, 293.66)]
    samples = bytearray()
    for i in range(int(rate * 12.0)):
        t = i / rate
        bar_f = t / 3.0
        bar = int(bar_f) % len(chords)
        fade = math.sin(math.pi * _clamp(bar_f - int(bar_f), 0.0, 1.0)) ** 0.45
        root, fifth, octave, high = chords[bar]
        tone = (math.sin(2 * math.pi * root * t) * 0.34
                + math.sin(2 * math.pi * fifth * t) * 0.20
                + math.sin(2 * math.pi * octave * t) * 0.16
                + math.sin(2 * math.pi * high * t) * (0.08 + 0.05 * math.sin(t * 2.0)))
        val = int(_clamp(32767 * 0.075 * fade * tone, -32768, 32767))
        samples.extend(val.to_bytes(2, "little", signed=True))
    try:
        return pygame.mixer.Sound(buffer=bytes(samples))
    except pygame.error:
        return None


class AudioManager:
    """Owns all game sounds and the ambient music loop."""

    def __init__(self):
        self.available = False
        self.music_volume, self.sfx_volume = 0.28, 0.62
        self.music, self.sounds = None, {}
        try:
            # pygame.init() already opens the mixer as 44.1 kHz stereo, which would
            # play our 22.05 kHz mono buffers 4x too fast and two octaves too high.
            if pygame.mixer.get_init() != (22050, -16, 1):
                pygame.mixer.quit()
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512,
                                  allowedchanges=0)
            self.available = True
            pygame.mixer.set_num_channels(16)
            self.music = make_ambient_music()
            self.sounds = {
                "jump":  make_tone(340, 0.13, 0.16, "triangle", slide=180),
                "land":  make_tone(125, 0.08, 0.14, "triangle", slide=-40),
                "wrong": make_tone(190, 0.25, 0.18, "triangle", slide=-55),
                "click": make_tone(580, 0.045, 0.11, "bell"),
                "hurt":  make_tone(150, 0.22, 0.20, "triangle", slide=-90),
                "check": make_chord([659.25, 880.00, 1174.66], 0.07, 0.15),
                "level": make_chord([523.25, 659.25, 783.99, 1046.50, 1318.51], 0.08, 0.18),
            }
            if self.music:
                self.music.set_volume(self.music_volume)
                self.music.play(-1)
        except (pygame.error, OSError) as exc:
            print(f"[audio] disabled ({exc}) — running silently")
            self.available = False

    def play(self, name):
        if not self.available:
            return
        snd = self.sounds.get(name)
        if snd:
            try:
                snd.set_volume(self.sfx_volume)
                ch = pygame.mixer.find_channel()
                if ch:
                    ch.play(snd)
            except pygame.error:
                pass

    def set_music(self, v):
        self.music_volume = _clamp(v, 0.0, 1.0)
        if self.music:
            self.music.set_volume(self.music_volume)

    def set_sfx(self, v):
        self.sfx_volume = _clamp(v, 0.0, 1.0)