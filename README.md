# whatsapp-to-sqlite
[![PyPI](https://img.shields.io/pypi/v/whatsapp-to-sqlite.svg)](https://pypi.org/project/whatsapp-to-sqlite/)
[![Tests](https://github.com/skowalak/whatsapp-to-sqlite/workflows/test/badge.svg)](https://github.com/skowalak/whatsapp-to-sqlite/actions?query=workflow%3Atest)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/skowalak/whatsapp-to-sqlite/blob/master/LICENSE)

Save your exported plaintext message logs to an SQLite database.

## How to install

    $ pip install whatsapp-to-sqlite
    
Upgrade with
    
    $ pip install --upgrade whatsapp-to-sqlite

## Customize the parser

WhatsApp message exports will differ according to your system's locale and/or
language. E.g, an export from a device with settings for Germany has a
timstamp formatted like this: `dd.mm.yy, HH:MM` while a device with US-settings
will have a timestamp formatted like this: `mm/dd/yy, HH:MM`.

Chat events like some person adding another person to a group or changing their
phone number will be in the devices default language:

**You were added to some group:**
```
German: <timestamp> - <admin_name> hat dich hinzugefügt.
English (US): <timestamp> - <admin_name>
```

To customize the parser according to your needs, just add your
location/language combination to the `parser.py` if not already there.

## TODOs

* Explain database schema and original WhatsApp Database schema
* Add and explain migration from WhatsApp DB to Matrix DB if possible
* Add content-addressable-storage
  * find sensible hashing algorithm with minimal collisions
