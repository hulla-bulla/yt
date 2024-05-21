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


from yt_dlp.utils import download_range_func
from playwright.sync_api import sync_playwright
from modules import google_docs


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


def download_video(url: str, range_str: str = None, download_folder: Path = None):
    yt_opts = {
        "verbose": False,
        "format": "best[ext=mp4]",
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
def dl(url: str, range_str: str, download_folder: Path):
    click.echo("Setting options for yt-dlp")
    click.echo(f"Downloading {url}")
    download_video(url, range_str, download_folder=download_folder)
    click.echo("Done")


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
        futures = [executor.submit(get_clips, url, query) for url in urls]
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


def get_clips(url, query, headless=True) -> list[dict[str, str]]:
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


if __name__ == "__main__":
    # channel = "https://www.youtube.com/@Gdconf"
    # query = "launcher"
    # clip_length = 10
    # headless = True

    # transcribe(channel, query, clip_length=clip_length)
    cli()
