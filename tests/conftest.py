from click.testing import CliRunner
import pytest
import sqlite_utils
import pathlib

@pytest.fixture
def test_chat_path():
    return pathlib.Path(__file__).parent / "test_chat.txt"

@pytest.fixture
def test_chat_fp(test_chat_path):
    return open(test_chat_path, "r")

@pytest.fixture
def db():
    return sqlite_utils.Database(":memory:")
