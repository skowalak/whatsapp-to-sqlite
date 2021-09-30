import sys

from whatsapp_to_sqlite import cli


def main():
    """Make runnable as module."""
    #cli.cli(sys.argv[1:])
    from whatsapp_to_sqlite.arPEGgio import parse_single_file
    chat_messages = parse_single_file(
        filename="WhatsApp Chat mit Die üblichen Verdächtigen.txt",
        #filename="eg.txt",
        #filename="WhatsApp Chat mit eiergilde.net Eiergilde.txt",
        path = "tests/logs"
    )
    print(json.dumps(chat_messages, indent=2, default=str, sort_keys=True))


if __name__ == '__main__':
    main()
