from pygame import *
import random
import os
import json
import math as Math

init()
mixer.pre_init(44100, -16, 1, 512)
mixer.init()

WIDTH, HEIGHT = 450, 700
screen = display.set_mode((WIDTH, HEIGHT))
display.set_caption("Wall Climber Pro: Ultimate Fix")
clock = time.Clock()

ACCENT_COLOR = (0, 200, 255)
WHITE = (255, 255, 255)
SPIKE_COLOR = (200, 50, 50)
GOLD_COLOR = (255, 215, 0)

GRAVITY = 0.25
JUMP_Y = -9
JUMP_X = 10
AIR_FRICTION = 0.96
GROUND_FRICTION = 0.8
CLIMB_SPEED = 3

jump_sfx = None
if os.path.exists("jump.wav"):
    jump_sfx = mixer.Sound("jump.wav")
    jump_sfx.set_volume(0.23)


def load_stats():
    default_stats = {"best": 0, "games_played": 0, "total_height": 0, "coins": 0}
    if os.path.exists("highscore.json"):
        with open("highscore.json", "r") as f:
            try:
                data = json.load(f)
                for key in default_stats:
                    if key not in data:
                        data[key] = default_stats[key]
                return data
            except:
                return default_stats
    return default_stats


def save_stats(new_score, current_stats):
    current_stats["games_played"] += 1
    current_stats["total_height"] += new_score
    if new_score > current_stats["best"]:
        current_stats["best"] = new_score
    with open("highscore.json", "w") as f:
        json.dump(current_stats, f)
    return current_stats


# --- IMAGE LOADING ---
def load_image(name, color=(80, 80, 90), size=(30, 140)):
    possible_exts = [name, name + ".png", name + ".jpg"]
    for img_name in possible_exts:
        if os.path.exists(img_name):
            img = image.load(img_name).convert_alpha()
            return img

    surf = Surface(size)
    surf.fill(color)
    if "moneta" in name:
        draw.circle(surf, (255, 215, 0), (size[0] // 2, size[1] // 2), size[0] // 2)
    elif "raket" in name:
        draw.rect(surf, (100, 100, 100), (0, 0, size[0], size[1]))
        draw.rect(surf, (255, 100, 0), (5, 5, size[0] - 10, size[1] - 10))
    else:
        draw.rect(surf, (color[0] + 20, color[1] + 20, color[2] + 20), (0, 0, 5, size[1]))
    return surf


raw_bg = load_image("Fon", (20, 20, 30), (WIDTH, HEIGHT))
BG_IMG = transform.scale(raw_bg, (WIDTH, HEIGHT))

raw_player = load_image("player.png", (30, 144, 255), (24, 32))
PLAYER_IMG = transform.scale(raw_player, (24, 32))

raw_player_jet = load_image("raket.png", (255, 100, 0), (34, 42))
PLAYER_JET_IMG = transform.scale(raw_player_jet, (34, 42))

BORTYK_IMG = load_image("bortyk.png", (80, 80, 90), (30, 140))

raw_coin = load_image("moneta.png", (255, 215, 0), (20, 20))
COIN_IMG = transform.scale(raw_coin, (25, 25))

raw_shop_jet = load_image("onlyraket.png", (100, 100, 100), (40, 40))
SHOP_JET_IMG = transform.scale(raw_shop_jet, (50, 50))


# --- CLASSES & HELPERS ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vel_x = random.uniform(-2, 2)
        self.vel_y = random.uniform(-2, 2)
        self.size = random.randint(2, 5)
        self.color = color
        self.life = 20

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.size -= 0.1
        self.life -= 1

    def draw(self, surface):
        if self.life > 0 and self.size > 0:
            draw.rect(surface, self.color, (self.x, self.y, self.size, self.size))


particles = []


def create_particles(x, y, color, count=5):
    for _ in range(count):
        particles.append(Particle(x, y, color))


# ФУНКЦІЯ ДЛЯ ЖОРСТКОЇ ПЕРЕВІРКИ НАКЛАДАННЯ
def check_platform_overlap(platforms, new_x, new_y, new_w, new_h, new_range):
    for p in platforms:
        if not p.is_floor:
            # Чи перетинаються вони по осі X? (знаходяться на одній стіні)
            p_left, p_right = p.rect.left, p.rect.right
            n_left, n_right = new_x, new_x + new_w

            if not (n_right < p_left or n_left > p_right):
                # Чи перетинаються їхні зони руху по осі Y?
                p_top = p.start_y - p.range
                p_bot = p.start_y + p.range + p.rect.height

                n_top = new_y - new_range
                n_bot = new_y + new_range + new_h

                # Додаємо 15 пікселів відступу для безпеки
                if not (n_bot < p_top - 15 or n_top > p_bot + 15):
                    return True  # Виявлено накладання!
    return False


class Coin(sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = COIN_IMG
        self.rect = self.image.get_rect(center=(x, y))
        self.start_y = y

    def update(self, scroll_y=0):
        self.rect.y = self.start_y + int(Math.sin(time.get_ticks() * 0.005) * 5)


class Spike(sprite.Sprite):
    def __init__(self, wall, direction, offset_y):
        super().__init__()
        self.image = Surface((10, 30), SRCALPHA)
        if direction == "LEFT":
            draw.polygon(self.image, SPIKE_COLOR, [(10, 0), (10, 30), (0, 15)])
            x_pos = wall.rect.left - 10
        else:
            draw.polygon(self.image, SPIKE_COLOR, [(0, 0), (0, 30), (10, 15)])
            x_pos = wall.rect.right

        self.rect = self.image.get_rect(topleft=(x_pos, wall.rect.y + offset_y))

        self.wall = wall
        self.offset_x = self.rect.x - wall.rect.x
        self.offset_y = offset_y

    def update(self):
        if self.wall:
            self.rect.x = self.wall.rect.x + self.offset_x
            self.rect.y = self.wall.rect.y + self.offset_y


class WallPlatform(sprite.Sprite):
    def __init__(self, x, y, width=30, height=140, is_floor=False, moving=False, move_range=50):
        super().__init__()
        self.is_floor = is_floor
        self.moving = moving
        self.dir = random.choice([-1, 1])
        self.speed = random.uniform(0.5, 1.5)
        self.start_y = y
        self.range = move_range if moving else 0
        self.spike_data = None

        if is_floor:
            self.image = Surface((WIDTH, 40))
            self.image.fill((50, 50, 60))
        else:
            self.image = transform.scale(BORTYK_IMG, (width, height))
            if not moving and random.random() < 0.3:
                self.spike_data = {
                    "offset": random.randint(20, height - 40),
                    "direction": "RIGHT" if x < WIDTH // 2 else "LEFT"
                }

        self.rect = self.image.get_rect(topleft=(x, y))

    def update(self):
        if self.moving and not self.is_floor:
            self.rect.y += self.dir * self.speed
            if abs(self.rect.y - self.start_y) > self.range:
                self.dir *= -1


class Player(sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.original_image = PLAYER_IMG
        self.image = self.original_image
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 60))
        self.vel_x = 0
        self.vel_y = 0
        self.on_wall = None
        self.facing_right = True
        self.jumps_left = 2
        self.attached_platform = None
        self.on_ground = False

        self.is_flying = False
        self.fly_target_height = 0

    def activate_jetpack(self, current_score):
        self.is_flying = True
        self.fly_target_height = current_score + 2500
        self.vel_y = -15
        self.on_wall = None
        create_particles(self.rect.centerx, self.rect.bottom, (255, 100, 0), 20)

    def update(self, keys, platforms, current_score):
        if self.is_flying:
            self.vel_y = -15
            self.vel_x = 0

            if keys[K_a] or keys[K_LEFT]:
                self.vel_x = -9
                self.facing_right = False
            elif keys[K_d] or keys[K_RIGHT]:
                self.vel_x = 9
                self.facing_right = True

            self.rect.x += self.vel_x
            self.rect.y += self.vel_y

            create_particles(self.rect.centerx, self.rect.bottom, (255, 200, 50), 2)

            if self.facing_right:
                self.image = PLAYER_JET_IMG
            else:
                self.image = transform.flip(PLAYER_JET_IMG, True, False)

            if current_score >= self.fly_target_height:
                self.is_flying = False
                self.vel_y = -5

            if self.rect.left < 0: self.rect.left = 0
            if self.rect.right > WIDTH: self.rect.right = WIDTH

            return

        if self.on_wall:
            self.jumps_left = 2
            self.vel_y = 0
            if keys[K_w] or keys[K_UP]:
                self.vel_y = -CLIMB_SPEED
            elif keys[K_s] or keys[K_DOWN]:
                self.vel_y = CLIMB_SPEED

            if self.attached_platform and self.attached_platform.moving:
                self.rect.y += self.attached_platform.dir * self.attached_platform.speed
        else:
            self.vel_y += GRAVITY
            self.attached_platform = None

        if keys[K_a] or keys[K_LEFT]:
            self.vel_x -= 0.6
            self.facing_right = False
        if keys[K_d] or keys[K_RIGHT]:
            self.vel_x += 0.6
            self.facing_right = True

        if self.on_ground:
            self.vel_x *= GROUND_FRICTION
        else:
            self.vel_x *= AIR_FRICTION

        self.rect.x += self.vel_x
        self.on_wall = None
        hits_x = sprite.spritecollide(self, platforms, False)
        for hit in hits_x:
            if not hit.is_floor:
                if self.vel_x > 0:
                    self.rect.right = hit.rect.left
                    self.on_wall = "RIGHT"
                    self.facing_right = False
                    self.attached_platform = hit
                    self.vel_x = 0
                elif self.vel_x < 0:
                    self.rect.left = hit.rect.right
                    self.on_wall = "LEFT"
                    self.facing_right = True
                    self.attached_platform = hit
                    self.vel_x = 0

        self.rect.y += self.vel_y
        self.on_ground = False
        hits_y = sprite.spritecollide(self, platforms, False)
        for hit in hits_y:
            if self.vel_y > 0:
                if self.rect.bottom <= hit.rect.top + 15:
                    self.rect.bottom = hit.rect.top
                    self.vel_y = 0
                    self.on_ground = True
                    self.jumps_left = 2
            elif self.vel_y < 0:
                if self.rect.top >= hit.rect.bottom - 15:
                    self.rect.top = hit.rect.bottom
                    self.vel_y = 0

        current_img = self.original_image
        if not self.facing_right:
            current_img = transform.flip(self.original_image, True, False)

        if abs(self.vel_y) > 3 and not self.on_wall:
            scale_y = int(32 + abs(self.vel_y))
            scale_x = int(24 - abs(self.vel_y) * 0.5)
            self.image = transform.scale(current_img, (max(10, scale_x), min(scale_y, 50)))
        else:
            self.image = current_img

        if self.rect.left < 0:
            self.rect.left = 0
            self.vel_x = 0
        if self.rect.right > WIDTH:
            self.rect.right = WIDTH
            self.vel_x = 0

    def jump(self):
        if self.is_flying: return False

        jumped = False
        if self.on_wall == "LEFT":
            self.vel_y = JUMP_Y
            self.vel_x = JUMP_X
            jumped = True
            create_particles(self.rect.left, self.rect.centery, WHITE)
        elif self.on_wall == "RIGHT":
            self.vel_y = JUMP_Y
            self.vel_x = -JUMP_X
            jumped = True
            create_particles(self.rect.right, self.rect.centery, WHITE)
        elif self.on_ground or self.jumps_left > 0:
            self.vel_y = JUMP_Y
            if self.on_ground:
                self.jumps_left = 1
            else:
                self.jumps_left -= 1
            jumped = True
            create_particles(self.rect.centerx, self.rect.bottom, WHITE)

        if jumped:
            if jump_sfx:
                jump_sfx.play()

        self.on_wall = None
        self.attached_platform = None
        self.on_ground = False
        return jumped


def draw_shop_ui(surface, stats):
    overlay = Surface((WIDTH, HEIGHT), SRCALPHA)
    overlay.fill((0, 0, 0, 200))
    surface.blit(overlay, (0, 0))

    font_title = font.SysFont("Arial", 40, bold=True)
    font_item = font.SysFont("Arial", 24)
    font_small = font.SysFont("Arial", 18)

    title = font_title.render("SHOP (PAUSE)", True, ACCENT_COLOR)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

    coins_text = font_item.render(f"Coins: {stats['coins']}", True, GOLD_COLOR)
    surface.blit(coins_text, (WIDTH // 2 - coins_text.get_width() // 2, 160))

    draw.rect(surface, (50, 50, 60), (50, 220, WIDTH - 100, 100), border_radius=10)
    surface.blit(SHOP_JET_IMG, (60, 245))

    name_text = font_item.render("Jetpack (+250m)", True, WHITE)
    cost_text = font_item.render("Cost: 20 Coins", True, GOLD_COLOR)
    key_text = font_small.render("[Press 1 to Buy]", True, (200, 200, 200))

    surface.blit(name_text, (120, 235))
    surface.blit(cost_text, (120, 265))
    surface.blit(key_text, (120, 295))

    exit_text = font_small.render("Press ESC to Resume", True, WHITE)
    surface.blit(exit_text, (WIDTH // 2 - exit_text.get_width() // 2, HEIGHT - 50))


def draw_revive_ui(surface, stats):
    overlay = Surface((WIDTH, HEIGHT), SRCALPHA)
    overlay.fill((50, 0, 0, 220))
    surface.blit(overlay, (0, 0))

    font_title = font.SysFont("Arial", 40, bold=True)
    font_text = font.SysFont("Arial", 25)

    title = font_title.render("YOU DIED!", True, WHITE)
    surface.blit(title, (WIDTH // 2 - title.get_width() // 2, 200))

    if stats['coins'] >= 25:
        q_text = font_text.render("Revive for 25 Coins?", True, GOLD_COLOR)
        y_text = font_text.render("[Y] YES     [N] NO", True, WHITE)
        surface.blit(q_text, (WIDTH // 2 - q_text.get_width() // 2, 300))
        surface.blit(y_text, (WIDTH // 2 - y_text.get_width() // 2, 350))
    else:
        q_text = font_text.render("Not enough coins to revive...", True, (150, 150, 150))
        n_text = font_text.render("Press SPACE to Continue", True, WHITE)
        surface.blit(q_text, (WIDTH // 2 - q_text.get_width() // 2, 300))
        surface.blit(n_text, (WIDTH // 2 - n_text.get_width() // 2, 350))


def game_loop():
    player = Player()
    platforms = sprite.Group()
    spikes = sprite.Group()
    coins_group = sprite.Group()
    particles.clear()

    score = 0
    font_ui = font.SysFont("Arial", 25, bold=True)
    stats = load_stats()

    platforms.add(WallPlatform(0, HEIGHT - 40, is_floor=True))

    last_y = HEIGHT - 180
    for i in range(6):
        w = random.randint(30, 90)
        side = random.choice([0, WIDTH - w])
        moving = random.choice([True, False]) if i > 1 else False
        move_range = random.randint(40, 80) if moving else 0

        # Перевіряємо чи безпечно спавнити при генерації
        if check_platform_overlap(platforms, side, last_y, w, 140, move_range):
            side = 0 if side > 0 else WIDTH - w  # Міняємо стіну
            if check_platform_overlap(platforms, side, last_y, w, 140, move_range):
                last_y -= 150  # Якщо обидві стіни зайняті, просто відступаємо вище

        wall = WallPlatform(side, last_y, width=w, moving=moving, move_range=move_range)
        platforms.add(wall)

        if wall.spike_data:
            spikes.add(Spike(wall, wall.spike_data["direction"], wall.spike_data["offset"]))

        last_y -= random.randint(180, 220)

    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 2)) for _ in range(50)]

    running = True
    paused = False
    waiting_for_revive = False

    while running:
        if paused:
            draw_shop_ui(screen, stats)
            display.flip()
            for ev in event.get():
                if ev.type == QUIT:
                    save_stats(score // 10, stats)
                    return "QUIT", score
                if ev.type == KEYDOWN:
                    if ev.key == K_ESCAPE:
                        paused = False
                    if ev.key == K_1:
                        if stats['coins'] >= 20 and not player.is_flying:
                            stats['coins'] -= 20
                            player.activate_jetpack(score)
                            paused = False
            continue

        if waiting_for_revive:
            draw_revive_ui(screen, stats)
            display.flip()
            for ev in event.get():
                if ev.type == QUIT:
                    save_stats(score // 10, stats)
                    return "QUIT", score
                if ev.type == KEYDOWN:
                    if ev.key == K_y and stats['coins'] >= 25:
                        stats['coins'] -= 25
                        waiting_for_revive = False
                        player.rect.y = HEIGHT // 2
                        player.vel_y = -5
                        player.is_flying = False
                        for s in spikes:
                            if abs(s.rect.y - player.rect.y) < 200:
                                s.kill()
                    elif ev.key == K_n or (stats['coins'] < 25 and ev.key == K_SPACE):
                        save_stats(score // 10, stats)
                        return "GAME_OVER", score
            continue

        screen.blit(BG_IMG, (0, 0))
        for s in stars:
            draw.circle(screen, (100, 100, 120), (s[0], s[1]), s[2])

        keys = key.get_pressed()

        for p in platforms:
            p.update()

        for s in spikes:
            s.update()

        for c in coins_group:
            c.update()

        if sprite.spritecollide(player, coins_group, True):
            stats['coins'] += 1

        if not player.is_flying and sprite.spritecollide(player, spikes, False):
            screen.fill(SPIKE_COLOR)
            display.flip()
            time.delay(100)
            waiting_for_revive = True
            continue

        for ev in event.get():
            if ev.type == QUIT:
                save_stats(score // 10, stats)
                return "QUIT", score
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE or ev.key == K_w or ev.key == K_UP:
                    player.jump()
                if ev.key == K_ESCAPE:
                    paused = True

        player.update(keys, platforms, score)

        target_cam_y = HEIGHT // 2

        if player.rect.y < target_cam_y:
            diff = target_cam_y - player.rect.y
            player.rect.y = target_cam_y
            score += int(diff)

            for c in coins_group:
                c.rect.y += diff
                c.start_y += diff
                if c.rect.y > HEIGHT:
                    c.kill()

            for p in platforms:
                p.rect.y += diff
                p.start_y += diff  # Важливо: оновлюємо стартову позицію для перевірки накладання!
                if p.rect.y > HEIGHT:
                    p.kill()

                    # --- НАДІЙНА ГЕНЕРАЦІЯ НОВИХ ПЛАТФОРМ ---
                    min_y = HEIGHT
                    for plat in platforms:
                        if plat.rect.y < min_y:
                            min_y = plat.rect.y

                    new_spawn_y = min_y - random.randint(180, 220)
                    new_w = random.randint(30, 90)
                    new_side = random.choice([0, WIDTH - new_w])
                    is_moving = random.random() < 0.35
                    move_range = random.randint(40, 80) if is_moving else 0

                    # Перевіряємо віртуальну зону руху на накладання
                    if check_platform_overlap(platforms, new_side, new_spawn_y, new_w, 140, move_range):
                        new_side = 0 if new_side > 0 else WIDTH - new_w  # Міняємо стіну

                        # Якщо навіть протилежна стіна зайнята (дуже рідко), робимо статичною і відсуваємо
                        if check_platform_overlap(platforms, new_side, new_spawn_y, new_w, 140, move_range):
                            new_spawn_y -= 150
                            is_moving = False
                            move_range = 0

                    new_wall = WallPlatform(new_side, new_spawn_y, width=new_w, moving=is_moving, move_range=move_range)
                    platforms.add(new_wall)

                    if random.random() < 0.3:
                        cx = new_side + new_w + 30 if new_side == 0 else new_side - 30
                        if random.random() < 0.5:
                            cx = WIDTH // 2
                        cy = new_spawn_y - random.randint(20, 100)
                        coins_group.add(Coin(cx, cy))

                    if new_wall.spike_data:
                        spikes.add(Spike(new_wall, new_wall.spike_data["direction"], new_wall.spike_data["offset"]))

            for s in spikes:
                if s.wall not in platforms:
                    s.kill()

            for i in range(len(stars)):
                stars[i] = (stars[i][0], (stars[i][1] + diff * 0.3) % HEIGHT, stars[i][2])

        for p in particles:
            p.update()
            p.draw(screen)
        particles[:] = [p for p in particles if p.life > 0]

        platforms.draw(screen)
        spikes.draw(screen)
        coins_group.draw(screen)
        screen.blit(player.image, player.rect)

        draw.rect(screen, (0, 0, 0), (15, 15, 180, 110), border_radius=10)
        draw.rect(screen, ACCENT_COLOR, (15, 15, 180, 110), 2, border_radius=10)

        screen.blit(font_ui.render(f"Height: {score // 10}m", True, WHITE), (25, 22))
        screen.blit(font_ui.render(f"Coins: {stats['coins']}", True, GOLD_COLOR), (25, 47))
        screen.blit(font_ui.render(f"Best: {stats['best']}m", True, (200, 200, 200)), (25, 72))
        screen.blit(font_ui.render(f"ESC - Shop", True, (100, 255, 100)), (25, 97))

        if player.rect.top > HEIGHT:
            waiting_for_revive = True

        display.flip()
        clock.tick(60)


def main_menu():
    if os.path.exists("Hero-Immortal.ogg"):
        mixer.music.load("Hero-Immortal.ogg")
        mixer.music.set_volume(0.5)
        mixer.music.play(-1)

    state = "MENU"
    last_score = 0
    stats = load_stats()

    title_font = font.SysFont("Arial", 45, bold=True)
    sub_font = font.SysFont("Arial", 25)
    info_font = font.SysFont("Arial", 20)

    while state != "QUIT":
        screen.blit(BG_IMG, (0, 0))

        if state == "MENU":
            stats = load_stats()
            title_shadow = title_font.render("WALL KICKER", True, (0, 0, 0))
            screen.blit(title_shadow, (WIDTH // 2 - title_shadow.get_width() // 2 + 3, HEIGHT // 3 + 3))

            title = title_font.render("WALL KICKER", True, ACCENT_COLOR)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))

            record = sub_font.render(f"Record: {stats['best']}m", True, (200, 200, 200))
            screen.blit(record, (WIDTH // 2 - record.get_width() // 2, HEIGHT // 2 - 40))

            coins_info = info_font.render(f"Total Coins: {stats['coins']}", True, GOLD_COLOR)
            screen.blit(coins_info, (WIDTH // 2 - coins_info.get_width() // 2, HEIGHT // 2 - 10))

            hint = sub_font.render("Press SPACE to Start", True, WHITE)

            if (time.get_ticks() // 500) % 2 == 0:
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 50))

        elif state == "GAME_OVER":
            title = title_font.render("GAME OVER", True, SPIKE_COLOR)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))

            score_text = sub_font.render(f"You climbed: {last_score // 10}m", True, WHITE)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))

            coins_text = info_font.render(f"Coins: {stats['coins']}", True, GOLD_COLOR)
            screen.blit(coins_text, (WIDTH // 2 - coins_text.get_width() // 2, HEIGHT // 2 + 30))

            hint = sub_font.render("Press SPACE to Retry", True, (150, 150, 150))
            screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 80))

        display.flip()

        for ev in event.get():
            if ev.type == QUIT:
                state = "QUIT"
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE:
                    if state == "MENU" or state == "GAME_OVER":
                        result, score = game_loop()
                        if result == "QUIT":
                            state = "QUIT"
                        else:
                            state = "GAME_OVER"
                            last_score = score
                            stats = load_stats()
    quit()


if __name__ == "__main__":
    main_menu()