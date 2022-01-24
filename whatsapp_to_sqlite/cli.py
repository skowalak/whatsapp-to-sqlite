import datetime
import os
import logging
import sqlite_utils

import click

from whatsapp_to_sqlite import utils

LOG = logging.getLogger(__name__)


@click.group()
@click.version_option()
def cli():
    """Convert your exported plaintext message logs to an SQLite database."""


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument(
    "log_directory",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=True),
    required=True,
)
@click.option(
    "-d",
    "--data-directory",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=False),
    default="data",
    help="Path(s) which contain additional exported media",
)
@click.option(
    "-e",
    "--force-erase",
    is_flag=True,
    help="Erase files after exporting them to target directory",
)
def run_import(db_path, log_directory, data_directory, force_erase=False):
    LOG.debug(db_path, log_directory, data_directory, force_erase)
    db = sqlite_utils.Database(db_path)
    files = utils.crawl_directory_for_rooms(log_directory)
    for file in files:
        room = utils.parse_room_file(file)
    if force_erase:
        # TODO(skowalak): save files that have been successfully imported so we
        # don't erase rooms that failed with errors.
        LOG.info("Erasing imported data")


def read_files(filenames, db):
    for filename in filenames:
        read_file(filename, db)


def read_file(filename, db):
    LOG.info("File: ", filename)
    messages = utils.parse(utils.tokenize(filename))
    for message in messages:
        utils.store_message(message, db)
        utils.store_ids(0)
