# yt

A tool using yt-dlp and ffmpeg to download videos.

## Features

* **Download YouTube Videos**: Download videos from YouTube in the best quality available.
* **Audio Extraction**: Extract audio from YouTube videos and save them as high-quality MP3 files.
* **Clip Downloading**: Download specific clips from YouTube videos based on search queries within video transcripts.
* **VP9 to H.264 Conversion**: Automatically convert videos encoded with VP9 to H.264, ensuring compatibility with editing software like Premiere Pro.
* **Batch Remuxing**: Remux OBS recordings or other video files, splitting audio tracks into separate WAV files and converting the video to MP4.
* **Google Docs Integration**: Parse comments and calculate script length from Google Docs exported text files.


## Install

1. [Download and install python here](https://www.python.org/downloads/)


2. Open a terminal and run

```sh
pip install git+https://github.com/hulla-bulla/yt.git
```

3. Then run

```sh
playwright install
```

4. Done!

### Update to a newer version

To update to the latest version, simply use:

```sh
pip install --upgrade git+https://github.com/hulla-bulla/yt.git
```

## How to use

Then run ```yt``` in a terminal to use the app.

> NOTE: the youtube link needs to be in quotes on windows like -> "<https://www.youtube.com/watch?v=FRpq7o1mKXY>" instead of <https://www.youtube.com/watch?v=FRpq7o1mKXY>

```sh
yt --help          # view help
yt clips --help    # view help for specific command

# download youtube video best quality available
yt video "https://www.youtube.com/watch?v=wA9MV-93K1I"

# download youtube audio best quality available
yt audio "https://www.youtube.com/watch?v=wA9MV-93K1I"

# Download a bunch of clips with "rust" as the keyword from playlists and or channels
yt clips rust "https://www.youtube.com/watch?v=SodXi2t1mtE&pp=ygUJcnVzdCBoeXBl" "https://www.youtube.com/watch?v=NtYHC1KNGoc&t=16s&pp=ygUJcnVzdCBoeXBl" "https://www.youtube.com/@NoBoilerplate"
```

## Development

1. create venv & activate
2. `python setup.py develop`
3. type `yt` to test the tool

## package for deploy

python setup.py sdist bdist_wheel
