from pathlib import Path
from typing import List, Optional
from logging import Logger

import base64
import hashlib
import io
import mimetypes
import os
import re
import time
import uuid

from PIL import Image

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError

from whatsapp_to_sqlite.parser import (
    MessageException,
    MessageParser,
    MessageVisitor,
    NoMatch,
    get_parser_by_locale,
    log,
    visit_parse_tree,
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


def make_db_backup(db_path: Path, logger: Logger) -> None:
    try:
        shutil.copy2(
            db_path, db_path.with_suffix(f".{time.time()}.bkp{db_path.suffix}")
        )
    except OSError as error:
        logger.error("Cannot write backup database file: %s", str(error))
        raise click.ClickException(
            "Database file already exists, cannot write backup file."
        )


def init_db(db: Database, logger: Logger) -> None:
    if db.schema == "":
        logger.debug("db is uninitialized, create tables")
        db["message"].create(
            {
                "id": str,
                "timestamp": datetime.datetime,
                "full_content": str,
                "sender_id": str,
                "room_id": str,
                "depth": int,
                "type": str,  # discriminator
                "message_content": str,
                "file": bool,
                "file_id": str,
                "target_user": str,
                "new_room_name": str,
                "new_number": str,
            },
            pk="id",
            if_not_exists=True,
        )
        db["message_x_message"].create(
            {"message_id": str, "parent_message_id": str},
            pk=("message_id", "parent_message_id"),
            foreign_keys=[
                ("message_id", "message", "id"),
                ("parent_message_id", "message", "id"),
            ],
            if_not_exists=True,
        )
        db["file"].create(
            {
                "id": str,
                "sha512sum": str,
                "name": str,
                "mime_type": str,
                "preview": str,
                "size": int,
            },
            pk="id",
            if_not_exists=True,
        )
        db["room"].create(
            {
                "id": str,
                "is_dm": bool,
                "first_message": str,
                "display_img": str,
                "name": str,
                "member_count": int,
            },
            pk="id",
            foreign_keys=[
                ("first_message", "message", "id"),
                ("display_img", "file", "id"),
            ],
            if_not_exists=True,
        )
        db["sender"].create(
            {
                "id": str,
                "name": str,
            },
            pk="id",
            if_not_exists=True,
        )
        db["system_message_id"].create({"id": int, "system_message_id": str})

        # add foreign keys for circular references
        db["message"].add_foreign_key("sender_id", "sender", "id")
        db["message"].add_foreign_key("room_id", "room", "id")
        db["message"].add_foreign_key("target_user", "sender", "id")
        db["message"].add_foreign_key("file_id", "file", "id")
        # TODO(skowalak): eval init using separate init.sql? -> Better DB
    else:
        # logger.error("Incorrect schema version: %s", db.schema)
        # raise click.ClickException("Incorrect database schema version.")
        logger.debug("database already initialized: %s", db.schema)


def parse_string(string: str, locale: str, logger) -> List[Message]:
    """Parse a single string using arpeggio grammar definition."""
    if not string.endswith("\n"):
        logger.debug("file not ending with EOL found, adding newline")
        string = string + "\n"

    localized_parser = get_parser_by_locale(locale)
    parse_tree = localized_parser(log).parse(string)
    return MessageVisitor().visit(parse_tree)


def parse_room_file(file_path: Path, locale: str, logger: Logger) -> List[Message]:
    with file_path.open("r", encoding="utf-8") as room_file:
        string = room_file.read()
        try:
            return parse_string(string, locale, logger)
        except NoMatch as exception:
            raise MessageException(file_path) from exception


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
            "id": str(room_id),
            "is_dm": room_is_dm,
            "first_message": str(first_message_id),
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
            message_text = message_text + message.continued_text
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
            "id": str(message_id),
            "timestamp": message.timestamp,
            "full_content": message.full_text,
            "sender_id": str(sender_id),
            "room_id": str(room_id),
            "depth": depth,
            "type": type_format.format(message.__class__.__name__),
            "message_content": message_text,
            "file": message_file,
            "file_id": str(file_id) if file_id else None,
            "target_user": str(message_target_user) if message_target_user else None,
            "new_room_name": message_new_room_name,
            "new_number": message_new_number,
        }
    )

    return message_id


def save_message_relationship(
    message_id: uuid.UUID, parent_message_id: uuid.UUID, db: Database
):
    db["message_x_message"].insert(
        {"message_id": str(message_id), "parent_message_id": str(parent_message_id)}
    )


def save_sender(name: str, db: Database) -> uuid.UUID:
    # remove all U+200e if exist
    # TODO(skowalak): If it ever happens: relevant for arabic locales?
    if name:
        name = name.lstrip("\u200e")
    # look up if sender name (assumed unique) already exists
    sender_id = None
    for pk, row in db["sender"].pks_and_rows_where("name = ?", [name]):
        # if exists use id
        sender_id = uuid.UUID(pk)
        return sender_id

    # if not exists create new and use that id
    sender_id = uuid.uuid4()
    db["sender"].insert({"id": (sender_id), "name": name})
    return sender_id


def save_file(filename: str, db: Database) -> uuid.UUID:
    """Create every file (even with same name) as new file row. Dedup comes later."""
    file_id = uuid.uuid4()
    file_mime_type = None
    if filename:
        file_mime_type, _ = mimetypes.guess_type(filename)

    db["file"].insert(
        {
            "id": str(file_id),
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
            {"id": 1, "system_message_id": str(system_message_id)}
        )
        return system_message_id

    return uuid.UUID(system_message_id_bytes["system_message_id"])


def crawl_directory(path: Path, locale: str) -> List[Path]:
    file_name_glob = parser.get_chat_file_glob_by_locale(locale)
    file_list = []
    for glob_path in path.glob(f"**/{file_name_glob}"):
        if glob_path.is_dir():
            continue

        file_list.append(glob_path)

    return file_list


def _get_hash(file_path: Path) -> bytes:
    hash_obj = hashlib.sha512()
    with file_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(2048), b""):
            hash_obj.update(chunk)
    return hash_obj.digest()


def update_files_in_db(data_dir_files: List[Path], db: Database, logger: Logger):
    data_dir_filenames = {file.name: file for file in data_dir_files}
    for row in db["file"].rows:
        filename = row["name"]
        if filename and filename in data_dir_filenames.keys():
            file_id = uuid.UUID(row["id"])

            file = data_dir_filenames[filename]
            file_sha512sum = _get_hash(file)
            file_preview = None  # FIXME(skowalak): PIL/pillow?
            file_size = file.stat().st_size

            db["file"].update(
                str(file_id),
                {
                    "sha512sum": file_sha512sum,
                    "preview": file_preview,
                    "size": file_size,
                },
            )


def match_media_files(db: Database, logger: Logger):
    logger.debug("Attempting to match imported media to imported chats")


def import_media_to_db(files: List[Path], db: Database, logger: Logger):
    logger.debug("Attempting to import %s media files to database", len(files))
    for path in files:
        file_id = uuid.uuid4()
        file_name = path.name
        file_sha512sum = _get_hash(path)
        file_mime_type, _ = mimetypes.guess_type(file_name)
        file_preview = _generate_preview(path, file_mime_type, logger)
        file_size = path.stat().st_size

        db["file"].insert(
            {
                "id": str(file_id),
                "sha512sum": file_sha512sum,
                "name": file_name,
                "mime_type": file_mime_type,
                "preview": file_preview,
                "size": file_size,
            },
            pk="id",
        )


def _generate_preview(file: Path, mime_type: str, logger: Logger) -> Optional[bytes]:
    # identify image files:
    try:
        return _generate_image_preview(file)
    except OSError as error:
        logger.debug("error from PIL (not an image?): %s.", str(error))
    except Exception as error:
        logger.warning("uncaught error generating img preview: %s.", str(error))


def _generate_image_preview(img: Path, preview_size=(20, 20)) -> Optional[bytes]:
    with Image.open(img) as image:
        image = Image.open(img)
        image.thumbnail(preview_size)

        with io.BytesIO() as buffer:
            image.save(buffer, format="JPEG")
            return buffer.getvalue()


def debug_dump(msglist: list) -> None:
    import json
    from datetime import datetime

    def json_serial(obj):
        if isinstance(obj, Message):
            return obj.toDict()

        if isinstance(obj, datetime):
            return obj.isoformat()

    print(json.dumps(msglist, indent=2, default=json_serial, sort_keys=True))
