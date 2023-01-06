# pylint: disable=logging-fstring-interpolation
import logging
import locale
import sys

from pathlib import Path

import click
import rich
import rich.progress
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
    "locale_opt",
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
    locale_opt: str,
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

    logger.debug("chats path: %s, db path: %s", chat_files, db_path)
    if db_path.exists():
        logger.warning("Database file at %s already exists! Creating backup.", db_path)
        utils.make_db_backup(db_path, logger)

    db = sqlite_utils.Database(db_path)
    utils.init_db(db, logger)

    errors = False
    system_message_id = utils.get_system_message_id(db)
    if chat_files.is_dir():
        files = utils.crawl_directory_for_chat_files(chat_files, locale_opt)
    else:
        files = [chat_files]

    with rich.progress.Progress(
        rich.progress.SpinnerColumn(spinner_name="dots10"),
        *rich.progress.Progress.get_default_columns(),
        rich.progress.TimeElapsedColumn(),
        rich.progress.TextColumn("{task.fields[room]}"),
    ) as progress:
        padding = " " * 19
        all_files = progress.add_task("Import progress", total=len(files), room="")
        current_file_save = progress.add_task(padding, room="")

        print(f"Parsing {len(files):n} chat files.")
        for file in files:
            room = None
            try:
                room_name = utils.get_room_name(file, locale_opt)
                progress.update(all_files, room=room_name)
                progress.reset(current_file_save, total=3, description="Parsing")
                room = utils.parse_room_file(file, locale_opt, logger)
                progress.advance(current_file_save)

            except MessageException as error:
                logger.warning(
                    "Parsing exception:\n  In file %s:\n  %s.",
                    error.file_path,
                    str(error.__cause__),
                )
                errors = True
            except Exception as error:  # pylint: disable=broad-except
                logger.warning("Uncaught exception during parsing: %s", str(error))
                errors = True
            try:
                # TODO(skowalak): Message duplicate check via cli flag?
                progress.update(
                    current_file_save,
                    description="Processing",
                )
                utils.save_room(
                    room,
                    room_name,
                    system_message_id,
                    db,
                    progress_callback=lambda: progress.update(
                        current_file_save,
                        advance=1,
                        room="",
                        description="Inserting",
                    ),
                )

            except Exception as error:  # pylint: disable=broad-except
                # FIXME(skowalak): Remove this clause completely
                logger.error("Uncaught error while saving: %s", str(error))
                errors = True
            progress.update(all_files, advance=1, room="")

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
    "-l",
    "--list",
    "list_path",
    default="whatsapp_to_sqlite_deleteable",
    type=click.Path(file_okay=True, dir_okay=False, resolve_path=True, path_type=Path),
    help="Write paths of copied files to this file.",
    required=False,
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
    output_directory: Path,
    list_path: Path,
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

    locale.setlocale(locale.LC_ALL, "")

    logger.debug("db path: %s, data dir: %s", db_path, data_directory)
    logger.debug(
        "options: output_dir: %s, list_path: %s, verbose %s",
        output_directory,
        list_path,
        verbose,
    )

    if not db_path.exists():
        logger.error("Database file does not exist: %s.", db_path)
        sys.exit(-1)

    logger.info("Database found at %s.", db_path)
    utils.make_db_backup(db_path, logger)
    db = sqlite_utils.Database(db_path)

    if not (data_directory and data_directory.exists()):
        logger.error("data_directory %s does not exist.", data_directory)
        sys.exit(-1)

    logger.debug("Data directory %s specified. Searching now.", data_directory)
    files = utils.crawl_directory(data_directory)
    len_files = len(files)
    logger.info(f"Importing {len_files:n} files into database.")

    with rich.progress.Progress(
        rich.progress.SpinnerColumn(spinner_name="dots10"),
        rich.progress.TextColumn(
            "[progress.description]{task.description}", justify="right"
        ),
        rich.progress.BarColumn(),
        rich.progress.TaskProgressColumn(),
        rich.progress.TimeRemainingColumn(),
        rich.progress.TimeElapsedColumn(),
    ) as progress:

        padding = " " * 19
        all_steps = progress.add_task("All Tasks", total=4)
        import_step = progress.add_task(padding, total=len(files), start=False)
        dedup_step = progress.add_task(padding, total=1, start=False)
        match_step = progress.add_task(padding, total=len(files), start=False)
        move_step = progress.add_task(padding, total=len(files), start=False)

        progress.start_task(import_step)
        progress.update(import_step, description="Importing")
        utils.import_media_to_db(
            files,
            db,
            logger,
            progress_callback=lambda: progress.advance(import_step),
        )
        progress.advance(import_step, advance=len(files))
        progress.advance(all_steps)

        # check imported file recoreds for duplicates (same name, same hash, same size)
        progress.start_task(dedup_step)
        progress.update(dedup_step, description="Removing Duplicates")
        removed_files = utils.remove_media_duplicates(db)
        print(f"Removed {removed_files:n} duplicate files.")
        progress.update(dedup_step, completed=1.0)
        len_files_after_dedup = len_files - removed_files
        progress.advance(all_steps)

        progress.start_task(match_step)
        progress.update(match_step, description="Matching")
        utils.match_media_files(
            db,
            logger,
            set_progress_size=lambda size: progress.update(match_step, total=size),
            progress_callback=lambda: progress.advance(match_step),
        )
        progress.advance(all_steps)

        progress.start_task(move_step)
        progress.update(move_step, description="Copying Files")
        deleteable_files = utils.move_files(
            db,
            output_directory,
            logger,
            set_progress_size=lambda size: progress.update(move_step, total=size),
            progress_callback=lambda: progress.advance(move_step),
        )
        progress.advance(all_steps)

        utils.write_list_of_files(deleteable_files, list_path)
        print(f"Copied {len(deleteable_files)}. List written to {list_path}.")
