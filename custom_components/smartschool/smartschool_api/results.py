from itertools import count
from typing import Iterator

from .exceptions import SmartSchoolDownloadError
from .objects import Result, ResultWithDetails
from .session import Smartschool

__all__ = ["Results", "ResultDetail"]


RESULTS_PER_PAGE = 50


class Results:
    """
    Interfaces with the evaluations of smartschool.

    To reproduce: "Ga naar" > "Resultaten", it'll be one of the XHR calls then.

    Example:
    -------
    >>> for result in Results():
    >>>     print(result.name)
    Repetitie hoofdstuk 1

    """

    smartschool: Smartschool  # Injected instance
    def __init__(self, smartschool: Smartschool):
        self.smartschool = smartschool

    def __iter__(self) -> Iterator[Result]:
        for page_nr in count(start=1):  # pragma: no branch
            downloaded_webpage = self.smartschool.get(f"/results/api/v1/evaluations/?pageNumber={page_nr}&itemsOnPage={RESULTS_PER_PAGE}")
            if not downloaded_webpage or not downloaded_webpage.content:
                raise SmartSchoolDownloadError("No JSON was returned for the results?!")

            json = downloaded_webpage.json()
            for result in json:
                yield Result(**result)

            if len(json) < RESULTS_PER_PAGE:
                break


class ResultDetail:
    def __init__(self, result_id: str):
        self.result_id = result_id

    def get(self) -> ResultWithDetails:
        downloaded_webpage = self.smartschool.get(f"/results/api/v1/evaluations/{self.result_id}")
        if not downloaded_webpage or not downloaded_webpage.content:
            raise SmartSchoolDownloadError("No JSON was returned for the details?!")

        json = downloaded_webpage.json()
        return ResultWithDetails(**json)
