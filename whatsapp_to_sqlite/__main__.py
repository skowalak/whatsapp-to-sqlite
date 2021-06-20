import sys

from whatsapp_to_sqlite import cli


def main():
    """Make runnable as module."""
    cli.cli(sys.argv[1:])


if __name__ == '__main__':
    main()
