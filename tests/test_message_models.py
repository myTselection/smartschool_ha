import sys
import types
from pathlib import Path

from pydantic.dataclasses import dataclass


ROOT = Path(__file__).resolve().parents[1]
API_PATH = ROOT / "custom_components" / "smartschool" / "smartschool_api"

custom_components_pkg = types.ModuleType("custom_components")
custom_components_pkg.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components_pkg)

smartschool_pkg = types.ModuleType("custom_components.smartschool")
smartschool_pkg.__path__ = [str(ROOT / "custom_components" / "smartschool")]
sys.modules.setdefault("custom_components.smartschool", smartschool_pkg)

api_pkg = types.ModuleType("custom_components.smartschool.smartschool_api")
api_pkg.__path__ = [str(API_PATH)]
sys.modules.setdefault("custom_components.smartschool.smartschool_api", api_pkg)

common_module = types.ModuleType("custom_components.smartschool.smartschool_api.common")
common_module.as_float = float
sys.modules.setdefault("custom_components.smartschool.smartschool_api.common", common_module)

session_module = types.ModuleType("custom_components.smartschool.smartschool_api.session")


@dataclass
class Smartschool:
    pass


session_module.Smartschool = Smartschool
sys.modules.setdefault("custom_components.smartschool.smartschool_api.session", session_module)

from custom_components.smartschool.smartschool_api.objects import FullMessage, ShortMessage


def test_short_message_accepts_numeric_label_string():
    message = ShortMessage(
        id="123",
        fromImage="",
        subject="Test",
        date="2026-06-14T10:30:00+0200",
        status="0",
        attachment="0",
        unread="1",
        label="3",
        deleted="0",
        allowreply="1",
        allowreplyenabled="1",
        hasreply="0",
        hasForward="0",
        realBox="inbox",
        sendDate="2026-06-14T10:30:00+0200",
        **{"from": "SmartSchool"},
    )

    assert message.label == 3


def test_full_message_accepts_numeric_label_string():
    message = FullMessage(
        id="123",
        to="Student",
        subject="Test",
        date="2026-06-14T10:30:00+0200",
        body="Hello",
        status="0",
        attachment="0",
        unread="1",
        label="4",
        receivers=[],
        ccreceivers=[],
        bccreceivers=[],
        senderPicture="",
        markedInLVS=None,
        fromTeam="0",
        totalNrOtherToReciviers="0",
        totalnrOtherCcReceivers="0",
        totalnrOtherBccReceivers="0",
        canReply="1",
        hasReply="0",
        hasForward="0",
        sendDate="2026-06-14T10:30:00+0200",
        **{"from": "SmartSchool"},
    )

    assert message.label == 4
