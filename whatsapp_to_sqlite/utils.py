from pathlib import Path
from typing import List, Optional, Dict, Tuple
from logging import Logger

import datetime
import hashlib
import io
import itertools
import mimetypes
import time
import shutil
import uuid

import click
from PIL import Image

from sqlite_utils import Database
from sqlite_utils.db import NotFoundError

from whatsapp_to_sqlite.parser import (
    MessageException,
    MessageVisitor,
    NoMatch,
    get_chat_file_glob_by_locale,
    get_parser_by_locale,
    get_room_name_by_locale,
    log,
)
from whatsapp_to_sqlite.messages import (
    Message,
    HasNewNumberMessage,
    HasNewRoomNameMessage,
    HasTargetUserMessage,
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


config_type_format: str = "com.github.skowalak.whatsapp-to-sqlite.{0}"
config_url_format: str = "http://whatsapp-media.local/{0}"


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
        db["file_fs"].create(
            {
                "id": str,
                "name": str,
                "sha512sum": str,
                "mime_type": str,
                "preview": str,
                "size": int,
                "original_file_path": str,
            },
            pk="id",
        )
        db["file_chat"].create(
            {
                "id": str,
                "name": str,
                "preview": str,
                "file_fs_id": str,
            },
            pk="id",
            foreign_keys=[("file_fs_id", "file_fs", "id")],
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
                ("display_img", "file_fs", "id"),
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
        db["message"].add_foreign_key("file_id", "file_chat", "id")
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


def get_room_name(absolute_file_path: str, locale) -> str:
    file_path = Path(absolute_file_path)
    room_name = get_room_name_by_locale(file_path.stem, locale)
    return room_name


def save_room(
    room: List[Message],
    room_name: str,
    system_message_id: uuid.UUID,
    db: Database,
    progress_callback=lambda *_: None,
):
    """Insert a room (list of messages in one room context) into the database."""
    if not room:
        return

    # create room
    room_id = uuid.uuid4()

    # check if first message in room matches a group or a DM
    room_is_dm = True
    if isinstance(
        room[0],
        (
            RoomCreateBySelf,
            RoomCreateByThirdParty,
        ),
    ):
        room_is_dm = False

    sender_lookup_table = get_sender_lookup_table(db)

    messages, files = prepare_messages(
        room,
        room_id,
        system_message_id,
        sender_lookup_table,
    )
    first_message_id = messages[0]["id"]
    message_ids = [message["id"] for message in messages]
    message_relationships = [
        {"message_id": str(y), "parent_message_id": str(x)}
        for x, y in itertools.pairwise(message_ids)
    ]
    senders = list(sender_lookup_table.values())

    progress_callback()

    db["file_chat"].insert_all(files)
    db["sender"].insert_all(senders, ignore=True)
    db["message"].insert_all(messages)
    db["message_x_message"].insert_all(message_relationships)

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

    progress_callback()


def prepare_messages(
    messages: List[Message],
    room_id: uuid.UUID,
    system_message_id: uuid.UUID,
    sender_lookup_table: Dict,
    progress_callback=lambda *_: None,
) -> Tuple[List[Dict], List[Dict]]:
    prepared_messages = []
    prepared_files = []
    for depth, message in enumerate(messages, start=1):
        sender_id = get_sender(message, system_message_id, sender_lookup_table)

        message_id = uuid.uuid4()
        file_id = None
        message_file = False
        message_text = None
        message_target_user = None
        message_new_room_name = None
        message_new_number = None

        if message.__class__ in (RoomMessage,):
            message_text = message.text
            if message_text and message.continued_text:
                message_text = message_text + message.continued_text
            elif not message_text and message.continued_text:
                message_text = message.continued_text

            msg_file = get_file(message)
            if msg_file:
                message_file = True
                prepared_files.append(msg_file)

        if isinstance(message, HasTargetUserMessage):
            # FIXME(skowalak): This does not handle multiple target users -> data model change
            message_target_user = get_participant(message.target, sender_lookup_table)

        if isinstance(message, HasNewRoomNameMessage):
            message_new_room_name = message.new_room_name

        if isinstance(message, HasNewNumberMessage):
            message_new_number = message.new_number

        prepared_messages.append(
            {
                "id": str(message_id),
                "timestamp": message.timestamp,
                "sender_id": str(sender_id),
                "room_id": str(room_id),
                "depth": depth,
                "type": config_type_format.format(message.__class__.__name__),
                "message_content": message_text,
                "file": message_file,
                "file_id": str(file_id) if file_id else None,
                "target_user": str(message_target_user)
                if message_target_user
                else None,
                "new_room_name": message_new_room_name,
                "new_number": message_new_number,
            }
        )
        progress_callback()

    return prepared_messages, prepared_files


def get_sender(
    message: Message, system_message_id: uuid.UUID, look_up_table: Dict
) -> uuid.UUID:
    """get the sender record of a message, if it has one"""
    if hasattr(message, "sender"):
        try:
            return get_participant(message.sender, look_up_table)
        except ValueError:
            # probably a "BySelf" message
            return system_message_id

    return system_message_id


def get_participant(name: str, look_up_table: Dict) -> uuid.UUID:
    """use the lookuptable to check if an id for this name already exists"""
    if not name:
        raise ValueError("invalid name")

    # TODO(skowalak): If it ever happens: relevant for arabic locales?
    name = name.lstrip("\u200e")

    sender_id = look_up_table.get(name, {}).get("id")
    if not sender_id:
        sender_id = uuid.uuid4()
        look_up_table[name] = {"id": sender_id, "name": name}

    return sender_id


def get_file(message: Message) -> Optional[Dict]:
    """get a file from a message, if one exists."""
    if message.file:
        if not message.filename and not message.file_lost:
            raise ValueError("message indicates file, but no filename")
        return {"id": uuid.uuid4(), "name": message.filename}


def get_sender_lookup_table(db: Database) -> Dict[uuid.UUID, Dict]:
    """
    get a dictionary of sender records with the names as lookup key.

    this will not respect non-unique names.
    """
    lut = {}
    for row in db["sender"].rows:
        name = row["name"]
        lut[name] = row

    return lut


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


def crawl_directory(path: Path, glob: str = "**/*") -> List[Path]:
    path_list = []
    for glob_path in path.glob(glob):
        if glob_path.is_dir():
            continue

        path_list.append(glob_path)

    return path_list


def crawl_directory_for_chat_files(path: Path, locale: str) -> List[Path]:
    file_name_glob = get_chat_file_glob_by_locale(locale)
    return crawl_directory(path, f"**/{file_name_glob}")


def _get_hash(file_path: Path) -> bytes:
    hash_obj = hashlib.sha512()
    with file_path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(2048), b""):
            hash_obj.update(chunk)
    return hash_obj.digest()


def match_media_files(
    db: Database,
    logger: Logger,
    set_progress_size=lambda *_, **__: None,
    progress_callback=lambda *_: None,
):
    """match media files imported from file system to file names from chats."""
    logger.debug("Attempting to match imported media to imported chats")

    # iterate over files that occur in chat messages
    progress_size = db["file_chat"].count
    set_progress_size(progress_size)
    for row in db["file_chat"].rows:
        file_id = row["id"]
        file_name = row["name"]
        if db["file_fs"].count_where("name = ?", [file_name]) > 1:
            logger.debug("more than one match for file name '%s', skipping.", file_name)
            continue

        for file_fs in db["file_fs"].rows_where("name = ?", [file_name]):
            # this should only yield one row, see check above
            file_fs_id = file_fs["id"]
            file_fs_preview = file_fs["preview"]
            db["file_chat"].update(
                file_id, {"file_fs_id": file_fs_id, "preview": file_fs_preview}
            )
            db["file_fs"].update(file_fs_id, {"preview": None})
            break

        progress_callback()


def import_media_to_db(
    files: List[Path],
    db: Database,
    logger: Logger,
    progress_callback=lambda *_: None,
):
    """import media from file system into a db table `file_fs`."""
    logger.debug("Attempting to import %s media files to database", len(files))

    # inserting appears to be kinda slow, so we are chunking our inserts to 1000 files at a time
    def chunker(iterable, n, fillvalue=None):
        args = [iter(iterable)]
        return itertools.zip_longest(*args, fillvalue=fillvalue)

    for chunk in chunker(files, 1000):
        files_in_chunk = []
        for path in chunk:
            # handle fillvalue
            if path is None:
                break

            file_id = uuid.uuid4()
            file_name = path.name
            file_sha512sum = _get_hash(path)
            file_mime_type, _ = mimetypes.guess_type(file_name)
            # FIXME(skowalak): file_preview requires PIL, make that optional
            file_preview = _generate_preview(path, file_mime_type, logger)
            file_size = path.stat().st_size

            files_in_chunk.append(
                {
                    "id": str(file_id),
                    "name": file_name,
                    "sha512sum": file_sha512sum,
                    "mime_type": file_mime_type,
                    "preview": file_preview,
                    "size": file_size,
                    "original_file_path": str(path),
                }
            )
            progress_callback()

        db["file_fs"].insert_all(files_in_chunk)


def remove_media_duplicates(db) -> int:
    cursor = db.execute(
        (
            "DELETE FROM file_fs "
            "WHERE rowid > ("
            "SELECT MIN(rowid) FROM file_fs f2 "
            "WHERE file_fs.name = f2.name "
            "AND file_fs.sha512sum = f2.sha512sum "
            "AND file_fs.size = f2.size"
            ");"
        )
    )
    return cursor.rowcount


def move_files(
    db: Database,
    output_directory: Path,
    logger: Logger,
    set_progress_size=lambda *_, **__: None,
    progress_callback=lambda *_: None,
) -> None:
    copyable_files_count = db["file_fs"].count
    set_progress_size(copyable_files_count)
    # for row in db["file_fs"].rows:
    for i in range(copyable_files_count):
        import time

        time.sleep(0.1)
        progress_callback()


def _generate_preview(file: Path, mime_type: str, logger: Logger) -> Optional[bytes]:
    """generate a small preview image for media files."""
    logger.debug("generate preview for %s: %s.", mime_type, file.name)
    if mime_type in ("application/pdf", "pdf"):
        # TODO(skowalak): invoke pdf preview generator method here
        return

    try:
        return _generate_image_preview(file)
    except OSError as error:
        logger.debug("error from PIL (not an image?): %s.", str(error))
    except Exception as error:  # pylint: disable=broad-except
        logger.warning("uncaught error generating img preview: %s.", str(error))


def _generate_image_preview(img: Path, preview_size=(20, 20)) -> Optional[bytes]:
    with Image.open(img) as image:
        image = Image.open(img)
        image.thumbnail(preview_size)

        with io.BytesIO() as buffer:
            image.save(buffer, format="JPEG")
            return buffer.getvalue()


# def debug_dump(msglist: list) -> None:
#     import json
#     from datetime import datetime
#
#     def json_serial(obj):
#         if isinstance(obj, Message):
#             return obj.toDict()
#
#         if isinstance(obj, datetime):
#             return obj.isoformat()
#
#     print(json.dumps(msglist, indent=2, default=json_serial, sort_keys=True))
#
