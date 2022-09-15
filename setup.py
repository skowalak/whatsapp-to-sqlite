from setuptools import setup
import os
VERSION = "0.1"

def get_long_description():
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
        encoding="utf8",
    ) as fp:
        return fp.read()


setup(
    name="whatsapp-to-sqlite",
    description="Convert your exported plaintext message logs to an SQLite database.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    author="Sebastian Kowalak",
    author_email="skowalak@techfak.uni-bielefeld.de",
    url="https://github.com/skowalak/whatsapp-to-sqlite",
    license="Apache License, Version 2.0",
    version=VERSION,
    packages=["whatsapp_to_sqlite"],
    entry_points="""
        [console_scripts]
        whatsapp-to-sqlite=whatsapp_to_sqlite.cli:cli
    """,
    install_requires=["click", "sqlite-utils>=2.7.2", "arpeggio", "marshmallow"],
    extras_require={"test": ["pytest"]},
    tests_require=["whatsapp-to-sqlite[test]"],
)
