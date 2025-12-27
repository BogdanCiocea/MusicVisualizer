import syncedlyrics
import os


def get_lyric_path(song_full_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    lyrics_dir = os.path.join(base_dir, "lyrics")

    if not os.path.exists(lyrics_dir):
        os.makedirs(lyrics_dir)

    filename = os.path.basename(song_full_path)
    name_no_ext = os.path.splitext(filename)[0]
    return os.path.join(lyrics_dir, f"{name_no_ext}.lrc")


def download_lyrics(song_name, save_path):
    try:
        print(f"--- [Lyrics] Searching lyrics for: {song_name} ---")
        lrc_content = syncedlyrics.search(song_name)

        if lrc_content:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(lrc_content)
            print(f"--- [Lyrics] Saved at: {save_path} ---")
            return True
        else:
            print("--- [Lyrics] Didn't find any lyrics. Creating a dummy ---")
            with open(save_path, "w", encoding="utf-8") as f:
                f.write("")
            return False
    except Exception:
        return False


def parse_lrc(lrc_path):
    lyrics_data = []
    if not os.path.exists(lrc_path):
        return []

    try:
        with open(lrc_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("[") and "]" in line:
                    time_part, text_part = line.split("]", 1)
                    time_part = time_part.replace("[", "")
                    try:
                        minutes, seconds = time_part.split(":")
                        total_seconds = float(minutes) * 60 + float(seconds)
                        lyrics_data.append((total_seconds, text_part.strip()))
                    except ValueError:
                        pass
    except Exception:
        pass
    return lyrics_data


def get_current_lyric(lyrics_data, current_time):
    current_line = ""
    for timestamp, text in lyrics_data:
        if timestamp <= current_time:
            current_line = text
        else:
            break
    return current_line
