#from whatsapp_to_sqlite import parser
#import pytest

# Locale: German
# Time Format: dotted, 24h
LOCALE_DE = {
    "SINGLE_LINE_MESSAGE": "16.01.21, 23:09 - John Doe: WhatsApp Chatlogs are definetly no fun :/",
    "MULTI_LINE_MESSAGE": "16.01.21, 23:10 - John Doe: Good Log parsing is mandatory.\nBut annoying.\n\nLike really annoying.",
    "ATTACHED_FILE_SINGLE_LINE_MESSAGE": "16.01.21, 23:09 - John Doe: abcdefgh.jpg (Datei angehängt)",
    "ATTACHED_FILE_MULTI_LINE_MESSAGE": "16.01.21, 23:09 - John Doe: abcdefgh.jpg (Datei angehängt)\nPotato Salad.",
    "ATTACHED_FILE_BROKEN_LINK": "16.01.21, 23:09 - John Doe: <Medien ausgeschlossen>",
    "SYS_MSG": "16.01.21, 23:19 - Nachrichten, die du in diesem Chat sendest, sowie Anrufe, sind jetzt mit Ende-zu-Ende-Verschlüsselung geschützt. Tippe für mehr Infos.",
}
