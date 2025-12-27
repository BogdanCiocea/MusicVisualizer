import librosa
import numpy as np
import soundfile as sf
import os


def generate_vocal_track(full_path):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        vocals_dir = os.path.join(base_dir, "vocals")

        if not os.path.exists(vocals_dir):
            os.makedirs(vocals_dir)

        y, sr = librosa.load(full_path, sr=None)
        S_full, phase = librosa.magphase(librosa.stft(y))

        S_filter = librosa.decompose.nn_filter(
            S_full,
            aggregate=np.median,
            metric="cosine",
            width=int(librosa.time_to_frames(2, sr=sr)),
        )
        S_filter = np.minimum(S_full, S_filter)

        margin_v = 2
        power = 5
        mask_v = librosa.util.softmask(
            S_full - S_filter, margin_v * S_filter, power=power
        )
        S_foreground = mask_v * S_full

        new_y = librosa.istft(S_foreground * phase)

        max_val = np.max(np.abs(new_y))
        if max_val > 0:
            new_y = new_y / max_val

        filename = os.path.basename(full_path)
        filename_no_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(vocals_dir, f"{filename_no_ext}_VOCALS.wav")

        sf.write(output_path, new_y, sr, subtype="PCM_16")

        return True

    except Exception as e:
        print(f"[ERROR] Vocal extract: {e}")
        return False


def get_vocal_path(song_full_path):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.basename(song_full_path)
    name_no_ext = os.path.splitext(filename)[0]
    return os.path.join(base_dir, "vocals", f"{name_no_ext}_VOCALS.wav")
