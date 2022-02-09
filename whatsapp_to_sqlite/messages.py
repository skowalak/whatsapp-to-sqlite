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
        data = asdict(self)
        data["type"] = self.__class__.__name__
        return {k: v for k, v in data.items() if v is not None}


@dataclass
class RoomMessage(Message):
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
    sender: str = None
    target: str = None
    room_name: str = None
    new_number: str = None


@dataclass
class RoomCreateByThirdParty(SystemMessage):
    pass


@dataclass
class RoomCreateBySelf(SystemMessage):
    pass


@dataclass
class RoomJoinThirdPartyByThirdParty(SystemMessage):
    pass


@dataclass
class RoomJoinThirdPartyByUnknown(SystemMessage):
    pass


@dataclass
class RoomJoinSelfByThirdParty(SystemMessage):
    pass


@dataclass
class RoomJoinThirdPartyBySelf(SystemMessage):
    pass


@dataclass
class RoomKickThirdPartyByThirdParty(SystemMessage):
    pass


@dataclass
class RoomKickThirdPartyByUnknown(SystemMessage):
    pass


@dataclass
class RoomKickSelfByThirdParty(SystemMessage):
    pass


@dataclass
class RoomKickThirdPartyBySelf(SystemMessage):
    pass


@dataclass
class RoomLeaveThirdParty(SystemMessage):
    pass


@dataclass
class RoomLeaveSelf(SystemMessage):
    pass


@dataclass
class RoomNameBySelf(SystemMessage):
    pass


@dataclass
class RoomNameByThirdParty(SystemMessage):
    pass


@dataclass
class RoomAvatarChangeBySelf(SystemMessage):
    pass


@dataclass
class RoomAvatarChangeByThirdParty(SystemMessage):
    pass


@dataclass
class RoomAvatarDeleteBySelf(SystemMessage):
    pass


@dataclass
class RoomAvatarDeleteByThirdParty(SystemMessage):
    pass


@dataclass
class RoomAdminPromotion(SystemMessage):
    pass


@dataclass
class RoomNumberChangeWithNumber(SystemMessage):
    pass


@dataclass
class RoomNumberChangeWithoutNumber(SystemMessage):
    pass
