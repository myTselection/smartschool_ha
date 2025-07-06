from __future__ import annotations

import base64
from abc import ABC
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from . import objects
from ._xml_interface import SmartschoolXML, SmartschoolXML_NoCache
from .objects import FullMessage, MessageChanged, MessageDeletionStatus, ShortMessage
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .session import Smartschool

__all__ = [
    "AdjustMessageLabel",
    "Attachment",
    "Attachments",
    "BoxType",
    "MarkMessageUnread",
    "Message",
    "MessageHeaders",
    "MessageLabel",
    "MessageMoveToArchive",
    "MessageMoveToTrash",
    "SortField",
    "SortOrder",
]


class SortField(Enum):
    DATE = "date"
    FROM = "from"
    READ_UNREAD = "status"
    ATTACHMENT = "attachment"
    FLAG = "label"


class SortOrder(Enum):
    ASC = "asc"
    DESC = "desc"


class BoxType(Enum):
    INBOX = "inbox"
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "outbox"
    TRASH = "trash"


class MessageLabel(Enum):
    NO_FLAG = 0
    GREEN_FLAG = 1
    YELLOW_FLAG = 2
    RED_FLAG = 3
    BLUE_FLAG = 4


class _MessagesPoster:
    _url = "/?module=Messages&file=dispatcher"


@dataclass
class MessageHeaders(_MessagesPoster, SmartschoolXML_NoCache):
    """
    Interfaces the mailbox principle in Smartschool.

    To reproduce: Open the messages and watch the XHR calls.

    Example:
    -------
    >>> for message in MessageHeaders():
    >>>     print(message.subject)
    Re: LO les
    Frans

    """

    box_type: BoxType = BoxType.INBOX
    sort_by: SortField = SortField.DATE
    sort_order: SortOrder = SortOrder.DESC
    already_seen_message_ids: list[int] | None = field(default_factory=list)

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _action(self) -> str:
        return "message list"

    @property
    def _params(self) -> dict:
        return {
            "boxType": self.box_type.value,
            "boxID": "0",
            "sortField": self.sort_by.value,
            "sortKey": self.sort_order.value,
            "poll": "false" if not self.already_seen_message_ids else "true",
            "poll_ids": ",".join(str(x) for x in self.already_seen_message_ids),
            "layout": "new",
        }

    @property
    def _xpath(self) -> str:
        return ".//messages/message"

    @property
    def _object_to_instantiate(self) -> type[ShortMessage]:
        return ShortMessage


# Cannot have `@dataclass`
class _FetchOneMessage(_MessagesPoster, SmartschoolXML, ABC):
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX):
        super().__init__(session=session)

        self.msg_id = msg_id
        self.box_type = box_type

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _params(self) -> dict:
        return {
            "msgID": self.msg_id,
            "boxType": self.box_type.value,
            "limitList": "true",
        }

    def _get_from_cache(self) -> object:
        return self.cache[(self.msg_id, self.box_type)]

    def _store_into_cache(self, obj: object) -> None:
        self.cache[(self.msg_id, self.box_type)] = obj


class Message(_FetchOneMessage):
    """
    Interface to fetch one message based on its MessageID.

    To reproduce: just go to a message and click it.

    Example:
    -------
    >>> message: FullMessage = list(Message(123))[0]
    >>> message.subject
    Griezelfestijn

    """

    @property
    def _action(self) -> str:
        return "show message"

    @property
    def _xpath(self) -> str:
        return ".//data/message"

    @property
    def _object_to_instantiate(self) -> type[FullMessage]:
        return FullMessage

    def _post_process_element(self, element: dict) -> None:
        for modify_this in ["receivers", "ccreceivers", "bccreceivers"]:
            if not element[modify_this]:
                element[modify_this] = []
                continue

            element[modify_this] = element[modify_this]["to"]

            if not isinstance(element[modify_this], list):
                element[modify_this] = [element[modify_this]]


@dataclass
class Attachment(SessionMixin, objects.Attachment):
    def download(self) -> bytes:
        resp = self.session.get(f"/?module=Messages&file=download&fileID={self.fileID}&target=0")
        return base64.b64decode(resp.content)


class Attachments(_FetchOneMessage):
    """
    Interface to fetch one message based on its MessageID.

    To reproduce: just go to a message (with the attachment symbol) and click it.

    Example:
    -------
    >>> for attachment in Attachments(123):
    >>>     print(attachment.name)
    Oproep figuranten en helpers.pdf
    Poster griezelfestijn.pdf

    """

    @property
    def _action(self) -> str:
        return "attachment list"

    @property
    def _xpath(self) -> str:
        return ".//attachmentlist/attachment"

    @property
    def _object_to_instantiate(self) -> type[Attachment]:
        return Attachment


class MarkMessageUnread(_FetchOneMessage):
    @property
    def _action(self) -> str:
        return "mark message unread"

    @property
    def _xpath(self) -> str:
        return ".//data/message"

    @property
    def _object_to_instantiate(self) -> type[MessageChanged]:
        return MessageChanged

    @property
    def _params(self) -> dict:
        return {
            "boxType": self.box_type.value,
            "boxID": "0",
            "msgID": self.msg_id,
            "clAction": "status",
        }


# Cannot have `@dataclass`
class AdjustMessageLabel(_FetchOneMessage):
    def __init__(self, session: Smartschool, msg_id: int, box_type: BoxType = BoxType.INBOX, label: MessageLabel = MessageLabel.NO_FLAG):
        super().__init__(session, msg_id, box_type)
        self.label = label

    @property
    def _action(self) -> str:
        return "save msglabel"

    @property
    def _xpath(self) -> str:
        return ".//data/message"

    @property
    def _object_to_instantiate(self) -> type[MessageChanged]:
        return MessageChanged

    @property
    def _params(self) -> dict:
        return {
            "boxType": self.box_type.value,
            "msgLabel": self.label.value,
            "msgID": self.msg_id,
            "clAction": "label",
        }


@dataclass
class MessageMoveToArchive(SessionMixin):
    """
    Archiving is weird.

    It's not following the XML protocol... Providing the same interface as the other XMLs though.
    """

    def __init__(self, session: Smartschool, msg_id: int | list[int]):
        super().__init__(session=session)

        if not isinstance(msg_id, list):
            msg_id = [msg_id]

        self.msg_ids = msg_id

    def get(self) -> MessageChanged:
        return next(iter(self))

    def __iter__(self) -> Iterator[MessageChanged]:
        construction = "&".join("msgIDs%5B%5D=" + quote_plus(str(msg_id)) for msg_id in self.msg_ids)

        resp = self.session.post(
            "/Messages/Xhr/archivemessages",
            data=construction,
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        success = resp.json()["success"]
        for msg_id in self.msg_ids:
            yield MessageChanged(id=msg_id, new=1 if msg_id in success else 0)


# Cannot have `@dataclass`
class MessageMoveToTrash(_MessagesPoster, SmartschoolXML_NoCache):
    def __init__(self, session: Smartschool, msg_id: int):
        super().__init__(session=session)

        self.msg_id = msg_id

    @property
    def _subsystem(self) -> str:
        return "postboxes"

    @property
    def _action(self) -> str:
        return "quick delete"

    @property
    def _xpath(self) -> str:
        return ".//data/details"

    @property
    def _object_to_instantiate(self) -> type[MessageDeletionStatus]:
        return MessageDeletionStatus

    @property
    def _params(self) -> dict:
        return {"msgID": self.msg_id}
