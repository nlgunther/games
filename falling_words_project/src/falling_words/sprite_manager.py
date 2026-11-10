import pygame
import random
import os
import glob
from loguru import logger

class FloatingSprite:
    def __init__(self, screen_width, screen_height, image_surface=None):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.size = random.randint(40, 90)
        self.x = random.randint(self.size, screen_width - self.size)
        
        self.moving_up = random.choice([True, False])
        if self.moving_up:
            self.y = screen_height + self.size
            self.speed_y = random.uniform(1.0, 3.0) * -1
        else:
            self.y = -self.size
            self.speed_y = random.uniform(1.0, 3.0)
            
        self.speed_x = random.uniform(-2.0, 2.0)
        self.angle = random.randint(0, 360)
        self.rotation_speed = random.uniform(-2.0, 2.0)
        
        if image_surface:
            self.original_surface = pygame.transform.smoothscale(image_surface, (self.size, self.size))
        else:
            self.original_surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
            alpha = random.randint(80, 160)
            if random.choice([True, False]):
                pygame.draw.circle(self.original_surface, (*color, alpha), (self.size//2, self.size//2), self.size//2)
            else:
                points = [(self.size//2, 0), (self.size, self.size//2), (self.size//2, self.size), (0, self.size//2)]
                pygame.draw.polygon(self.original_surface, (*color, alpha), points)

    def update(self):
        self.y += self.speed_y
        self.x += self.speed_x
        self.angle = (self.angle + self.rotation_speed) % 360
        
        if self.x <= self.size // 2:
            self.x = self.size // 2
            self.speed_x *= -1
        elif self.x >= self.screen_width - (self.size // 2):
            self.x = self.screen_width - (self.size // 2)
            self.speed_x *= -1

    def draw(self, surface):
        rotated_surface = pygame.transform.rotate(self.original_surface, self.angle)
        rect = rotated_surface.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_surface, rect.topleft)

    def is_off_screen(self):
        if self.moving_up and self.y < -self.size * 2:
            return True
        if not self.moving_up and self.y > self.screen_height + self.size * 2:
            return True
        return False

class SpriteManager:
    def __init__(self, width, height, enabled=True, asset_folder="assets"):
        self.enabled = enabled
        self.width = width
        self.height = height
        self.sprites = []
        self.spawn_chance = 0.01  
        self.max_sprites = 5
        self.loaded_images = []
        self.load_assets(asset_folder)
        logger.info(f"SpriteManager initialized. Enabled: {self.enabled}")

    def load_assets(self, folder_name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        asset_dir = os.path.join(base_dir, folder_name)
        if not os.path.exists(asset_dir):
            try:
                os.makedirs(asset_dir)
                logger.info(f"Created empty asset directory at: {asset_dir}")
            except Exception as e:
                logger.error(f"Could not create asset directory: {e}")
                return
        png_files = glob.glob(os.path.join(asset_dir, "*.png"))
        for file_path in png_files:
            try:
                img = pygame.image.load(file_path).convert_alpha()
                self.loaded_images.append(img)
                logger.info(f"Loaded sprite asset: {os.path.basename(file_path)}")
            except Exception as e:
                logger.error(f"Failed to load image {file_path}: {e}")
        if not self.loaded_images:
            logger.info("No .png files found. Using fallback shapes.")

    def toggle(self):
        self.enabled = not self.enabled

    def update(self):
        if not self.enabled:
            return
        if len(self.sprites) < self.max_sprites and random.random() < self.spawn_chance:
            img_to_use = random.choice(self.loaded_images) if self.loaded_images else None
            self.sprites.append(FloatingSprite(self.width, self.height, image_surface=img_to_use))
        for sprite in self.sprites[:]:
            sprite.update()
            if sprite.is_off_screen():
                self.sprites.remove(sprite)

    def draw(self, surface):
        if not self.enabled:
            return
        for sprite in self.sprites:
            sprite.draw(surface)
