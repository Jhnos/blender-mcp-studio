"""Unit tests for Session entity."""

from src.core.domain.session import Session


def test_session_has_unique_id() -> None:
    s1 = Session()
    s2 = Session()
    assert s1.id != s2.id


def test_session_add_message() -> None:
    session = Session()
    updated = session.add_message("user", "建立一個立方體")
    assert len(updated.messages) == 1
    assert updated.messages[0].role == "user"
    assert updated.messages[0].content == "建立一個立方體"
    assert session.messages == []  # original unchanged


def test_session_last_user_message() -> None:
    session = (
        Session()
        .add_message("user", "第一條")
        .add_message("assistant", "回應")
        .add_message("user", "第二條")
    )
    assert session.last_user_message() == "第二條"


def test_session_last_user_message_none_when_empty() -> None:
    session = Session()
    assert session.last_user_message() is None
