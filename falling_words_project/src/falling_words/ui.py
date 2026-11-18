"""Colors, cached fonts and the small reusable widgets (FloatingText, Button, Dropdown)."""
from functools import cache

import pygame

from .coaching import FINGER_NUMBER, FINGER_OF, KEY_ROWS, finger_code

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 100, 255)
YELLOW = (255, 255, 0)
PURPLE = (180, 0, 255)
ORANGE = (255, 165, 0)
DARK_GREEN = (0, 150, 0)
DARK_RED = (150, 0, 0)
DARK_BLUE = (0, 0, 150)
GOLD = (255, 215, 0)

FONT_NORMAL, FONT_SMALL, FONT_BIG, FONT_BUTTON = 48, 32, 72, 36
FONT_TITLE, FONT_BODY, FONT_KEY = 40, 28, 26


@cache
def get_font(size: int) -> pygame.font.Font:
    """Default pygame font at `size`; created lazily so importing this module needs no display."""
    return pygame.font.Font(None, size)


class FloatingText:
    def __init__(self, x, y, text, color):
        self.x = x
        self.y = y
        self.text = text
        self.color = color
        self.alpha = 255
        self.speed = 2
        
    def update(self):
        self.y -= self.speed
        self.alpha -= 5
        
    def draw(self, surface):
        if self.alpha > 0:
            text_surf = get_font(FONT_SMALL).render(self.text, True, self.color)
            text_surf.set_alpha(max(0, self.alpha))
            surface.blit(text_surf, (self.x, self.y))

class Button:
    def __init__(self, x, y, width, height, text, color, hover_color):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.current_color = color
    
    def draw(self, surface):
        shadow_rect = self.rect.copy()
        shadow_rect.y += 4
        pygame.draw.rect(surface, (50, 50, 50), shadow_rect, border_radius=8)
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=8)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=8)
        text_surface = get_font(FONT_BUTTON).render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def update(self, mouse_pos):
        self.current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
    
    def handle_event(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

class Dropdown:
    def __init__(self, x, y, width, height, options, selected_index=0):
        self.rect = pygame.Rect(x, y, width, height)
        self.options = options
        self.selected_index = selected_index
        self.is_open = False
        self.color = (180, 100, 0)
        self.hover_color = ORANGE
        self.current_color = self.color
        
        self.open_rects = []
        for i in range(len(options)):
            self.open_rects.append(pygame.Rect(x, y + (i + 1) * height, width, height))
            
    def draw(self, surface):
        pygame.draw.rect(surface, self.current_color, self.rect, border_radius=4)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=4)
        
        indicator_x = self.rect.right - 20
        indicator_y = self.rect.centery
        if self.is_open:
            pygame.draw.polygon(surface, WHITE, [(indicator_x-6, indicator_y+4), (indicator_x+6, indicator_y+4), (indicator_x, indicator_y-4)])
        else:
            pygame.draw.polygon(surface, WHITE, [(indicator_x-6, indicator_y-4), (indicator_x+6, indicator_y-4), (indicator_x, indicator_y+4)])
            
        text_surf = get_font(FONT_SMALL).render(f"{self.options[self.selected_index]}", True, WHITE)
        text_rect = text_surf.get_rect(center=(self.rect.centerx - 10, self.rect.centery))
        surface.blit(text_surf, text_rect)
        
        if self.is_open:
            for i, opt_rect in enumerate(self.open_rects):
                pygame.draw.rect(surface, (150, 80, 0), opt_rect)
                pygame.draw.rect(surface, WHITE, opt_rect, 1)
                opt_text = get_font(FONT_SMALL).render(self.options[i], True, WHITE)
                surface.blit(opt_text, opt_text.get_rect(center=opt_rect.center))
                
    def update(self, mouse_pos):
        self.current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_open:
                for i, opt_rect in enumerate(self.open_rects):
                    if opt_rect.collidepoint(event.pos):
                        self.selected_index = i
                        self.is_open = False
                        return self.options[i]
                self.is_open = False
                return "CLOSED"
            else:
                if self.rect.collidepoint(event.pos):
                    self.is_open = True
                    return "OPENED"
        return None


class Slider:
    """Horizontal slider with a labelled value. Drag the knob or click the track.

    handle_event returns True only when the player lets go AND the value changed, so the
    caller can restart the game once per adjustment instead of on every pixel of the drag.

    Example:
        speed = Slider(x=600, y=250, width=250, minimum=0.5, maximum=2.5, step=0.1, value=1.0)
        if speed.handle_event(event):
            print(speed.value)
    """

    KNOB_RADIUS = 11

    def __init__(self, x, y, width, minimum, maximum, step, value):
        if not minimum <= value <= maximum:
            raise ValueError(f"slider value {value} outside {minimum}..{maximum}")
        self.left, self.y, self.width = x, y, width
        self.minimum, self.maximum, self.step = minimum, maximum, step
        self.value = value
        self.dragging = False
        self._value_at_press = value
        self.hit_rect = pygame.Rect(x - self.KNOB_RADIUS, y - self.KNOB_RADIUS, width + 2 * self.KNOB_RADIUS,
                                    2 * self.KNOB_RADIUS)

    def value_at(self, mouse_x) -> float:
        """Slider value for a mouse x position, snapped to the step and clamped to the range."""
        fraction = min(1.0, max(0.0, (mouse_x - self.left) / self.width))
        steps = round(fraction * (self.maximum - self.minimum) / self.step)
        return round(self.minimum + steps * self.step, 2)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hit_rect.collidepoint(event.pos):
            self.dragging, self._value_at_press = True, self.value
            self.value = self.value_at(event.pos[0])
        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.value = self.value_at(event.pos[0])
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            self.dragging = False
            return self.value != self._value_at_press
        return False

    def draw(self, surface, label):
        text = get_font(FONT_SMALL).render(f"{label}: {self.value:.1f}", True, ORANGE)
        surface.blit(text, (self.left, self.y - 38))
        pygame.draw.line(surface, (90, 90, 90), (self.left, self.y), (self.left + self.width, self.y), 6)
        knob_x = self.left + round((self.value - self.minimum) / (self.maximum - self.minimum) * self.width)
        pygame.draw.line(surface, ORANGE, (self.left, self.y), (knob_x, self.y), 6)
        pygame.draw.circle(surface, WHITE, (knob_x, self.y), self.KNOB_RADIUS)
        pygame.draw.circle(surface, ORANGE, (knob_x, self.y), self.KNOB_RADIUS - 4)


class Checkbox:
    """A labelled tick box; handle_event returns True when it was clicked (and so toggled)."""

    SIZE = 26

    def __init__(self, x, y, label, checked=True):
        self.rect = pygame.Rect(x, y, self.SIZE, self.SIZE)
        self.label, self.checked = label, checked
        text_width = get_font(FONT_SMALL).size(label)[0]
        self.hit_rect = pygame.Rect(x, y, self.SIZE + 10 + text_width, self.SIZE)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.hit_rect.collidepoint(event.pos):
            self.checked = not self.checked
            return True
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, (40, 40, 40), self.rect, border_radius=4)
        pygame.draw.rect(surface, WHITE, self.rect, 2, border_radius=4)
        if self.checked:
            r = self.rect
            pygame.draw.lines(surface, GREEN, False, [(r.x + 5, r.centery), (r.x + 10, r.bottom - 7),
                                                      (r.right - 5, r.y + 6)], 4)
        text = get_font(FONT_SMALL).render(self.label, True, WHITE)
        surface.blit(text, (self.rect.right + 10, self.rect.centery - text.get_height() // 2))


# ---------- coaching card helpers ----------
FINGER_COLORS = {"pinky": (200, 90, 200), "ring": (90, 150, 255), "middle": (80, 200, 120), "index": (255, 190, 60)}
WORD_COL_WIDTH, CODE_FONT = 32, 22   # one letter's column in finger-code mode, and its small code text
KEY_SIZE, KEY_GAP, ROW_INDENT = 42, 4, 20   # each row is shifted right like a real keyboard
KEYBOARD_WIDTH = len(KEY_ROWS[0]) * (KEY_SIZE + KEY_GAP) + 2 * ROW_INDENT
KEYBOARD_HEIGHT = len(KEY_ROWS) * (KEY_SIZE + KEY_GAP) + 34   # three rows plus the finger legend


def draw_word(surface, text, x, y, typed="", show_codes=False) -> None:
    """Draw a falling word. With `show_codes`, each letter gets its hand and finger under it.

    Each letter sits in a fixed-width column with its code (e.g. "R1") centered beneath, colored by
    finger, and letters already typed correctly turn green. Without it, the word is plain white text.

    Example:
        draw_word(screen, "haha", 100, 50, typed="h", show_codes=True)
    """
    if not show_codes:
        surface.blit(get_font(FONT_NORMAL).render(text, True, WHITE), (x, y))
        return
    done = len(typed) if text.lower().startswith(typed.lower()) else 0
    letter_font, code_font = get_font(FONT_NORMAL), get_font(CODE_FONT)
    for i, ch in enumerate(text):
        center_x = x + i * WORD_COL_WIDTH + WORD_COL_WIDTH // 2
        letter = letter_font.render(ch, True, GREEN if i < done else WHITE)
        surface.blit(letter, letter.get_rect(midtop=(center_x, y)))
        code = code_font.render(finger_code(ch), True, FINGER_COLORS[FINGER_OF[ch][1]])
        surface.blit(code, code.get_rect(midtop=(center_x, y + letter.get_height())))


def draw_dim_overlay(surface, color, alpha=200) -> None:
    overlay = pygame.Surface(surface.get_size())
    overlay.set_alpha(alpha)
    overlay.fill(color)
    surface.blit(overlay, (0, 0))


def draw_wrapped(surface, text, font, color, x, y, max_width) -> int:
    """Draw `text` word-wrapped to `max_width`; returns the y just below the last line."""
    line = ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and font.size(candidate)[0] > max_width:
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize()
            candidate = word
        line = candidate
    surface.blit(font.render(line, True, color), (x, y))
    return y + font.get_linesize()


def draw_keyboard(surface, left, top, highlighted) -> None:
    """QWERTY picture: keys in `highlighted` are colored by finger, the rest are dim.

    The little bar on F and J marks where the index fingers rest.
    """
    key_font = get_font(FONT_KEY)
    for row, keys in enumerate(KEY_ROWS):
        for col, key in enumerate(keys):
            x = left + ROW_INDENT * row + col * (KEY_SIZE + KEY_GAP)
            y = top + row * (KEY_SIZE + KEY_GAP)
            rect = pygame.Rect(x, y, KEY_SIZE, KEY_SIZE)
            lit = key in highlighted
            pygame.draw.rect(surface, FINGER_COLORS[FINGER_OF[key][1]] if lit else (45, 45, 55), rect, border_radius=6)
            label = key_font.render(key.upper(), True, (20, 20, 20) if lit else (110, 110, 120))
            surface.blit(label, label.get_rect(center=rect.center))
            if key in "fj":
                pygame.draw.line(surface, (20, 20, 20) if lit else (110, 110, 120),
                                 (x + 12, y + KEY_SIZE - 7), (x + KEY_SIZE - 12, y + KEY_SIZE - 7), 3)
    legend_y = top + len(KEY_ROWS) * (KEY_SIZE + KEY_GAP) + 6
    x = left + ROW_INDENT
    for finger, color in FINGER_COLORS.items():
        pygame.draw.rect(surface, color, (x, legend_y, 18, 18), border_radius=4)
        text = get_font(FONT_BODY - 4).render(f"{FINGER_NUMBER[finger]} {finger}", True, WHITE)
        surface.blit(text, (x + 24, legend_y - 1))
        x += 24 + text.get_width() + 24
