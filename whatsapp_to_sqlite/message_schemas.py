import uuid

from marshmallow import (
    RAISE,
    Schema,
    ValidationError,
    fields,
    post_load,
    validate,
)

EVENT_TYPE = "de.skowalak.wat"


class ContentSchema(Schema):
    body = fields.String()
    creator = fields.String()
    info = fields.Nested(Schema())
    is_direct = fields.Boolean()
    membership = fields.Str(validate=validate.OneOf(
        ["invite", "join", "knock", "leave", "ban"]
    ))
    msgtype = fields.String()
    name = fields.String()
    pinned = fields.List(fields.String())
    topic = fields.String()
    url = fields.String()


class EventSchema(Schema):
    event_content = fields.Nested(ContentSchema())
    event_id = fields.UUID(default=uuid.uuid4())
    event_timestamp = fields.DateTime()
    event_type = fields.String(default=EVENT_TYPE)
    room_id = fields.UUID()
    sender = fields.String()
    state_key = fields.Str(default="")

    class Meta:
        unknown = RAISE


class CreateRoomEventSchema(EventSchema):
    """
    Root Event of every room.
    """
    event_content = fields.Nested(ContentSchema(only=(creator,)))
    event_type = fields.Str(default=EVENT_TYPE + ".room.create")


class MemberRoomEventSchema(EventSchema):
    event_content = fields.Nested(ContentSchema(only=(membership,)))
    event_type = fields.Str(default=EVENT_TYPE + ".room.member")
    state_key = fields.Str(required=True, validate=validate.Length(min=1))


class NameRoomEventSchema(EventSchema):
    """
    Every Room gets an auto-generated event ID.
    
    Apart from that ID a room can also have a user-given room name. This event
    sets that name.
    """
    event_content = fields.Nested(ContentSchema(only=()))
    event_type = fields.String(default=EVENT_TYPE + ".room.name")
    

class MessageRoomEventSchema(EventSchema):
    """
    A Message sent
    """
    event_content = fields.Nested(ContentSchema(only(body,)))
    event_type = fields.String(default=EVENT_TYPE + ".room.message")


class AvatarRoomEventSchema(EventSchema):
    """
    Changing the rooms avatar image.
    """
    event_content = fields.Nested(ContentSchema(only(info, url)))
    event_type = fields.String(default=EVENT_TYPE + ".room.avatar")
