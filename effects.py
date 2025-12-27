import numpy as np
from scipy.signal import butter, lfilter


def noise_gate(audio_data, threshold=500):
    audio_data = np.clip(audio_data * 2.0, -32767, 32767).astype(np.int16)
    audio_data[np.abs(audio_data) < threshold] = 0

    return audio_data


def distortion(audio_data):
    audio_data = np.clip(audio_data * 5.0, -32767, 32767).astype(np.int16)

    return audio_data


def overdrive(audio_data, gain=5.0):
    signal = audio_data / 32768.0

    saturated = np.tanh(signal * gain)
    output = saturated * 32767.0
    output = np.clip(output, -32768, 32767)

    return output.astype(np.int16)


def alien(audio_data, phase):
    freq_alien = 500
    t = np.arange(len(audio_data)) + phase
    carrier = np.sin(2 * np.pi * freq_alien * t / 44100)

    audio_data = (audio_data * carrier).astype(np.int16)

    return audio_data


def vibrato(audio_data, phase, rate=44100):
    vib_freq = 5.0
    vib_depth = 0.002

    try:
        n_samples = len(audio_data)
        t = (np.arange(n_samples) / rate) + phase
        delay_samples = (vib_depth * rate) * (1 + np.sin(2 * np.pi * vib_freq * t))

        read_indices = np.arange(n_samples) - delay_samples
        read_indices = np.clip(read_indices, 0, n_samples - 1)

        idx_floor = read_indices.astype(int)
        idx_ceil = np.clip(idx_floor + 1, 0, n_samples - 1)
        alpha = read_indices - idx_floor
        output = (1 - alpha) * audio_data[idx_floor] + alpha * audio_data[idx_ceil]
        return output.astype(np.int16)
    except Exception:
        # print(f"[ERROR] Vibrato: {e}")
        return None


def low_pass(audio_data, cutoff=1000, fs=44100, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    # Get the filter coefficients
    b, a = butter(order, normal_cutoff, btype="low", analog=False)
    y = lfilter(b, a, audio_data)
    return y.astype(np.int16)


def high_pass_filter(data, cutoff=1000, fs=44100, order=5):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    # Get the filter coefficients
    b, a = butter(order, normal_cutoff, btype="high", analog=False)
    y = lfilter(b, a, data)
    return y.astype(np.int16)


def bitcrusher(audio_data, bit_depth=8, sample_rate_reduction=4):
    reduction_factor = 10
    audio_float = audio_data.astype(np.float32)
    max_val = np.iinfo(np.int16).max

    num_levels = 2 ** (bit_depth - 1) - 1
    if bit_depth == 1:
        num_levels = 1

    step_size = max_val / num_levels
    quantized_audio = np.round(audio_float / step_size) * step_size

    quantized_audio = np.clip(quantized_audio, -max_val, max_val)

    indices = np.arange(len(quantized_audio))

    base_indices = indices - (indices % reduction_factor)

    return quantized_audio[base_indices].astype(np.int16)


def tremolo(audio_data, phase, speed=10.0, framerate=44100):
    try:
        t = np.arange(len(audio_data)) / framerate
        modulator = (np.sin(2 * np.pi * speed * t + phase) + 1) / 2
        processed_data = audio_data * modulator

        return processed_data.astype(np.int16)
    except Exception:
        return None


def echo(current_chunk, delayed_chunk, decay=0.6):
    if delayed_chunk is None:
        return current_chunk

    mixed = current_chunk.astype(np.float32) + (
        delayed_chunk.astype(np.float32) * decay
    )

    mixed = np.clip(mixed, -32768, 32767)

    return mixed.astype(np.int16)
