# yt

A tool using yt-dlp and ffmpeg to download videos. 


# How to use
[Download and install python here](https://www.python.org/downloads/)

Open a terminal and run
```
pip install git+https://github.com/hulla-bulla/yt.git
```

Then run 
```
playwright install
```

Then run ```yt``` in a terminal to use the app. 

```
yt --help          # view help
yt clips --help    # view help for specific command

# Download a bunch of clips with "rust" as the keyword from playlists and or channels
yt clips rust "https://www.youtube.com/watch?v=SodXi2t1mtE&pp=ygUJcnVzdCBoeXBl" "https://www.youtube.com/watch?v=NtYHC1KNGoc&t=16s&pp=ygUJcnVzdCBoeXBl" "https://www.youtube.com/@NoBoilerplate" "https://www.youtube.com/@serverlessjames" "https://www.youtube.com/@deno_land"
``` 




# Development

1. create venv & activate
2. `python setup.py develop`
3. type `yt` to test the tool 


# package for deploy
python setup.py sdist bdist_wheel

