import tkinter as tk
from tkinter import messagebox
import math
from PIL import Image, ImageTk  # Requires Pillow library for image handling

class ImpossibleDinosaurGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Impossible Dinosaur Game")
        
        self.canvas = tk.Canvas(root, width=600, height=400, bg="white")
        self.canvas.pack()
        
        # Load dinosaur image
        try:
            self.dino_image = Image.open("purple_dinosaur.png")
            self.dino_image = self.dino_image.resize((40, 40), Image.Resampling.LANCZOS)  # Match original circle size
            self.dino_photo = ImageTk.PhotoImage(self.dino_image)
        except Exception as e:
            print(f"Error loading image: {e}")
            print("Please ensure 'purple_dinosaur.png' is in the same directory as this script.")
            self.root.quit()
            return
        
        # Dinosaur properties
        self.dino_radius = 20  # Hitbox radius for clicking and movement
        self.dino_x = 300
        self.dino_y = 200
        self.dinosaur = self.canvas.create_image(
            self.dino_x, self.dino_y, image=self.dino_photo, anchor="center"
        )
        
        # Movement settings
        self.movement_enabled = True
        self.avoid_distance = 100  # Distance at which dinosaur starts moving away
        self.move_speed = 5  # Pixels to move per update
        self.canvas_width = 600
        self.canvas_height = 400
        
        # Right-click counter
        self.right_click_count = 0
        
        # Bind events
        self.canvas.bind("<Motion>", self.on_mouse_move)
        self.canvas.bind("<Button-1>", self.on_left_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        
    def on_mouse_move(self, event):
        if not self.movement_enabled:
            return
        
        mouse_x, mouse_y = event.x, event.y
        dist = math.hypot(mouse_x - self.dino_x, mouse_y - self.dino_y)
        
        if dist < self.avoid_distance:
            # Calculate direction away from mouse
            dx = self.dino_x - mouse_x
            dy = self.dino_y - mouse_y
            norm = math.hypot(dx, dy)
            if norm != 0:
                dx /= norm
                dy /= norm
            
            # Move dinosaur
            self.dino_x += dx * self.move_speed
            self.dino_y += dy * self.move_speed
            
            # Check boundaries and jump to opposite side
            if self.dino_x < self.dino_radius:
                self.dino_x = self.canvas_width - self.dino_radius
            elif self.dino_x > self.canvas_width - self.dino_radius:
                self.dino_x = self.dino_radius
                
            if self.dino_y < self.dino_radius:
                self.dino_y = self.canvas_height - self.dino_radius
            elif self.dino_y > self.canvas_height - self.dino_radius:
                self.dino_y = self.dino_radius
            
            # Update position
            self.canvas.coords(self.dinosaur, self.dino_x, self.dino_y)
    
    def on_left_click(self, event):
        mouse_x, mouse_y = event.x, event.y
        dist = math.hypot(mouse_x - self.dino_x, mouse_y - self.dino_y)
        
        if dist <= self.dino_radius:
            messagebox.showinfo("Win!", "You clicked the dinosaur! You win!")
            self.root.quit()
    
    def on_right_click(self, event):
        self.right_click_count += 1
        if self.right_click_count >= 2:
            self.movement_enabled = not self.movement_enabled
            self.right_click_count = 0
            status = "disabled" if not self.movement_enabled else "enabled"
            print(f"Dinosaur movement {status}")  # Optional: for debugging

if __name__ == "__main__":
    root = tk.Tk()
    game = ImpossibleDinosaurGame(root)
    root.mainloop()