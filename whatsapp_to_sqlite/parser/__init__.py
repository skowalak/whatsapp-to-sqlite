from whatsapp_to_sqlite.parser.parser_de_de import (
    MessageException,
    MessageParser,
    MessageVisitor,
    NoMatch,
    log,
    visit_parse_tree,
)

def get_parser_by_locale(locale: str) -> MessageParser:
    if locale == "de_de":
        return MessageParser
    else:
        raise NotImplementedError(f"No parser for locale {locale} could be found.")
