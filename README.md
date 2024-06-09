# yt

A helper tool for downloading, converting, editing youtube videos.

## Features

### 🎥 **YouTube**

* **📥 Download YouTube Videos**: Download videos from YouTube in the best quality available.
* **🎵 Download Audio Only**: Extract audio from YouTube videos and save them as high-quality MP3 files.
* **✂️ Clip Downloading**: Download specific clips from YouTube videos based on search queries within video transcripts. The search can be from a channel, playlist, or video.
* **🔄 Automatic VP9 to H.264 Conversion**: When downloading videos from YouTube, not all of them can be edited in Premiere Pro and other video editing tools. YT automatically converts videos encoded with VP9 to H.264, ensuring compatibility with editing software like Premiere Pro.


### 🖥️ **OBS**
* **🔄 Batch Remuxing**: Remux High Quality MKV OBS recordings with lossless audio or other video files, splitting audio tracks into separate WAV files and copying the video data (no conversion) to MP4.

### 📄 **Google Docs**
* **📝 Google Docs Integration**: Parse comments and calculate script length from Google Docs exported text files.

## 🚀 Installation

1. 🐍 [Download and install Python here](https://www.python.org/downloads/)

2. 💻 Open a terminal and run:

    ```sh
    pip install git+https://github.com/hulla-bulla/yt.git
    ```

3. Then run:

    ```sh
    playwright install
    ```

4. Done! 🎉

### 🔄 Update to a Newer Version


To update to the latest version, simply use:

```sh
pip install --upgrade git+https://github.com/hulla-bulla/yt.git
```

## 🎈 How to use

Then run ```yt``` in a 💻 terminal to use the app.

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

## 💩 Development

1. create venv & activate
2. `python setup.py develop`
3. type `yt` to test the tool

## package for deploy

python setup.py sdist bdist_wheel
