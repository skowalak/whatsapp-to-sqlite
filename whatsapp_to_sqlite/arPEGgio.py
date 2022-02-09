from arpeggio import *
from arpeggio.cleanpeg import ParserPEG
from arpeggio import RegExMatch as _

from datetime import datetime
from zoneinfo import ZoneInfo

from whatsapp_to_sqlite.messages import (
    Message,
    UserMessage,
    SystemMessage,
    RoomCreate,
)

###############################################################################
# Grammar Definition
###############################################################################


def log():
    return OneOrMore(message), EOF


def message():
    return [user_message, system_message]

def user_message():
    return (
        timestamp,
        " - ",
        username,
        ": ",
        [file_attached, file_excluded, message_text],
        ZeroOrMore(continued_message)
    )

def system_message():
    return timestamp, " - ", system_event


# FIXME: Timestamp localization
def timestamp():
    return day, ".", month, ".", year, ", ", hour, ":", minute


def day():
    return _(r"(\d\d)")


def month():
    return _(r"(\d\d)")


def year():
    return _(r"(\d\d)")


def hour():
    return _(r"(\d\d)")


def minute():
    return _(r"(\d\d)")


def username():
    return _(r".*?(?=:)")


def name():
    return _(r"(.*)")


# FIXME: File attachment localization
def file_attached():
    return filename, " (Datei angehängt)\n"


def file_excluded():
    return "<Medien ausgeschlossen>\n"


def filename():
    return _(r"(.+\.\w+)")


def message_text():
    return any_text_with_newline


def continued_message():
    return Not(timestamp), any_text_with_newline


def any_text_with_newline():
    return _(r"(.*?\n)")


# FIXME(skowalak): event localization
def system_event():
    return [
        room_create_t,
        room_create_f,
        room_join_t_t,
        room_join_t_t2,
        room_join_t_f,
        room_join_f_t,
        room_kick_t_t,
        room_kick_t_t2,
        room_kick_t_f,
        room_kick_f_t1,
        room_leave_t,
        room_leave_f,
        number_change1,
        number_change2,
        room_name_t,
        room_name_f,
        room_avatar_t,
        room_avatar_f,
        room_avatar_delete_t,
        room_avatar_delete_f,
        admin_promotion,
#        any_text_with_newline
    ]


# Notation:
# <event>_t_t = a Third party did something to a Third Party
# <event>_t_f = a Third party did something to you (First party)
# <event>_f_t = you (First party) did something to a Third party

# Create room
def room_create_t():
    return _(r".+?(?= hat)"), " hat die Gruppe \"", _(r".+?(?=\" erstellt)"), "\" erstellt.\n"


def room_create_f():
    return "Du hast die Gruppe \"", _(r".+?(?=\" erstellt)"), "\" erstellt.\n"

# Join / Adds to a room
def room_join_t_t():
    #return name, " hat ", Not("dich"), name, " hinzugefügt.\n"
    return _(r"(.*) hat (.*) hinzugefügt.\n")


def room_join_t_f():
    #return name, " hat dich hinzugefügt.\n"
    return _(r"(.*) hat dich hinzugefügt.\n")


def room_join_f_t():
    #return "Du hast ", name, " hinzugefügt.\n"
    return _(r"Du hast (.*) hinzugefügt.\n")


def room_join_t_t2():
    return _(r"(.*) wurde hinzugefügt.\n")


# Kick / Leaves from a room
def room_kick_t_t():
    #return name, " hat ", Not("dich"), name, " entfernt.\n"
    return _(r"(.*) hat (.*) entfernt.\n")


def room_kick_t_f():
    #return name, " hat dich entfernt.\n"
    return _(r"(.*) hat dich entfernt.\n")


def room_kick_f_t1():
    #return "Du hast ", name, " entfernt.\n"
    return _(r"Du hast (.*) entfernt.\n")


def room_kick_t_t2():
    #return name, " wurde entfernt.\n"
    return _(r"(.*) wurde entfernt.\n")


def room_leave_t():
    #return name, " hat die Gruppe verlassen.\n"
    return _(r"(.*) hat die Gruppe verlassen.\n")


def room_leave_f():
    #return "Du hast die Gruppe verlassen.\n"
    return "Du hast die Gruppe verlassen.\n"


def number_change1():
    #return name, " hat zu ", name, " gewechselt.\n"
    return _(r"(.*) hat zu (.*) gewechselt.\n")


def number_change2():
    #return (
    #    name, 
    #    (" hat eine neue Telefonnummer. Tippe, um eine Nachricht zu "
    #    "schreiben oder die neue Nummer hinzuzufügen.\n")
    #)
    return _(r"(.*) hat eine neue Telefonnummer. Tippe, um eine Nachricht zu "
            "schreiben oder die neue Nummer hinzuzufügen.\n")


# Room Modification
def room_name_t():
    #return (
    #    name,
    #    " hat den Betreff von \"",
    #    name,
    #    "\" zu \"",
    #    name,
    #    "\" geändert.\n")
    return _(r"(.*) hat den Betreff von \"(.*)\" zu \"(.*)\" geändert.\n")

def room_name_f():
    #return "Du hast den Betreff von \"", name, "\" zu \"", name, "\" geändert.\n"
    return _(r"Du hast den Betreff von \"(.*)\" zu \"(.*)\" geändert.\n")


def room_avatar_t():
    return _(r"(.*) hat das Gruppenbild geändert.\n")


def room_avatar_f():
    return "Du hast das Gruppenbild geändert.\n"


def room_avatar_delete_t():
    #return name, " hat das Gruppenbild gelöscht.\n"
    return _(r"(.*) hat das Gruppenbild gelöscht.\n")


def room_avatar_delete_f():
    return "Du hast das Gruppenbild gelöscht.\n"


def admin_promotion():
    return "Du bist jetzt ein Admin.\n"


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
        return str(node)

    # BEGIN system events
    def visit_system_event(self, node, children):
        full_text = str(node)
        if children and isinstance(children[0], Message):
            msg = children[0]
            msg.full_text = full_text
            return msg

        return SystemMessage(full_text=full_text)
        
    def visit_room_create_t(self, node, children):
        return RoomCreate(sender=children[0], room_name=children[1])
    
    def visit_room_create_f(self, node, children):
        pass

    def visit_room_join_t_t(self, node, children):
        pass

    def visit_room_join_t_f(self, node, children):
        pass

    def visit_room_join_f_t(self, node, children):
        pass

    def visit_room_kick_t_t(self, node, children):
        pass
    
    def visit_room_kick_t_t2(self, node, children):
        pass

    def visit_room_kick_t_f(self, node, children):
        pass

    def visit_room_kick_f_t1(self, node, children):
        pass

    def visit_room_leave_t(self, node, children):
        pass

    def visit_room_leave_f(self, node, children):
        pass

    def visit_number_change1(self, node, children):
        pass

    def visit_number_change2(self, node, children):
        pass

    def visit_room_name_t(self, node, children):
        pass

    def visit_room_name_f(self, node, children):
        pass

    def visit_room_avatar_t(self, node, children):
        pass

    def visit_room_avatar_f(self, node, children):
        pass

    def visit_room_avatar_delete_t(self, node, children):
        pass

    def visit_room_avatar_delete_f(self, node, children):
        pass

    def visit_admin_promotion(self, node, children):
        pass

    # END system events
    
    def visit_file_excluded(self, node, children):
        return {
            "file": True,
            "filename": None,
            "file_lost": True
        }

    def visit_file_attached(self, node, children):
        return {
            "file": True,
            "filename": children[0],
            "file_lost": False
        }

    def visit_message_text(self, node, children):
        return {"text": str(node)}



    def visit_continued_message(self, node, children):
        return {"continuted_text": str(node)}


    def visit_user_message(self, node, children):
        msgdict = {}
        for child in children[2:]:
            msgdict.update(child)

        msg = UserMessage(
            timestamp=children[0],
            full_text=str(node),
            sender=children[1],
            text=msgdict.get("text"),
            continued_text=msgdict.get("continued_text"),
            filename=msgdict.get("filename"),
            file_lost=msgdict.get("file_lost"),
            file=msgdict.get("file", False)
        )
        return msg


    def visit_system_message(self, node, children):
        msg = children[1]
        msg.timestamp = children[0]
        return msg


    def visit_message(self, node, children):
        return children[0]
            

    def visit_log(self, node, children):
        return children


def parse(f) -> list[Message]:
    logstring = f.read()
    parser = ParserPython(log, skipws=False, debug=False, memoization=True)
    parse_tree = parser.parse(logstring)
    result = visit_parse_tree(parse_tree, MessageVisitor(debug=True))
    return result
