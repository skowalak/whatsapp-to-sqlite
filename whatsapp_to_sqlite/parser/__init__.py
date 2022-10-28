from whatsapp_to_sqlite.parser.parser_de_de import (
    MessageException,
    MessageParser,
    MessageVisitor,
    NoMatch,
    log,
    visit_parse_tree,
)


def get_room_name_by_locale(room_file_name: str, locale: str) -> str:
    if locale == "de_de":
        room_name = re.search(r"WhatsApp Chat mit (.*)", room_file_name).group(1)
        return room_name

    raise NotImplementedError(
        f"No room name could be matched for {room_file_name} and {locale=}."
    )


def get_chat_file_glob_by_locale(locale: str) -> str:
    if locale == "de_de":
        return "WhatsApp Chat mit *.txt"

    raise NotImplementedError(f"No file glob for locale {locale} could be found.")


def get_parser_by_locale(locale: str) -> MessageParser:
    if locale == "de_de":
        return MessageParser

    raise NotImplementedError(f"No parser for locale {locale} could be found.")
