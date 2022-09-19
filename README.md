# whatsapp-to-sqlite
[![PyPI](https://img.shields.io/pypi/v/whatsapp-to-sqlite.svg)](https://pypi.org/project/whatsapp-to-sqlite/)
[![Tests](https://github.com/skowalak/whatsapp-to-sqlite/actions/workflows/test.yml/badge.svg)](https://github.com/skowalak/whatsapp-to-sqlite/actions?query=workflow%3Atest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/skowalak/whatsapp-to-sqlite/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Save your exported plaintext message logs to an SQLite database.

## How to install

    $ pip install whatsapp-to-sqlite
    
Upgrade with
    
    $ pip install --upgrade whatsapp-to-sqlite

## Supported locales/languages

* ✅ de_DE (german, germany)
* 🔧 en_US (english, USA) work in progress

## My `locale` is not supported, what can I do?

WhatsApp chat exports differ across installs in different languages/locales. To
support more locales, this project needs example export files from these
locales.

It is not complicated to add your own parser configuration for a different
locale, so if you want to use `whatsapp-to-sqlite` with an unsupported locale,
you are very welcome to open a PR. See `CONTRIBUTING.md` for more information.

If you have no idea how to work on adding locale support, you can always open
an issue and I will look into it if and when I have the time. This can take a
long time.

## Why is there a "transform" phase?

One of the design goals of the _datasette_ project, as I understand it, is to
keep as close as possible to the original data structures. Yet,
`whatsapp-to-sqlite` contains an additional _transform_-phase, where the data
parsed from chat logs changes quite a bit. Private Chats and Group Chats get
generalized into "Rooms", User Messages and System Notifications get
generalized into "Events". This transformation is **not lossless**! (More on
that in the next section).

So why is there a transformation here? I found the WhatsApp export format quite
hard to work with and decided to stick to a simpler data model, inspired by the
[Matrix][matrix-org]-Project. If you do not want transformed data and would
like the data in the most original state possible, you can pass the
`--do-not-transform`-flag (work-in-progress 🔧) during extraction and no
transformation will be done.

### What happens during transform?

1. Some WhatsApp System-Messages will be merged. E.g. if someone gets kicked
   from or leaves a room, I found there are 5 different system messages
   WhatsApp uses to report that. These all get merged into the same type of
   "someone left a room" event, which also contains the reason ("leave" or
   "kick").
2. If a path to exported media files is available (given using the
   `--data-directory` option), those will be searched whenever a message
   containing a file is found. If no file with the right filename is found, it
   will be marked as missing in the event. If a file is found, its hash will be
   computed and added to the event.

## Data Model

tbd

## Media files (Audio Messages, Images, Documents, Videos and other files

* Explain database schema and original WhatsApp Database schema

[matrix-org]: https://matrix.org
