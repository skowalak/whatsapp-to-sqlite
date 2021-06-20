from arpeggio import *
from arpeggio.cleanpeg import ParserPEG
from arpeggio import RegExMatch as _

###############################################################################
# Grammar Definition
###############################################################################

def log(): return OneOrMore(line), EOF
def line(): return [start_with_header, continued_message, newline]
def start_with_header(): return timestamp, " - ", [system_event, message], newline

# timestamps: customize according to your locale
def timestamp(): return day, ".", month, ".", year, ", ", hour, ":", minute
def day(): return _(r'(\d\d)')
def month(): return _(r'(\d\d)')
def year(): return _(r'(\d\d)')
def hour(): return _(r'(\d\d)')
def minute(): return _(r'(\d\d)')

# system event: customize according to your locale/system language
def system_event(): return _(r'(.*)')

# text message: matches any text
def message(): return username, ": ", [file_attached, file_excluded, any_text]
def username(): return _(r'(.*)')
def file_attached(): return filename, " (Datei angehängt)"
def file_excluded(): return "<Medien ausgeschlossen>"
def filename(): return _(r'(.+\.\w+)')


def continued_message(): return any_text

def any_text(): return _(r'(.*)')
def newline(): return "\n"

###############################################################################
# End of Grammar Definition
###############################################################################

logfile = open("tests/logs/WhatsApp Chat mit eiergilde.net Eiergilde.txt")
logstring = logfile.read()
logfile.close()

parser = ParserPython(log, skipws=False, debug=True)
parse_tree = parser.parse(logstring)
print(type(parse_tree))
