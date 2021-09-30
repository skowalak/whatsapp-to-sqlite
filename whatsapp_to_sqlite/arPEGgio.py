from arpeggio import *
from arpeggio.cleanpeg import ParserPEG
from arpeggio import RegExMatch as _

from datetime import datetime
from zoneinfo import ZoneInfo

import json
import os.path

###############################################################################
# Grammar Definition
###############################################################################

def log(): return OneOrMore(message), EOF
def message(): 
    return [
        (timestamp, " - ", username, [file_attached,
                                      file_excluded,
                                      message_text], ZeroOrMore(continued_message)),
        (timestamp, " - ", room_event)]

# FIXME: Timestamp localization
def timestamp(): return day, ".", month, ".", year, ", ", hour, ":", minute
def day(): return _(r"(\d\d)")
def month(): return _(r"(\d\d)")
def year(): return _(r"(\d\d)")
def hour(): return _(r"(\d\d)")
def minute(): return _(r"(\d\d)")

def username(): return _(r"(.*?): ")
# FIXME: File attachment localization
def file_attached(): return filename, " (Datei angehängt)\n"
def file_excluded(): return "<Medien ausgeschlossen>\n"
def filename(): return _(r"(.+\.\w+)")

def message_text(): return any_text_with_newline
def continued_message(): return Not(timestamp), any_text_with_newline

def any_text_with_newline(): return _(r"(.*?\n)")

# FIXME: event localization
def room_event(): return any_text_with_newline

def room_create(): return username, " hat die Gruppe \"", groupname, "\" erstellt.\n"
def room_join(): return any_text_with_newline
def room_kick(): return any_text_with_newline
def room_leave(): return any_text_with_newline
def number_change(): return any_text_with_newline


###############################################################################
# End of Grammar Definition
###############################################################################

class MessageVisitor(PTNodeVisitor):
    def visit_timestamp(self, node, children):
        # prepend century (thank god whatsapp did not exist before 2000 a.D.
        century = "20"
        year = int(century + children[2])
        month = int(children[1])
        day = int(children[0])
        hours = int(children[3])
        minutes = int(children[4])
        timezone = ZoneInfo("Europe/Berlin")
        timestamp = datetime(year, month, day, hours, minutes, tzinfo=timezone)
        return timestamp
    
    def visit_username(self, node, children):
        """
        Strip trailing colon and space chars from username
        """
        name_without_colon = str(node)[0:len(str(node)) - 2]
        return name_without_colon

    def visit_user_gen(self, node, children):
        user_author = children[0]
        message_text = children[1]
        message_dict = {}
        message_dict["user"] = user_author
        message_dict["content"] = message_text
        message_dict["type"] = "message"
        return message_dict

    def visit_file_excluded(self, node, children):
        message_dict = {}
        message_dict["file"] = True
        message_dict["file_lost"] = True
        return message_dict

    def visit_file_attached(self, node, children):
        message_dict = {}
        message_dict["file"] = True
        message_dict["filename"] = children[0]
        message_dict["file_lost"] = False
        return message_dict

    def visit_message_text(self, node, children):
        message_dict = {}
        message_dict["text"] = str(node)
        return message_dict

    def visit_start_with_header(self, node, children):
        timestamp = children[0]
        message_dict = children[1]
        message_dict["timestamp"] = timestamp
        return message_dict

    def visit_system_event(self, node, children):
        message_dict = {}
        message_dict["type"] = "system"
        message_dict["content"] = node
        return message_dict

    def visit_continued_message(self, node, children):
        return str(node)
    
    def visit_message(self, node, children):
        message = children[0]
        if len(children) > 1 and message["type"] == "message":
            message_text = message["content"]
            # More than one child node -> more than one line of content
            additional_lines = children[1:]
            for line in additional_lines:
                try:
                    message_text["text"] = message_text.get("text", "") + line
                except KeyError as e:
                    print(message_text)
                    print(line)
                    raise e


        #print("\n", json.dumps(message, indent=2, default=str), "\n")
        return message

    def visit_log(self, node, children):
        #TODO: Iterate over messages and load
        return children



def parse_single_file(filename=None, path=None):
    #logfile = open("tests/logs/WhatsApp Chat mit eiergilde.net Eiergilde.txt")
    #logfile = open("tests/logs/eg.txt")
    filepath = os.path.join(path, filename)
    print(filepath)
    logfile = open(filepath)

    with open(filepath, "r", encoding="utf-8") as logfile:
        logstring = logfile.read()
        parser = ParserPython(log, skipws=False, debug=True, memoization=True)
        parse_tree = parser.parse(logstring)
        result = visit_parse_tree(parse_tree, MessageVisitor(debug=True))
        return result


