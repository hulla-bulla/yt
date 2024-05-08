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


@cli.command()
@click.argument("url", type=str, required=True)
@click.option(
    "-r",
    "--range",
    "range_str",
    type=str,
    help="Download range in min:sec as on youtube. Example: 01:11-20:22.",
)
def dl(url: str, range_str: str):
    yt_opts = {
        "verbose": True,
        "format": "best[ext=mp4]",
    }

    if range_str:
        start_time, end_time = convert_range_to_tuple(range_str)
        # download_ranges are in seconds
        yt_opts["download_ranges"] = yt_dlp.utils.download_range_func(
            None, [(start_time, end_time)]
        )
        yt_opts["force_keyframes_at_cuts"] = True

    click.echo("Setting options for yt-dlp")
    dlp = yt_dlp.YoutubeDL(yt_opts)

    click.echo(f"Downloading {url}")
    a = dlp.download(url)

    click.echo("Done")


@cli.command()
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
def comments(path: str, delimiter):
    google_docs.parse_comments(path, delimiter=delimiter)


def transcribe(channel, query):

    channel = urllib.parse.quote(channel, safe="")
    query = urllib.parse.quote(query, safe="")
    url = f"https://ytks.app/search?url={channel}&query={query}"

    browser = sync_playwright().start()
    page = browser.chromium.launch(headless=False).new_page(
        permissions=[
            "clipboard-read",
        ]
    )
    page.set_default_timeout(2000)
    page.goto(url)

    page.get_by_role("button", name="Consent").click()

    grid = page.locator(".mantine-SimpleGrid-root")
    grid.wait_for(timeout=30000)

    cards = grid.locator(".mantine-Paper-root")
    cards.wait_for()
    cards = cards.all()

    card = cards[0]

    # card.get_by_role("button",name="Copy link to match").click()
    # a=page.evaluate("navigator.clipboard.readText()")

    tree = HTMLParser(card.inner_html())

    print(tree)
    pprint(card.inner_html())

    page.epext
    grid.wait_for()

    page.close()
    browser.stop()


if __name__ == "__main__":
    channel = "https://www.youtube.com/@Gdconf"
    query = "launcher"

    transcribe()
