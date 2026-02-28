import pygame
import random
import sys
import platform
import winsound 
from loguru import logger

from .word_manager import WordManager
from .sprite_manager import SpriteManager
from .score_manager import ScoreManager

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

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 900, 650
FPS = 60

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

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Modular Falling Words")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 48)
small_font = pygame.font.Font(None, 32)
big_font = pygame.font.Font(None, 72)
button_font = pygame.font.Font(None, 36)

def play_correct():
    if platform.system() == "Windows": winsound.Beep(880, 150)

def play_incorrect():
    if platform.system() == "Windows": winsound.Beep(220, 200)

def play_victory():
    if platform.system() == "Windows": winsound.Beep(784, 3000)

def play_game_over_good():
    if platform.system() == "Windows": winsound.Beep(523, 3000)

def play_game_over_bad():
    if platform.system() == "Windows": winsound.Beep(196, 1000)

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
            text_surf = small_font.render(self.text, True, self.color)
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
        text_surface = button_font.render(self.text, True, WHITE)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
    
    def update(self, mouse_pos):
        self.current_color = self.hover_color if self.rect.collidepoint(mouse_pos) else self.color
    
    def handle_event(self, event):
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)

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
        word_surface = font.render(self.text, True, self.color)
        surface.blit(word_surface, (self.x, self.y))
    
    def is_off_screen(self):
        return self.y > HEIGHT - 100

class Game:
    def __init__(self):
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
        self.level_button = Button(
            x=WIDTH - 640, y=20, width=250, height=40,
            text=f"LVL: {self.word_manager.current_level}", color=(180, 100, 0), hover_color=ORANGE
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
        
        if event.key == pygame.K_BACKSPACE:
            self.handle_backspace()
            self.backspace_pressed = True
            self.backspace_last_time = pygame.time.get_ticks()
            self.made_mistake = True
        
        # Support for both Spacebar and Enter/Return to submit a word
        elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
            matched = False
            for word in self.words[:]:
                if word.text.lower() == self.current_input.lower():
                    self.words.remove(word)
                    self.words_typed += 1
                    matched = True
                    play_correct()
                    
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
                        play_victory()
                    break
            
            if not matched:
                self.current_input = ""
                self.made_mistake = False
                play_incorrect()
        
        elif event.unicode.isprintable():
            self.current_input += event.unicode
        elif event.key == pygame.K_k and pygame.key.get_mods() & pygame.KMOD_CTRL:
            self.current_input = ""  
            play_incorrect()  
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
                play_incorrect()
                
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
                play_game_over_good()
            else:
                play_game_over_bad()
    
    def draw(self):
        screen.fill(BLACK)
        for x in range(0, WIDTH, 50):
            pygame.draw.line(screen, (20, 20, 20), (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, 50):
            pygame.draw.line(screen, (20, 20, 20), (0, y), (WIDTH, y), 1)
            
        self.sprite_manager.draw(screen)
        
        mouse_pos = pygame.mouse.get_pos()
        self.reset_button.update(mouse_pos)
        self.reset_button.draw(screen)
        self.diff_button.update(mouse_pos)
        self.diff_button.draw(screen)
        self.fx_button.update(mouse_pos)
        self.fx_button.draw(screen)
        self.level_button.update(mouse_pos)
        self.level_button.draw(screen)
        
        if not self.victory and not self.game_over:
            for word in self.words:
                word.draw(screen)
            for f_text in self.floating_texts:
                f_text.draw(screen)
        
        score_text = big_font.render(f"{self.score}", True, GREEN)
        screen.blit(score_text, (WIDTH - 150, 80))
        score_label = small_font.render("SCORE", True, WHITE)
        screen.blit(score_label, (WIDTH - 150, 140))
        
        progress_x, progress_y = WIDTH - 300, 180
        progress_width, progress_height = 250, 25
        pygame.draw.rect(screen, (50, 50, 50), (progress_x, progress_y, progress_width, progress_height))
        if self.score > 0:
            fill_width = int((min(self.score, TOTAL_WORDS) / TOTAL_WORDS) * progress_width)
            pygame.draw.rect(screen, GREEN, (progress_x, progress_y, fill_width, progress_height))
        pygame.draw.rect(screen, WHITE, (progress_x, progress_y, progress_width, progress_height), 2)
        progress_text = small_font.render(f"{self.score}/{TOTAL_WORDS} to win", True, WHITE)
        screen.blit(progress_text, progress_text.get_rect(center=(progress_x + progress_width//2, progress_y + progress_height//2)))
        
        stats_x, stats_y = 20, 20
        current_speed = self.current_speed + (self.words_typed * SPEED_INCREASE_PER_WORD)
        screen.blit(small_font.render(f"⚡ SPEED: {current_speed:.1f}", True, ORANGE), (stats_x, stats_y))
        screen.blit(small_font.render(f"🌟 PERFECT: {self.perfect_words}", True, PURPLE), (stats_x, stats_y + 40))
        screen.blit(small_font.render(f"📝 ON SCREEN: {len(self.words)}", True, BLUE), (stats_x, stats_y + 80))
        screen.blit(small_font.render(f"❌ MISSED: {self.total_missed}", True, RED), (stats_x, stats_y + 120))
        
        total_attempts = self.words_typed + self.total_missed
        if total_attempts > 0:
            accuracy = (self.words_typed / total_attempts) * 100
            screen.blit(small_font.render(f"🎯 ACCURACY: {accuracy:.1f}%", True, YELLOW), (stats_x, stats_y + 160))
        
        screen.blit(small_font.render(f"⌨️ Space/Enter: submit  |  Ctrl+K: clear", True, (150, 150, 150)), (stats_x, stats_y + 200))
        
        if not self.victory and not self.game_over:
            screen.blit(small_font.render("TYPE:", True, GREEN), (50, HEIGHT - 80))
            input_surface = font.render(f"{self.current_input}", True, GREEN)
            screen.blit(input_surface, (150, HEIGHT - 88))
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_x = 150 + input_surface.get_width()
                pygame.draw.line(screen, GREEN, (cursor_x, HEIGHT - 85), (cursor_x, HEIGHT - 45), 4)
        
        if self.victory or self.game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT))
            overlay.set_alpha(200)
            overlay.fill((20, 0, 30) if self.victory else ((30, 0, 0) if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else (0, 0, 30)))
            screen.blit(overlay, (0, 0))
            
            banner_x, banner_y = WIDTH//2 - 300, HEIGHT//2 - 150
            banner_height = 360 if self.is_new_high_score else 320
            
            pygame.draw.rect(screen, GOLD if self.victory else (DARK_RED if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else DARK_BLUE), (banner_x, banner_y, 600, banner_height))
            pygame.draw.rect(screen, GOLD if self.victory else (RED if self.score/(self.score+self.total_missed if self.score+self.total_missed > 0 else 1) < 0.5 else BLUE), (banner_x, banner_y, 600, banner_height), 4)
            
            title_text = big_font.render("🏆 VICTORY! 🏆" if self.victory else "GAME OVER", True, GOLD if self.victory else WHITE)
            screen.blit(title_text, title_text.get_rect(center=(WIDTH//2, banner_y + 50)))
            
            score_text = font.render(f"✓ SCORE: {self.score} points", True, GREEN)
            screen.blit(score_text, score_text.get_rect(center=(WIDTH//2, banner_y + 110)))
            
            missed_text = font.render(f"✗ MISSED: {self.total_missed} words", True, RED)
            screen.blit(missed_text, missed_text.get_rect(center=(WIDTH//2, banner_y + 160)))
            
            total_attempts = self.words_typed + self.total_missed
            accuracy = (self.words_typed / total_attempts) * 100 if total_attempts > 0 else 100
            
            accuracy_text = font.render(f"🎯 ACCURACY: {accuracy:.1f}%", True, YELLOW)
            screen.blit(accuracy_text, accuracy_text.get_rect(center=(WIDTH//2, banner_y + 210)))
            
            if self.is_new_high_score:
                hs_text = small_font.render("🎉 NEW HIGH SCORE! 🎉", True, PURPLE)
                screen.blit(hs_text, hs_text.get_rect(center=(WIDTH//2, banner_y + 260)))
            
            restart_text = small_font.render("Click RESET button to play again", True, WHITE)
            screen.blit(restart_text, restart_text.get_rect(center=(WIDTH//2, HEIGHT - 50)))
        
        pygame.display.flip()

def main():
    if platform.system() != "Windows":
        logger.warning("winsound only works on Windows. Sound will be disabled.")
    
    game = Game()
    running = True
    
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                game.handle_input(event)
            elif event.type == pygame.KEYUP:
                game.handle_keyup(event)
            elif game.reset_button.handle_event(event):
                game.reset_game()
            elif game.diff_button.handle_event(event):
                game.difficulty_index = (game.difficulty_index + 1) % len(game.difficulties)
                game.diff_button.text = game.difficulties[game.difficulty_index]
                game.reset_game()
            elif game.fx_button.handle_event(event):
                game.sprite_manager.toggle()
                game.fx_button.text = "🌌 FX ON" if game.sprite_manager.enabled else "🌌 FX OFF"
            elif game.level_button.handle_event(event):
                new_level = game.word_manager.cycle_level()
                game.level_button.text = f"LVL: {new_level}"
                game.reset_game()
        
        game.update()
        game.draw()
        clock.tick(FPS)
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
