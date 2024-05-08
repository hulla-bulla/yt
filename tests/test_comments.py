from pathlib import Path
from click.testing import CliRunner

from yt import cli


def _read_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        data = f.read()
    return data


def _filepaths_textfiles():
    return [
        Path("tests/testdata/Video - rust game launcher.txt"),
    ]


def _filepaths_textfiles_expected():
    return [
        Path("tests/testdata/expected/Video - rust game launcher_expected_comments"),
    ]


def _load_files():
    files = _filepaths_textfiles()
    file_data = [_read_file(x) for x in files]
    return file_data


def test_comments():
    expected_output = _read_file(_filepaths_textfiles_expected()[0])

    files = _filepaths_textfiles()
    file = files[0]
    runner = CliRunner()
    result = runner.invoke(cli, ["doc", "comments", str(file)])
    print(result.stdout)

    assert result.exit_code == 0
    #assert result.output == expected_output
