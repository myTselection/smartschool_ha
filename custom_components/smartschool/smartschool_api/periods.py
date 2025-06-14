from typing import Iterator

from .objects import Period
from .session import Smartschool

__all__ = ["Periods"]


class Periods:
    """
    Retrieves a list of the periods.

    To reproduce: go to "Results", one of the XHR calls is this one

    Example:
    -------
    >>> for period in Periods():
    >>>     print(period.name)
    1 september - 24 oktober
    25 oktober - 19 december

    """

    def __init__(self, smartschool: Smartschool):
        super().__init__(smartschool= smartschool)

    def __iter__(self) -> Iterator[Period]:
        for period in self.smartschool.json("/results/api/v1/periods/"):
            yield Period(**period)
