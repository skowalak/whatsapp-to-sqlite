import datetime
import logging
import os
import shutil
import time

from pathlib import Path

import click
import sqlite_utils

from whatsapp_to_sqlite import utils
from whatsapp_to_sqlite.parser import MessageException


@click.group()
@click.version_option()
def cli():
    """
    Convert your exported plaintext message logs to an SQLite database.
    """


@cli.command(name="import-chats")
@click.argument(
    "chat_files",
    type=click.Path(
        file_okay=True,
        dir_okay=True,
        allow_dash=False,
        resolve_path=True,
        path_type=Path,
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
        path_type=Path,
    ),
    required=False,
)
@click.option(
    "-l",
    "--locale",
    default="de_de",
    type=str,
    help=("Locale for which the files will be parsed."),
    required=False,
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Be more verbose when logging errors.",
)
def run_import(
    chat_files: Path,
    db_path: Path,
    locale: str,
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

    logger.debug("chats path: %s, db path: %s, data dir: %s", chat_files, db_path)
    if db_path.exists():
        logger.warning("Database file at %s already exists! Creating backup.", db_path)
        utils.make_db_backup(db_path, logger)

    db = sqlite_utils.Database(db_path)
    utils.init_db(db, logger)

    errors = False
    system_message_id = utils.get_system_message_id(db)
    if chat_files.is_dir():
        files = utils.crawl_directory(chat_files, locale)
    else:
        files = [chat_files]

    system_message_id = db["system_message_id"].get(1)
    logger.info("Parsing %s chat files.", len(files))
    with click.progressbar(
        length=len(files) * 2,
        label="",
        item_show_func=lambda x: x,
    ) as bar_files:
        for file in files:
            room = None
            try:
                logger.debug("Starting to parse file %s.", file)
                room_name = utils.get_room_name(file)
                logger.debug("Found room: %s.", room_name)
                room = utils.parse_room_file(file, locale, logger)
                bar_files.update(1, f'Saving "{room_name}" to database.')
            except MessageException as error:
                logger.warning(
                    "Parsing exception:\n  In file %s:\n  %s.",
                    error.file_path,
                    str(error.__cause__),
                )
                errors = True
            except Exception as error:
                logger.warning("Uncaught exception during parsing: %s", str(error))
                errors = True
            try:
                utils.save_room(room, room_name, system_message_id, db)
                # utils.debug_dump(room)
                bar_files.update(1)  # , f"Saving \"{room_name}\" to database.")
            except Exception as error:
                # FIXME(skowalak): Remove this clause completely
                logger.error("Uncaught error while saving: %s", str(error))
                errors = True

    if errors:
        logger.warning(
            "Warning: Errors occurred during import.\n"
            "Check the logs for more info, and try to run again with the -v "
            "option."
        )


@cli.command(name="import-media")
@click.argument(
    "data_directory",
    type=click.Path(resolve_path=True, path_type=Path),
    required=True,
)
@click.argument(
    "db_path",
    default="messagedb.sqlite3",
    type=click.Path(dir_okay=False, resolve_path=True, path_type=Path),
    required=False,
)
@click.option(
    "-o",
    "--output-directory",
    default="messagedb_files",
    type=click.Path(file_okay=False, resolve_path=True, path_type=Path),
    help=("Path to directory, where processed media will be copied to."),
    required=False,
)
@click.option(
    "-e",
    "--erase",
    is_flag=True,
    help="Generate list of erasable filenames after exporting them to target directory.",
)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Be more verbose when logging errors.",
)
def run_media_import(
    data_directory: Path,
    db_path: Path,
    output_directory,
    erase=False,
    verbose=False,
):
    """
    Import a media file or a directory of media files into an existing SQLite3
    message database at DB_PATH.

    If an output directory is specified, imported media will be renamed and
    copied there.
    """
    loglevel = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(format="%(message)s", level=loglevel)
    logger = logging.getLogger(__name__)

    logger.debug("db path: %s, data dir: %s", db_path, data_directory)
    logger.debug(
        "options: output_dir: %s, erase: %s, verbose %s",
        output_directory,
        erase,
        verbose,
    )

    if not db_path.exists():
        # TODO(skowalak): init db II
        logger.error("Database file does not exist: %s.", db_path)
        exit(-1)

    logger.info("Database found at %s.", db_path)
    utils.make_db_backup(db_path, logger)
    db = sqlite_utils.Database(db_path)

    if not (data_directory and data_directory.exists()):
        logger.error("data_directory %s does not exist: %s.", data_directory)

    logger.debug("Data directory %s specified. Searching now.", data_directory)
    files = utils.crawl_directory(data_directory)
    utils.import_media_to_db(files, db, logger)
    # TODO(skowalak): Match media files
    # utils.update_files_in_db(db, logger)

    if erase:
        logger.info("Generating list of imported files.")
