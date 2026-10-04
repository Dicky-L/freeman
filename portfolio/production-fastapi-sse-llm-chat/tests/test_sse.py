import json

from production_sse_chat.sse import encode_comment, encode_event


def test_sse_json_frame_is_well_formed() -> None:
    frame = encode_event(event="delta", event_id="7", data={"text": "hello\nworld"})
    text = frame.decode()
    assert text.startswith("id: 7\nevent: delta\n")
    data_line = next(line for line in text.splitlines() if line.startswith("data: "))
    assert json.loads(data_line[6:]) == {"text": "hello\nworld"}
    assert text.endswith("\n\n")


def test_heartbeat_is_comment_frame() -> None:
    assert encode_comment("ping") == b": ping\n\n"
