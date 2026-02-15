from pygame import *
import random
import os
import json

init()
mixer.pre_init(44100, -16, 1, 512)
mixer.init()

WIDTH, HEIGHT = 450, 700
screen = display.set_mode((WIDTH, HEIGHT))
display.set_caption("Wall Climber Pro")
clock = time.Clock()

ACCENT_COLOR = (0, 200, 255)
WHITE = (255, 255, 255)
SPIKE_COLOR = (200, 50, 50)

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
    default_stats = {"best": 0, "games_played": 0, "total_height": 0}
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


def load_image(name, color=(80, 80, 90), size=(30, 140)):
    possible_exts = [name, name + ".png", name + ".jpg"]
    for img_name in possible_exts:
        if os.path.exists(img_name):
            img = image.load(img_name).convert_alpha()
            return img

    surf = Surface(size)
    surf.fill(color)
    draw.rect(surf, (color[0] + 20, color[1] + 20, color[2] + 20), (0, 0, 5, size[1]))
    return surf


raw_bg = load_image("Fon", (20, 20, 30), (WIDTH, HEIGHT))
BG_IMG = transform.scale(raw_bg, (WIDTH, HEIGHT))

raw_player = load_image("player.png", (30, 144, 255), (24, 32))
PLAYER_IMG = transform.scale(raw_player, (24, 32))

BORTYK_IMG = load_image("bortyk.png", (80, 80, 90), (30, 140))


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
    def __init__(self, x, y, width=30, height=140, is_floor=False, moving=False):
        super().__init__()
        self.is_floor = is_floor
        self.moving = moving
        self.dir = random.choice([-1, 1])
        self.speed = random.uniform(0.5, 1.5)
        self.start_y = y
        self.range = random.randint(50, 100)
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

    def update(self, keys, platforms):
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


def game_loop():
    player = Player()
    platforms = sprite.Group()
    spikes = sprite.Group()
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
        wall = WallPlatform(side, last_y, width=w, moving=moving)
        platforms.add(wall)

        if wall.spike_data:
            spikes.add(Spike(wall, wall.spike_data["direction"], wall.spike_data["offset"]))

        last_y -= 180

    stars = [(random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 2)) for _ in range(50)]

    running = True
    while running:
        screen.blit(BG_IMG, (0, 0))
        for s in stars:
            draw.circle(screen, (100, 100, 120), (s[0], s[1]), s[2])

        keys = key.get_pressed()

        for p in platforms:
            p.update()

        for s in spikes:
            s.update()

        if sprite.spritecollide(player, spikes, False):
            screen.fill(SPIKE_COLOR)
            display.flip()
            time.delay(100)
            stats = save_stats(score // 10, stats)
            return "GAME_OVER", score

        for ev in event.get():
            if ev.type == QUIT:
                save_stats(score // 10, stats)
                return "QUIT", score
            if ev.type == KEYDOWN:
                if ev.key == K_SPACE or ev.key == K_w or ev.key == K_UP:
                    player.jump()

        player.update(keys, platforms)

        if player.rect.y < HEIGHT // 2:
            diff = HEIGHT // 2 - player.rect.y
            player.rect.y = HEIGHT // 2
            score += int(diff)

            for p in platforms:
                p.rect.y += diff
                p.start_y += diff
                if p.rect.y > HEIGHT:
                    p.kill()

                    min_y = HEIGHT
                    for plat in platforms:
                        if plat.rect.y < min_y:
                            min_y = plat.rect.y

                    new_spawn_y = min_y - random.randint(180, 220)

                    new_w = random.randint(30, 90)
                    new_side = random.choice([0, WIDTH - new_w])
                    is_moving = random.random() < 0.35
                    new_wall = WallPlatform(new_side, new_spawn_y, width=new_w, moving=is_moving)
                    platforms.add(new_wall)

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
        screen.blit(player.image, player.rect)

        draw.rect(screen, (0, 0, 0), (15, 15, 160, 85), border_radius=10)
        draw.rect(screen, ACCENT_COLOR, (15, 15, 160, 85), 2, border_radius=10)

        screen.blit(font_ui.render(f"Height: {score // 10}m", True, WHITE), (25, 22))
        screen.blit(font_ui.render(f"Best: {stats['best']}m", True, (200, 200, 200)), (25, 47))
        screen.blit(font_ui.render(f"Total: {stats['total_height']}m", True, (150, 150, 150)), (25, 72))

        if player.rect.top > HEIGHT:
            stats = save_stats(score // 10, stats)
            return "GAME_OVER", score

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

            games = info_font.render(f"Games Played: {stats['games_played']}", True, (150, 150, 150))
            screen.blit(games, (WIDTH // 2 - games.get_width() // 2, HEIGHT // 2 - 10))

            hint = sub_font.render("Press SPACE to Start", True, WHITE)

            if (time.get_ticks() // 500) % 2 == 0:
                screen.blit(hint, (WIDTH // 2 - hint.get_width() // 2, HEIGHT // 2 + 50))

        elif state == "GAME_OVER":
            title = title_font.render("GAME OVER", True, SPIKE_COLOR)
            screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 3))

            score_text = sub_font.render(f"You climbed: {last_score // 10}m", True, WHITE)
            screen.blit(score_text, (WIDTH // 2 - score_text.get_width() // 2, HEIGHT // 2))

            best_text = sub_font.render(f"Best: {stats['best']}m", True, ACCENT_COLOR)
            screen.blit(best_text, (WIDTH // 2 - best_text.get_width() // 2, HEIGHT // 2 + 30))

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