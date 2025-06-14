from typing import Iterator

from .objects import StudentSupportLink
from .session import Smartschool

__all__ = ["StudentSupportLinks"]


class StudentSupportLinks:
    """
    Interfaces with the link section that is loaded when opening the main interface of smartschool.

    To reproduce: Just open the homepage, it'll be one of the XHR calls then.

    Example:
    -------
    >>> for link in StudentSupportLinks():
    >>>     print(link.name)
    1712
    Autisme chat

    """

    def __init__(self, smartschool: Smartschool):
        super().__init__(smartschool= smartschool)

    def __iter__(self) -> Iterator[StudentSupportLink]:
        json = self.smartschool.json("/student-support/api/v1/")
        for result in json:
            yield StudentSupportLink(**result)
