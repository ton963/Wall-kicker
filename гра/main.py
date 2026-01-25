from pygame import *
import random
import os

# --- Ініціалізація ---
init()
WIDTH, HEIGHT = 450, 700
screen = display.set_mode((WIDTH, HEIGHT))
display.set_caption("Wall Climber Pro")
clock = time.Clock()

# --- Налаштування повільної фізики ---
GRAVITY = 0.25
JUMP_Y = -8
JUMP_X = 13
CLIMB_SPEED = 2.5
AIR_FRICTION = 0.98


# --- Створення спрайтів ---
def create_assets():
    # Гравець
    p_surf = Surface((35, 45), SRCALPHA)
    draw.circle(p_surf, (255, 220, 180), (17, 12), 10)
    draw.rect(p_surf, (30, 144, 255), (8, 22, 19, 20), border_radius=5)
    image.save(p_surf, "player.png")

    # Стінка
    plat_surf = Surface((30, 140), SRCALPHA)
    draw.rect(plat_surf, (80, 80, 90), (0, 0, 30, 140), border_radius=3)
    draw.rect(plat_surf, (0, 255, 127), (0, 0, 30, 10), border_radius=3)
    image.save(plat_surf, "platform.png")


create_assets()
PLAYER_IMG = image.load("player.png").convert_alpha()
PLATFORM_IMG = image.load("platform.png").convert_alpha()


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
            if keys[K_w]:
                self.vel_y = -CLIMB_SPEED
            elif keys[K_s]:
                self.vel_y = CLIMB_SPEED
        elif on_ground:
            self.jumps_left = 2
            self.vel_y = 0
        else:
            self.vel_y += GRAVITY

        if keys[K_a]: self.vel_x -= 0.4
        if keys[K_d]: self.vel_x += 0.4

        self.vel_x *= AIR_FRICTION
        self.rect.x += self.vel_x
        self.rect.y += self.vel_y

        # Анімація розтягування (stretch)
        if abs(self.vel_y) > 1:
            scale_y = int(45 + abs(self.vel_y) * 2)
            self.image = transform.scale(self.original_image, (35, min(scale_y, 60)))
        else:
            self.image = self.original_image

        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > WIDTH: self.rect.right = WIDTH

    def jump(self):
        if self.on_wall == "LEFT":
            self.vel_y = JUMP_Y
            self.vel_x = JUMP_X
            self.jumps_left = 1
        elif self.on_wall == "RIGHT":
            self.vel_y = JUMP_Y
            self.vel_x = -JUMP_X
            self.jumps_left = 1
        elif self.jumps_left > 0:
            self.vel_y = JUMP_Y
            self.jumps_left -= 1


class WallPlatform(sprite.Sprite):
    def __init__(self, x, y, w=30, h=140):
        super().__init__()
        self.image = transform.scale(PLATFORM_IMG, (w, h))
        self.rect = self.image.get_rect(topleft=(x, y))


def game_loop():
    player = Player()
    platforms = sprite.Group()
    score = 0

    # Початкова підлога
    floor = WallPlatform(0, HEIGHT - 40, WIDTH, 40)
    floor.image.fill((50, 50, 60))
    platforms.add(floor)

    for i in range(1, 7):
        side = random.choice([0, WIDTH - 30])
        platforms.add(WallPlatform(side, HEIGHT - i * 180 - 100))

    running = True
    while running:
        screen.fill((25, 25, 35))
        keys = key.get_pressed()
        player.on_wall = None
        on_ground = False

        hits = sprite.spritecollide(player, platforms, False)
        for hit in hits:
            # Захист від заходження в низ стінки
            if player.vel_y < 0 and player.rect.top < hit.rect.bottom and player.rect.bottom > hit.rect.bottom:
                player.rect.top = hit.rect.bottom
                player.vel_y = 0

            # Приземлення зверху
            elif player.vel_y >= 0 and player.rect.bottom <= hit.rect.top + 15:
                player.rect.bottom = hit.rect.top
                on_ground = True

            # Лазіння по боках
            elif player.rect.right >= hit.rect.left and player.rect.centerx < hit.rect.left:
                player.rect.right = hit.rect.left
                player.on_wall = "RIGHT"
            elif player.rect.left <= hit.rect.right and player.rect.centerx > hit.rect.right:
                player.rect.left = hit.rect.right
                player.on_wall = "LEFT"

        for ev in event.get():
            if ev.type == QUIT: return "QUIT"
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE: player.jump()

        player.update(keys, on_ground)

        # Камера
        if player.rect.y < HEIGHT // 2:
            diff = HEIGHT // 2 - player.rect.y
            player.rect.y = HEIGHT // 2
            score += 1
            for p in platforms:
                p.rect.y += diff
                if p.rect.y > HEIGHT:
                    p.kill()
                    platforms.add(WallPlatform(random.choice([0, WIDTH - 30]), -180))

        platforms.draw(screen)
        screen.blit(player.image, player.rect)

        score_font = font.SysFont("Arial", 30, bold=True)
        screen.blit(score_font.render(f"Score: {score}", True, (255, 255, 255)), (20, 20))

        if player.rect.top > HEIGHT: return "MENU"

        display.flip()
        clock.tick(60)


# --- Цикл Меню ---
state = "MENU"
while state != "QUIT":
    if state == "MENU":
        screen.fill((15, 15, 20))
        menu_font = font.SysFont("Arial", 40, bold=True)
        screen.blit(menu_font.render("SKY CLIMBER", True, (0, 200, 255)), (110, HEIGHT // 3))
        screen.blit(menu_font.render("SPACE TO START", True, (255, 255, 255)), (100, HEIGHT // 2))
        display.flip()
        for ev in event.get():
            if ev.type == QUIT: state = "QUIT"
            if ev.type == KEYDOWN and ev.key == K_SPACE: state = "PLAY"
    if state == "PLAY":
        state = game_loop()

quit()