from click.testing import CliRunner
import pytest
import sqlite_utils
import pathlib
import unittest

@pytest.fixture
def test_chat_path():
    return pathlib.Path(__file__).parent / "test_chat.txt"

@pytest.fixture
def test_chat_fp(test_chat_path):
    return open(test_chat_path, "r")

@pytest.fixture
def file_all_types():
    with (pathlib.Path(__file__).parent / "WhatsApp Chat mit ayy.txt").open("r") as file:
        yield file

@pytest.fixture(scope="function")
def logger():
    yield unittest.mock.Mock()


@pytest.fixture
def db():
    return sqlite_utils.Database(":memory:")
