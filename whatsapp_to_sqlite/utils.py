from typing import List

import base64
import hashlib
import os
import sqlite_utils

from whatsapp_to_sqlite.arPEGgio import (
    MessageParser,
    MessageVisitor,
    visit_parse_tree,
    log,
)
from whatsapp_to_sqlite.events import (
    Event,
    RoomCreateEvent,
)
from whatsapp_to_sqlite.messages import (
    Message,
    RoomCreateByThirdParty,
)


def parse_string(string: str) -> List[Message]:
    """Parse a single string using arpeggio grammar definition."""
    parse_tree = MessageParser(log).parse(string)
    return MessageVisitor().visit(parse_tree)


def parse_room_file(absolute_file_path: str) -> List[Message]:
    with open(absolute_file_path, "r", encoding="utf-8") as room_file:
        string = room_file.read()
        return parse_string(string)


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
    with open(filepath, "rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(2048), b""):
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


def debug_dump(msglist: list) -> None:
    import json
    from datetime import datetime

    def json_serial(obj):
        if isinstance(obj, Message):
            return obj.toDict()

        if isinstance(obj, datetime):
            return obj.isoformat()

    print(json.dumps(msglist, indent=2, default=json_serial, sort_keys=True))
