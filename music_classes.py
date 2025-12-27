from collections import deque


class StatusObj:
    def __init__(self):
        self.text = "Write the song name"
        self.color = (255, 255, 255)


class PlaylistSong:
    def __init__(self, query):
        self.query = query
        self.ready = False
        self.path = None
        self.title = None
        self.failed = False


class AppState:
    def __init__(self):
        self.running = True

        self.effect_noise_gate = False
        self.effect_distortion = False
        self.effect_alien = False
        self.effect_pan = False
        self.effect_low_pass = False
        self.effect_high_pass = False
        self.effect_bitcrusher = False
        self.slowed = False
        self.effect_vibrato = False
        self.effect_tremolo = False
        self.effect_overdrive = False
        self.effect_echo = False

        self.downloading_playlist_item = False
        self.current_song_index = 0

        self.pan_phase = 0.0
        self.alien_phase = 0.0
        self.vibrato_phase = 0.0

        self.song_name = ""
        self.volume = 100
        self.speed = 1.0
        self.speed_rate = 0
        self.current_lyrics = []
        self.echo_buffer = deque(maxlen=20)
        self.next_song_data = ()
        self.playlist = []
        self.current_song_index = -1
        self.next_song_data = None
