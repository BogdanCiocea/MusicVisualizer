import pygame
import constants

# Font Setup
pygame.font.init()
my_font = pygame.font.SysFont("Arial", 20, bold=False)
title_font = pygame.font.SysFont("Arial", 30, bold=True)
WIDTH, HEIGHT = 1920, 1080
cx, cy = WIDTH // 2, HEIGHT // 2
screen = pygame.display.set_mode()

green = (0, 255, 0)
white = (255, 255, 255)

val_kick = 0
val_snare = 0
val_hihat = 0
val_vocals = 0


def show_ui_texts(list_of_effects, state, space, shake_x, shake_y):
    for effect in list_of_effects:
        if not getattr(state, effect):
            continue

        effect_name = effect.replace("effect_", "").replace("_", " ").title()
        txt_effect = my_font.render(
            f"{effect_name} ({effect_name.upper()[0]}): {"ON" if getattr(state, effect) else "OFF"}",
            True,
            green if getattr(state, effect) else white,
        )
        screen.blit(txt_effect, (cx + cx // 2 + shake_x, 20 + space + shake_y))

        space += 30

    return space


def show_ui_effects(state, shake_x, shake_y):
    space = 0

    cx_new = cx + cx // 2 + shake_x

    txt_song = title_font.render(f"{state.song_name}", True, (255, 255, 255))

    song_rect = txt_song.get_rect(midtop=(constants.WIDTH // 2 + shake_x, 20))
    screen.blit(txt_song, song_rect)

    space += 30

    txt_volume = my_font.render(
        f"Volume (Arrows): {state.volume}",
        True,
        white,
    )
    screen.blit(txt_volume, (cx_new, 20 + space + shake_y))

    space += 30

    if state.speed_rate != 0:
        txt_speed = my_font.render(
            f"Speed (S): TikTok {int(state.speed * 100)}%", True, (255, 255, 255)
        )
    else:
        txt_speed = my_font.render("Speed (S): Normal", True, (255, 255, 255))

    screen.blit(txt_speed, (cx_new, 20 + space + shake_y))

    space += 30
    txt_skip_song = my_font.render(
        "Skip song (K)",
        True,
        white,
    )
    screen.blit(txt_skip_song, (cx_new, 20 + space + shake_y))

    space += 30

    space = show_ui_texts(
        (
            "effect_noise_gate",
            "effect_distortion",
            "effect_alien",
            "effect_pan",
            "effect_low_pass",
            "effect_bitcrusher",
            "effect_vibrato",
            "effect_high_pass",
            "effect_tremolo",
            "effect_overdrive",
            "effect_echo",
        ),
        state,
        space,
        shake_x,
        shake_y,
    )


def show_ui_circles(shake_x, shake_y):
    # KICK: red
    r_kick = int(val_kick * 2)
    if r_kick > 0:
        pygame.draw.circle(screen, (200, 50, 50), (cx + shake_x, cy + shake_y), r_kick)
        # Text Kick
        txt_kick = my_font.render("BASS", True, (255, 200, 200))
        screen.blit(txt_kick, (cx - txt_kick.get_width() // 2, cy - r_kick - 30))

    # VOCALS: yellow
    r_vocals = int(val_vocals * 7)
    y_vocals = cy // 2
    if r_vocals > 0:
        pygame.draw.circle(
            screen, (255, 215, 0), (cx // 2 + shake_x, y_vocals + shake_y), r_vocals
        )  # Gold/Yellow
        # Text Vocals
        txt_voc = my_font.render("VOCALS", True, (255, 255, 100))
        screen.blit(
            txt_voc, (cx // 2 - txt_voc.get_width() // 2, y_vocals - r_vocals - 30)
        )

    # SNARE: green
    r_snare = int(val_snare * 2)
    x_snare = cx // 2
    if r_snare > 0:
        pygame.draw.circle(
            screen, (50, 255, 50), (x_snare + shake_x, cy + shake_y), r_snare
        )
        # Text Snare
        txt_snare = my_font.render("MIDS", True, (150, 255, 150))
        screen.blit(
            txt_snare, (x_snare - txt_snare.get_width() // 2, cy - r_snare - 30)
        )

    # HIHAT: blue
    r_hihat = int(val_hihat * 4)
    x_hihat = cx
    if r_hihat > 0:
        pygame.draw.circle(
            screen, (50, 50, 255), (x_hihat + shake_x, cy // 2 + shake_y), r_hihat
        )
        # Text HiHat
        txt_hihat = my_font.render("HIGHS", True, (150, 150, 255))
        screen.blit(
            txt_hihat, (x_hihat - txt_hihat.get_width() // 2, cy // 2 - r_hihat - 30)
        )
