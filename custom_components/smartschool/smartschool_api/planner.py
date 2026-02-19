# from __future__ import annotations

# from collections.abc import Iterable
# from dataclasses import dataclass, field
# from datetime import datetime, timedelta
# from typing import TYPE_CHECKING
# from zoneinfo import ZoneInfo

# from .objects import ApplicableAssignmentType, PlannedElement
# from .session import SessionMixin
# from .session import Smartschool

# if TYPE_CHECKING:
#     from collections.abc import Iterator
#     from datetime import date

# __all__ = ["ApplicableAssignmentTypes", "PlannedElements"]


# @dataclass
# class ApplicableAssignmentTypes(SessionMixin, Iterable[ApplicableAssignmentType]):
#     def __iter__(self) -> Iterator[ApplicableAssignmentType]:
#         for type_ in self.session.json("/lesson-content/api/v1/assignments/applicable-assigment-types"):
#             yield ApplicableAssignmentType(**type_)


# @dataclass
# class PlannedElements(SessionMixin, Iterable[PlannedElement]):
#     from_date: date = field(default_factory=lambda: datetime.now(tz=ZoneInfo("Europe/Brussels")).replace(hour=0, minute=0, second=0, microsecond=0))
#     till_date: date | None = None

#     def __post_init__(self):
#         if self.till_date is None:
#             self.till_date = self.from_date + timedelta(days=34, seconds=-1)

#     def __iter__(self) -> Iterator[PlannedElement]:
#         data = self.session.json(
#             f"/planner/api/v1/planned-elements/user/{self.session.authenticated_user['id']}",
#             data={"from": self.from_date.isoformat(), "to": self.till_date.isoformat(), "types": "planned-assignments,planned-to-dos"},
#         )
#         for element in data:
#             yield PlannedElement(**element)


from datetime import date, datetime
from typing import Iterator

from .objects import ApplicableAssignmentType, PlannedElement
from .session import Smartschool

__all__ = ["Planner", "ApplicableAssignmentTypes"]


class Planner:
    """
    Retrieves planner.

    """

    def __init__(self, smartschool: Smartschool, from_date: datetime | date | None = None,till_date: datetime | date | None = None):
        self.smartschool = smartschool
        self.from_date = from_date
        self.till_date = till_date

    def __iter__(self) -> Iterator[PlannedElement]:
        for element in self.smartschool.json(f"/planner/api/v1/planned-elements/user/{self.smartschool.authenticated_user['id']}", method="post", data={"from": self.from_date.isoformat(), "to": self.till_date.isoformat(), "types": "planned-assignments,planned-to-dos"}):
            yield PlannedElement(**element)

class ApplicableAssignmentTypes():
    def __init__(self, smartschool: Smartschool):
        self.smartschool = smartschool

    def __iter__(self) -> Iterator[ApplicableAssignmentType]:
        for type_ in self.smartschool.json("/lesson-content/api/v1/assignments/applicable-assigment-types"):
            yield ApplicableAssignmentType(**type_)