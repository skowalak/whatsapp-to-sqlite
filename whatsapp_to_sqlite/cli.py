import datetime
import logging
import os
import pathlib
import shutil
import time
import uuid

import click
import sqlite_utils

from whatsapp_to_sqlite import utils


@click.group()
@click.version_option()
def cli():
    """
    Convert your exported plaintext message logs to an SQLite database.
    """


@cli.command(name="import")
@click.argument(
    "chat_files",
    type=click.Path(
        file_okay=True,
        dir_okay=True,
        allow_dash=True,
        resolve_path=True,
        path_type=pathlib.Path,
    ),
    required=True,
)
@click.argument(
    "db_path",
    default="messagedb.sqlite3",
    type=click.Path(
        file_okay=True,
        dir_okay=False,
        allow_dash=False,
        resolve_path=True,
        path_type=pathlib.Path,
    ),
    required=False,
)
@click.option(
    "-d",
    "--data-directory",
    type=click.Path(
        file_okay=False, dir_okay=True, allow_dash=False, resolve_path=True
    ),
    help=(
        "Path(s) which contain additional exported media. "
        "If left empty images, videos, files and voice memos "
        "will not be processed."
    ),
    required=False,
)
@click.option(
    "-o",
    "--output-directory",
    default="messagedb_files",
    type=click.Path(
        file_okay=False, dir_okay=True, allow_dash=False, resolve_path=True
    ),
    help=("Path to directory, where processed media will be stored."),
    required=False,
)
@click.option(
    "-e",
    "--force-erase",
    is_flag=True,
    help="Erase media files after exporting them to target directory.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Be more verbose when logging errors.",
)
def run_import(
    chat_files: pathlib.Path,
    db_path: pathlib.Path,
    data_directory,
    output_directory,
    force_erase=False,
    verbose=False,
):
    """
    Import one file or a directory CHAT_FILES into an SQLite3 database at
    DB_PATH.

    Files containing chat logs must consist of one file per chat log. Its
    filename must match the pattern "WhatsApp Chat with <name>.txt"
    """
    loglevel = logging.INFO if not verbose else logging.DEBUG
    logging.basicConfig(format="%(message)s", level=loglevel)
    logger = logging.getLogger(__name__)
    logger.debug(
        "chats path: %s, db path: %s, data dir: %s", chat_files, db_path, data_directory
    )
    if db_path.exists():
        logger.warning("Database file at %s already exists! Creating backup.", db_path)
        try:
            shutil.copy2(str(db_path), f"{db_path}.{time.time()}.bkp")
        except OSError as error:
            logger.error("Cannot write backup database file: %s", str(error))
            raise click.ClickException(
                "Database file already exists, cannot write backup file."
            )
    db = sqlite_utils.Database(db_path)
    if db.schema == "":
        # db is uninitialized, create tables
        # message table with discriminator on type
        db["message"].create(
            {
                "id": bytes,
                "timestamp": datetime.datetime,
                "full_content": str,
                "sender_id": bytes,  # fk
                "room_id": bytes,  # fk
                "depth": int,
                "type": str,  # discriminator
                "message_content": str,
                "file": bool,
                "file_id": bytes,
                "target_user": bytes,  # fk
                "new_room_name": str,
                "new_number": str,
            },
            pk="id",
            if_not_exists=True,
        )
        db["message_x_message"].create(
            {"message_id": bytes, "parent_message_id": bytes},
            pk=("message_id", "parent_message_id"),
            foreign_keys=[
                ("message_id", "message", "id"),
                ("parent_message_id", "message", "id"),
            ],
            if_not_exists=True,
        )
        db["file"].create(
            {
                "id": bytes,
                "uri": bytes,
                "filename": str,
                "mime_type": str,
                "preview": str,
                "size": int,
            },
            pk="id",
            if_not_exists=True,
        )
        db["room"].create(
            {
                "id": bytes,
                "is_dm": bool,
                "first_message": bytes,  # fk
                "display_img": bytes,  # fk
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
                "id": bytes,
                "name": str,
            },
            pk="id",
            if_not_exists=True,
        )
        db["system_message_id"].create({"id": int, "system_message_id": bytes})
        db["message"].add_foreign_key("sender_id", "sender", "id")
        db["message"].add_foreign_key("room_id", "room", "id")
        db["message"].add_foreign_key("target_user", "sender", "id")
        # TODO(skowalak): init using separate init.sql? -> Better DB
    else:
        # db is already initialized, continue
        # logger.error("Incorrect schema version: %s", db.schema)
        # raise click.ClickException("Incorrect database schema version.")
        logger.debug("database already initialized: %s", db.schema)

    errors = False
    system_message_id = utils.get_system_message_id(db)
    # TODO(skowalak): For which locale are we crawling? What form do log
    # filenames have there? -> CLI flag with default value.
    if chat_files.is_dir():
        files = utils.crawl_directory_for_rooms(chat_files, "WhatsApp Chat mit *.txt")
    else:
        files = [chat_files]

    system_message_id = db["system_message_id"].get(1)
    for file in files:
        try:
            room = utils.parse_room_file(file)
            room_name = utils.get_room_name(file)
            utils.save_room(room, room_name, system_message_id, db)
            utils.debug_dump(room)
        except Exception as error:
            logger.warning("Uncaught exception during parsing: %s", str(error))
            errors = True
    if force_erase and not errors:
        # TODO(skowalak): save files that have been successfully imported so we
        # don't erase rooms that failed with errors.
        # TODO(skowalak): Maybe populate a table with filenames and hashes?
        logger.info("Erasing imported data")

    if errors:
        print(
            (
                "Warning: Errors occurred during import. No files were deleted."
                "Check the logs for more info, and try to run again with the -v"
                "option"
            )
        )
