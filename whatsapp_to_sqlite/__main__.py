import sys
import json
import os

from whatsapp_to_sqlite import cli, arPEGgio


def parse_single_file(filename=None, path=None):
    filepath = os.path.join(path, filename)

    with open(filepath, "r", encoding="utf-8") as logfile:
        return arPEGgio.parse(logfile)


def debug_dump(msglist: list) -> None:
    from whatsapp_to_sqlite.messages import Message
    from datetime import datetime
    def json_serial(obj):
        if isinstance(obj, Message):
            return obj.toDict()

        if isinstance(obj, datetime):
            return obj.isoformat()

    print(json.dumps(msglist, indent=2, default=json_serial, sort_keys=True))


def main():
    fname="WhatsApp Chat mit Die üblichen Verdächtigen.txt"
    # fname="eg.txt"
    # fname="WhatsApp Chat mit eiergilde.net Eiergilde.txt"
    
    chat_messages = parse_single_file(
        filename=fname,
        path="tests/logs",
    )

    debug_dump(chat_messages)


if __name__ == "__main__":
    main()
