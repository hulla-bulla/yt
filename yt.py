from pathlib import Path
from time import sleep, time
import click
from tqdm import tqdm
import yt_dlp
from pprint import pprint
from datetime import datetime, timedelta
from selectolax.parser import HTMLParser

import urllib.parse
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from threading import Thread

import subprocess
import sys
from yt_dlp.utils import download_range_func
from playwright.sync_api import sync_playwright
from modules import google_docs
import json

try:
    import imageio_ffmpeg as ffmpeg_lib
except ImportError:
    ffmpeg_lib = None


def _check_ffmpeg_installed():
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def convert_range_to_tuple(range_str: str) -> tuple[float, float]:
    if len(range_str) != 11:
        raise ValueError("Range should be in format 00:00-00:00")

    data = [int(y) for x in range_str.split("-") for y in x.split(":")]

    st = timedelta(minutes=data[0], seconds=data[1]).total_seconds()
    et = timedelta(minutes=data[2], seconds=data[3]).total_seconds()

    return st, et


@click.group()
def cli():
    pass


@cli.group(invoke_without_command=True)
@click.pass_context
def doc(ctx):
    if ctx.invoked_subcommand is None:
        # click.echo('I was invoked without subcommand')
        pass
    else:
        # click.echo(f"I am about to invoke {ctx.invoked_subcommand}")
        pass


@doc.command(name="default")
@click.argument(
    "path",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
)
def doc_default(path: Path):
    google_docs.parse_comments(path)
    google_docs.length(path)


@doc.command(name="comments")
@click.argument(
    "path",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
)
@click.option(
    "-d", "--delimiter", type=str, default="#edit ", help="What to split comments with"
)
def doc_comments(path: Path, delimiter):
    google_docs.parse_comments(path, delimiter=delimiter)


@doc.command(name="length")
@click.argument(
    "path",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
)
@click.option(
    "-w",
    "--words-per-minute",
    "wpm",
    type=int,
    default=160,
    help="How many words per minute to calculate length of script.",
)
@click.option(
    "-d",
    "--delimiter",
    type=str,
    default="#edit ",
    help="What to remove comments with, to exclude them from the calculation",
)
def doc_length(path: Path, wpm, delimiter):
    google_docs.length(path, words_per_minute=wpm, delimiter=delimiter)


@cli.command()
@click.argument("urls", type=str, nargs=-1, required=True)
@click.option(
    "--download-folder",
    type=click.Path(
        exists=True,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=Path.cwd(),
    help="Folder to save the downloaded audio files.",
)
@click.option(
    "--workers",
    type=int,
    default=4,
    help="Number of worker threads to use for downloading.",
)
def audio(urls: tuple, download_folder: Path, workers: int):
    """
    Downloads YouTube videos and converts them to MP3 audio files.

    URLS: YouTube video URLs (Multiple).
    """
    yt_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "320",
            }
        ],
        "outtmpl": str(download_folder / "%(title)s.%(ext)s"),
    }

    if not download_folder.exists():
        download_folder.mkdir(parents=True)

    def download_audio(url):
        dlp = yt_dlp.YoutubeDL(yt_opts)
        click.echo(f"Downloading audio from {url}")
        dlp.download([url])
        click.echo(f"Finished downloading audio from {url}")

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(download_audio, url) for url in urls]
        for future in as_completed(futures):
            future.result()

    click.echo("All downloads are complete.")



def download_video(
    url: str, range_str: str | None = None, download_folder: Path | None = None
) -> Path:
    yt_opts = {
        "verbose": False,
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
        "merge_output_format": "mp4",
    }

    if range_str:
        start_time, end_time = convert_range_to_tuple(range_str)
        start_str = f"[{int(start_time // 60):02d}-{int(start_time % 60):02d}]"
        end_str = f"[{int(end_time // 60):02d}-{int(end_time % 60):02d}]"
        suffix = f"{start_str}-{end_str}"
    else:
        suffix = ""

    if download_folder:
        yt_opts["outtmpl"] = f"{download_folder}/%(title)s_{suffix}.%(ext)s"
    else:
        yt_opts["outtmpl"] = f"%(title)s_{suffix}.%(ext)s"

    if range_str:
        yt_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(start_time, end_time)]
        )
        yt_opts["force_keyframes_at_cuts"] = True

    dlp = yt_dlp.YoutubeDL(yt_opts)
    dlp.download(url)

    # Get the file path of the downloaded file
    info_dict = dlp.extract_info(url, download=False)
    output_file = dlp.prepare_filename(info_dict)

    file_path = Path(output_file)

    if not file_path.exists() or not file_path.is_file():
        click.echo("Can find downloaded file")
        raise FileNotFoundError(file_path)

    return file_path


@cli.command()
@click.argument("url", type=str, required=True)
@click.option(
    "-r",
    "--range",
    "range_str",
    type=str,
    help="Download range in min:sec as on youtube. Example: 01:11-20:22.",
)
@click.option(
    "--download-folder",
    type=click.Path(
        exists=True,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=Path.cwd(),
)
def video(url: str, range_str: str, download_folder: Path):
    click.echo("Setting options for yt-dlp")
    click.echo(f"Downloading {url}")
    file_path: Path = download_video(url, range_str, download_folder=download_folder)

    click.echo(f"Downloaded to {file_path}")
    click.echo("Done")


@cli.command()
@click.argument("query", type=str, required=True)
@click.argument("urls", type=str, required=True, nargs=-1)
@click.option("--clip-length", type=int, default=10, help="Clip length in seconds")
@click.option(
    "--download-folder",
    type=click.Path(
        exists=True,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=Path.cwd(),
)
def clips(
    urls: tuple, query: str, clip_length: int, download_folder: Path, workers: int = 4
):
    """Finds and downloads clips with the query inside the transcript.

    QUERY What to search youtube for
    URLS youtube channel/playlist url (Multiple)

    """
    st = time()
    clip_queue = Queue()
    num_clips = 0

    # Define a function to download a single clip
    def download_single_clip():
        while True:
            clip = clip_queue.get()
            if clip is None:
                break
            youtube_id = clip["youtube_id"]
            start_time = clip["start_time"]
            range_str = f"{start_time}-"
            start_min, start_sec = map(int, start_time.split(":"))
            start_total_sec = start_min * 60 + start_sec
            end_total_sec = start_total_sec + clip_length
            end_min = end_total_sec // 60
            end_sec = end_total_sec % 60
            end_time = f"{end_min:02}:{end_sec:02}"
            range_str += end_time
            video_url = f"https://www.youtube.com/watch?v={youtube_id}"
            download_video(video_url, range_str, download_folder=download_folder)
            clip_queue.task_done()

    # Start the downloader threads
    threads = []
    for _ in range(workers):
        thread = Thread(target=download_single_clip)
        thread.start()
        threads.append(thread)

    # Collect clips and add them to the queue
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_get_clips, url, query) for url in urls]
        for future in as_completed(futures):
            new_clips = future.result()
            for clip in new_clips:
                clip_queue.put(clip)
                num_clips += 1
            print(f"{len(new_clips)} new clips")

    # Block until all clips are processed
    clip_queue.join()

    # Stop the downloader threads
    for _ in range(workers):
        clip_queue.put(None)
    for thread in threads:
        thread.join()

    time_elapsed = time() - st
    print(f"Num of clips      {num_clips}")
    print(f"Average time clip {time_elapsed/num_clips:.2f}s")
    print(f"Total time took   {time_elapsed:.2f}s")


def _get_clips(url, query, headless=True) -> list[dict[str, str]]:
    """Finds clips with the query inside the transcript.

    Returns starttime and youtubeid


    """

    url = urllib.parse.quote(url, safe="")
    query = urllib.parse.quote(query, safe="")
    url = f"https://ytks.app/search?url={url}&query={query}"

    try:
        print("getting clips..")

        browser = sync_playwright().start()
        page = browser.chromium.launch(headless=headless).new_page(
            # permissions=[
            #     "clipboard-write",
            #     "clipboard-read",
            # ]
            # not needed anymore
        )
        page.set_default_timeout(5000)
        print("Going to url")
        page.goto(url)

        print("Clicking on consent button")
        page.get_by_role("button", name="Consent").click()

        print("Waiting for things to load... Timeout 60s...", end="")
        grid = page.locator(".mantine-SimpleGrid-root")
        grid.wait_for(timeout=60000)
        print("Done!")

        print("Parsing cards")
        cards = grid.locator(".mantine-Paper-root").all()
        card = cards[0]

        data: list[dict[str, str]] = []
        for card in cards:
            # image link
            try:
                youtube_id = (
                    card.locator(".mantine-Image-imageWrapper img")
                    .first.get_attribute("src")
                    .split("/")[-2]
                )
            except Exception as e:
                print("Found no image link")
                raise e

            # start time
            try:
                start_time = (
                    card.locator(".mantine-Text-root")
                    .all()[1]
                    .text_content()
                    .split()[0]
                )
            except Exception as e:
                print("Found no starttime")
                raise e

            print(f"{start_time} \t {youtube_id}")
            data.append({"youtube_id": youtube_id, "start_time": start_time})
    finally:
        print("Cleanup")
        page.close()
        browser.stop()
    return data


def _get_audio_track_count(file_path: str) -> int:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "a",
                "-show_entries",
                "stream=index",
                "-of",
                "csv=p=0",
                file_path,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        audio_tracks = result.stdout.strip().split("\n")
        return len(audio_tracks)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error getting audio track count: {e.stderr}")
        return 0


@cli.command()
@click.argument(
    "file_paths",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
    required=True,
    nargs=-1,
)
@click.option(
    "--output-dir",
    "-o",
    "output_dir",
    type=click.Path(
        exists=False,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=Path.cwd(),
    help="Output dir, will be created if not exists.",
)
@click.option(
    "--delete",
    "-d",
    "delete",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Delete original file after successful convertion.",
)
@click.option(
    "--no-prompt",
    "no_prompt",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Shows no prompt for example when deleting original file. with --delete flag.",
)
def remux(file_paths: tuple[Path], output_dir: Path, delete: bool, no_prompt: bool):
    """
    Remuxes the given MKV to mp4 and multiple wav files.
    
    From OBS video file splitting audio tracks to separate WAV files and converting the video to MP4.

    FILE_PATH: Path to the video file to remux.
    """
    if not _check_ffmpeg_installed():
        click.echo("FFmpeg is not installed.")
        return

    output_dir.mkdir(exist_ok=True)

    for file_path in file_paths:
        audio_track_count = _get_audio_track_count(str(file_path))
        if audio_track_count == 0:
            click.echo("No audio tracks found in the file.")
            return

        filename = Path(file_path).stem
        output_base = f"{filename}_remux"

        filenames = [
            f"{output_dir/output_base}.mp4",
        ]
        filenames.extend(
            [f"{output_dir/output_base}_{i+1}.wav" for i in range(audio_track_count)]
        )

        commands = []
        for filename in filenames:
            if filename.endswith(".mp4"):
                commands.append(
                    f'ffmpeg -i "{file_path}" -c:v copy -c:a aac "{filename}"'
                )
            elif filename.endswith(".wav"):
                # get audio track from filename. Kinda reverse but doesn't matter. 0 based so -1 as well.
                audio_track = int(filename.split(".")[-2].split("_")[-1]) - 1
                commands.append(
                    f'ffmpeg -i "{file_path}" -map 0:a:{audio_track} -acodec pcm_s24le "{filename}"'
                )

        for cmd in commands:
            click.echo(f"Running command: {cmd}")
            subprocess.run(cmd, shell=True, check=True)
            click.echo("Done")

        if delete:
            click.echo(f"Delete? {file_path}")
            if no_prompt:
                file_path.unlink()
            elif (
                input("Do you want to delete the original file? y/n: ").strip().lower()
                == "y"
            ):
                file_path.unlink()


@cli.command()
@click.argument(
    "file_paths",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
    required=True,
    nargs=-1,
)
@click.option(
    "--output-dir",
    "-o",
    "output_dir",
    type=click.Path(
        exists=False,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
    default=Path.cwd(),
    help="Output dir, will be created if not exists.",
)
@click.option(
    "--delete",
    "-d",
    "delete",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Delete original file after successful convertion.",
)
@click.option(
    "--no-prompt",
    "no_prompt",
    type=bool,
    is_flag=True,
    show_default=True,
    default=False,
    help="Shows no prompt for example when deleting original file. with --delete flag.",
)
def auto(file_paths: tuple[Path], output_dir: Path, delete: bool, no_prompt: bool):
    """Using the auto-editor to automatically remove silence from video clips, even with multiple audiotracks and export to premiere.
    auto-editor.exe --keep-tracks-separate --edit "audio:threshold=10%%,stream=1" --margin 0.2sec --export premiere %1
    """
    raise NotImplementedError
    cmd = ""
    subprocess.run(cmd, shell=True, check=True)
    pass


@cli.command()
@click.argument(
    "file_path",
    type=click.Path(
        exists=True,
        file_okay=True,
        readable=True,
        path_type=Path,
    ),
    required=True,
)
def probe(file_path: Path):
    """probe video file using ffprobe and output to json"""
    data = _ffprobe(file_path)
    click.echo(json.dumps(data))


def _ffprobe(input_file: Path) -> dict:
    if not input_file.exists() or not input_file.is_file():
        raise TypeError("ffprobe Inputfile doesn't exist or is not file")

    cmd = (
        f'ffprobe -v error -show_format -show_streams -print_format json "{input_file}"'
    )
    p = subprocess.run(cmd, shell=True, capture_output=True)
    if not p.returncode == 0:
        print(p.stdout)
        print(p.stderr)
        raise ValueError(f"ffprobe Got other returncode: {p.returncode}")

    data: dict = json.loads(p.stdout)

    if not data:
        raise ValueError(f"ffprobe Got no data: {p.returncode}")
    return data


def _is_video_vp9(input_file: Path) -> bool:
    """
    Checks if the input video file is encoded with the VP9 codec.

    Args:
        input_file (Path): Path to the input video file.

    Returns:
        bool: True if the video codec is VP9, False otherwise.
    """
    try:
        data = _ffprobe(input_file)
        for stream in data.get("streams", []):
            if (
                stream.get("codec_type") == "video"
                and stream.get("codec_name") == "vp9"
            ):
                return True
        return False
    except Exception as e:
        print(f"Error checking if video is VP9: {e}")
        return False


def _convert_vp9_to_mp4(input_file: Path, output_file: Path):
    cmd = f'ffmpeg -i "{input_file}" -c:v libx264 -c:a aac {output_file}'
    p = subprocess.run(cmd, shell=True, capture_output=True)
    if not p.returncode == 0:
        print(p.stdout)
        print(p.stderr)
        raise ValueError(f"convert_vp9_to_mp4 Got other returncode: {p.returncode}")


if __name__ == "__main__":
    # channel = "https://www.youtube.com/@Gdconf"
    # query = "launcher"
    # clip_length = 10
    # headless = True

    # transcribe(channel, query, clip_length=clip_length)
    cli()
