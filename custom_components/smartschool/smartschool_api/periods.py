from collections.abc import Iterator
from dataclasses import dataclass

from .objects import Period
from .session import SessionMixin

__all__ = ["Periods"]


@dataclass
class Periods(SessionMixin):
    """
    Retrieves a list of the periods.

    To reproduce: go to "Results", one of the XHR calls is this one

    Example:
    -------
    >>> for period in Periods(session):
    >>>     print(period.name)
    1 september - 24 oktober
    25 oktober - 19 december

    """

    def __iter__(self) -> Iterator[Period]:
        for period in self.session.json("/results/api/v1/periods/"):
            yield Period(**period)
