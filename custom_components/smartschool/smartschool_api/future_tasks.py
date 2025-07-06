from collections.abc import Iterator

from .objects import FutureTaskOneDay
from .session import SessionMixin

__all__ = ["FutureTasks"]


class FutureTasks(SessionMixin):
    """
    Class that interfaces the retrieval of any task that needs to be made in the near future.

    Example:
    -------
    >>> for day in FutureTasks(session):
    >>>     for course in day.courses:
    >>>         print("Course:", course.course_title)
    >>>         for task in course.items.tasks:
    >>>             print("Task:", task.description)
    Course: 2 - AAR1, Lotte Peeters
    Task: Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47

    """

    def __iter__(self) -> Iterator[FutureTaskOneDay]:
        """I need to do this here because when I do it in Agenda, it'll not lazily load it. But in this way, I load it on construction."""
        json = self.session.json(
            "/Agenda/Futuretasks/getFuturetasks",
            method="post",
            data={
                "lastAssignmentID": 0,
                "lastDate": "",
                "filterType": "false",
                "filterID": "false",
            },
            headers={
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        for d in json["days"]:
            yield FutureTaskOneDay(**d)
