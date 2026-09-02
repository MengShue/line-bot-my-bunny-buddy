def get_conversation_id(source):
    """Return the LINE conversation that produced an event.

    A push sent after the reply token has been consumed must target the group or
    room for group/room events. Targeting ``user_id`` would instead send the
    message to the member's one-to-one chat with the bot.
    """
    source_type = getattr(source, "type", None)

    if source_type == "group":
        conversation_id = getattr(source, "group_id", None)
    elif source_type == "room":
        conversation_id = getattr(source, "room_id", None)
    elif source_type == "user":
        conversation_id = getattr(source, "user_id", None)
    else:
        conversation_id = (
            getattr(source, "group_id", None)
            or getattr(source, "room_id", None)
            or getattr(source, "user_id", None)
        )

    if not conversation_id:
        raise ValueError("LINE event source does not contain a conversation ID")

    return conversation_id
