# Music Visualizer

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge&logo=python)
![Status](https://img.shields.io/badge/Status-Active-green?style=for-the-badge)
![License](https://img.shields.io/badge/License-Apache_2.0-blue?style=for-the-badge)

> A powerful audio visualizer that analyzes sound spectrums in real-time, generating dynamic visual effects synchronized with your favorite music.

## Features

* **Spectrum Analysis:** Real-time visualization of audio frequencies.
* **Dynamic Effects:** Audio filters that change the sounds.
* **Synced Lyrics:** Automatically fetches and displays lyrics using `syncedlyrics`.
* **YouTube Support:** Stream and visualize audio directly from YouTube via `yt-dlp`.
* **High-Fidelity Audio:** Supports high-quality local file playback.

## Installation

### Must have pip installed:
#### Windows
```bash
py -m ensurepip --upgrade
```

#### Linux
```bash
python -m ensurepip --upgrade
```

### Dependencies

* pip install
```bash
pip install scipy
pip install numpy
pip install syncedlyrics
pip install pygame
pip install PyAudio
pip install Wave
pip install yt-dlp
pip install librosa
pip install soundfile
```

#### Other things to install
This project requires **FFmpeg** to handle audio download.
#### Windows
1. Download the executable from the [official website](https://www.ffmpeg.org/download.html).
2. Extract the files and add the `bin` folder to your System PATH.

#### Linux
Run the command for your distribution:

```bash
# Debian / Ubuntu
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

Ensure you have **Python 3.x** installed on your system.

### Clone the repository
```bash
git clone git@github.com:BogdanCiocea/MusicVisualizer.git
cd MusicVisualizer
```

## Run application
```bash
python3 music.py
```
