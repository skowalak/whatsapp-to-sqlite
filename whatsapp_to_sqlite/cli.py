import datetime
import os
import logging
import sqlite_utils

import click

from whatsapp_to_sqlite import utils


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
    print(db_path, log_directory, data_directory, force_erase)
    db = sqlite_utils.Database(db_path)
    filenames = []
    for subdir, dirs, files in os.walk(log_directory):
        for filename in files:
            filenames.append(os.path.join(subdir, filename))
    read_files(filenames, db)
    if force_erase:
        logging.info("reached deduplication")
        print("utils.dedup_data()")


def read_files(filenames, db):
    for filename in filenames:
        read_file(filename, db)


def read_file(filename, db):
    print("File: ", filename)
    messages = utils.parse(utils.tokenize(filename))
    for message in messages:
        utils.store_message(message, db)
        utils.store_ids(0)
