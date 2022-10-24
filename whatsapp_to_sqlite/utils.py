from pathlib import Path
from typing import List

import base64
import hashlib
import mimetypes
import os
import re
import uuid

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError

from whatsapp_to_sqlite.arPEGgio import (
    MessageParser,
    MessageVisitor,
    visit_parse_tree,
    log,
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


def parse_room_file(file_path: str) -> List[Message]:
    with file_path.open("r", encoding="utf-8") as room_file:
        string = room_file.read()
        return parse_string(string)


def get_room_name(absolute_file_path: str) -> str:
    file_path = Path(absolute_file_path)
    # TODO(skowalak): internationalization of file names
    room_name = re.search(r"WhatsApp Chat mit (.*)", file_path.stem).group(1)
    return room_name


def save_room(
    room: List[Message], room_name: str, system_message_id: uuid.UUID, db: Database
):
    """Insert a room (list of messages in one room context) into the database."""
    if not room:
        return

    # create room
    room_id = uuid.uuid4()

    # check if first message in room matches a group or a DM
    # TODO(skowalak): do it
    room_is_dm = False

    message_ids = []
    first_message_id = None
    last_message_id = None
    for depth, message in enumerate(room, start=1):
        message_id = save_message(message, room_id, depth, system_message_id, db)

        if not first_message_id:
            first_message_id = message_id

        if last_message_id:
            save_message_relationship(message_id, last_message_id, db)

        last_message_id = message_id

    db["room"].insert(
        {
            "id": room_id.bytes,
            "is_dm": room_is_dm,
            "first_message": first_message_id.bytes,
            "display_img": None,
            "name": room_name,
            "member_count": 0,
        }
    )


def save_message(
    message: Message,
    room_id: uuid.UUID,
    depth: int,
    system_message_id: uuid.UUID,
    db: Database,
) -> uuid.UUID:
    if hasattr(message, "sender"):
        sender_id = save_sender(message.sender, db)
    else:
        sender_id = system_message_id

    # TODO(skowalak): Into config
    type_format = "com.github.skowalak.whatsapp-to-sqlite.{0}"
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
        if message_text and message.continued_text:
            message_text = message_text + "\n" + message.continued_text
        elif not message_text and message.continued_text:
            message_text = message.continued_text
        if message.file:
            message_file = True
            file_id = save_file(message.filename, db)

    if message.__class__ in msg_w_target_user:
        message_target_user = save_sender(message.target, db)

    if message.__class__ in msg_w_new_room_name:
        message_new_room_name = message.new_room_name

    if message.__class__ in msg_w_new_number:
        message_new_number = message.new_number

    db["message"].insert(
        {
            "id": message_id.bytes,
            "timestamp": message.timestamp,
            "full_content": message.full_text,
            "sender_id": sender_id.bytes,
            "room_id": room_id.bytes,
            "depth": depth,
            "type": type_format.format(message.__class__.__name__),
            "message_content": message_text,
            "file": message_file,
            "file_id": file_id.bytes if file_id else None,
            "target_user": message_target_user.bytes if message_target_user else None,
            "new_room_name": message_new_room_name,
            "new_number": message_new_number,
        }
    )

    return message_id


def save_message_relationship(
    message_id: uuid.UUID, parent_message_id: uuid.UUID, db: Database
):
    db["message_x_message"].insert(
        {"message_id": message_id.bytes, "parent_message_id": parent_message_id.bytes}
    )


def save_sender(name: str, db: Database) -> uuid.UUID:
    # look up if sender name (assumed unique) already exists
    sender_id = None
    for pk, row in db["sender"].pks_and_rows_where("name = ?", [name]):
        # if exists use id
        sender_id = uuid.UUID(bytes=pk)
        return sender_id

    # if not exists create new and use that id
    sender_id = uuid.uuid4()
    db["sender"].insert({"id": sender_id.bytes, "name": name})
    return sender_id


def save_file(filename: str, db: Database) -> uuid.UUID:
    """Create every file (even with same name) as new file row. Dedup comes later."""
    file_id = uuid.uuid4()
    file_mime_type = None
    if filename:
        file_mime_type, _ = mimetypes.guess_type(filename)

    db["file"].insert(
        {
            "id": file_id.bytes,
            "sha512sum": None,
            "name": filename,
            "mime_type": file_mime_type,
            "preview": None,
            "size": None,
        }
    )
    return file_id


def get_system_message_id(db: Database) -> uuid.UUID:
    try:
        system_message_id_bytes = db["system_message_id"].get(1)
    except NotFoundError:
        system_message_id = uuid.uuid4()
        db["system_message_id"].insert(
            {"id": 1, "system_message_id": system_message_id.bytes}
        )
        return system_message_id

    return uuid.UUID(bytes=system_message_id_bytes["system_message_id"])


def crawl_directory(path: Path, file_name_glob: str = "*") -> List[Path]:
    file_list = []
    for glob_path in path.glob(f"**/{file_name_glob}"):
        file_list.append(glob_path)

    return file_list


def get_hash(file_path: Path) -> bytes:
    hash_obj = hashlib.sha512()
    with filepath.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(2048), b""):
            hash_obj.update(chunk)
    return hash_obj.digest()


def update_all_files(data_dir_files: List[Path], db: Database):
    data_dir_filenames = {file.name: file for file in data_dir_files}
    for row in db["file"].rows:
        filename = row["name"]
        if filename and filename in data_dir_filenames.keys():
            file_id = uuid.UUID(bytes=row["id"])

            file = data_dir_filenames[filename]
            file_sha512sum = get_hash(file)
            file_preview = None  # FIXME(skowalak): PIL/pillow?
            file_size = file.stat().st_size

            db["file"].update(
                file_id.bytes,
                {
                    "id": file_id.bytes,
                    "sha512sum": file_sha512sum,
                    "preview": file_preview,
                    "size": file_size,
                },
            )


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


def debug_dump(msglist: list) -> None:
    import json
    from datetime import datetime

    def json_serial(obj):
        if isinstance(obj, Message):
            return obj.toDict()

        if isinstance(obj, datetime):
            return obj.isoformat()

    print(json.dumps(msglist, indent=2, default=json_serial, sort_keys=True))
