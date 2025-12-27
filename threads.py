from music import process_song_files, get_song_by_string_youtube


def worker_thread(next_song, song_file_hashmap, state, current_status):
    try:
        song_key = next_song.strip().replace(" ", "_")
        search_lower = next_song.lower()

        found_entry = None
        if song_key in song_file_hashmap:
            found_entry = song_file_hashmap[song_key]
        if not found_entry:
            for key, val in song_file_hashmap.items():
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
            current_status.color = (0, 255, 255)

            full_path = found_entry[0]
            real_title = found_entry[1]

            process_song_files(full_path, real_title, state, current_status)
            state.next_song_data = (full_path, real_title)
            state.downloading_playlist_item = False
            return

        current_status.color = (255, 255, 0)
        current_status.text = f"Downloading: {next_song}..."

        try:
            full_path, real_title = get_song_by_string_youtube(next_song, state)
            if full_path and real_title:
                song_file_hashmap[song_key] = (full_path, real_title)

                process_song_files(full_path, real_title, state, current_status)

                state.next_song_data = (full_path, real_title)

                current_status.text = "Success!"
                current_status.color = (0, 255, 0)
                # running_settings = False
            else:
                current_status.text = "[ERROR]: Download failed."
                current_status.color = (255, 0, 0)

        except Exception as e:
            current_status.text = f"Error: {e}"
            print(f"Worker Error: {e}")
    finally:
        state.downloading_playlist_item = False
