from typing import List

import base64
import hashlib
import os
import sqlite_utils

from whatsapp_to_sqlite.messages import (
    Message,
    RoomCreateByThirdParty,
)
from whatsapp_to_sqlite.events import (
    RoomCreateEvent,
)


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


def get_hash(filepath: str):
    hash_obj = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(2048), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()


def sanitize_user_message(message: Message) -> List[Message]:
    # merge first and next lines if any
    if message.text and message.continued_text:
        message.text = message.text + message.continued_text
        message.continued_text = None

    # remove lrm marks that get inserted into some messages
    message.sender.lstrip("\u200e")

    # split messages containing files and text
    if message.file and message.continued_text:
        first_message = message.replace(continued_text=None)
        second_message = message.replace(
            file=False,
            file_lost=False,
            filename=None,
            text=message.continued_text,
            continued_text=None,
        )
        return [first_message, second_message]

    return [message]


def transform(messages: List[Message], room_name: str, user_name: str):
    senders = []
    for message in messages:
        senders.append(message.sender)
    events = []
    for message in messages:
        message.room_name = room_name

        if isinstance(message, RoomCreateByThirdParty):
            event = Event.of()
        elif isinstance(message, RoomCreateSelf):
            event = RoomCreateEvent(sender=user_name, room_name=room_name)
