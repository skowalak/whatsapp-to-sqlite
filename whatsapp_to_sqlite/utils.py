from pathlib import Path
from typing import List

import base64
import hashlib
import os
import re
import uuid

from sqlite_utils import Database

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
    RoomCreateBySelf,
    RoomCreateByThirdParty,
    RoomJoinThirdPartyBySelf,
    RoomJoinThirdPartyByThirdParty,
    RoomJoinThirdPartyByUnknown,
    RoomKickThirdPartyBySelf,
    RoomKickThirdPartyByThirdParty,
    RoomKickThirdPartyByUnknown,
    RoomMessage,
    RoomNameBySelf,
    RoomNameByThirdParty,
    RoomNumberChangeWithNumber,
)


def parse_string(string: str) -> List[Message]:
    """Parse a single string using arpeggio grammar definition."""
    parse_tree = MessageParser(log).parse(string)
    return MessageVisitor().visit(parse_tree)


def parse_room_file(absolute_file_path: str) -> List[Message]:
    with open(absolute_file_path, "r", encoding="utf-8") as room_file:
        string = room_file.read()
        return parse_string(string)


def get_room_name(absolute_file_path: str) -> str:
    file_path = Path(absolute_file_path)
    # TODO(skowalak): internationalization of file names
    room_name = re.search(r"WhatsApp Chat mit (.*)", file_path.stem).group(1)
    return room_name


def save_message(
    message: Message, room_id: uuid.UUID, depth: int, db: Database
) -> uuid.UUID:
    # FIXME(skowalak): Events by Self do not always have a sender id? Just create random?
    # FIXME(skowalak): Maybe just use a configurable uuid for all events without sender (only system events).
    sender_id = save_sender(message.sender)

    # TODO(skowalak): Into config
    type_format = "com.github.com.skowalak.whatsapp-to-sqlite.{0}"
    msg_w_user_content = [RoomMessage]
    msg_w_target_user = [
        RoomJoinThirdPartyByThirdParty,
        RoomJoinThirdPartyByUnknown,
        RoomJoinThirdPartyBySelf,
        RoomKickThirdPartyByThirdParty,
        RoomKickThirdPartyByUnknown,
        RoomKickThirdPartyBySelf,
    ]
    msg_w_new_room_name = [
        RoomCreateByThirdParty,
        RoomCreateBySelf,
        RoomNameBySelf,
        RoomNameByThirdParty,
    ]
    msg_w_new_number = [RoomNumberChangeWithNumber]

    message_id = uuid.uuid4()
    file_id = None
    message_file = False
    message_text = None
    message_target_user = None
    message_new_room_name = None
    message_new_number = None

    if message.__class__ in msg_w_user_content:
        message_text = message.text
        if message.continued_text:
            message_text = message_text + "\n" + message.continued_text
        if message.file:
            message_file = True
            file_id = save_file(message.filename, message.file_lost)

    if message.__class__ in msg_w_target_user:
        message_target_user = message.target_user

    if message.__class__ in msg_w_new_room_name:
        message_new_room_name = message.new_room_name

    if message.__class__ in msg_w_new_number:
        message_new_number = message.new_number

    db["message"].insert(
        {
            "id": message_id.bytes,
            "timestamp": message.timestamp,
            "full_content": message.full_text,
            "sender_id": sender_id,
            "room_id": room_id,
            "depth": depth,
            "type": type_format.format(message.__class__.__name__),
            "message_content": message_text,
            "file": message_file,
            "file_id": file_id,
            "target_user": message_target_user,
            "new_room_name": message_new_room_name,
            "new_number": message_new_number,
        }
    )

    return message_id


def save_sender(name: str) -> uuid.UUID:
    # look up if sender name (assumed unique) already exists


def save_room(room: List[Message], room_name: str, db: Database):
    """Insert a room (list of messages in one room context) into the database."""
    # create room
    room_id = uuid.uuid4()

    db["room"].insert()


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
