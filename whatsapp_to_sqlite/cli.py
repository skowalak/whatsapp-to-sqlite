import datetime
import logging
import os
import pathlib
import shutil

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
    type=click.Path(file_okay=True, dir_okay=True, allow_dash=True),
    required=True,
)
@click.argument(
    "db_path",
    default="messagedb.sqlite3",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=False,
)
@click.option(
    "-d",
    "--data-directory",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
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
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
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
    chat_files,
    db_path,
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
    if pathlib.Path(db_path).exists():
        logger.warning("Database file at %s already exists! Creating backup.")
        try:
            shutil.copy2(db_path, f"{db_path}.{time.time()}.bkp")
        except OSError as error:
            logger.error("Cannot write backup database file: %s", str(error))
            raise click.ClickException(
                "Database file already exists, cannot write backup file."
            )
    db = sqlite_utils.Database(db_path)
    # TODO(skowalak): check if database already has correct schema. if not,
    # initialize tables

    errors = False
    # TODO(skowalak): For which locale are we crawling? What form do log
    # filenames have there? -> CLI flag with default value.
    files = utils.crawl_directory_for_rooms(chat_files)
    for file in files:
        try:
            room = utils.parse_room_file(file)
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
