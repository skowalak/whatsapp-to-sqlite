"""
Messages
"""

from dataclasses import dataclass, asdict, replace
from datetime import datetime


@dataclass
class Message:
    timestamp: datetime = None
    full_text: str = None
    sender: str = None
    room_name: str = None

    def toDict(self):
        data = asdict(self)
        data["type"] = self.__class__.__name__
        return {k: v for k, v in data.items() if v is not None}

    def replace(self, **changes):
        return replace(self, **changes)


@dataclass
class RoomMessage(Message):
    text: str = None
    continued_text: str = None
    filename: str = None
    file_lost: bool = False
    file: bool = False


@dataclass
class SystemMessage(Message):
    target: str = None
    new_number: str = None
    new_room_name: str = None


class HasTargetUserMessage:
    pass


class HasNewRoomNameMessage:
    pass


class HasNewNumberMessage:
    pass


@dataclass
class RoomCreateByThirdParty(SystemMessage, HasNewRoomNameMessage):
    pass


@dataclass
class RoomCreateBySelf(SystemMessage, HasNewRoomNameMessage):
    pass


@dataclass
class RoomJoinThirdPartyByThirdParty(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomJoinThirdPartyByUnknown(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomJoinSelfByThirdParty(SystemMessage):
    pass


@dataclass
class RoomJoinThirdPartyBySelf(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomKickThirdPartyByThirdParty(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomKickThirdPartyByUnknown(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomKickSelfByThirdParty(SystemMessage):
    pass


@dataclass
class RoomKickThirdPartyBySelf(SystemMessage, HasTargetUserMessage):
    pass


@dataclass
class RoomLeaveThirdParty(SystemMessage):
    pass


@dataclass
class RoomLeaveSelf(SystemMessage):
    pass


@dataclass
class RoomNameBySelf(SystemMessage, HasNewRoomNameMessage):
    pass


@dataclass
class RoomNameByThirdParty(SystemMessage, HasNewRoomNameMessage):
    pass


@dataclass
class RoomDescriptionBySelf(SystemMessage):
    pass


@dataclass
class RoomDescriptionByThirdParty(SystemMessage):
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
class RoomNumberChangeWithNumber(SystemMessage, HasNewNumberMessage):
    pass


@dataclass
class RoomNumberChangeWithoutNumber(SystemMessage):
    pass


@dataclass
class RoomE2EEnabledNotification(SystemMessage):
    pass
