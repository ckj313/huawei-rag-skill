from pathlib import Path

from src.experience import load_protocol_profiles, detect_intent


def test_detect_intent_ospf_hello():
    profiles = load_protocol_profiles(Path(__file__).parent / "fixtures" / "experience")
    intent = detect_intent("帮我测试一下ospf的hello报文", profiles)
    assert intent["protocol"] == "ospf"
    assert intent["packet"] == "hello"
    assert "process_id" in intent["required_fields"]
