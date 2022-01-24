import base64
import os
import sqlite_utils


def parse_room_file(absolute_file_path: str) -> list[dict]:
    pass


def save_messages(message, db):
    pass


def save_senders():
    pass


def save_rooms():
    pass


def save_file():
    pass


def crawl_directory_for_rooms(path: str) -> list[str]:
    path = os.path.abspath(path)
    file_list = []
    # iterate over all files in directory
    for root, dirs, files in os.walk(path):
        for file in files:
            if file.endswith(".txt"):
                file_list.append(os.path.join(root, file))

    return file_list
