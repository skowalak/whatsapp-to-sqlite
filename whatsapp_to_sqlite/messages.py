"""
Messages
"""

from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Message:
    timestamp: datetime
    full_text: str

    def toDict(self):
        return asdict(self)


@dataclass
class UserMessage(Message):
    sender: str
    text: str
    continued_text: str
    filename: str
    file_lost: bool
    file: bool = False
    msgtype: str = "USER"


@dataclass
class SystemMessage(Message):
    """Base class for all WhatsApp-issued messages"""
    msgtype: str = "SYSTEM"


class RoomCreate(SystemMessage):
    sender: str = None
    room_name: str = None


class RoomName(SystemMessage):
    sender: str = None
    room_name: str = None

class RoomJoinByAdminSelf(SystemMessage):
    pass


class RoomAvatar(SystemMessage):
    sender: str = None


class RoomKickByAdminSelf(SystemMessage):
    sender: str = None


class RoomKickByAdminThirdParty(SystemMessage):
    sender: str = None
    target: str = None


class RoomKickThirdParty(SystemMessage):
    target: str = None


class RoomKickSelf(SystemMessage):
    target: str = None


class RoomLeave(SystemMessage):
    pass


class RoomNameChange1(SystemMessage):
    sender: str = None
    old_name: str = None
    new_name: str = None


class RoomNameChange2(SystemMessage):
    sender: str = None

