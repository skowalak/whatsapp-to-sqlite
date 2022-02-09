"""
Messages
"""

from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Message:
    timestamp: datetime = None
    full_text: str = None

    def toDict(self):
        return asdict(self)


@dataclass
class UserMessage(Message):
    sender: str = None
    text: str = None
    continued_text: str = None
    filename: str = None
    file_lost: bool = False
    file: bool = False
    msgtype: str = "USER"


@dataclass
class SystemMessage(Message):
    """Base class for all WhatsApp-issued messages"""
    msgtype: str = "SYSTEM"


@dataclass
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

