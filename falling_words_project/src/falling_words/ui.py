"""Colors, cached fonts and the small reusable widgets (FloatingText, Button, Dropdown)."""
from functools import cache

import pygame

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
