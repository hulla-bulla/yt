from pathlib import Path
from time import sleep
import click
import yt_dlp
from pprint import pprint
from datetime import datetime, timedelta
from selectolax.parser import HTMLParser

import urllib.parse
import httpx

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
        "verbose": True,
        "format": "best[ext=mp4]",
    }

    if download_folder:
        yt_opts["outtmpl"] = f"{download_folder}/%(title)s.%(ext)s"

    if range_str:
        start_time, end_time = convert_range_to_tuple(range_str)
        # download_ranges are in seconds
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
@click.argument("query", type=str, required=True)
@click.argument("channel_url", type=str, required=True)
@click.option("--clip-length", type=int, default=10, help="Clip length in seconds")
@click.option(
    "--download-folder",
    type=click.Path(
        exists=True,
        file_okay=False,
        readable=True,
        path_type=Path,
    ),
)
def clips(channel_url: str, query: str, clip_length: int, download_folder: Path):
    """Finds and downloads clips with the query inside the transcript.

    QUERY What to search youtube for
    CHANNEL_URL youtube channel/playlist url

    """
    clips = get_clips(channel_url, query)

    for clip in clips:
        youtube_id = clip["youtube_id"]
        start_time = clip["start_time"]
        range_str = f"{start_time}-"  # Assuming you need to calculate the end time based on clip_length
        start_min, start_sec = map(int, start_time.split(":"))
        start_total_sec = start_min * 60 + start_sec
        end_total_sec = start_total_sec + clip_length
        end_min = end_total_sec // 60
        end_sec = end_total_sec % 60
        end_time = f"{end_min:02}:{end_sec:02}"
        range_str += end_time

        video_url = f"https://www.youtube.com/watch?v={youtube_id}"

        download_video(video_url, range_str, download_folder=download_folder)


def get_clips(channel, query, headless=True) -> list[dict[str, str]]:
    """Finds clips with the query inside the transcript.

    Returns starttime and youtubeid


    """

    channel = urllib.parse.quote(channel, safe="")
    query = urllib.parse.quote(query, safe="")
    url = f"https://ytks.app/search?url={channel}&query={query}"

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
