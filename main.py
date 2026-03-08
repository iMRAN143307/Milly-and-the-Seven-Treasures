import pygame
import os
import math
import random
import asyncio
from collections import deque

pygame.mixer.pre_init(44100, -16, 2, 4096)
pygame.init()
screen = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()

async def main():
    running = True
    game_over = False
    game_won = False
    dt = 0
    accel = 0
    milly_angle = 180

    # Player's real-world coordinates
    pos_x = 15.0
    pos_y = 50.0

    def random_spawn(x, y, min_dist, max_dist, occupied_spots):
        min_separation = 550
        for i in range(500):
            angle = random.uniform(0, 2*(math.pi))
            distance = random.uniform(min_dist, max_dist)
            spawnx = x + (math.cos(angle) * distance)
            spawny = y + (math.sin(angle) * distance)

            valid = 1
            for xpos, ypos in occupied_spots:
                if math.hypot(spawnx - xpos, spawny - ypos) < min_separation:
                    valid = 0
                    break
            if valid != 0:
                return (spawnx, spawny)
        return (spawnx, spawny)
    # --- Camera Settings ---
    camera_x = 0.0
    camera_y = 0.0
    MARGIN = 200

    # --- Asset Loading ---

    # --- Intro Centering Math ---
    intro_size = 720 # Smaller 400x400 square
    intro_x = 0
    intro_y = 0

    # Load Intro Sequence
    intro_frames = []
    for i in range(1, 18):
        try:
            img = pygame.image.load(os.path.join(f"intro{i}.png")).convert_alpha()
            img = pygame.transform.scale(img, (intro_size, intro_size))
            intro_frames.append(img)
        except FileNotFoundError:
            # Transparent fallback surface
            fallback = pygame.Surface((intro_size, intro_size), pygame.SRCALPHA)
            font = pygame.font.SysFont(None, 48)
            text = font.render(f"Frame {i} Missing", True, "white")
            text_rect = text.get_rect(center=(intro_size // 2, intro_size // 2))
            fallback.blit(text, text_rect)
            intro_frames.append(fallback)
    def rotated_images(image):
        rotations = dict()
        for a in range(360):
            rotations[a] = pygame.transform.rotate(image, a)
        return rotations
    # Load player animation frames
    milly_frame1 = pygame.image.load(os.path.join("milly.png")).convert_alpha()
    milly_frame2 = pygame.image.load(os.path.join("milly2.png")).convert_alpha()
    milly_rotations = [rotated_images(milly_frame1), rotated_images(milly_frame2)]

    current_frame = 0
    anim_timer = 0.0
    ANIMATION_SPEED = 0.15

    # Load background tiles
    def load_and_scale_bg(filename):
        unscaled = pygame.image.load(os.path.join(filename)).convert()
        return pygame.transform.scale(unscaled, (720, 720))

    bg_tiles = [
        load_and_scale_bg("bg.png"),
        load_and_scale_bg("bg2.png"),
        load_and_scale_bg("bg3.png"),
        load_and_scale_bg("bg4.png"),
        load_and_scale_bg("bg5.png")
    ]

    tile_cache = {}
    trail = deque([(10, 10), (10, 20), (10, 30), (10, 40), (10, 50)]) # Start with an empty trail to avoid visual bugs

    # --- Arrow Image Loading ---
    try:
        arrow_img = pygame.image.load(os.path.join("arrow.png")).convert_alpha()
        arrow_img = pygame.transform.scale(arrow_img, (64, 64))
    except FileNotFoundError:
        arrow_img = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_img, "yellow", [(64, 32), (0, 64), (0, 0)])

    arrow_rotations = rotated_images(arrow_img)
    # --- Fullscreen Game Over Image Loading ---
    try:
        gameover_img = pygame.image.load(os.path.join("gameover.png")).convert_alpha()
        gameover_img = pygame.transform.scale(gameover_img, (1280, 720))
    except FileNotFoundError:
        gameover_img = pygame.Surface((1280, 720))
        gameover_img.fill("red")

    # --- Fullscreen Win Image Loading ---
    try:
        win_img = pygame.image.load(os.path.join("win.png")).convert_alpha()
        win_img = pygame.transform.scale(win_img, (1280, 720))
    except FileNotFoundError:
        win_img = pygame.Surface((1280, 720))
        win_img.fill("green")

    # --- Enemy System ---
    enemy_images = []
    for name in ["e1.png", "e2.png", "e3.png"]:
        try:
            e_img = pygame.image.load(os.path.join(name)).convert_alpha()
            e_img = pygame.transform.scale(e_img, (90, 90))
        except FileNotFoundError:
            e_img = pygame.Surface((90, 90), pygame.SRCALPHA)
            pygame.draw.circle(e_img, "red", (45, 45), 45)
        enemy_images.append(e_img)

    enemy_rotations = [rotated_images(enemy) for enemy in enemy_images]

    occupied_spots = set()

    enemies = []
    enemy_spawns = []
    for i in range(3):
        enemy_spawns.append(random_spawn(pos_x, pos_y, 1250, 4000, occupied_spots))
        occupied_spots.add(enemy_spawns[i])
    for i, pos in enumerate(enemy_spawns):
        enemies.append({
            "x": pos[0],
            "y": pos[1],
            "vx": 0.0,
            "vy": 0.0,
            "angle": 0.0,
            "rotations": enemy_rotations[i % len(enemy_rotations)],
            "trail": deque(),
            "grazed": False
        })

    # --- Artifact System ---
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

    artifacts_on_map = []
    for i in range(7):
        artifacts_on_map.append({
            "pos": random_spawn(pos_x, pos_y, 1250, 4000, occupied_spots),
            "collected": False,
            "img": artifact_images[i]
        })
        occupied_spots.add(artifacts_on_map[i]["pos"])

    collected_artifacts = []
    active_effects = []

    # --- Intro Sequence Loop ---
    intro_running = True
    intro_frame_index = 0
    intro_timer = 0
    TIME_PER_FRAME = 180

    while intro_running and running:
        delta_time = clock.tick(60)
        intro_timer += delta_time

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                intro_running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    intro_running = False

        if intro_timer >= TIME_PER_FRAME:
            intro_timer -= TIME_PER_FRAME
            intro_frame_index += 1

            if intro_frame_index >= len(intro_frames):
                intro_running = False

        if intro_running and running:
            # Draw the current frame ON TOP, centered dynamically
            screen.blit(intro_frames[intro_frame_index], (intro_x, intro_y))
            pygame.display.flip()

        await asyncio.sleep(0) # REQUIRED FOR PYGBAG TO NOT FREEZE

    dt = clock.tick(60) / 1000

    # --- Start Background Music and Load SFX ---
    try:
        pygame.mixer.music.load(os.path.join("music.ogg"))
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(loops=-1, start=30.0)
    except pygame.error:
        print("Warning: 'music.ogg' not found or could not be loaded. Playing without music.")

    try:
        gameover_sound = pygame.mixer.Sound(os.path.join("gameover.ogg"))
        gameover_sound.set_volume(1.0)
    except (FileNotFoundError, pygame.error):
        gameover_sound = None
        print("Warning: 'gameover.ogg' not found.")

    try:
        win_sound = pygame.mixer.Sound(os.path.join("win.ogg"))
        win_sound.set_volume(1.0)
    except (FileNotFoundError, pygame.error):
        win_sound = None
        print("Warning: 'win.ogg' not found.")

    try:
        collect_sound = pygame.mixer.Sound(os.path.join("collect.ogg"))
        collect_sound.set_volume(1.0)
    except (FileNotFoundError, pygame.error):
        collect_sound = None
        print("Warning: 'collect.ogg' not found.")

    try:
        whoosh_sound = pygame.mixer.Sound(os.path.join("whoosh.ogg"))
        whoosh_sound.set_volume(0.8)
    except (FileNotFoundError, pygame.error):
        whoosh_sound = None
        print("Warning: 'whoosh.ogg' not found.")

    # --- Main Game Loop ---
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and (game_over or game_won):
                    if gameover_sound: gameover_sound.stop()
                    if win_sound: win_sound.stop()

                    game_over = False
                    game_won = False
                    pos_x = 15.0
                    pos_y = 50.0
                    accel = 0
                    milly_angle = 180
                    camera_x = 0.0
                    camera_y = 0.0
                    trail = deque([(10, 10), (10, 20), (10, 30), (10, 40), (10, 50)])
                    occupied_spots = set()
                    enemy_spawns = []
                    for i in range(3):
                        enemy_spawns.append(random_spawn(pos_x, pos_y, 1250, 4000, occupied_spots))
                        occupied_spots.add(enemy_spawns[i])
                    for i, pos in enumerate(enemy_spawns):
                        enemies[i]["x"] = pos[0]
                        enemies[i]["y"] = pos[1]
                        enemies[i]["vx"] = 0.0
                        enemies[i]["vy"] = 0.0
                        enemies[i]["angle"] = 0.0
                        enemies[i]["trail"] = deque()
                        enemies[i]["grazed"] = False

                    for artifact in artifacts_on_map:
                        artifact["pos"] = random_spawn(pos_x,pos_y,1250, 4000, occupied_spots)
                        artifact["collected"] = False
                        occupied_spots.add(artifact["pos"])
                    collected_artifacts = []
                    active_effects = []

                    try:
                        pygame.mixer.music.set_volume(0.4)
                        pygame.mixer.music.play(loops=-1, start=30.0)
                    except pygame.error:
                        pass

        if not game_over and not game_won:
            accel = max(accel - 0.2, 0)

            keys = pygame.key.get_pressed()
            if keys[pygame.K_w]:
                if accel < 14:
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
                    current_frame = (current_frame + 1) % 2
                    anim_timer = 0.0
            else:
                current_frame = 0
                anim_timer = 0.0

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

            # --- Enemy AI & Physics ---
            for enemy in enemies:
                dist = math.hypot(pos_x - enemy["x"], pos_y - enemy["y"])

                if dist < 65:
                    if not game_over:
                        pygame.mixer.music.stop()
                        if gameover_sound:
                            gameover_sound.play()
                    game_over = True

                elif dist < 200 and not enemy["grazed"]:
                    accel += 4.0
                    if whoosh_sound:
                        whoosh_sound.play()
                    enemy["grazed"] = True

                if dist > 300:
                    enemy["grazed"] = False

                screen_ex = enemy["x"] - camera_x
                screen_ey = enemy["y"] - camera_y
                is_on_screen = (-100 < screen_ex < 1280 + 100) and (-100 < screen_ey < 720 + 100)

                max_speed = 15.0

                if dist < 800 and is_on_screen:
                    target_angle = math.atan2(pos_y - enemy["y"], pos_x - enemy["x"])
                    angle_diff = (target_angle - enemy["angle"])
                    angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi

                    turn_speed = 0.08
                    accel_rate = 0.8

                    if angle_diff > turn_speed:
                        enemy["angle"] += turn_speed
                    elif angle_diff < -turn_speed:
                        enemy["angle"] -= turn_speed
                    else:
                        enemy["angle"] = target_angle

                    if abs(angle_diff) > (math.pi / 2):
                        enemy["vx"] *= 0.85
                        enemy["vy"] *= 0.85
                    else:
                        enemy["vx"] += math.cos(enemy["angle"]) * accel_rate
                        enemy["vy"] += math.sin(enemy["angle"]) * accel_rate
                        enemy["vx"] *= 0.96
                        enemy["vy"] *= 0.96
                else:
                    enemy["vx"] *= 0.96
                    enemy["vy"] *= 0.96

                speed = math.hypot(enemy["vx"], enemy["vy"])
                if speed > max_speed:
                    enemy["vx"] = (enemy["vx"] / speed) * max_speed
                    enemy["vy"] = (enemy["vy"] / speed) * max_speed

                enemy["x"] += enemy["vx"]
                enemy["y"] += enemy["vy"]

                if speed > 0.5:
                    if not enemy["trail"] or math.hypot(enemy["trail"][-1][0] - enemy["x"], enemy["trail"][-1][1] - enemy["y"]) > 5:
                        enemy["trail"].append((enemy["x"], enemy["y"]))
                        if len(enemy["trail"]) > 4000:
                            enemy_trail_on_screen = enemy["trail"][0]
                            enemy_trailx, enemy_traily = enemy_trail_on_screen
                            if (enemy_trailx - camera_x < -50) or (enemy_trailx - camera_x > 1330) or (enemy_traily - camera_y < -50) or (enemy_traily - camera_y > 770):
                                enemy_trail_off_screen = True
                            else:
                                enemy_trail_off_screen = False

                            if enemy_trail_off_screen:
                                enemy["trail"].popleft()
            # --- Trail Logic ---
            if accel > 0:
                if not trail or math.hypot(trail[-1][0] - pos_x, trail[-1][1] - pos_y) > 5:
                    trail.append((pos_x, pos_y))
                    if len(trail) > 4000:
                        trail_on_screen = trail[0]
                        trailx, traily = trail_on_screen
                        if (trailx - camera_x < -50) or (trailx - camera_x > 1330) or (traily - camera_y < -50) or (traily - camera_y > 770):
                            trail_off_screen = True
                        else:
                            trail_off_screen = False

                        if trail_off_screen:
                            trail.popleft()

            # --- Artifact Collision Logic ---
            for artifact in artifacts_on_map:
                if not artifact["collected"]:
                    ax, ay = artifact["pos"]
                    distance = math.hypot(pos_x - ax, pos_y - ay)
                    if distance < 60:
                        artifact["collected"] = True
                        collected_artifacts.append(artifact["img"])
                        if collect_sound:
                            collect_sound.play()
                        active_effects.append({
                            "x": ax, "y": ay, "radius": 10.0,
                            "max_radius": 200.0, "speed": 500.0
                        })

            for effect in active_effects[:]:
                effect["radius"] += effect["speed"] * dt
                if effect["radius"] >= effect["max_radius"]:
                    active_effects.remove(effect)

            if len(collected_artifacts) == len(artifacts_on_map):
                if not game_won:
                    pygame.mixer.music.stop()
                    if win_sound: win_sound.play()
                game_won = True

        # --- Rendering ---
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

        for enemy in enemies:
            for tx, ty in enemy["trail"]:
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

        for enemy in enemies:
            screen_ex = round(enemy["x"] - camera_x)
            screen_ey = round(enemy["y"] - camera_y)
            if -100 < screen_ex < 1280 + 100 and -100 < screen_ey < 720 + 100:
                angle_deg = int(-math.degrees(enemy["angle"]) - 90) % 360
                rotated_enemy = enemy["rotations"][angle_deg]
                img_rect = rotated_enemy.get_rect(center=(screen_ex, screen_ey))
                screen.blit(rotated_enemy, img_rect)

        for effect in active_effects:
            screen_ex = round(effect["x"] - camera_x)
            screen_ey = round(effect["y"] - camera_y)
            r = effect["radius"]
            if -r < screen_ex < 1280 + r and -r < screen_ey < 720 + r:
                points = [
                    (screen_ex, screen_ey - r),
                    (screen_ex + r, screen_ey),
                    (screen_ex, screen_ey + r),
                    (screen_ex - r, screen_ey)
                ]
                pygame.draw.polygon(screen, "white", points, 3)

        for enemy in enemies:
            dist = math.hypot(pos_x - enemy["x"], pos_y - enemy["y"])
            if dist < 1200:
                screen_ex = enemy["x"] - camera_x
                screen_ey = enemy["y"] - camera_y

                if not (0 <= screen_ex <= 1280 and 0 <= screen_ey <= 720):
                    ind_x = max(0, min(1280, screen_ex))
                    ind_y = max(0, min(720, screen_ey))
                    bar_width, bar_height = 0, 0
                    rect_x, rect_y = ind_x, ind_y

                    if screen_ex < 0:
                        bar_width, bar_height = 10, 60
                        rect_x = 0
                    elif screen_ex > 1280:
                        bar_width, bar_height = 10, 60
                        rect_x = 1280 - bar_width

                    if screen_ey < 0:
                        bar_width, bar_height = 60, 10
                        rect_y = 0
                    elif screen_ey > 720:
                        bar_width, bar_height = 60, 10
                        rect_y = 720 - bar_height

                    if (screen_ex < 0 or screen_ex > 1280) and (screen_ey < 0 or screen_ey > 720):
                        bar_width, bar_height = 30, 30

                    if screen_ex < 0 or screen_ex > 1280:
                        rect_y = ind_y - (bar_height / 2)
                    if screen_ey < 0 or screen_ey > 720:
                        rect_x = ind_x - (bar_width / 2)

                    rect_x = max(0, min(1280 - bar_width, rect_x))
                    rect_y = max(0, min(720 - bar_height, rect_y))
                    pygame.draw.rect(screen, "red", (rect_x, rect_y, bar_width, bar_height))

        milly_drawing_angle = int(milly_angle) % 360
        milly = milly_rotations[current_frame][milly_drawing_angle]
        milly_rect = milly.get_rect(center=(round(pos_x - camera_x), round(pos_y - camera_y)))
        screen.blit(milly, milly_rect)

        nearest_dist = float('inf')
        nearest_target = None
        for artifact in artifacts_on_map:
            if not artifact["collected"]:
                ax, ay = artifact["pos"]
                dist = math.hypot(pos_x - ax, pos_y - ay)
                if dist < nearest_dist:
                    nearest_dist = dist
                    nearest_target = (ax, ay)

        if nearest_target:
            tx, ty = nearest_target
            angle_rad = math.atan2(-(ty - pos_y), tx - pos_x)
            angle_deg = math.degrees(angle_rad)
            snapped_angle = int(round(angle_deg / 45.0) * 45.0) % 360
            rotated_arrow = arrow_rotations[snapped_angle]
            arrow_rect = rotated_arrow.get_rect(center=(1200, 80))
            screen.blit(rotated_arrow, arrow_rect)

        for i, collected_img in enumerate(collected_artifacts):
            screen.blit(collected_img, (20 + (i * 60), 20))

        if game_over:
            screen.blit(gameover_img, (0, 0))
        elif game_won:
            screen.blit(win_img, (0, 0))

        pygame.display.flip()
        dt = clock.tick(60) / 1000

        await asyncio.sleep(0) # REQUIRED FOR PYGBAG TO NOT FREEZE

    pygame.quit()

asyncio.run(main()) # TRIGGER THE ASYNC FUNCTION
