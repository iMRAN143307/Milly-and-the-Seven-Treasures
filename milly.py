import pygame
import os
import math
import random

pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
running = True
dt = 0
accel = 0
milly_angle = 180

pos_x = 15.0
pos_y = 50.0

camera_x = 0.0
camera_y = 0.0
MARGIN = 200
milly_frame1 = pygame.image.load(os.path.join("milly.png")).convert_alpha()
milly_frame2 = pygame.image.load(os.path.join("milly2.png")).convert_alpha()
milly_frames = [milly_frame1, milly_frame2]

current_frame = 0
anim_timer = 0.0
ANIMATION_SPEED = 0.15
def load_and_scale_bg(filename):
    unscaled = pygame.image.load(os.path.join(filename)).convert_alpha()
    return pygame.transform.scale(unscaled, (720, 720))

bg_tiles = [
    load_and_scale_bg("bg.png"),
    load_and_scale_bg("bg2.png"),
    load_and_scale_bg("bg3.png"),
    load_and_scale_bg("bg4.png"),
    load_and_scale_bg("bg5.png")
]

tile_cache = {}

trail = [(30, 30), (30, 60)]

artifact_images = []
for i in range(1, 8):
    try:
        img = pygame.image.load(os.path.join(f"a{i}.png")).convert_alpha()

        bounding_rect = img.get_bounding_rect()

        cropped_img = img.subsurface(bounding_rect)

        img = pygame.transform.scale(cropped_img, (50, 50))

    except FileNotFoundError:
        img = pygame.Surface((50, 50))
        img.fill("pink")
    artifact_images.append(img)

artifacts_on_map = [
    {"pos": (1200, -1000), "collected": False, "img": artifact_images[0]},
    {"pos": (-1500, 1200), "collected": False, "img": artifact_images[1]},
    {"pos": (2400, 1800), "collected": False, "img": artifact_images[2]},
    {"pos": (-2200, -1800), "collected": False, "img": artifact_images[3]},
    {"pos": (3500, 400), "collected": False, "img": artifact_images[4]},
    {"pos": (400, 3200), "collected": False, "img": artifact_images[5]},
    {"pos": (4000, -2500), "collected": False, "img": artifact_images[6]},
]

collected_artifacts = []

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    accel = max(accel - 0.2, 0)

    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        accel = min(accel + 1, 14)
    if keys[pygame.K_a]:
        milly_angle += 3
    if keys[pygame.K_d]:
        milly_angle -= 3

    radians = math.radians(milly_angle)
    pos_x -= math.sin(radians) * accel
    pos_y -= math.cos(radians) * accel

    if accel > 0.5:
        anim_timer += dt
        if anim_timer >= ANIMATION_SPEED:
            current_frame = (current_frame + 1) % len(milly_frames)
            anim_timer = 0.0
    else:
        current_frame = 0
        anim_timer = 0.0

    # --- Camera Logic ---
    screen_x = pos_x - camera_x
    screen_y = pos_y - camera_y

    if screen_x < MARGIN:
        camera_x -= (MARGIN - screen_x)
    elif screen_x > 1280 - MARGIN:
        camera_x += (screen_x - (1280 - MARGIN))

    if screen_y < MARGIN:
        camera_y -= (MARGIN - screen_y)
    elif screen_y > 720 - MARGIN:
        camera_y += (screen_y - (720 - MARGIN))

    if accel > 0:
        if not trail or math.hypot(trail[-1][0] - pos_x, trail[-1][1] - pos_y) > 5:
            trail.append((pos_x, pos_y))

    for artifact in artifacts_on_map:
        if not artifact["collected"]:
            ax, ay = artifact["pos"]
            distance = math.hypot(pos_x - ax, pos_y - ay)
            if distance < 60:
                artifact["collected"] = True
                collected_artifacts.append(artifact["img"])

    tile_size = 720
    start_x = -(camera_x % tile_size)
    start_y = -(camera_y % tile_size)

    for x in range(int(start_x), 1280, tile_size):
        for y in range(int(start_y), 720, tile_size):
            grid_x = math.floor((camera_x + x) / tile_size)
            grid_y = math.floor((camera_y + y) / tile_size)

            if (grid_x, grid_y) not in tile_cache:
                tile_cache[(grid_x, grid_y)] = random.choice(bg_tiles)

            screen.blit(tile_cache[(grid_x, grid_y)], (x, y))

    for tx, ty in trail:
        screen_tx = round(tx - camera_x)
        screen_ty = round(ty - camera_y)
        if -40 < screen_tx < 1280 + 40 and -40 < screen_ty < 720 + 40:
            pygame.draw.circle(screen, "black", (screen_tx, screen_ty), 40)

    for artifact in artifacts_on_map:
        if not artifact["collected"]:
            ax, ay = artifact["pos"]
            screen_ax = round(ax - camera_x)
            screen_ay = round(ay - camera_y)

            if -100 < screen_ax < 1280 + 100 and -100 < screen_ay < 720 + 100:

                pygame.draw.circle(screen, "black", (screen_ax, screen_ay), 55)

                img_rect = artifact["img"].get_rect(center=(screen_ax, screen_ay))
                screen.blit(artifact["img"], img_rect)

    milly_current_image = milly_frames[current_frame]
    milly = pygame.transform.rotate(milly_current_image, milly_angle)
    milly_rect = milly.get_rect(center=(round(pos_x - camera_x), round(pos_y - camera_y)))
    screen.blit(milly, milly_rect)

    for i, collected_img in enumerate(collected_artifacts):
        screen.blit(collected_img, (20 + (i * 60), 20))

    pygame.display.flip()
    dt = clock.tick(60) / 1000

pygame.quit()
