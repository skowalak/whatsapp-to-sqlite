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

## Why are there so many message types?

One of the design goals of the _datasette_ project, as I understand it, is to
keep as close as possible to the original data structures. While writing the
parser, I found e.g. there are 5 different system messages WhatsApp uses to
handle someone getting kicked from a room/dm (in the text exports, anyway).

I believe _the hard part_ of this script is the parsing and if one wanted to
use this database to export chat data from WhatsApp to another chat system
(e.g. Matrix) it should be possible to do so, **because** it is so close to the
original data format.

## What happens to my files, those are not part of the txt export?!

WhatsApp-Messages that have a file attachment are represented in the export
files with the first line of the message containing the file name and a short
notice if the file was included in the export. If the file was not included in
the export, instead of the file name there will be a notice that no media was
included in the export. That is a little frustrating, because then there is no
reliable way to match media files to those messages.

When a directory containing files that match the exported file names is give to
`whatsapp-to-sqlite` via the `--data-directory` option, the script will iterate
all these files to match them against the database. All matched files will be
addressed by their `sha512` digest in the database and copied to a target
directory. In case of ambiguity (i.e. two files in separate sub-directories of 
the data directory have the same name), those files will be skipped.

## Data Model

* All messages are contained in the `message` table. To distinguish between
  differen message types a discriminator value is given in the `type` column.
  Primary key is an UUID.
* To maintain ordering of messages, even with the same timestamp, the original
  order of messages (of the text export) is retained by creating a graph of
  message UUIDs in `message_x_message` between parent and child messages. For
  easier matching, the `message` table contains a `depth` value with a strict
  ordering of messages in the same room.
* Files are referenced by an UUID primary key and contained in the `file`
  table. If a file was imported, it has a `sha512` digest, mime type, preview
  thumbnail depending on its file type and a size. Otherwise it may or may not
  have a filename.
* All senders except the first person sender (referenced as "You" in the text
  export) are listed in the `sender` table with an UUID and their name **or**
  number, depending on which was included in the text export.
  To fuse senders, update the `sender_id` foreign key in all relevant message
  rows.
* For the first person sender (only relevant for system messages like "you
  kicked <name> from the group") a special UUID is saved with primary key 1 in
  the table `system_message_id`.
* A room is a representation of a direct-message chat (dm) or a group. If it
  could be detected as a group chat by looking at the first few messages, the
  `is_dm` flag will be set as `false` / 0. The first message in a room, i.e.
  the root is saved in `first_message`. A room image can be set in the `file`
  table and referenced in `display_img`. EXPERIMENTAL: A member type can be
  determined by iterating the room messages and counting all senders while
  considering all kicks and leaves.

[matrix-org]: https://matrix.org
