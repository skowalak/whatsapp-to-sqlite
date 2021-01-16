import datetime
import os
import sqlite_utils

import click

from whatsapp_to_sqlite import utils


@click.group()
@click.version_option()
def cli():
    "Convert your exported plaintext message logs to an SQLite database."


@cli.command()
@click.argument(
    "db_path",
    type=click.Path(file_okay=True, dir_okay=False, allow_dash=False),
    required=True,
)
@click.argument(
    "log_directory",
    type=click.Path(file_okay=False, dir_okay=True, allow_dash=True),
    help="Directory with all exported text files",
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
    help="Erase redundant files in the database",
)
def run_import(db_path, log_directory, data_directory, force_erase):
    db = sqlite_utils.Database(db_path)
    utils.crawl_directory(db, log_directory)
    utils.import_data(db, data_directory)
    utils.connect_data()
    utils.deduplicate_data()
    if force_erase:
        utils.clean_redundant_data()
