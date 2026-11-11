"""Falling Words: type each falling word and press Space or Enter before it reaches the bottom."""
import argparse
import random
import sys
from pathlib import Path

import pygame
from loguru import logger

from . import sounds
from .coaching import display_name, intro_card, result_lines, streak_cheers, suggested_level
from .profiles import DEFAULT_PROFILES_DIR, DIFFICULTY_SETTINGS, Profile, load_profile
from .score_manager import ScoreManager, scores_path
from .sounds import play
from .sprite_manager import SpriteManager
from .ui import (BLACK, BLUE, DARK_BLUE, DARK_GREEN, DARK_RED, FONT_BIG, FONT_BODY, FONT_NORMAL, FONT_SMALL, FONT_TITLE,
                 GOLD, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW,
                 Button, Dropdown, FloatingText, draw_dim_overlay, draw_keyboard, draw_wrapped, get_font)
from .ui import KEYBOARD_WIDTH
from .word_manager import WordManager

TOTAL_WORDS = 30           
SPEED_INCREASE_PER_WORD = 0.02  
MAX_WORDS_ON_SCREEN = 10   
INITIAL_WORDS = 1          
WORD_SPAWN_DELAY = 2.0     
BACKSPACE_DELAY = 150      
BACKSPACE_INTERVAL = 50    

MIN_WORD_LENGTH = 3
DECELERATION_RATE = 1.0
NUMBER_OF_WORDS_BEFORE_LAG = 4
LAG = 5  

WIDTH, HEIGHT = 900, 650
FPS = 60


class Word:
    def __init__(self, x, y, text, speed):
        self.x = x
        self.y = y
        self.text = text
        self.speed = speed
        self.color = WHITE
    
    def update(self):
        self.y += self.speed
    
    def draw(self, surface):
        word_surface = get_font(FONT_NORMAL).render(self.text, True, self.color)
        surface.blit(word_surface, (self.x, self.y))
    
    def is_off_screen(self):
        return self.y > HEIGHT - 100

class Game:
    def __init__(self, screen, profile: Profile | None = None):
        self.screen = screen
        self.word_manager = WordManager(profile=profile)
        self.sprite_manager = SpriteManager(width=WIDTH, height=HEIGHT, enabled=True)
        self.score_manager = ScoreManager(scores_path(profile.name if profile else None))
        self.player_name = display_name(profile.name) if profile else ""
        
        self.reset_button = Button(
            x=WIDTH - 130, y=20, width=110, height=40,
            text="🔄 RESET", color=DARK_GREEN, hover_color=GREEN
        )
        self.difficulties = list(DIFFICULTY_SETTINGS.keys())
        self.difficulty_index = self.difficulties.index(profile.difficulty) if profile else 0
        self.diff_button = Button(
            x=WIDTH - 260, y=20, width=120, height=40,
            text=self.difficulties[self.difficulty_index], color=DARK_BLUE, hover_color=BLUE
        )
        self.fx_button = Button(
            x=WIDTH - 380, y=20, width=110, height=40,
            text="🌌 FX ON", color=(100, 0, 150), hover_color=PURPLE
        )
        
        level_names = self.word_manager.level_names
        current_idx = level_names.index(self.word_manager.current_level) if self.word_manager.current_level in level_names else 0
        self.dropdown = Dropdown(
            x=WIDTH - 640, y=20, width=250, height=40, 
            options=level_names, selected_index=current_idx
        )
        
        self.reset_game()
        self.show_intro()

    def reset_game(self):
        self.words = []
        self.floating_texts = []
        self.current_input = ""
        self.score = 0  
        self.words_typed = 0  
        self.words_spawned = 0
        self.total_missed = 0  
        self.total_attempts = 0  
        self.game_over = False
        self.victory = False
        self.is_new_high_score = False
        self.perfect_streak = 0
        self.final_accuracy = 0.0
        self.suggested_level = ""   # "" = no next level to suggest
        self.result_text = []
        
        diff_name = self.difficulties[self.difficulty_index]
        self.current_speed = DIFFICULTY_SETTINGS[diff_name]
        
        self.last_spawn_time = pygame.time.get_ticks()
        self.spawn_delay = int(WORD_SPAWN_DELAY * 1000)
        self.made_mistake = False
        self.perfect_words = 0
        self.backspace_pressed = False
        self.backspace_last_time = 0
        self.words_spawned_since_lag = 0
        self.lag_end_time = 0
        
        for _ in range(INITIAL_WORDS):
            self.spawn_word()
    
    def spawn_word(self):
        word_text = self.word_manager.get_word()
        x = random.randint(10, WIDTH - 200)
        y = random.randint(10, 100)
        current_base = self.current_speed + (self.words_typed * SPEED_INCREASE_PER_WORD)
        
        word_length = len(word_text)
        if word_length <= MIN_WORD_LENGTH:
            speed = current_base
        else:
            speed = current_base * DECELERATION_RATE * (MIN_WORD_LENGTH / word_length)
            
        self.words.append(Word(x, y, word_text, speed))
        self.words_spawned += 1
        self.total_attempts += 1
        
        self.words_spawned_since_lag += 1
        if self.words_spawned_since_lag >= NUMBER_OF_WORDS_BEFORE_LAG:
            self.lag_end_time = pygame.time.get_ticks() + (LAG * 1000)
            self.words_spawned_since_lag = 0
    
    def handle_backspace(self):
        if len(self.current_input) > 0:
            self.current_input = self.current_input[:-1]
    
    def handle_input(self, event):
        if event.key == pygame.K_F1:
            self.show_intro()
            return
        if self.intro_open:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_ESCAPE):
                self.dismiss_intro()
            return
        if self.game_over or self.victory:
            if event.key == pygame.K_RETURN:
                self.select_level(self.suggested_level) if self.suggested_level else self.reset_game()
            return

        if self.dropdown.is_open:
            return

        if event.key == pygame.K_BACKSPACE:
            self.handle_backspace()
            self.backspace_pressed = True
            self.backspace_last_time = pygame.time.get_ticks()
            self.made_mistake = True
        
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            matched = False
            for word in self.words[:]:
                if word.text.lower() == self.current_input.lower():
                    self.words.remove(word)
                    self.words_typed += 1
                    matched = True
                    play("correct")
                    
                    if not self.made_mistake:
                        self.score += 2
                        self.perfect_words += 1
                        self.perfect_streak += 1
                        self.floating_texts.append(FloatingText(150, HEIGHT - 110, "+2 Perfect!", PURPLE))
                        for cheer in streak_cheers(self.player_name, self.perfect_streak):
                            self.floating_texts.append(FloatingText(WIDTH // 2 - 200, HEIGHT // 2, cheer, GOLD))
                    else:
                        self.score += 1
                        self.perfect_streak = 0
                    
                    self.current_input = ""
                    self.made_mistake = False
                    
                    if not self.victory and not self.game_over:
                        if pygame.time.get_ticks() > self.lag_end_time:
                            self.spawn_word()
                    
                    if self.score >= TOTAL_WORDS and not self.victory:
                        self._finish(won=True)
                    break
            
            if not matched:
                self.current_input = ""
                self.made_mistake = False
                self.perfect_streak = 0
                play("incorrect")
        
        elif event.unicode.isprintable():
            self.current_input += event.unicode
        elif event.key == pygame.K_k and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_input = ""  
            play("incorrect")  
            self.made_mistake = True
    
    def handle_keyup(self, event):
        if event.key == pygame.K_BACKSPACE:
            self.backspace_pressed = False
    
    def update_backspace_repeat(self):
        if self.backspace_pressed and not self.game_over and not self.victory:
            current_time = pygame.time.get_ticks()
            if current_time - self.backspace_last_time > BACKSPACE_DELAY:
                if (current_time - self.backspace_last_time - BACKSPACE_DELAY) % BACKSPACE_INTERVAL < 10:
                    self.handle_backspace()
    
    def update(self):
        self.sprite_manager.update()
        if self.victory or self.game_over or self.intro_open:
            return
        
        if self.dropdown.is_open:
            return
            
        self.update_backspace_repeat()
        current_time = pygame.time.get_ticks()
        
        if (current_time - self.last_spawn_time > self.spawn_delay and 
            len(self.words) < MAX_WORDS_ON_SCREEN and
            current_time > self.lag_end_time):
            self.spawn_word()
            self.last_spawn_time = current_time
        
        for word in self.words[:]:
            word.update()
            if word.is_off_screen():
                self.words.remove(word)
                self.total_missed += 1
                self.total_attempts += 1
                self.perfect_streak = 0
                play("incorrect")
                
                if len(self.words) < MAX_WORDS_ON_SCREEN * 2 and pygame.time.get_ticks() > self.lag_end_time:
                    self.spawn_word()
                    
        for f_text in self.floating_texts[:]:
            f_text.update()
            if f_text.alpha <= 0:
                self.floating_texts.remove(f_text)
        
        if len(self.words) > MAX_WORDS_ON_SCREEN * 2:
            self._finish(won=False)
    
    @property
    def playing(self) -> bool:
        return not (self.victory or self.game_over or self.intro_open)

    def show_intro(self):
        """Pause and show the coaching card (finger placement and keyboard picture) for this level."""
        self.intro = intro_card(self.player_name, self.word_manager.level_letters())
        self.intro_open = True

    def dismiss_intro(self):
        self.intro_open = False
        self.last_spawn_time = pygame.time.get_ticks()  # restart the spawn timer; words resume where they were

    def select_level(self, level_name):
        self.word_manager.set_level(level_name)
        self.dropdown.selected_index = self.word_manager.level_names.index(level_name)
        self.reset_game()
        self.show_intro()

    def _finish(self, won: bool):
        """End-of-game bookkeeping shared by a win and a loss."""
        self.victory, self.game_over = won, not won
        total = self.words_typed + self.total_missed
        self.final_accuracy = self.words_typed / total * 100 if total else 0
        self.is_new_high_score = self.score_manager.update_score(
            self.word_manager.current_level, self.difficulties[self.difficulty_index],
            self.final_accuracy, self.perfect_words)
        self.suggested_level = suggested_level(won, self.final_accuracy, self.word_manager.next_graded_level())
        self.result_text = result_lines(self.player_name, won, self.final_accuracy, self.perfect_words, self.suggested_level)
        play("victory" if won else "game_over_good" if self.final_accuracy >= 50 else "game_over_bad")

    def _draw_end_screen(self):
        """Victory / game-over card: the stats, then the coaching message and what to press next."""
        poor = not self.victory and self.final_accuracy < 50
        fill, edge, dim = ((50, 40, 0), GOLD, (20, 0, 30)) if self.victory else (
            (DARK_RED, RED, (30, 0, 0)) if poor else (DARK_BLUE, BLUE, (0, 0, 30)))
        draw_dim_overlay(self.screen, dim)
        banner = pygame.Rect(WIDTH // 2 - 330, 80, 660, 500 if self.is_new_high_score else 460)
        pygame.draw.rect(self.screen, fill, banner)
        pygame.draw.rect(self.screen, edge, banner, 4)

        def centered(text, size, color, y):
            surface = get_font(size).render(text, True, color)
            self.screen.blit(surface, surface.get_rect(center=(WIDTH // 2, banner.top + y)))

        centered("VICTORY!" if self.victory else "GAME OVER", FONT_BIG, GOLD if self.victory else WHITE, 45)
        centered(f"SCORE: {self.score} points", FONT_NORMAL, GREEN, 105)
        centered(f"MISSED: {self.total_missed} words", FONT_NORMAL, RED, 150)
        centered(f"ACCURACY: {self.final_accuracy:.1f}%", FONT_NORMAL, YELLOW, 195)
        if self.is_new_high_score:
            centered("NEW HIGH SCORE!", FONT_SMALL, PURPLE, 240)
        y = banner.top + (285 if self.is_new_high_score else 245)
        for line in self.result_text:
            y = draw_wrapped(self.screen, line, get_font(FONT_BODY), WHITE, banner.left + 30, y, banner.width - 60) + 8
        hint = get_font(FONT_BODY).render("Or click RESET to restart this level.", True, (170, 170, 170))
        self.screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT - 40)))

    def _draw_intro(self):
        """Coaching card: which rows and fingers this level uses, with a keyboard picture."""
        draw_dim_overlay(self.screen, (10, 10, 30))
        card = pygame.Rect(40, 70, WIDTH - 80, HEIGHT - 100)
        pygame.draw.rect(self.screen, (20, 20, 45), card)
        pygame.draw.rect(self.screen, GOLD, card, 4)
        x, width = card.left + 25, card.width - 50
        y = draw_wrapped(self.screen, self.intro.title, get_font(FONT_TITLE), GOLD, x, card.top + 18, width) + 10
        for line in self.intro.lines:
            y = draw_wrapped(self.screen, line, get_font(FONT_BODY), WHITE, x, y, width) + 6
        draw_keyboard(self.screen, card.centerx - KEYBOARD_WIDTH // 2, y + 12, self.intro.keys)
        footer = get_font(FONT_BODY).render("Press Space to start   |   F1 shows this guide again", True, (170, 170, 170))
        self.screen.blit(footer, footer.get_rect(center=(card.centerx, card.bottom - 28)))

    def draw(self):
        self.screen.fill(BLACK)
        for x in range(0, WIDTH, 50):
            pygame.draw.line(self.screen, (20, 20, 20), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(self.screen, (20, 20, 20), (0, y), (WIDTH, y), 1)
            
        self.sprite_manager.draw(self.screen)
        
        mouse_pos = pygame.mouse.get_pos()
        self.reset_button.update(mouse_pos)
        self.reset_button.draw(self.screen)
        self.diff_button.update(mouse_pos)
        self.diff_button.draw(self.screen)
        self.fx_button.update(mouse_pos)
        self.fx_button.draw(self.screen)
        self.dropdown.update(mouse_pos)
        
        if self.playing:
            for word in self.words:
                word.draw(self.screen)
            for f_text in self.floating_texts:
                f_text.draw(self.screen)
        
        score_text = get_font(FONT_BIG).render(f"{self.score}", True, GREEN)
        self.screen.blit(score_text, (WIDTH - 150, 80))
        score_label = get_font(FONT_SMALL).render("SCORE", True, WHITE)
        self.screen.blit(score_label, (WIDTH - 150, 140))
        
        progress_x, progress_y = WIDTH - 300, 180
        progress_width, progress_height = 250, 25
        pygame.draw.rect(self.screen, (50, 50, 50), (progress_x, progress_y, progress_width, progress_height))
        if self.score > 0:
            fill_width = int((min(self.score, TOTAL_WORDS) / TOTAL_WORDS) * progress_width)
            pygame.draw.rect(self.screen, GREEN, (progress_x, progress_y, fill_width, progress_height))
        pygame.draw.rect(self.screen, WHITE, (progress_x, progress_y, progress_width, progress_height), 2)
        progress_text = get_font(FONT_SMALL).render(f"{self.score}/{TOTAL_WORDS} to win", True, WHITE)
        self.screen.blit(progress_text, progress_text.get_rect(center=(progress_x + progress_width//2, progress_y + progress_height//2)))
        
        stats_x, stats_y = 20, 20
        current_speed = self.current_speed + (self.words_typed * SPEED_INCREASE_PER_WORD)
        self.screen.blit(get_font(FONT_SMALL).render(f"⚡ SPEED: {current_speed:.1f}", True, ORANGE), (stats_x, stats_y))
        self.screen.blit(get_font(FONT_SMALL).render(f"🌟 PERFECT: {self.perfect_words}", True, PURPLE), (stats_x, stats_y + 40))
        self.screen.blit(get_font(FONT_SMALL).render(f"📝 ON SCREEN: {len(self.words)}", True, BLUE), (stats_x, stats_y + 80))
        self.screen.blit(get_font(FONT_SMALL).render(f"❌ MISSED: {self.total_missed}", True, RED), (stats_x, stats_y + 120))
        
        total_attempts = self.words_typed + self.total_missed
        if total_attempts > 0:
            accuracy = (self.words_typed / total_attempts) * 100
            self.screen.blit(get_font(FONT_SMALL).render(f"🎯 ACCURACY: {accuracy:.1f}%", True, YELLOW), (stats_x, stats_y + 160))
        
        self.screen.blit(get_font(FONT_SMALL).render("⌨️ Space/Enter: submit  |  Ctrl+K: clear", True, (150, 150, 150)), (stats_x, stats_y + 200))
        self.screen.blit(get_font(FONT_SMALL).render("F1: finger guide", True, (150, 150, 150)), (stats_x, stats_y + 232))
        
        if self.playing:
            self.screen.blit(get_font(FONT_SMALL).render("TYPE:", True, GREEN), (50, HEIGHT - 80))
            input_surface = get_font(FONT_NORMAL).render(f"{self.current_input}", True, GREEN)
            self.screen.blit(input_surface, (150, HEIGHT - 88))
            if not self.dropdown.is_open and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = 150 + input_surface.get_width()
                pygame.draw.line(self.screen, GREEN, (cursor_x, HEIGHT - 85), (cursor_x, HEIGHT - 45), 4)
        
        if self.victory or self.game_over:
            self._draw_end_screen()

        self.dropdown.draw(self.screen)
        if self.intro_open:
            self._draw_intro()
        
        pygame.display.flip()

def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="falling-words", description="A touch-typing game graded by keyboard row.")
    parser.add_argument("--profile", help="player profile name, from profiles/<name>.json")
    parser.add_argument("--profiles-dir", type=Path, default=DEFAULT_PROFILES_DIR,
                        help="folder holding the profile files (default: ./profiles, so start the game in the project folder)")
    return parser.parse_args(argv)


def main():
    args = parse_args()
    try:
        profile = load_profile(args.profile, args.profiles_dir) if args.profile else None
    except (FileNotFoundError, ValueError) as e:
        sys.exit(f"Profile error: {e}")

    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption(f"Falling Words - {profile.name}" if profile else "Falling Words")
    clock = pygame.time.Clock()
    if not sounds.ENABLED:
        logger.warning("winsound is Windows-only; sound is disabled.")

    game = Game(screen, profile)
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            if game.intro_open and event.type == pygame.MOUSEBUTTONDOWN:
                game.dismiss_intro()
                continue

            dropdown_event = game.dropdown.handle_event(event)
            
            if dropdown_event == "OPENED" or dropdown_event == "CLOSED":
                continue 
            elif dropdown_event:
                game.select_level(dropdown_event)
                continue
                
            if not game.dropdown.is_open:
                if game.reset_button.handle_event(event):
                    game.reset_game()
                elif game.diff_button.handle_event(event):
                    game.difficulty_index = (game.difficulty_index + 1) % len(game.difficulties)
                    game.diff_button.text = game.difficulties[game.difficulty_index]
                    game.reset_game()
                elif game.fx_button.handle_event(event):
                    game.sprite_manager.toggle()
                    game.fx_button.text = "🌌 FX ON" if game.sprite_manager.enabled else "🌌 FX OFF"
            
            if event.type == pygame.KEYDOWN or event.type == pygame.KEYUP:
                if event.type == pygame.KEYDOWN:
                    game.handle_input(event)
                elif event.type == pygame.KEYUP:
                    game.handle_keyup(event)
                    
        game.update()
        game.draw()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()
