import numpy as np
import pygame
import pyaudio
import wave
import effects
import ui
import os
import yt_dlp
import threading
import constants
import random
import threads
import time

from music_classes import AppState, StatusObj
from vocal_extract import generate_vocal_track, get_vocal_path
from lyrics import download_lyrics, parse_lrc, get_current_lyric, get_lyric_path
from constants import bg_path

os.environ["OMP_NUM_THREADS"] = "4"
os.environ["MKL_NUM_THREADS"] = "4"

# SETUP AUDIO STREAM
p = pyaudio.PyAudio()
audio_input_stream = None
audio_output_stream = None
wav_file = None
vocal_wav_file = None

# SETUP VISUALS
# pygame.init()
# screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
# clock = pygame.time.Clock()
# pygame.display.set_caption("Music Visualizer")

phase = 0


def init_song_file_hashmap():
    init_hashmap = {}
    base_path = os.path.dirname(os.path.abspath(__file__))
    songs_directory = os.path.join(base_path, "songs")
    supported_formats = (".mp3", ".wav", ".ogg")

    if os.path.exists(songs_directory):
        for filename in os.listdir(songs_directory):
            if filename.lower().endswith(supported_formats):
                full_path = os.path.join(songs_directory, filename)
                title = os.path.splitext(filename)[0].replace("_", " ")
                init_hashmap[os.path.splitext(filename)[0]] = (full_path, title)

    # for title, data in init_hashmap.items():
    #     print(f"{title}: {data[0]}")

    return init_hashmap


def get_song_by_string_youtube(song_string, state):
    search_query = f"ytsearch1:{song_string}"
    out_tmpl = f"{constants.SONGS_DIRECTORY}/%(title)s.%(ext)s"

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "outtmpl": out_tmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
            }
        ],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search_query, download=True)

            if "entries" in info:
                video_info = info["entries"][0]
            else:
                video_info = info

            real_title = video_info.get("title", song_string)
            # state.song_name = real_title

            filename = ydl.prepare_filename(video_info)
            base, _ = os.path.splitext(filename)
            final_wav_path = base + ".wav"

            return final_wav_path, real_title
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None


def play_song(song_path, state, song_name):
    global wav_file, audio_output_stream, vocal_wav_file

    if audio_output_stream:
        audio_output_stream.stop_stream()
        audio_output_stream.close()
        audio_output_stream = None
    if wav_file:
        wav_file.close()
        wav_file = None
    if vocal_wav_file:
        vocal_wav_file.close()
        vocal_wav_file = None
    try:
        wav_file = wave.open(song_path, "rb")

        v_path = get_vocal_path(song_path)
        if os.path.exists(v_path):
            vocal_wav_file = wave.open(v_path, "rb")

        l_path = get_lyric_path(song_path)
        if os.path.exists(l_path):
            state.current_lyrics = parse_lrc(l_path)
        else:
            state.current_lyrics = []

        state.song_name = song_name
        state.echo_buffer.clear()
        audio_output_stream = p.open(
            format=p.get_format_from_width(wav_file.getsampwidth()),
            channels=wav_file.getnchannels(),
            rate=int(wav_file.getframerate() * state.speed),
            output=True,
        )
    except Exception as e:
        print(f"[ERROR] Play song: {e}")
        state.song_name = ""


def process_song_files(full_path, real_title, state, status_obj):
    vocal_path = get_vocal_path(full_path)
    if not os.path.exists(vocal_path):
        if status_obj:
            status_obj.text = "Generating vocals..."
            status_obj.color = (255, 255, 0)
        print("Generating vocals...")
        generate_vocal_track(full_path)

    lrc_path = get_lyric_path(full_path)
    if not os.path.exists(lrc_path):
        if status_obj:
            status_obj.text = "Downloading lyrics..."
        download_lyrics(real_title, lrc_path)


def add_songs_to_hashmap(song_file_hashmap, song_string, state, status_obj):
    full_path, real_title = get_song_by_string_youtube(song_string, state)
    song_key = song_string.replace(" ", "_")

    if full_path and real_title:
        song_file_hashmap[song_key] = (full_path, real_title)

        vocal_path = get_vocal_path(full_path)
        if not os.path.exists(vocal_path):
            status_obj.text = "Generating vocals..."
            status_obj.color = (255, 255, 0)
            print(f"Status update: {status_obj.text}")
            generate_vocal_track(full_path)

        lrc_path = get_lyric_path(full_path)
        if not os.path.exists(lrc_path):
            status_obj.text = "Downloading lyrics..."
            download_lyrics(real_title, lrc_path)

        state.song_name = real_title
        play_song(full_path, state, real_title)
    else:
        print("[ERROR]: add songs to hashmap")

    return song_file_hashmap


def add_song_to_playlist(main_screen, song_hashmap, state):
    modal_width, modal_height = 800, 600
    modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)

    input_box_width = 600
    input_box_height = 55
    input_box_rect = pygame.Rect(
        (modal_width - input_box_width) // 2, 120, input_box_width, input_box_height
    )
    user_text = ""

    running_playlist = True

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_INPUT_BG = (68, 71, 90)
    C_TEXT = (248, 248, 242)
    C_TEXT_DIM = (180, 180, 180)
    C_ACCENT = (189, 147, 249)
    C_BORDER = (98, 114, 164)
    C_LIST_BG = (50, 50, 60)

    cursor_visible = True
    last_blink_time = time.time()

    list_start_y = 220
    item_height = 40
    scroll_y = 0
    visible_height = modal_height - list_start_y - 20

    while running_playlist:
        mx, my = pygame.mouse.get_pos()

        content_height = len(state.playlist) * item_height
        max_scroll = max(0, content_height - visible_height)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_playlist = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running_playlist = False

                elif event.key == pygame.K_RETURN:
                    if user_text.strip():
                        new_song = user_text.strip()
                        state.playlist.append(new_song)
                        user_text = ""

                        new_content_h = len(state.playlist) * item_height
                        if new_content_h > visible_height:
                            scroll_y = new_content_h - visible_height
                        else:
                            scroll_y = 0

                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]

                else:
                    user_text += event.unicode

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 20
                if scroll_y < 0:
                    scroll_y = 0
                if scroll_y > max_scroll:
                    scroll_y = max_scroll

        if time.time() - last_blink_time > 0.5:
            cursor_visible = not cursor_visible
            last_blink_time = time.time()

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        modal_surface.fill((0, 0, 0, 0))

        shadow_rect = pygame.Rect(15, 15, modal_width, modal_height)
        pygame.draw.rect(modal_surface, (0, 0, 0, 100), shadow_rect, border_radius=20)

        main_rect = pygame.Rect(0, 0, modal_width, modal_height)
        pygame.draw.rect(modal_surface, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(modal_surface, C_BORDER, main_rect, 2, border_radius=20)

        title_surf = ui.title_font.render("PLAYLIST MANAGER", True, C_TEXT)
        title_rect = title_surf.get_rect(center=(modal_width // 2, 50))
        modal_surface.blit(title_surf, title_rect)

        pygame.draw.rect(modal_surface, C_INPUT_BG, input_box_rect, border_radius=10)
        pygame.draw.rect(modal_surface, C_BORDER, input_box_rect, 2, border_radius=10)

        txt_surf = ui.my_font.render(user_text, True, C_TEXT)
        modal_surface.blit(txt_surf, (input_box_rect.x + 15, input_box_rect.y + 12))

        if cursor_visible:
            cursor_x = input_box_rect.x + 15 + txt_surf.get_width() + 2
            pygame.draw.line(
                modal_surface,
                C_ACCENT,
                (cursor_x, input_box_rect.y + 12),
                (cursor_x, input_box_rect.y + 42),
                2,
            )

        label_surf = ui.my_font.render("Add new song:", True, C_TEXT_DIM)
        modal_surface.blit(label_surf, (input_box_rect.x, input_box_rect.y - 30))

        header_surf = ui.my_font.render(
            f"Current Playlist ({len(state.playlist)}):", True, C_ACCENT
        )
        modal_surface.blit(header_surf, (input_box_rect.x, list_start_y - 35))

        clip_rect = pygame.Rect(0, list_start_y, modal_width, visible_height)
        modal_surface.set_clip(clip_rect)

        for i, song in enumerate(state.playlist):
            pos_y = list_start_y + (i * item_height) - scroll_y

            if pos_y + item_height < list_start_y or pos_y > modal_height:
                continue

            row_rect = pygame.Rect(
                input_box_rect.x, pos_y, input_box_width, item_height - 5
            )
            pygame.draw.rect(modal_surface, C_LIST_BG, row_rect, border_radius=8)

            final_title = song
            search_query = song.lower().strip()
            for key, val in song_hashmap.items():
                if isinstance(val, tuple) and len(val) >= 2:
                    path, hashmap_title = val
                    if (
                        search_query in hashmap_title.lower()
                        and "vocal" not in search_query
                        and "vocal" not in hashmap_title.lower()
                    ):
                        final_title = hashmap_title
                        break

            display_text = f"{i + 1}. {final_title}"
            if len(display_text) > 50:
                display_text = display_text[:47] + "..."

            item_surf = ui.my_font.render(display_text, True, C_TEXT)
            item_rect = item_surf.get_rect(midleft=(row_rect.x + 15, row_rect.centery))
            modal_surface.blit(item_surf, item_rect)

        modal_surface.set_clip(None)

        if content_height > visible_height:
            scrollbar_height = (visible_height / content_height) * visible_height
            scroll_ratio = scroll_y / max_scroll
            scrollbar_y = list_start_y + (
                scroll_ratio * (visible_height - scrollbar_height)
            )
            scrollbar_rect = pygame.Rect(
                input_box_rect.right + 10, scrollbar_y, 6, scrollbar_height
            )
            pygame.draw.rect(
                modal_surface, (100, 100, 100), scrollbar_rect, border_radius=3
            )

        x_pos = (main_screen.get_width() - modal_width) // 2
        y_pos = (main_screen.get_height() - modal_height) // 2
        main_screen.blit(modal_surface, (x_pos, y_pos))

        pygame.display.flip()


def show_songs_library(main_screen, song_hashmap, state):
    modal_width, modal_height = 800, 600
    modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)

    running_state = True

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_TEXT = (248, 248, 242)
    C_BORDER = (98, 114, 164)
    C_LIST_BG = (50, 50, 60)

    title = "SONGS LIBRARY"
    song_list = list(song_hashmap.keys())

    scroll_y = 0
    item_height = 50
    list_start_y = 100
    visible_height = modal_height - list_start_y - 20

    while running_state:
        content_height = len(song_list) * item_height
        max_scroll = max(0, content_height - visible_height)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_state = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running_state = False

                if event.key == pygame.K_UP:
                    scroll_y -= 20
                if event.key == pygame.K_DOWN:
                    scroll_y += 20

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 20

        if scroll_y < 0:
            scroll_y = 0
        if scroll_y > max_scroll:
            scroll_y = max_scroll

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        modal_surface.fill((0, 0, 0, 0))

        shadow_rect = pygame.Rect(15, 15, modal_width, modal_height)
        pygame.draw.rect(modal_surface, (0, 0, 0, 100), shadow_rect, border_radius=20)

        main_rect = pygame.Rect(0, 0, modal_width, modal_height)
        pygame.draw.rect(modal_surface, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(modal_surface, C_BORDER, main_rect, 2, border_radius=20)

        title_surf = ui.title_font.render(title, True, C_TEXT)
        title_rect = title_surf.get_rect(center=(modal_width // 2, 50))
        modal_surface.blit(title_surf, title_rect)

        pygame.draw.line(modal_surface, C_BORDER, (50, 80), (modal_width - 50, 80), 1)

        clip_rect = pygame.Rect(0, list_start_y, modal_width, visible_height)
        modal_surface.set_clip(clip_rect)

        for i, song_name in enumerate(song_list):
            pos_y = list_start_y + (i * item_height) - scroll_y

            if pos_y + item_height < list_start_y or pos_y > modal_height:
                continue

            row_rect = pygame.Rect(50, pos_y, modal_width - 100, item_height - 5)
            pygame.draw.rect(modal_surface, C_LIST_BG, row_rect, border_radius=8)

            if len(song_name) > 50:
                display_name = song_name[:47] + "..."
            else:
                display_name = song_name

            item_text = ui.my_font.render(display_name, True, C_TEXT)
            item_rect = item_text.get_rect(midleft=(row_rect.x + 15, row_rect.centery))
            modal_surface.blit(item_text, item_rect)

        modal_surface.set_clip(None)

        if content_height > visible_height:
            scrollbar_height = (visible_height / content_height) * visible_height
            scroll_ratio = scroll_y / max_scroll
            scrollbar_y = list_start_y + (
                scroll_ratio * (visible_height - scrollbar_height)
            )
            scrollbar_rect = pygame.Rect(
                modal_width - 15, scrollbar_y, 6, scrollbar_height
            )
            pygame.draw.rect(
                modal_surface, (100, 100, 100), scrollbar_rect, border_radius=3
            )

        x_pos = (main_screen.get_width() - modal_width) // 2
        y_pos = (main_screen.get_height() - modal_height) // 2
        main_screen.blit(modal_surface, (x_pos, y_pos))

        pygame.display.flip()


def delete_a_song(main_screen, song_hashmap, state):
    running_state = True

    modal_width, modal_height = 800, 600
    modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_INPUT_BG = (68, 71, 90)
    C_TEXT = (248, 248, 242)
    C_ACCENT = (255, 85, 85)
    C_ACCENT_HOVER = (255, 110, 110)
    C_BORDER = (98, 114, 164)

    input_box_width = 600
    input_box_height = 50
    input_box_rect = pygame.Rect(
        (modal_width - input_box_width) // 2, 100, input_box_width, input_box_height
    )
    user_text = ""

    song_list = list(song_hashmap.keys())
    scroll_y = 0
    item_height = 50
    list_start_y = 170
    visible_height = modal_height - list_start_y - 20

    while running_state:
        filtered_songs = [s for s in song_list if user_text.lower() in s.lower()]
        content_height = len(filtered_songs) * item_height
        max_scroll = max(0, content_height - visible_height)

        mx, my = pygame.mouse.get_pos()
        modal_x = (main_screen.get_width() - modal_width) // 2
        modal_y = (main_screen.get_height() - modal_height) // 2
        rel_mx = mx - modal_x
        rel_my = my - modal_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_state = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running_state = False
                    return
                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]
                else:
                    user_text += event.unicode
                scroll_y = 0

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 20
                if scroll_y < 0:
                    scroll_y = 0
                if scroll_y > max_scroll:
                    scroll_y = max_scroll

            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    clip_rect = pygame.Rect(
                        0, list_start_y, modal_width, visible_height
                    )

                    if clip_rect.collidepoint(rel_mx, rel_my):
                        for i, song_name in enumerate(filtered_songs):
                            pos_y = list_start_y + (i * item_height) - scroll_y

                            btn_rect = pygame.Rect(
                                modal_width - 140, pos_y + 10, 100, 30
                            )

                            if btn_rect.collidepoint(rel_mx, rel_my):
                                print(f"Deleting: {song_name}")
                                if song_name in song_hashmap:
                                    full_path_original = song_hashmap[song_name][0]
                                    path_to_vocal = get_vocal_path(full_path_original)
                                    path_to_lyrics = get_lyric_path(full_path_original)

                                    try:
                                        if os.path.exists(full_path_original):
                                            os.remove(full_path_original)
                                            print(f"Deleted file: {full_path_original}")
                                        if os.path.exists(path_to_vocal):
                                            os.remove(path_to_vocal)
                                            print(f"Deleted vocals: {path_to_vocal}")
                                        if os.path.exists(path_to_lyrics):
                                            os.remove(path_to_lyrics)
                                            print(f"Deleted lyrics: {path_to_lyrics}")
                                    except PermissionError as e:
                                        print(f"[ERROR] Delete a song permission: {e}")
                                    except Exception as e:
                                        print(f"[ERROR] Delete a song: {e}")

                                    del song_hashmap[song_name]
                                    song_list = list(song_hashmap.keys())
                                break

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        modal_surface.fill((0, 0, 0, 0))

        main_rect = pygame.Rect(0, 0, modal_width, modal_height)
        pygame.draw.rect(modal_surface, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(modal_surface, C_BORDER, main_rect, 2, border_radius=20)

        title_surf = ui.title_font.render("DELETE A SONG", True, C_TEXT)
        title_rect = title_surf.get_rect(center=(modal_width // 2, 40))
        modal_surface.blit(title_surf, title_rect)

        pygame.draw.rect(modal_surface, C_INPUT_BG, input_box_rect, border_radius=10)
        pygame.draw.rect(modal_surface, C_BORDER, input_box_rect, 2, border_radius=10)

        txt_surf = ui.my_font.render(user_text, True, C_TEXT)
        modal_surface.blit(txt_surf, (input_box_rect.x + 15, input_box_rect.y + 10))

        label_surf = ui.my_font.render("Search to delete:", True, (150, 150, 150))
        modal_surface.blit(label_surf, (input_box_rect.x, input_box_rect.y - 25))

        clip_rect = pygame.Rect(0, list_start_y, modal_width, visible_height)
        modal_surface.set_clip(clip_rect)

        for i, song_name in enumerate(filtered_songs):
            pos_y = list_start_y + (i * item_height) - scroll_y

            if pos_y + item_height < list_start_y or pos_y > modal_height:
                continue

            row_rect = pygame.Rect(50, pos_y, modal_width - 100, item_height - 5)
            is_hovered = row_rect.collidepoint(rel_mx, rel_my)
            row_color = (60, 60, 70) if not is_hovered else (70, 70, 80)
            pygame.draw.rect(modal_surface, row_color, row_rect, border_radius=8)

            display_name = song_name if len(song_name) < 35 else song_name[:32] + "..."
            name_surf = ui.my_font.render(display_name, True, C_TEXT)
            name_rect = name_surf.get_rect(midleft=(row_rect.x + 15, row_rect.centery))
            modal_surface.blit(name_surf, name_rect)

            btn_rect = pygame.Rect(row_rect.right - 110, row_rect.y + 10, 100, 30)
            btn_hovered = btn_rect.collidepoint(rel_mx, rel_my)
            btn_color = C_ACCENT_HOVER if btn_hovered else C_ACCENT

            pygame.draw.rect(modal_surface, btn_color, btn_rect, border_radius=5)
            del_txt = ui.my_font.render("DELETE", True, (40, 40, 40))
            del_rect = del_txt.get_rect(center=btn_rect.center)
            modal_surface.blit(del_txt, del_rect)

        modal_surface.set_clip(None)

        main_screen.blit(modal_surface, (modal_x, modal_y))

        pygame.display.flip()


def skip_the_current_song(song_hashmap, state, current_status):
    global wav_file, audio_output_stream, vocal_wav_file
    if len(state.playlist) == 0 and state.song_name == "":
        return

    if state.song_name != "":
        if audio_output_stream:
            audio_output_stream.stop_stream()
            audio_output_stream.close()
            audio_output_stream = None
        if wav_file:
            wav_file.close()
            wav_file = None
        if vocal_wav_file:
            vocal_wav_file.close()
            vocal_wav_file = None
            state.song_name = ""
            state.current_lyrics = []
            state.paused = False
        return

    try:
        next_song = state.playlist[0]
        state.downloading_playlist_item = True
        state.song_name = ""
        download_thread = threading.Thread(
            target=threads.worker_thread,
            args=(next_song, song_hashmap, state, current_status),
        )
        download_thread.start()
        state.playlist.pop(0)
    except Exception as e:
        print(f"[ERROR] Skip a song: {e}")


def show_controls(main_screen):
    running_state = True

    modal_width, modal_height = 800, 600
    modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_TEXT = (248, 248, 242)
    C_TEXT_DIM = (180, 180, 180)
    C_BORDER = (98, 114, 164)
    C_KEY_BG = (255, 255, 255)
    C_KEY_TEXT = (40, 42, 54)
    C_ROW_HOVER = (68, 71, 90)

    controls_data = [
        ("Playback", "Category"),
        ("Play / Pause", "SPACE"),
        # ("Stop / Next Song", "X"),
        ("Skip Song", "K"),
        ("Open Menu / Back", "ESC"),
        ("Audio Settings", "Category"),
        ("Volume Up", "UP ARROW"),
        ("Volume Down", "DOWN ARROW"),
        ("Change Speed", "S"),
        ("Audio Effects", "Category"),
        ("Noise Gate", "N"),
        ("Distortion", "D"),
        ("Alien Effect", "A"),
        ("Pan Effect", "P"),
        ("Low Pass Filter", "L"),
        ("High Pass Filter", "H"),
        ("Bitcrusher", "B"),
        ("Vibrato", "V"),
        ("Tremolo", "T"),
        ("Overdrive", "O"),
        ("Echo / Delay", "E"),
    ]

    scroll_y = 0
    item_height = 45
    list_start_y = 100
    visible_height = modal_height - list_start_y - 20

    content_height = len(controls_data) * item_height

    while running_state:
        max_scroll = max(0, content_height - visible_height)

        mx, my = pygame.mouse.get_pos()
        modal_x = (main_screen.get_width() - modal_width) // 2
        modal_y = (main_screen.get_height() - modal_height) // 2
        rel_mx = mx - modal_x
        rel_my = my - modal_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_state = False

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_f):
                    running_state = False
                if event.key == pygame.K_UP:
                    scroll_y -= 20
                if event.key == pygame.K_DOWN:
                    scroll_y += 20

            if event.type == pygame.MOUSEWHEEL:
                scroll_y -= event.y * 20

        if scroll_y < 0:
            scroll_y = 0
        if scroll_y > max_scroll:
            scroll_y = max_scroll

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        modal_surface.fill((0, 0, 0, 0))

        shadow_rect = pygame.Rect(10, 10, modal_width, modal_height)
        pygame.draw.rect(modal_surface, (0, 0, 0, 100), shadow_rect, border_radius=20)

        main_rect = pygame.Rect(0, 0, modal_width, modal_height)
        pygame.draw.rect(modal_surface, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(modal_surface, C_BORDER, main_rect, 2, border_radius=20)

        title_surf = ui.title_font.render("CONTROLS & SHORTCUTS", True, C_TEXT)
        title_rect = title_surf.get_rect(center=(modal_width // 2, 40))
        modal_surface.blit(title_surf, title_rect)

        pygame.draw.line(modal_surface, C_BORDER, (50, 80), (modal_width - 50, 80), 1)

        clip_rect = pygame.Rect(0, list_start_y, modal_width, visible_height)
        modal_surface.set_clip(clip_rect)

        for i, (action, key_val) in enumerate(controls_data):
            pos_y = list_start_y + (i * item_height) - scroll_y

            if pos_y + item_height < list_start_y or pos_y > modal_height:
                continue

            if key_val == "Category":
                cat_surf = ui.my_font.render(action.upper(), True, (189, 147, 249))
                cat_rect = cat_surf.get_rect(midleft=(50, pos_y + item_height // 2))
                modal_surface.blit(cat_surf, cat_rect)
                pygame.draw.line(
                    modal_surface,
                    (189, 147, 249),
                    (50, pos_y + item_height - 5),
                    (200, pos_y + item_height - 5),
                    1,
                )

            else:
                row_rect = pygame.Rect(50, pos_y, modal_width - 100, item_height - 5)

                if row_rect.collidepoint(rel_mx, rel_my):
                    pygame.draw.rect(
                        modal_surface, C_ROW_HOVER, row_rect, border_radius=8
                    )

                action_surf = ui.my_font.render(action, True, C_TEXT_DIM)
                action_rect = action_surf.get_rect(
                    midleft=(row_rect.x + 20, row_rect.centery)
                )
                modal_surface.blit(action_surf, action_rect)

                key_surf = ui.my_font.render(key_val, True, C_KEY_TEXT)

                key_w = key_surf.get_width() + 20
                key_h = 30
                key_rect = pygame.Rect(0, 0, key_w, key_h)
                key_rect.midright = (row_rect.right - 20, row_rect.centery)

                pygame.draw.rect(
                    modal_surface,
                    (150, 150, 150),
                    (key_rect.x, key_rect.y + 3, key_rect.width, key_rect.height),
                    border_radius=6,
                )

                pygame.draw.rect(modal_surface, C_KEY_BG, key_rect, border_radius=6)

                key_txt_rect = key_surf.get_rect(center=key_rect.center)
                modal_surface.blit(key_surf, key_txt_rect)

        modal_surface.set_clip(None)

        if content_height > visible_height:
            scrollbar_height = (visible_height / content_height) * visible_height
            scroll_ratio = scroll_y / max_scroll
            scrollbar_y = list_start_y + (
                scroll_ratio * (visible_height - scrollbar_height)
            )

            scrollbar_rect = pygame.Rect(
                modal_width - 15, scrollbar_y, 6, scrollbar_height
            )
            pygame.draw.rect(
                modal_surface, (100, 100, 100), scrollbar_rect, border_radius=3
            )

        main_screen.blit(modal_surface, (modal_x, modal_y))
        pygame.display.flip()


def settings(main_screen, song_hashmap, state, current_status):
    settings_width, settings_height = 800, 600
    settings_surf = pygame.Surface((settings_width, settings_height), pygame.SRCALPHA)

    running_settings = True
    title = "MENU"

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_BORDER = (98, 114, 164)
    C_TEXT = (248, 248, 242)
    C_TEXT_DIM = (180, 180, 180)
    C_SELECTED_BG = (68, 71, 90)
    C_ACCENT = (139, 233, 253)

    if os.path.exists(bg_path):
        bg_img = pygame.image.load(bg_path).convert()
        bg_img = pygame.transform.scale(
            bg_img, (main_screen.get_width(), main_screen.get_height())
        )
        bg_img.set_alpha(100)
    else:
        bg_img = None

    menu_settings = [
        "Resume",
        "Play a song",
        "Skip the current song",
        "Add a song to the playlist",
        "Delete a song",
        "Songs library",
        "Controls",
        "Exit",
    ]

    button_height = 45
    button_width = 500
    menu_start_y = 120

    selected_item_index = 0
    while running_settings:
        mx, my = pygame.mouse.get_pos()
        modal_x = (main_screen.get_width() - settings_width) // 2
        modal_y = (main_screen.get_height() - settings_height) // 2
        rel_mx = mx - modal_x
        rel_my = my - modal_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_settings = False

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_f):
                    running_settings = False
                if event.key == pygame.K_UP:
                    selected_item_index = (selected_item_index - 1) % len(menu_settings)
                if event.key == pygame.K_DOWN:
                    selected_item_index = (selected_item_index + 1) % len(menu_settings)
                if event.key == pygame.K_RETURN:
                    if menu_settings[selected_item_index] == "Resume":
                        running_settings = False
                    if menu_settings[selected_item_index] == "Play a song":
                        find_song_window(
                            main_screen, song_hashmap, state, current_status
                        )
                        # running_settings = False
                    if menu_settings[selected_item_index] == "Skip the current song":
                        skip_the_current_song(song_hashmap, state, current_status)
                        running_settings = False
                    if (
                        menu_settings[selected_item_index]
                        == "Add a song to the playlist"
                    ):
                        add_song_to_playlist(main_screen, song_hashmap, state)
                        # running_settings = False

                    if menu_settings[selected_item_index] == "Songs library":
                        show_songs_library(main_screen, song_hashmap, state)
                    if menu_settings[selected_item_index] == "Controls":
                        show_controls(main_screen)
                    if menu_settings[selected_item_index] == "Delete a song":
                        delete_a_song(main_screen, song_hashmap, state)
                    if menu_settings[selected_item_index] == "Exit":
                        running_settings = False
                        return -1

        if bg_img:
            main_screen.blit(bg_img, (0, 0))
        else:
            main_screen.fill((0, 0, 0))

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        settings_surf.fill((0, 0, 0, 0))

        shadow_rect = pygame.Rect(15, 15, settings_width, settings_height)
        pygame.draw.rect(settings_surf, (0, 0, 0, 100), shadow_rect, border_radius=20)

        main_rect = pygame.Rect(0, 0, settings_width, settings_height)
        pygame.draw.rect(settings_surf, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(settings_surf, C_BORDER, main_rect, 2, border_radius=20)

        title_text = ui.title_font.render(title, True, C_TEXT)
        title_rect = title_text.get_rect(center=(settings_width // 2, 60))
        settings_surf.blit(title_text, title_rect)

        pygame.draw.line(
            settings_surf, C_BORDER, (150, 100), (settings_width - 150, 100), 1
        )

        for i, item in enumerate(menu_settings):
            y_pos = menu_start_y + (i * (button_height + 10))
            btn_rect = pygame.Rect(
                (settings_width - button_width) // 2, y_pos, button_width, button_height
            )

            is_selected = i == selected_item_index

            if is_selected:
                bg_color = C_SELECTED_BG
                text_color = C_ACCENT
                border_color = C_ACCENT
                border_width = 2
            else:
                bg_color = C_MODAL_BG
                text_color = C_TEXT_DIM
                border_color = (60, 60, 70)
                border_width = 1

            pygame.draw.rect(settings_surf, bg_color, btn_rect, border_radius=10)
            pygame.draw.rect(
                settings_surf, border_color, btn_rect, border_width, border_radius=10
            )

            item_text = ui.my_font.render(item, True, text_color)
            item_rect = item_text.get_rect(center=btn_rect.center)
            settings_surf.blit(item_text, item_rect)

        main_screen.blit(settings_surf, (modal_x, modal_y))
        pygame.display.flip()


def find_song_window(main_screen, song_hashmap, state, current_status):
    modal_width, modal_height = 800, 450
    modal_surface = pygame.Surface((modal_width, modal_height), pygame.SRCALPHA)

    input_box_width = 600
    input_box_height = 55
    input_box_rect = pygame.Rect(
        (modal_width - input_box_width) // 2, 120, input_box_width, input_box_height
    )
    user_text = ""

    running_settings = True

    C_OVERLAY = (0, 0, 0, 180)
    C_MODAL_BG = (40, 42, 54)
    C_INPUT_BG = (68, 71, 90)
    C_TEXT = (248, 248, 242)
    C_ACCENT = (139, 233, 253)
    C_BORDER = (98, 114, 164)

    cursor_visible = True
    last_blink_time = time.time()

    def thread_worker(text_to_download):
        nonlocal running_settings, state
        song_key = text_to_download.strip().replace(" ", "_")
        search_lower = text_to_download.lower()

        found_entry = None
        if song_key in song_hashmap:
            found_entry = song_hashmap[song_key]

        if not found_entry:
            for key, val in song_hashmap.items():
                if isinstance(val, tuple) and len(val) >= 2:
                    path, title = val
                    if (
                        search_lower in title.lower()
                        and "vocal" not in search_lower
                        and "vocal" not in title.lower()
                    ):
                        found_entry = val
                        break

        if found_entry:
            current_status.text = f"Song found! Playing: {found_entry[1]}..."
            current_status.color = (80, 250, 123)

            full_path = found_entry[0]
            real_title = found_entry[1]

            process_song_files(full_path, real_title, state, current_status)
            state.next_song_data = (full_path, real_title)

            running_settings = False
            return

        current_status.color = (241, 250, 140)
        current_status.text = f"Downloading: {text_to_download}..."

        try:
            full_path, real_title = get_song_by_string_youtube(text_to_download, state)
            if full_path and real_title:
                song_hashmap[song_key] = (full_path, real_title)

                process_song_files(full_path, real_title, state, current_status)

                state.next_song_data = (full_path, real_title)

                current_status.text = "Success!"
                current_status.color = (80, 250, 123)
                running_settings = False
            else:
                current_status.text = "[ERROR]: Download failed."
                current_status.color = (255, 85, 85)

        except Exception as e:
            current_status.text = f"Error: {e}"
            print(f"Worker Error: {e}")

    while running_settings:
        mx, my = pygame.mouse.get_pos()
        modal_x = (main_screen.get_width() - modal_width) // 2
        modal_y = (main_screen.get_height() - modal_height) // 2
        rel_mx = mx - modal_x
        rel_my = my - modal_y

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running_settings = False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running_settings = False
                    user_text = ""
                    break

                elif event.key == pygame.K_RETURN:
                    if user_text.strip() != "":
                        download_thread = threading.Thread(
                            target=thread_worker,
                            args=(user_text,),
                        )
                        download_thread.start()
                        user_text = ""

                elif event.key == pygame.K_BACKSPACE:
                    user_text = user_text[:-1]

                else:
                    user_text += event.unicode

        if time.time() - last_blink_time > 0.5:
            cursor_visible = not cursor_visible
            last_blink_time = time.time()

        overlay = pygame.Surface(main_screen.get_size(), pygame.SRCALPHA)
        overlay.fill(C_OVERLAY)
        main_screen.blit(overlay, (0, 0))

        modal_surface.fill((0, 0, 0, 0))

        shadow_rect = pygame.Rect(15, 15, modal_width, modal_height)
        pygame.draw.rect(modal_surface, (0, 0, 0, 100), shadow_rect, border_radius=20)

        main_rect = pygame.Rect(0, 0, modal_width, modal_height)
        pygame.draw.rect(modal_surface, C_MODAL_BG, main_rect, border_radius=20)
        pygame.draw.rect(modal_surface, C_BORDER, main_rect, 2, border_radius=20)

        title_surf = ui.title_font.render("PLAY / DOWNLOAD SONG", True, C_TEXT)
        title_rect = title_surf.get_rect(center=(modal_width // 2, 50))
        modal_surface.blit(title_surf, title_rect)

        pygame.draw.rect(modal_surface, C_INPUT_BG, input_box_rect, border_radius=10)
        pygame.draw.rect(modal_surface, C_BORDER, input_box_rect, 2, border_radius=10)

        label_surf = ui.my_font.render(
            "Type a song name or URL:", True, (150, 150, 150)
        )
        modal_surface.blit(label_surf, (input_box_rect.x, input_box_rect.y - 30))

        txt_surf = ui.my_font.render(user_text, True, C_TEXT)
        modal_surface.blit(txt_surf, (input_box_rect.x + 15, input_box_rect.y + 12))

        if cursor_visible:
            cursor_x = input_box_rect.x + 15 + txt_surf.get_width() + 2
            pygame.draw.line(
                modal_surface,
                C_ACCENT,
                (cursor_x, input_box_rect.y + 12),
                (cursor_x, input_box_rect.y + 42),
                2,
            )

        status_box_rect = pygame.Rect(
            input_box_rect.x, input_box_rect.bottom + 40, input_box_width, 100
        )
        pygame.draw.rect(modal_surface, (50, 50, 60), status_box_rect, border_radius=10)

        status_label = ui.my_font.render("Status:", True, (180, 180, 180))
        modal_surface.blit(
            status_label, (status_box_rect.x + 15, status_box_rect.y + 10)
        )

        status_text_surf = ui.my_font.render(
            current_status.text, True, current_status.color
        )
        status_rect = status_text_surf.get_rect(
            midleft=(status_box_rect.x + 15, status_box_rect.centery + 10)
        )
        modal_surface.blit(status_text_surf, status_rect)

        main_screen.blit(modal_surface, (modal_x, modal_y))
        pygame.display.flip()


def poll_events(screen, state, song_file_hashmap, current_status):
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state.running = False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_n:
                state.effect_noise_gate = not state.effect_noise_gate
            if event.key == pygame.K_d:
                state.effect_distortion = not state.effect_distortion
            if event.key == pygame.K_a:
                state.effect_alien = not state.effect_alien
            if event.key == pygame.K_p:
                state.effect_pan = not state.effect_pan
            if event.key == pygame.K_l:
                state.effect_low_pass = not state.effect_low_pass
            if event.key == pygame.K_h:
                state.effect_high_pass = not state.effect_high_pass
            if event.key == pygame.K_b:
                state.effect_bitcrusher = not state.effect_bitcrusher
            if event.key == pygame.K_v:
                state.effect_vibrato = not state.effect_vibrato
            if event.key == pygame.K_t:
                state.effect_tremolo = not state.effect_tremolo
            if event.key == pygame.K_o:
                state.effect_overdrive = not state.effect_overdrive
            if event.key == pygame.K_e:
                state.effect_echo = not state.effect_echo
            if event.key == pygame.K_UP:
                state.volume = min(100, state.volume + 10)
            if event.key == pygame.K_k:
                skip_the_current_song(song_file_hashmap, state, current_status)
            if event.key == pygame.K_DOWN:
                state.volume = max(0, state.volume - 10)
            if event.key == pygame.K_s:
                state.speed_rate += 1
                state.speed_rate %= 3

                if state.speed_rate == 0:
                    state.speed = 1.0
                elif state.speed_rate == 1:
                    state.speed = 0.8
                elif state.speed_rate == 2:
                    state.speed = 1.2

                global wav_file, audio_output_stream
                if wav_file:
                    audio_output_stream.stop_stream()
                    audio_output_stream.close()

                    audio_output_stream = p.open(
                        format=p.get_format_from_width(wav_file.getsampwidth()),
                        channels=wav_file.getnchannels(),
                        rate=int(wav_file.getframerate() * state.speed),
                        output=True,
                    )

            if event.key == pygame.K_q:
                state.running = False
                break

            if event.key == pygame.K_ESCAPE:
                result = settings(screen, song_file_hashmap, state, current_status)
                if result == -1:
                    state.running = False
                    break


def apply_effects(audio_data, state):
    if state.effect_noise_gate:
        audio_data = effects.noise_gate(audio_data)
    if state.effect_distortion:
        audio_data = effects.distortion(audio_data)
    if state.effect_low_pass:
        audio_data = effects.low_pass(audio_data)
    if state.effect_bitcrusher:
        audio_data = effects.bitcrusher(audio_data)
    if state.effect_high_pass:
        audio_data = effects.high_pass_filter(audio_data)
    if state.effect_overdrive:
        audio_data = effects.overdrive(audio_data)

    return audio_data


def set_background(bg_path):
    if os.path.exists(bg_path):
        fade_surface = pygame.image.load(bg_path).convert()
        fade_surface = pygame.transform.scale(
            fade_surface, (constants.WIDTH, constants.HEIGHT)
        )
    else:
        fade_surface = pygame.Surface((constants.WIDTH, constants.HEIGHT))
        fade_surface.fill((0, 0, 0))
        fade_surface = fade_surface.convert()
    fade_surface.set_alpha(100)

    return fade_surface


def show_lyrics(screen, state, current_time_sec, shake_x, shake_y):
    lyric_font = pygame.font.SysFont("Arial", 40, bold=True)
    lyric_text = get_current_lyric(state.current_lyrics, current_time_sec)

    center_x = constants.WIDTH // 2 + shake_x
    center_y = constants.HEIGHT - 100 + shake_y

    # sh_surf = lyric_font.render(lyric_text, True, (0, 0, 0))
    # sh_rect = sh_surf.get_rect(center=(center_x + 10, center_y + 10))
    # screen.blit(sh_surf, sh_rect)

    txt_surf = lyric_font.render(lyric_text, True, (255, 255, 200))
    txt_rect = txt_surf.get_rect(center=(center_x, center_y))
    screen.blit(txt_surf, txt_rect)


def cleanup(audio_input_stream, audio_output_stream, wav_file, vocal_wav_file, p):
    if audio_input_stream:
        audio_input_stream.stop_stream()
        audio_input_stream.close()
    if audio_output_stream:
        audio_output_stream.stop_stream()
        audio_output_stream.close()
    if wav_file:
        wav_file.close()
    if vocal_wav_file:
        vocal_wav_file.close()
    p.terminate()
    pygame.quit()


def main():
    global wav_file, audio_output_stream, vocal_wav_file

    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    # screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    # clock = pygame.time.Clock()
    pygame.display.set_caption("Music Visualizer")

    state = AppState()
    song_file_hashmap = init_song_file_hashmap()
    current_status = StatusObj()
    max_kick = 0
    state.next_song_data = None

    # lyric_font = pygame.font.SysFont("Arial", 40, bold=True)
    fade_surface = set_background(bg_path)

    while state.running:
        # EVENTS
        # clock.tick()

        poll_events(screen, state, song_file_hashmap, current_status)

        if state.next_song_data:
            path, name = state.next_song_data
            state.next_song_data = None
            play_song(path, state, name)
        if (
            not wav_file
            and len(state.playlist) > 0
            and not state.downloading_playlist_item
        ):
            # next_idx = state.current_song_index + 1
            next_song = state.playlist[0]
            state.downloading_playlist_item = True
            download_thread = threading.Thread(
                target=threads.worker_thread,
                args=(next_song, song_file_hashmap, state, current_status),
            )
            download_thread.start()
            state.playlist.pop(0)

        has_audio = False
        current_time_sec = 0
        current_channels = wav_file.getnchannels() if wav_file else 2

        audio_data = np.zeros(constants.CHUNK_SIZE * current_channels, dtype=np.int16)

        if wav_file:
            try:
                framerate = wav_file.getframerate()
                current_time_sec = wav_file.tell() / framerate
                data = wav_file.readframes(constants.CHUNK_SIZE)
                if data and len(data) > 0:
                    read_data = np.frombuffer(data, dtype=np.int16)
                    audio_data[: len(read_data)] = read_data
                    has_audio = True
                else:
                    state.song_name = ""
                    state.current_lyrics = ""
                    wav_file = None
                    # has_audio = False
                    if vocal_wav_file:
                        vocal_wav_file.close()
                        vocal_wav_file = None
            except Exception:
                pass

        vocal_data_np = None
        if vocal_wav_file and has_audio:
            try:
                v_data = vocal_wav_file.readframes(constants.CHUNK_SIZE)
                if v_data:
                    v_read = np.frombuffer(v_data, dtype=np.int16)
                    vocal_data_np = np.zeros(len(v_read), dtype=np.int16)
                    vocal_data_np[:] = v_read
            except Exception:
                pass

        audio_data = apply_effects(audio_data, state)
        try:
            vocal_data_np = apply_effects(vocal_data_np, state)
        except Exception:
            pass
        framerate = wav_file.getframerate() if wav_file else 44100

        # Pan
        if state.effect_pan and current_channels == 2:
            pan_speed = 0.5
            state.pan_phase += (constants.CHUNK_SIZE / framerate) * pan_speed
            pan_pos = np.sin(2 * np.pi * state.pan_phase)
            vol_L = np.clip((1.0 - pan_pos), 0, 1)
            vol_R = np.clip((1.0 + pan_pos), 0, 1)

            if len(audio_data) % 2 == 0:
                stereo_data = audio_data.reshape(-1, 2)
                stereo_data[:, 0] = (stereo_data[:, 0] * vol_L).astype(np.int16)
                stereo_data[:, 1] = (stereo_data[:, 1] * vol_R).astype(np.int16)
                audio_data = stereo_data.flatten()

        # Vibrato
        if state.effect_vibrato:
            audio_data = effects.vibrato(audio_data, state.vibrato_phase)
            vocal_data_np = effects.vibrato(vocal_data_np, state.vibrato_phase)
            state.vibrato_phase += constants.CHUNK_SIZE / framerate

        # Tremolo
        if state.effect_tremolo:
            audio_data = effects.tremolo(audio_data, state.pan_phase)
            vocal_data_np = effects.tremolo(vocal_data_np, state.pan_phase)
            state.pan_phase += (constants.CHUNK_SIZE / framerate) * 5.0

        # Alien
        if state.effect_alien:
            audio_data = effects.alien(audio_data, state.alien_phase)
            vocal_data_np = effects.alien(vocal_data_np, state.alien_phase)
            state.alien_phase += len(audio_data)

        if len(state.echo_buffer) == state.echo_buffer.maxlen:
            delayed_chunk = state.echo_buffer[0]
        else:
            delayed_chunk = None

        if state.effect_echo:
            audio_data = effects.echo(audio_data, delayed_chunk)

        state.echo_buffer.append(audio_data.copy())

        audio_data = audio_data * (state.volume / 100)
        audio_data = audio_data.astype(np.int16)

        if has_audio and audio_output_stream:
            try:
                audio_output_stream.write(audio_data.tobytes())
            except Exception:
                pass

        if current_channels > 1:
            fft_input = audio_data[::current_channels]
        else:
            fft_input = audio_data

        fft_data = np.fft.fft(fft_input)
        magnitude = np.abs(fft_data) / 50000.0

        raw_kick = np.mean(magnitude[1:5])
        raw_snare = np.mean(magnitude[5:8])
        raw_hihat = np.mean(magnitude[116:232])

        shake_x = 0
        shake_y = 0

        if max_kick < raw_kick:
            max_kick = raw_kick

        # print(max_kick)
        if raw_kick > 100:
            intensity = int((raw_kick - 100) / 3)

            intensity = min(intensity, 30)

            if intensity > 0:
                shake_x = random.randint(-intensity, intensity)
                shake_y = random.randint(-intensity, intensity)

        bg_x = 0 + shake_x
        bg_y = 0 + shake_y

        if vocal_data_np is not None:
            fft_input_vocal = (
                vocal_data_np[::current_channels]
                if current_channels > 1
                else vocal_data_np
            )
            fft_data_vocal = np.fft.fft(fft_input_vocal)
            magnitude_vocal = np.abs(fft_data_vocal) / 50000.0
            raw_vocals = np.mean(magnitude_vocal[10:60]) * 5.0
            raw_vocals = raw_vocals * (state.volume / 100)
        else:
            raw_vocals_est = np.mean(magnitude[12:70])
            background_noise = (raw_kick * 0.4) + (raw_hihat * 0.2) + (raw_snare * 1.5)
            raw_vocals = (
                max(0, raw_vocals_est - background_noise) * 1.5 * (state.volume / 100)
            )

        # Smoothing
        ui.val_kick = ui.val_kick * constants.SMOOTHING + raw_kick * (
            1.0 - constants.SMOOTHING
        )
        ui.val_snare = ui.val_snare * constants.SMOOTHING + raw_snare * (
            1.0 - constants.SMOOTHING
        )
        ui.val_hihat = ui.val_hihat * constants.SMOOTHING + raw_hihat * (
            1.0 - constants.SMOOTHING
        )
        ui.val_vocals = ui.val_vocals * constants.SMOOTHING + raw_vocals * (
            1.0 - constants.SMOOTHING
        )

        screen.blit(fade_surface, (bg_x, bg_y))

        sens = 0.04
        r = (
            30
            + (
                200 * ui.val_kick
                + 50 * ui.val_snare
                + 50 * ui.val_hihat
                + 50 * ui.val_vocals
            )
            * sens
        )
        g = (
            30
            + (
                50 * ui.val_kick
                + 255 * ui.val_snare
                + 50 * ui.val_hihat
                + 50 * ui.val_vocals
            )
            * sens
        )
        b = (
            30
            + (
                50 * ui.val_kick
                + 50 * ui.val_snare
                + 255 * ui.val_hihat
                + 50 * ui.val_vocals
            )
            * sens
        )

        waveform_color = (
            max(0, min(255, int(r))),
            max(0, min(255, int(g))),
            max(0, min(255, int(b))),
        )

        draw_data = fft_input

        points = []
        step = 5
        waveform_height_scale = constants.HEIGHT / 4
        waveform_y_offset = constants.HEIGHT * 3 / 4

        for i in range(0, len(draw_data), step):
            sample_value = draw_data[i]
            scaled_y = (sample_value / 32768.0) * (waveform_height_scale)
            x = int((i / len(draw_data)) * constants.WIDTH)
            y = int(waveform_y_offset - scaled_y)
            points.append((x + shake_x, y + shake_y))

        if len(points) > 1:
            pygame.draw.lines(screen, waveform_color, False, points, 2)

        ui.show_ui_circles(shake_x * 3, shake_y * 3)
        ui.show_ui_effects(state, shake_x * 4, shake_y * 4)

        if state.current_lyrics:
            show_lyrics(screen, state, current_time_sec, shake_x, shake_y)

        pygame.display.flip()

    cleanup(audio_input_stream, audio_output_stream, wav_file, vocal_wav_file, p)


if __name__ == "__main__":
    main()
