"""

Google docs
File download as text file

comments in bottom will be formatted
Will split and keep #edit ones
"""

from pathlib import Path
from rich.console import Console
from rich.table import Table
from typeguard import typechecked
import click


class ExcelColumnIterator:
    def __init__(self):
        self.current = []

    def __iter__(self):
        return self

    def __next__(self):
        # Increment the column name
        index = len(self.current) - 1

        while index >= 0 and self.current[index] == "z":
            self.current[index] = "a"
            index -= 1

        if index == -1:
            self.current.insert(0, "a")
        else:
            self.current[index] = chr(ord(self.current[index]) + 1)

        return "".join(self.current)


@typechecked
def _load_doc(filepath: Path):
    with open(filepath, "r", encoding="utf-8") as f:
        raw_data = f.readlines()
    return raw_data


@typechecked
def length(filepath: Path, words_per_minute=160, delimiter="#edit "):
    raw_data = _load_doc(filepath)

    words = len([y for x in raw_data for y in x.split()])
    words_no_bracket = len(
        [
            y
            for x in raw_data
            for y in x.split()
            if "[" not in y and "]" not in y and delimiter not in y
        ]
    )

    time_length_all = words / words_per_minute
    time_length_no_bracket = words_no_bracket / words_per_minute

    table = Table(title="Script Length")
    columns = ["Description", "Value"]
    for column in columns:
        table.add_column(column)
    table.add_section()



    table.add_row(
        "Words [All]",
        str(words),
        style="bright_blue"
    )
    table.add_section()
    table.add_row(
        "Words [no brackets (comments)]",
        str(words_no_bracket),
        style="bright_blue"
    )
    table.add_section()
    table.add_row(
        "Words [All]",
        f"{time_length_all:.1f}",
        style="bright_blue"
    )
    table.add_section()
    table.add_row(
        "Words [no brackets (comments)]",
        f"{time_length_no_bracket:.1f}",
        style="bright_blue"
    )
    table.add_section()
    console = Console()
    console.print(table)


@typechecked
def parse_comments(filepath: Path, delimiter="#edit "):
    len_delimiter = len(delimiter)

    raw_data = _load_doc(filepath)

    excel_col_gen = ExcelColumnIterator()
    matches = []
    for _ in range(10000):  # Generate 52 columns
        # print(next(excel_col_gen))

        id = next(excel_col_gen)
        id = f"[{id}]"
        match = [x.strip() for x in raw_data if id in x]
        if not match:
            break
        # print(f"{i} -> {match}")
        if len(match) < 2:
            continue
        if delimiter not in match[1]:
            continue
        matches.append((id, *match))

    table = Table(title="Edits")
    columns = ["Id", "Script reference", "Edit notes"]
    for column in columns:
        table.add_column(column)
    table.add_section()

    every_other_tracker = False

    for match in matches:
        # unpack
        id, reference, comment = match

        # remove comment id from both
        reference = reference.replace(id, "")
        comment = comment.replace(id, "")

        # remove prefix from comment
        index_to_start_from = comment.index(delimiter) + len_delimiter
        comment = comment[index_to_start_from:]

        table.add_row(
            *[
                id[1:-1],  # cannot be [ab] need to be ab to show up
                reference,
                comment,
            ],
            style="bright_blue" if every_other_tracker else "bright_green",
        )
        table.add_section()
        every_other_tracker = not every_other_tracker

    table.add_row(
            *[
                "",
                f"Number of {delimiter}comments",
                str(table.row_count),
            ],
            style="bright_yellow",
        )
    table.add_section()

    console = Console()
    console.print(table)


if __name__ == "__main__":
    filepath = r"c:\Users\fred\Downloads\Video - rust game launcher.txt"
    delimiter = "#edit "

    parse_comments(filepath, delimiter=delimiter)
