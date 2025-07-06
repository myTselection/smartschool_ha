from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from .objects import StudentSupportLink
from .session import SessionMixin

__all__ = ["StudentSupportLinks"]


@dataclass
class StudentSupportLinks(SessionMixin, Iterable[StudentSupportLink]):
    """
    Interfaces with the link section that is loaded when opening the main interface of smartschool.

    To reproduce: Just open the homepage, it'll be one of the XHR calls then.

    Example:
    -------
    >>> for link in StudentSupportLinks(session):
    >>>     print(link.name)
    1712
    Autisme chat

    """

    def __iter__(self) -> Iterator[StudentSupportLink]:
        json = self.session.json("/student-support/api/v1/")
        for result in json:
            yield StudentSupportLink(**result)
