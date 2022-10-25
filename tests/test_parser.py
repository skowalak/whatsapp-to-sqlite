import datetime
import pytest
import logging
import zoneinfo
from unittest import mock

from whatsapp_to_sqlite import utils
from whatsapp_to_sqlite.messages import (
    RoomMessage,
    RoomE2EEnabledNotification
)


def dt_help(isotime: str, dst: bool = False) -> datetime.datetime:
    isotime = isotime + f":00+0{2 if dst else 1}:00"
    return datetime.datetime.fromisoformat(isotime)


# Locale: de_DE, (german)
# Time Format: dotted, 24h
LOCALE_DE1 = {
    "SYS_MSG": "16.01.21, 23:19 - Nachrichten, die du in diesem Chat sendest, sowie Anrufe, sind jetzt mit Ende-zu-Ende-Verschlüsselung geschützt. Tippe für mehr Infos.",
}

LOCALE_DE = [
    (
        "16.01.21, 23:09 - John Doe: WhatsApp Export Syntax is hard :/ 🤐\n",
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:09"),
            sender="John Doe",
            text="WhatsApp Export Syntax is hard :/ 🤐\n",
        ),
    ),
    (
        # Bug: Some chat log files do not have EOL at the end of the file
        "16.01.21, 23:09 - John Doe: This message does not have a newline -> ",
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:09"),
            sender="John Doe",
            text="This message does not have a newline -> \n",
        ),
    ),
    (
        "16.01.21, 23:10 - John Doe: This is a multi-\nline message.\n\nAyy\n",
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:10"),
            sender="John Doe",
            text="This is a multi-\n",
            continued_text="line message.\n\nAyy\n",
        ),
    ),
    (
        # Message with file attachment without additional text
        "16.01.21, 23:11 - John Doe: abcdefgh.jpg (Datei angehängt)\n",
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:11"),
            sender="John Doe",
            text=None,
            file=True,
            filename="abcdefgh.jpg"
        ),
    ),
    (
        # Message with file attachment with additional text
        ("16.01.21, 23:12 - John Doe: abcdefgh.jpg (Datei angehängt)\n"
         "This is a comment to the file I just sent\n"),
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:12"),
            sender="John Doe",
            text=None,
            file=True,
            filename="abcdefgh.jpg",
            continued_text="This is a comment to the file I just sent\n",
        ),
    ),
    (
        # Message with missing file attachment and no comment
        "16.01.21, 23:14 - John Doe: <Medien ausgeschlossen>\n",
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:14"),
            sender="John Doe",
            text=None,
            file=True,
            file_lost=True,
        ),
    ),
    (
        # Message with missing file attachment and added comment
        ("16.01.21, 23:15 - John Doe: <Medien ausgeschlossen>\n"
         "This is a comment to the (missing) file I just sent\n"),
        RoomMessage(
            timestamp=dt_help("2021-01-16T23:15"),
            sender="John Doe",
            text=None,
            file=True,
            file_lost=True,
            continued_text="This is a comment to the (missing) file I just sent\n",
        ),
    ),
    (
        # Notification when WhatsApp got E2E encryption
        "16.01.21, 23:16 - Nachrichten, die du in diesem Chat sendest, sowie Anrufe, sind jetzt mit Ende-zu-Ende-Verschlüsselung geschützt. Tippe für mehr Infos.\n",
        RoomE2EEnabledNotification(
            timestamp=dt_help("2021-01-16T23:16"),
        ),
    ),


]


class TestHelpers:
    def test_dt_help_hp(self):
        isotime = "2022-01-01T13:37"
        dt_time = dt_help(isotime)

        expected = datetime.datetime(
            2022, 1, 1, 13, 37, 0, tzinfo=zoneinfo.ZoneInfo("Europe/Berlin")
        )
        assert dt_time == expected


class TestParser:
    @pytest.mark.parametrize("raw, expected", LOCALE_DE)
    def test_message_types_de_de(self, raw, expected, logger):
        messages = utils.parse_string(raw, "de_de", logger)

        assert len(messages) == 1

        message = messages[0]
        # ignore full_text attribute, because it is not really relevant (and if
        # it will become relevant it will be tested separately).
        message.full_text = None
        assert message == expected
