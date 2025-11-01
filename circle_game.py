# --------------------------------------------------------------
#  IMPOSSIBLE DINOSAUR – SASSY, CHATTY, AND CORRECTLY NAMED
# --------------------------------------------------------------
#  • Image: purple_dinosaur.png
#  • Speaks on EVERY left-click
#  • No errors, no silent clicks
# --------------------------------------------------------------

import tkinter as tk
from tkinter import messagebox
import math
import random
import threading
from pathlib import Path

# ---------- TEXT-TO-SPEECH (per-click fresh engine) ----------
def speak(text: str):
    """Speak text using a new pyttsx3 engine in a background thread."""
    def _run():
        try:
            import pyttsx3
            engine = pyttsx3.init()
            # Try to pick a sassy/female voice
            for v in engine.getProperty('voices'):
                if any(k in v.name.lower() for k in ('female', 'zira', 'karen', 'anna', 'samantha')):
                    engine.setProperty('voice', v.id)
                    break
            engine.setProperty('rate', 170)
            engine.setProperty('volume', 0.9)
            engine.say(text)
            engine.runAndWait()
        except Exception as e:
            print(f"[TTS Error] {e}")

    threading.Thread(target=_run, daemon=True).start()


# ---------- SASSY TAUNTS ----------
SASSY_LINES = [
    "You missed! Why can't you do this? I'm just a little dinosaur and not very fast!",
    "Ouch! That was close… but not close enough. Try harder, human!",
    "Ha! You call that a click? My grandma clicks faster than that!",
    "Missed again? Maybe you should ask the mouse for help.",
    "Keep swinging, champ! One day you'll hit something… maybe.",
    "Is that the best you've got? Even a T-Rex with tiny arms could do better!",
    "Aww, did the big scary cursor scare you? I'm just a purple dino!",
    "You’re making me dizzy with all that missing. Take a break!",
    "Pro tip: the dinosaur is the purple thing. Just saying.",
    "I’m starting to feel bad for you… almost.",
]

# ---------- GAME CLASS ----------
class ImpossibleDinosaurGame:
    def __init__(self, root):
        self.root = root
        self.root.title("Impossible Dinosaur – Sassy Edition")

        self.canvas = tk.Canvas(root, width=600, height=400, bg="white")
        self.canvas.pack()

        # ----- LOAD IMAGE: purple_dinosaur.png -----
        img_path = Path("purple_dinosaur.png")
        try:
            from PIL import Image, ImageTk
            img = Image.open(img_path).resize((40, 40), Image.Resampling.LANCZOS)
            self.dino_photo = ImageTk.PhotoImage(img)
            self.is_image = True
        except Exception as e:
            print(f"Image 'purple_dinosaur.png' not found → using purple oval ({e})")
            self.dino_photo = None
            self.is_image = False

        self.radius = 20
        self.x = 300
        self.y = 200

        # Create canvas item
        if self.is_image:
            self.dino_item = self.canvas.create_image(
                self.x, self.y, image=self.dino_photo, anchor="center"
            )
        else:
            self.dino_item = self.canvas.create_oval(
                self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius,
                fill="purple"
            )

        # Game settings
        self.movement_enabled = True
        self.avoid_dist = 100
        self.speed = 5
        self.w = 600
        self.h = 400
        self.right_clicks = 0

        # Bindings
        self.canvas.bind("<Motion>", self._move)
        self.canvas.bind("<Button-1>", self._left_click)
        self.canvas.bind("<Button-3>", self._right_click)

    # ------------------------------------------------------------------
    def _update_position(self):
        """Update canvas item: 2 coords for image, 4 for oval."""
        if self.is_image:
            self.canvas.coords(self.dino_item, self.x, self.y)
        else:
            self.canvas.coords(
                self.dino_item,
                self.x - self.radius, self.y - self.radius,
                self.x + self.radius, self.y + self.radius
            )

    # ------------------------------------------------------------------
    def _move(self, event):
        if not self.movement_enabled:
            return

        mx, my = event.x, event.y
        dist = math.hypot(mx - self.x, my - self.y)

        if dist < self.avoid_dist:
            dx = self.x - mx
            dy = self.y - my
            norm = math.hypot(dx, dy)
            if norm:
                dx /= norm
                dy /= norm

            self.x += dx * self.speed
            self.y += dy * self.speed

            half_w, half_h = self.w // 2, self.h // 2

            # Random jump to opposite half on boundary
            if self.x < self.radius:
                self.x = random.randint(half_w, self.w - self.radius)
                self.y = random.randint(self.radius, self.h - self.radius)
            elif self.x > self.w - self.radius:
                self.x = random.randint(self.radius, half_w)
                self.y = random.randint(self.radius, self.h - self.radius)

            if self.y < self.radius:
                self.x = random.randint(self.radius, self.w - self.radius)
                self.y = random.randint(half_h, self.h - self.radius)
            elif self.y > self.h - self.radius:
                self.x = random.randint(self.radius, self.w - self.radius)
                self.y = random.randint(self.radius, half_h)

            self._update_position()

    # ------------------------------------------------------------------
    def _left_click(self, event):
        dist = math.hypot(event.x - self.x, event.y - self.y)

        if dist <= self.radius:
            msg = "You caught the dinosaur! You win!"
            messagebox.showinfo("Win!", msg)
            speak("Yay! You finally got me. Good job, human!")
            self.root.quit()
        else:
            msg = random.choice(SASSY_LINES)
            messagebox.showinfo("Missed!", msg)
            speak(msg)  # SPEAKS EVERY TIME

    # ------------------------------------------------------------------
    def _right_click(self, event):
        self.right_clicks += 1
        if self.right_clicks >= 2:
            self.movement_enabled = not self.movement_enabled
            self.right_clicks = 0
            status = "disabled" if not self.movement_enabled else "enabled"
            # print(f"Dinosaur movement {status}")
            # speak(f"Movement {status}!")
            s = f"This doesn't seem like a good game for you ... how about I just stay still?"
            print(s)
            speak(s)


# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Check for missing packages
    missing = []
    for mod in ("Pillow", "pyttsx3"):
        try:
            __import__(mod.lower().replace("-", "_"))
        except ImportError:
            missing.append(mod)
    if missing:
        print("Missing packages:", ", ".join(missing))
        print("Run: pip install " + " ".join(missing))

    root = tk.Tk()
    game = ImpossibleDinosaurGame(root)
    root.mainloop()