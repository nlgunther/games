"""Falling Words: type each falling word and press Space or Enter before it reaches the bottom."""
import random
import sys

import pygame
from loguru import logger

from . import sounds
from .score_manager import ScoreManager
from .sounds import play
from .sprite_manager import SpriteManager
from .ui import (BLACK, BLUE, DARK_BLUE, DARK_GREEN, DARK_RED, FONT_BIG, FONT_NORMAL, FONT_SMALL,
                 GOLD, GREEN, ORANGE, PURPLE, RED, WHITE, YELLOW,
                 Button, Dropdown, FloatingText, get_font)
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

DIFFICULTY_SETTINGS = {
    "BEGINNER": 1.0,
    "STANDARD": 1.5,
    "EXPERT": 2.0
}

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
    def __init__(self, screen):
        self.screen = screen
        self.word_manager = WordManager()
        self.sprite_manager = SpriteManager(width=WIDTH, height=HEIGHT, enabled=True)
        self.score_manager = ScoreManager()
        
        self.reset_button = Button(
            x=WIDTH - 130, y=20, width=110, height=40,
            text="🔄 RESET", color=DARK_GREEN, hover_color=GREEN
        )
        self.difficulties = list(DIFFICULTY_SETTINGS.keys())
        self.difficulty_index = 0
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
        if self.game_over or self.victory:
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
                        self.floating_texts.append(FloatingText(150, HEIGHT - 110, "+2 Perfect!", PURPLE))
                    else:
                        self.score += 1
                    
                    self.current_input = ""
                    self.made_mistake = False
                    
                    if not self.victory and not self.game_over:
                        if pygame.time.get_ticks() > self.lag_end_time:
                            self.spawn_word()
                    
                    if self.score >= TOTAL_WORDS and not self.victory:
                        self.victory = True
                        total_att = self.words_typed + self.total_missed
                        accuracy = (self.words_typed / total_att * 100) if total_att > 0 else 0
                        diff_name = self.difficulties[self.difficulty_index]
                        self.is_new_high_score = self.score_manager.update_score(
                            self.word_manager.current_level, diff_name, accuracy, self.perfect_words
                        )
                        play("victory")
                    break
            
            if not matched:
                self.current_input = ""
                self.made_mistake = False
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
        if self.victory or self.game_over:
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
                play("incorrect")
                
                if len(self.words) < MAX_WORDS_ON_SCREEN * 2 and pygame.time.get_ticks() > self.lag_end_time:
                    self.spawn_word()
                    
        for f_text in self.floating_texts[:]:
            f_text.update()
            if f_text.alpha <= 0:
                self.floating_texts.remove(f_text)
        
        if len(self.words) > MAX_WORDS_ON_SCREEN * 2:
            self.game_over = True
            total_att = self.words_typed + self.total_missed
            accuracy = (self.words_typed / total_att * 100) if total_att > 0 else 0
            diff_name = self.difficulties[self.difficulty_index]
            self.is_new_high_score = self.score_manager.update_score(
                self.word_manager.current_level, diff_name, accuracy, self.perfect_words
            )
            if accuracy >= 50:
                play("game_over_good")
            else:
                play("game_over_bad")
    
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
        
        if not self.victory and not self.game_over:
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
        
        if not self.victory and not self.game_over:
            self.screen.blit(get_font(FONT_SMALL).render("TYPE:", True, GREEN), (50, HEIGHT - 80))
            input_surface = get_font(FONT_NORMAL).render(f"{self.current_input}", True, GREEN)
            self.screen.blit(input_surface, (150, HEIGHT - 88))
            if not self.dropdown.is_open and pygame.time.get_ticks() % 1000 < 500:
                cursor_x = 150 + input_surface.get_width()
                pygame.draw.line(self.screen, GREEN, (cursor_x, HEIGHT - 85), (cursor_x, HEIGHT - 45), 4)
        
        if self.victory or self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((20, 0, 30) if self.victory else ((30, 0, 0) if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else (0, 0, 30)))
            self.screen.blit(overlay, (0, 0))
            
            banner_x, banner_y = WIDTH//2 - 300, HEIGHT//2 - 150
            banner_height = 360 if self.is_new_high_score else 320
            
            pygame.draw.rect(self.screen, GOLD if self.victory else (DARK_RED if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else DARK_BLUE), (banner_x, banner_y, 600, banner_height))
            pygame.draw.rect(self.screen, GOLD if self.victory else (RED if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else BLUE), (banner_x, banner_y, 600, banner_height), 4)
            
            title_text = get_font(FONT_BIG).render("🏆 VICTORY! 🏆" if self.victory else "GAME OVER", True, GOLD if self.victory else WHITE)
            self.screen.blit(title_text, title_text.get_rect(center=(WIDTH//2, banner_y + 50)))
            
            score_text = get_font(FONT_NORMAL).render(f"✓ SCORE: {self.score} points", True, GREEN)
            self.screen.blit(score_text, score_text.get_rect(center=(WIDTH//2, banner_y + 110)))
            
            missed_text = get_font(FONT_NORMAL).render(f"✗ MISSED: {self.total_missed} words", True, RED)
            self.screen.blit(missed_text, missed_text.get_rect(center=(WIDTH//2, banner_y + 160)))
            
            total_attempts = self.words_typed + self.total_missed
            accuracy = (self.words_typed / total_attempts) * 100 if total_attempts > 0 else 100
            
            accuracy_text = get_font(FONT_NORMAL).render(f"🎯 ACCURACY: {accuracy:.1f}%", True, YELLOW)
            self.screen.blit(accuracy_text, accuracy_text.get_rect(center=(WIDTH//2, banner_y + 210)))
            
            if self.is_new_high_score:
                hs_text = get_font(FONT_SMALL).render("🎉 NEW HIGH SCORE! 🎉", True, PURPLE)
                self.screen.blit(hs_text, hs_text.get_rect(center=(WIDTH//2, banner_y + 260)))
            
            restart_text = get_font(FONT_SMALL).render("Click RESET button to play again", True, WHITE)
            self.screen.blit(restart_text, restart_text.get_rect(center=(WIDTH//2, HEIGHT - 50)))

        self.dropdown.draw(self.screen)
        
        pygame.display.flip()

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Falling Words")
    clock = pygame.time.Clock()
    if not sounds.ENABLED:
        logger.warning("winsound is Windows-only; sound is disabled.")

    game = Game(screen)
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            dropdown_event = game.dropdown.handle_event(event)
            
            if dropdown_event == "OPENED" or dropdown_event == "CLOSED":
                continue 
            elif dropdown_event:
                game.word_manager.set_level(dropdown_event)
                game.reset_game()
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
