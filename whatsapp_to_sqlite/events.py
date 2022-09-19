"""
Events
"""
import uuid
from dataclasses import dataclass
from datetime import datetime

EVENT_TYPE = "de.skowalak.wat"

# non-working
@dataclass
class EventContent:
    body: str
    creator: str
    info: dict
    is_direct: bool
    # one of: "invite", "join", "knock", "leave", "ban"
    membership: str
    msgtype = str
    name: str
    pinned: list[str]
    topic: str
    url: str


# end non-working


@dataclass
class Event:
    """Base Event Type"""

    event_id: uuid.UUID = uuid.uuid4()
    event_id: datetime = None
    event_type: str = EVENT_TYPE
    room_id: uuid.UUID = None
    sender: uuid.UUID = None
    state_key: str = ""


class RoomEvent(Event):
    """Room-related events"""

    pass


class RoomCreateEvent(RoomEvent):
    """Creation of a new room (root event of every room)"""

    # only: creator
    event_content: EventContent
    event_type: str = f"{EVENT_TYPE}.room.create"


class RoomNameEvent(RoomEvent):
    """
    Every room has an auto-generated UUID.

    Apart from that, a room can also have user-given room names, set by this
    event type.
    """

    event_content: EventContent
    event_type: str = f"{EVENT_TYPE}.room.name"


class RoomAvatarEvent(RoomEvent):
    """
    Set/Change the rooms avatar image.
    """

    # only: info, url
    event_content: EventContent
    event_type: str = f"{EVENT_TYPE}.room.avatar"


class RoomMessageEvent(RoomEvent):
    # only: body
    event_content: EventContent
    event_type: str = f"{EVENT_TYPE}.room.message"


class RoomMemberEvent(RoomEvent):
    # only: membership
    event_content: EventContent
    event_type: str = f"{EVENT_TYPE}.room.member"
    # state key not-null required
