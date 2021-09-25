from arpeggio import *
from arpeggio.cleanpeg import ParserPEG
from arpeggio import RegExMatch as _

from datetime import datetime
from zoneinfo import ZoneInfo

import json

###############################################################################
# Grammar Definition
###############################################################################

def log(): return OneOrMore(message), EOF
def message(): return [start_with_header, continued_message]
#def message(): 
#    return [(message_header, [file_attached, file_excluded, message_text]),
#            (timestamp, " - ", system_event)]
def start_with_header(): 
    return timestamp, " - ", [user_gen, system_event]

#def message_header():
#    return timestamp, " - ", username

# timestamps: customize according to your locale
def timestamp(): return day, ".", month, ".", year, ", ", hour, ":", minute
def day(): return _(r"(\d\d)")
def month(): return _(r"(\d\d)")
def year(): return _(r"(\d\d)")
def hour(): return _(r"(\d\d)")
def minute(): return _(r"(\d\d)")

# text message: matches any text
def user_gen(): 
    return username, [file_attached, file_excluded, message_text]
def username(): return _(r"(.*?): ")
def file_attached(): return filename, " (Datei angehängt)", newline
def file_excluded(): return "<Medien ausgeschlossen>", newline
def filename(): return _(r"(.+\.\w+)")

# system event: customize according to your locale/system language
def system_event(): return any_text_with_newline

def message_text(): return any_text_with_newline
def continued_message(): return any_text_with_newline

def any_text(): return _(r"(.*)")
def any_text_with_newline(): return _(r"(.*\n)")
def newline(): return "\n"

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
        message_dict["message"] = message_text
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
        return message_dict

    def visit_continued_message(self, node, children):
        message_dict = {}
        message_dict["type"] = "continued"
        message_dict["content"] = str(node)
        return message_dict
    
    def visit_message(self, node, children):
        return children[0]

    def visit_log(self, node, children):
        print("=> LOG: ", children)
        return children



#logfile = open("tests/logs/WhatsApp Chat mit eiergilde.net Eiergilde.txt")
logfile = open("tests/logs/eg.txt")
logstring = logfile.read()
logfile.close()

parser = ParserPython(log, skipws=False, debug=True, memoization=True)
parse_tree = parser.parse(logstring)
result = visit_parse_tree(parse_tree, MessageVisitor(debug=True))
print(json.dumps(result, indent=2, default=str, sort_keys=True))

