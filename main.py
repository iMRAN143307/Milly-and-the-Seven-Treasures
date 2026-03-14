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
    milly_pos_x = 15.0
    milly_pos_y = 50.0

    def random_spawn(x, y, min_dist, max_dist, occupied_spots):
        min_separation_sq = 550 ** 2
        for i in range(500):
            angle = random.uniform(0, 2*(math.pi))
            distance = random.uniform(min_dist, max_dist)
            spawnx = x + (math.cos(angle) * distance)
            spawny = y + (math.sin(angle) * distance)

            valid = 1
            for xpos, ypos in occupied_spots:
                if (spawnx - xpos)**2 + (spawny - ypos)**2 < min_separation_sq:
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
    intro_frames = []
    for i in range(34):
        try:
            img = pygame.image.load(os.path.join(f"p41_{i}.png")).convert_alpha()
            img = pygame.transform.scale(img, (1280, 720))
            intro_frames.append(img)
        except FileNotFoundError:
            fallback = pygame.Surface((1280, 720), pygame.SRCALPHA)
            font = pygame.font.SysFont(None, 48)
            text = font.render(f"Frame {i} Missing", True, "white")
            text_rect = text.get_rect(center=(1280 // 2, 720 // 2))
            fallback.blit(text, text_rect)
            intro_frames.append(fallback)

    def rotated_images(image):
        rotations = dict()
        for a in range(360):
            rotations[a] = pygame.transform.rotate(image, a)
        return rotations

    milly_frame1 = pygame.image.load(os.path.join("milly.png")).convert_alpha()
    milly_frame2 = pygame.image.load(os.path.join("milly2.png")).convert_alpha()
    milly_rotations = [rotated_images(milly_frame1), rotated_images(milly_frame2)]

    current_frame = 0
    intro_animation_timer = 0.0
    ANIMATION_SPEED = 0.2

    def load_and_scale_bg(filename):
        try:
            unscaled = pygame.image.load(os.path.join(filename)).convert()
        except FileNotFoundError:
            unscaled = pygame.Surface((720, 720))
            unscaled.fill((20, 20, 40))
        return pygame.transform.scale(unscaled, (720, 720))

    bg_tiles = [
        load_and_scale_bg("bg.png"),
        load_and_scale_bg("bg2.png"),
        load_and_scale_bg("bg3.png"),
        load_and_scale_bg("bg4.png"),
        load_and_scale_bg("bg5.png")
    ]

    trail = deque([(10, 10), (10, 20), (10, 30), (10, 40), (10, 50)])

    # --- Arrow Image Loading ---
    try:
        arrow_img = pygame.image.load(os.path.join("arrow.png")).convert_alpha()
        arrow_img = pygame.transform.scale(arrow_img, (64, 64))
    except FileNotFoundError:
        arrow_img = pygame.Surface((64, 64), pygame.SRCALPHA)
        pygame.draw.polygon(arrow_img, "yellow", [(64, 32), (0, 64), (0, 0)])

    arrow_rotations = rotated_images(arrow_img)

    # --- Fullscreen Images ---
    try:
        gameover_img = pygame.image.load(os.path.join("gameover.png")).convert_alpha()
        gameover_img = pygame.transform.scale(gameover_img, (1280, 720))
    except FileNotFoundError:
        gameover_img = pygame.Surface((1280, 720))
        gameover_img.fill("red")

    try:
        win_img = pygame.image.load(os.path.join("win.png")).convert_alpha()
        win_img = pygame.transform.scale(win_img, (1280, 720))
    except FileNotFoundError:
        win_img = pygame.Surface((1280, 720))
        win_img.fill("green")

    # --- Enemy System ---
    enemy_images = []
    for name in ["e1.png", "e2.png", "e3.png", "e4.png", "e5.png", "e6.png", "e7.png"]:
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

    for i in range(7):
        enemy_spawns.append(random_spawn(milly_pos_x, milly_pos_y, 1250, 4000, occupied_spots))
        occupied_spots.add(enemy_spawns[i])

    for i, pos in enumerate(enemy_spawns):
        enemies.append({
            "x": pos[0], "y": pos[1], "vx": 0.0, "vy": 0.0, "angle": 0.0,
            "rotations": enemy_rotations[i % len(enemy_rotations)],
            "trail": deque(), "grazed": False, "type": i+1, "wave": 0.0, "colour": "None"
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
            "pos": random_spawn(milly_pos_x, milly_pos_y, 1250, 4000, occupied_spots),
            "collected": False, "img": artifact_images[i]
        })
        occupied_spots.add(artifacts_on_map[i]["pos"])

    collected_artifacts = []
    active_effects = []

    # OPTIMIZATION: Particle Object Pool
    # Pre-allocate 250 dictionaries to avoid Python garbage collection stutters
    MAX_PARTICLES = 250
    particles = [{"active": False, "x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "life": 0.0, "size": 0, "color": "white"} for _ in range(MAX_PARTICLES)]
    particle_idx = 0

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
            screen.blit(intro_frames[intro_frame_index], (0, 0))
            pygame.display.flip()

        await asyncio.sleep(0)

    dt = clock.tick(60) / 1000

    # --- Audio Loading ---
    try:
        pygame.mixer.music.load(os.path.join("music.ogg"))
        pygame.mixer.music.set_volume(0.3)
        pygame.mixer.music.play(loops=-1, start=30.0)
    except pygame.error:
        print("Warning: 'music.ogg' not found.")

    try: gameover_sound = pygame.mixer.Sound(os.path.join("gameover.ogg"))
    except: gameover_sound = None

    try: win_sound = pygame.mixer.Sound(os.path.join("win.ogg"))
    except: win_sound = None

    try: collect_sound = pygame.mixer.Sound(os.path.join("collect.ogg"))
    except: collect_sound = None

    try: whoosh_sound = pygame.mixer.Sound(os.path.join("whoosh.ogg"))
    except: whoosh_sound = None

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
                    milly_pos_x, milly_pos_y = 15.0, 50.0
                    accel = 0
                    milly_angle = 180
                    camera_x, camera_y = 0.0, 0.0
                    trail = deque([(10, 10), (10, 20), (10, 30), (10, 40), (10, 50)])
                    occupied_spots = set()
                    enemy_spawns = []

                    for i in range(7):
                        enemy_spawns.append(random_spawn(milly_pos_x, milly_pos_y, 1250, 4000, occupied_spots))
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
                        artifact["pos"] = random_spawn(milly_pos_x,milly_pos_y,1250, 4000, occupied_spots)
                        artifact["collected"] = False
                        occupied_spots.add(artifact["pos"])

                    collected_artifacts = []
                    active_effects = []

                    # Reset particle pool instead of re-instantiating
                    for p in particles:
                        p["active"] = False

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
                    accel += 1
            if keys[pygame.K_a]:
                milly_angle += 3
            if keys[pygame.K_d]:
                milly_angle -= 3

            radians = math.radians(milly_angle)
            milly_pos_x -= math.sin(radians) * accel
            milly_pos_y -= math.cos(radians) * accel

            if accel > 0.5:
                intro_animation_timer += dt
                if intro_animation_timer >= ANIMATION_SPEED:
                    current_frame = (current_frame + 1) % 2
                    intro_animation_timer = 0.0
            else:
                current_frame = 0
                intro_animation_timer = 0.0

            screen_x = milly_pos_x - camera_x
            screen_y = milly_pos_y - camera_y

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
                dist_sq = (milly_pos_x - enemy["x"])**2 + (milly_pos_y - enemy["y"])**2

                if dist_sq < 4225: # 65 squared
                    if not game_over:
                        pygame.mixer.music.stop()
                        if whoosh_sound: whoosh_sound.stop()
                        if gameover_sound: gameover_sound.play()
                    game_over = True

                elif dist_sq < 25600 and not enemy["grazed"]: # 160 squared
                    accel += 6.0
                    if whoosh_sound: whoosh_sound.play()
                    enemy["grazed"] = True

                    mid_x = (milly_pos_x + enemy["x"]) / 2
                    mid_y = (milly_pos_y + enemy["y"]) / 2

                    # OPTIMIZATION: Pull from particle pool instead of creating new dicts
                    for _ in range(10):
                        p = particles[particle_idx]
                        p["active"] = True
                        p["x"] = mid_x
                        p["y"] = mid_y
                        angle = random.uniform(0, 2 * math.pi)
                        speed = random.uniform(3.0, 8.0)
                        p["vx"] = math.cos(angle) * speed
                        p["vy"] = math.sin(angle) * speed
                        p["life"] = random.uniform(0.2, 0.5)
                        p["size"] = random.randint(3, 7)
                        p["color"] = random.choice(["white", "yellow", "orange"])

                        # Round-robin: if we hit the end of the pool, loop back to the start
                        particle_idx = (particle_idx + 1) % MAX_PARTICLES

                if dist_sq > 90000: # 300 squared
                    enemy["grazed"] = False

                screen_ex = enemy["x"] - camera_x
                screen_ey = enemy["y"] - camera_y
                is_on_screen = (-100 < screen_ex < 1280 + 100) and (-100 < screen_ey < 720 + 100)

                turn_speed, accel_rate, max_speed, friction = 0.08, 0.8, 15.0, 0.96
                tracking_active = (dist_sq < 640000 and is_on_screen)
                apply_turn_penalty, increment_45, wave = True, False, False
                target_angle = math.atan2(milly_pos_y - enemy["y"], milly_pos_x - enemy["x"])

                if enemy["type"] == 1:
                    enemy["colour"] = "azure2"
                elif enemy["type"] == 2:
                    wave = True
                    enemy["colour"] = "green"
                elif enemy["type"] == 3:
                    target_angle = (math.pi / 4) * round(target_angle / (math.pi / 4))
                    turn_speed = 0.3
                    increment_45 = True
                    enemy["colour"] = "azure4"
                elif enemy["type"] == 4:
                    apply_turn_penalty = False
                    turn_speed, accel_rate = 0.15, 1
                    enemy["colour"] = "cyan"
                elif enemy["type"] == 5:
                    accel_rate += 0.4
                    max_speed += 3
                    friction += 0.02
                    enemy["colour"] = "hotpink1"
                elif enemy["type"] == 6:
                    player_vx = -math.sin(math.radians(milly_angle)) * accel
                    player_vy = -math.cos(math.radians(milly_angle)) * accel
                    future_x = milly_pos_x + (player_vx * 20)
                    future_y = milly_pos_y + (player_vy * 20)
                    target_angle = math.atan2(future_y - enemy["y"], future_x - enemy["x"])
                    max_speed, turn_speed, accel_rate = 23.0, 0.055, 1.2
                    enemy["colour"], enemy["is_sniping"] = "purple", False
                elif enemy["type"] == 7:
                    nearest_art_dist_sq = float('inf')
                    target_artifact = None

                    for artifact in artifacts_on_map:
                        if not artifact["collected"]:
                            ax, ay = artifact["pos"]
                            dist_to_art_sq = (ax - enemy["x"])**2 + (ay - enemy["y"])**2
                            if dist_to_art_sq < nearest_art_dist_sq:
                                nearest_art_dist_sq = dist_to_art_sq
                                target_artifact = (ax, ay)
                    enemy["target_artifact"] = target_artifact
                    enemy["is_guarding"] = False

                    if target_artifact:
                        ax, ay = target_artifact
                        player_dist_to_art_sq = (milly_pos_x - ax)**2 + (milly_pos_y - ay)**2

                        if player_dist_to_art_sq < 202500: # 450 squared
                            max_speed, accel_rate, turn_speed = 17.0, 1.2, 0.15
                            enemy["is_guarding"] = True
                        else:
                            if nearest_art_dist_sq > 22500: # 150 squared
                                target_angle = math.atan2(ay - enemy["y"], ax - enemy["x"])
                                max_speed, turn_speed = 12.0, 0.08
                                enemy["is_guarding"] = False
                            else:
                                target_angle = math.atan2(ay - enemy["y"], ax - enemy["x"]) + (math.pi / 2)
                                max_speed, turn_speed = 7.0, 0.1
                                enemy["is_guarding"] = True
                    enemy["colour"] = "yellow"

                if tracking_active:
                    if enemy["type"] == 6: enemy["is_sniping"] = True
                    angle_diff = (target_angle - enemy["angle"])
                    angle_diff = (angle_diff + math.pi) % (2 * math.pi) - math.pi

                    if angle_diff > turn_speed: enemy["angle"] += turn_speed
                    elif angle_diff < -turn_speed: enemy["angle"] -= turn_speed
                    else:
                        move_angle = enemy["angle"]
                        if wave:
                            enemy["wave"] += 0.15
                            move_angle += math.sin(enemy["wave"])
                        if increment_45: move_angle = (math.pi / 4) * round(enemy["angle"] / (math.pi / 4))

                        enemy["vx"] += math.cos(move_angle) * accel_rate
                        enemy["vy"] += math.sin(move_angle) * accel_rate

                        if apply_turn_penalty and abs(angle_diff) > (math.pi / 2):
                            enemy["vx"] *= 0.85
                            enemy["vy"] *= 0.85
                        else:
                            move_angle = enemy["angle"]

                        if increment_45: move_angle = (math.pi / 4) * round(enemy["angle"] / (math.pi / 4))
                        enemy["vx"] += math.cos(move_angle) * accel_rate
                        enemy["vy"] += math.sin(move_angle) * accel_rate

                enemy["vx"] *= friction
                enemy["vy"] *= friction

                speed_sq = enemy["vx"]**2 + enemy["vy"]**2
                if speed_sq > max_speed**2:
                    speed = math.sqrt(speed_sq)
                    enemy["vx"] = (enemy["vx"] / speed) * max_speed
                    enemy["vy"] = (enemy["vy"] / speed) * max_speed

                enemy["x"] += enemy["vx"]
                enemy["y"] += enemy["vy"]

                if speed_sq > 0.25:
                    if not enemy["trail"] or (enemy["trail"][-1][0] - enemy["x"])**2 + (enemy["trail"][-1][1] - enemy["y"])**2 > 25:
                        enemy["trail"].append((enemy["x"], enemy["y"]))
                        if len(enemy["trail"]) > 4000:
                            enemy["trail"].popleft()

            if accel > 0:
                if not trail or (trail[-1][0] - milly_pos_x)**2 + (trail[-1][1] - milly_pos_y)**2 > 25:
                    trail.append((milly_pos_x, milly_pos_y))
                    if len(trail) > 4000:
                        trail.popleft()

            # --- Artifact Collision Logic ---
            for artifact in artifacts_on_map:
                if not artifact["collected"]:
                    ax, ay = artifact["pos"]
                    if (milly_pos_x - ax)**2 + (milly_pos_y - ay)**2 < 3600:
                        artifact["collected"] = True
                        collected_artifacts.append(artifact["img"])
                        if collect_sound: collect_sound.play()
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
                    if whoosh_sound: whoosh_sound.stop()
                    if win_sound: win_sound.play()
                game_won = True

        # --- Rendering ---

        bg_w, bg_h = 720, 720
        offset_x = -int(camera_x) % bg_w
        offset_y = -int(camera_y) % bg_h

        for x in range(offset_x - bg_w, 1280, bg_w):
            for y in range(offset_y - bg_h, 720, bg_h):
                grid_x = (int(camera_x) + x) // bg_w
                grid_y = (int(camera_y) + y) // bg_h
                tile_index = abs(grid_x * 37 + grid_y * 89) % len(bg_tiles)
                screen.blit(bg_tiles[tile_index], (x, y))

        for tx, ty in trail:
            screen_tx = round(tx - camera_x)
            screen_ty = round(ty - camera_y)
            if -40 < screen_tx < 1320 and -40 < screen_ty < 760:
                pygame.draw.circle(screen, "black", (screen_tx, screen_ty), 40)

        for enemy in enemies:
            for tx, ty in enemy["trail"]:
                screen_tx = round(tx - camera_x)
                screen_ty = round(ty - camera_y)
                if -40 < screen_tx < 1320 and -40 < screen_ty < 760:
                    pygame.draw.circle(screen, "black", (screen_tx, screen_ty), 40)

        for enemy in enemies:
            if enemy["trail"]:
                tx, ty = enemy["trail"][-1]
                screen_tx = round(tx - camera_x)
                screen_ty = round(ty - camera_y)
                if -40 < screen_tx < 1320 and -40 < screen_ty < 760:
                    pygame.draw.circle(screen, enemy["colour"], (screen_tx, screen_ty), 40)

        # --- DRAW GUARDIAN TERRITORIES ---
        for enemy in enemies:
            if enemy["type"] == 7 and enemy.get("target_artifact") and enemy.get("is_guarding"):
                ax, ay = enemy["target_artifact"]
                screen_ax = round(ax - camera_x)
                screen_ay = round(ay - camera_y)

                if -450 < screen_ax < 1280 + 450 and -450 < screen_ay < 720 + 450:
                    pygame.draw.circle(screen, "yellow", (screen_ax, screen_ay), 450, 2)

        # --- DRAW SNIPER LINE OF SIGHT ---
        for enemy in enemies:
            if enemy["type"] == 6:
                speed_sq = enemy["vx"]**2 + enemy["vy"]**2
                if speed_sq < 49.0 and enemy.get("is_sniping"):
                    screen_ex = enemy["x"] - camera_x
                    screen_ey = enemy["y"] - camera_y

                    player_vx = -math.sin(math.radians(milly_angle)) * accel
                    player_vy = -math.cos(math.radians(milly_angle)) * accel
                    future_x = milly_pos_x + (player_vx * 20)
                    future_y = milly_pos_y + (player_vy * 20)

                    dist_to_target = math.sqrt((future_x - enemy["x"])**2 + (future_y - enemy["y"])**2)

                    end_x = screen_ex + math.cos(enemy["angle"]) * dist_to_target
                    end_y = screen_ey + math.sin(enemy["angle"]) * dist_to_target

                    pygame.draw.line(screen, "red", (screen_ex, screen_ey), (end_x, end_y), 4)

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

        # --- UPDATE AND DRAW PARTICLES (Object Pool) ---
        for p in particles:
            if p["active"]:
                p["x"] += p["vx"]
                p["y"] += p["vy"]
                p["life"] -= dt

                if p["life"] <= 0:
                    # Instead of deleting it, we just mark it as available
                    p["active"] = False
                else:
                    screen_px = round(p["x"] - camera_x)
                    screen_py = round(p["y"] - camera_y)

                    if -10 < screen_px < 1280 + 10 and -10 < screen_py < 720 + 10:
                        pygame.draw.rect(screen, p["color"], (screen_px, screen_py, p["size"], p["size"]))

        for enemy in enemies:
            dist_sq = (milly_pos_x - enemy["x"])**2 + (milly_pos_y - enemy["y"])**2
            if dist_sq < 1440000: # 1200 squared
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
        milly_rect = milly.get_rect(center=(round(milly_pos_x - camera_x), round(milly_pos_y - camera_y)))
        screen.blit(milly, milly_rect)

        nearest_dist_sq = float('inf')
        nearest_target = None
        for artifact in artifacts_on_map:
            if not artifact["collected"]:
                ax, ay = artifact["pos"]
                dist_sq = (milly_pos_x - ax)**2 + (milly_pos_y - ay)**2
                if dist_sq < nearest_dist_sq:
                    nearest_dist_sq = dist_sq
                    nearest_target = (ax, ay)

        if nearest_target:
            tx, ty = nearest_target
            angle_rad = math.atan2(-(ty - milly_pos_y), tx - milly_pos_x)
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

        await asyncio.sleep(0)

    pygame.quit()

asyncio.run(main())
