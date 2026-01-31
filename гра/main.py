from pygame import *
import random
import os

init()
WIDTH, HEIGHT = 450, 700
screen = display.set_mode((WIDTH, HEIGHT))
display.set_caption("Wall Climber Pro")
clock = time.Clock()

GRAVITY = 0.25
JUMP_Y = -8
JUMP_X = 11
CLIMB_SPEED = 2.5
AIR_FRICTION = 0.95


def load_image(name, color=(80, 80, 90), size=(30, 140)):
    if os.path.exists(name):
        return image.load(name).convert_alpha()
    else:
        surf = Surface(size)
        surf.fill(color)
        return surf


PLAYER_IMG = load_image("player.png", (30, 144, 255), (35, 45))
BORTYK_IMG = load_image("bortyk.png", (80, 80, 90), (30, 140))


class Player(sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = PLAYER_IMG
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 100))
        self.vel_x = 0
        self.vel_y = 0
        self.on_wall = None
        self.jumps_left = 2

    def update(self, keys, on_ground):
        if self.on_wall:
            self.jumps_left = 2
            self.vel_y = 0
            if keys[K_w] or keys[K_UP]:
                self.vel_y = -CLIMB_SPEED
            elif keys[K_s] or keys[K_DOWN]:
                self.vel_y = CLIMB_SPEED
        elif on_ground:
            self.jumps_left = 2
            self.vel_y = 0
        else:
            self.vel_y += GRAVITY

        if keys[K_a] or keys[K_LEFT]: self.vel_x -= 0.5
        if keys[K_d] or keys[K_RIGHT]: self.vel_x += 0.5

        self.vel_x *= AIR_FRICTION
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        if abs(self.vel_y) > 2:
            scale_y = int(45 + abs(self.vel_y) * 1.5)
            self.image = transform.scale(self.original_image, (35, min(scale_y, 65)))
        else:
            self.image = self.original_image

        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > WIDTH: self.rect.right = WIDTH

    def jump(self):
        if self.on_wall == "LEFT":
            self.vel_y = JUMP_Y
            self.vel_x = JUMP_X
        elif self.on_wall == "RIGHT":
            self.vel_y = JUMP_Y
            self.vel_x = -JUMP_X
        elif self.jumps_left > 0:
            self.vel_y = JUMP_Y
            self.jumps_left -= 1


class WallPlatform(sprite.Sprite):
    def __init__(self, x, y, is_floor=False):
        super().__init__()
        if is_floor:
            self.image = Surface((WIDTH, 40))
            self.image.fill((50, 50, 60))
        else:
            self.image = transform.scale(BORTYK_IMG, (30, 140))

        self.rect = self.image.get_rect(topleft=(x, y))


def game_loop():
    player = Player()
    platforms = sprite.Group()
    score = 0

    platforms.add(WallPlatform(0, HEIGHT - 40, is_floor=True))

    for i in range(1, 6):
        side = random.choice([0, WIDTH - 30])
        platforms.add(WallPlatform(side, HEIGHT - i * 200))

    running = True
    while running:
        screen.fill((20, 20, 30))
        keys = key.get_pressed()

        player.on_wall = None
        on_ground = False

        hits = sprite.spritecollide(player, platforms, False)
        for hit in hits:
            if hit.rect.width > 100:
                if player.vel_y >= 0:
                    player.rect.bottom = hit.rect.top
                    on_ground = True
            else:
                if player.rect.right >= hit.rect.left and player.rect.centerx < hit.rect.left:
                    player.rect.right = hit.rect.left
                    player.on_wall = "RIGHT"
                elif player.rect.left <= hit.rect.right and player.rect.centerx > hit.rect.right:
                    player.rect.left = hit.rect.right
                    player.on_wall = "LEFT"

                if player.vel_y >= 0 and player.rect.bottom <= hit.rect.top + 10:
                    player.rect.bottom = hit.rect.top
                    on_ground = True

        for ev in event.get():
            if ev.type == QUIT: return "QUIT"
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE or ev.key == K_w or ev.key == K_UP:
                    player.jump()

        player.update(keys, on_ground)

        if player.rect.y < HEIGHT // 2:
            diff = HEIGHT // 2 - player.rect.y
            player.rect.y = HEIGHT // 2
            score += 1
            for p in platforms:
                p.rect.y += diff
                if p.rect.y > HEIGHT:
                    p.kill()
                    new_side = random.choice([0, WIDTH - 30])
                    platforms.add(WallPlatform(new_side, -150))

        platforms.draw(screen)
        screen.blit(player.image, player.rect)

        score_font = font.SysFont("Arial", 30, bold=True)
        text = score_font.render(f"Score: {score // 10}", True, (255, 255, 255))
        screen.blit(text, (20, 20))

        if player.rect.top > HEIGHT:
            return "MENU"

        display.flip()
        clock.tick(60)


state = "MENU"
while state != "QUIT":
    if state == "MENU":
        screen.fill((10, 10, 15))
        menu_font = font.SysFont("Arial", 40, bold=True)
        screen.blit(menu_font.render("WALL KICKER", True, (0, 200, 255)), (110, HEIGHT // 3))
        screen.blit(menu_font.render("PRESS SPACE", True, (255, 255, 255)), (120, HEIGHT // 2))
        display.flip()
        for ev in event.get():
            if ev.type == QUIT: state = "QUIT"
            if ev.type == KEYDOWN and ev.key == K_SPACE: state = "PLAY"

    if state == "PLAY":
        state = game_loop()

quit()
