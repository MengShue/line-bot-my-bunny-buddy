from types import SimpleNamespace

import pytest

from app.line_destination import get_conversation_id


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (SimpleNamespace(type="user", user_id="U-user"), "U-user"),
        (
            SimpleNamespace(
                type="group", group_id="C-group", user_id="U-member"
            ),
            "C-group",
        ),
        (
            SimpleNamespace(
                type="room", room_id="R-room", user_id="U-member"
            ),
            "R-room",
        ),
    ],
)
def test_get_conversation_id_uses_event_conversation(source, expected):
    assert get_conversation_id(source) == expected


def test_get_conversation_id_rejects_source_without_destination():
    with pytest.raises(ValueError, match="conversation ID"):
        get_conversation_id(SimpleNamespace(type="group", user_id="U-member"))
