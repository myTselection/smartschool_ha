from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import count
from typing import TYPE_CHECKING

from . import objects
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = ["Results"]

RESULTS_PER_PAGE = 50


@dataclass
class Result(objects.Result, SessionMixin):
    def __getattribute__(self, name: str):
        attr = super().__getattribute__(name)
        if name != "details":
            return attr

        if attr is not None:
            return attr

        data = self.session.json(f"/results/api/v1/evaluations/{self.identifier}")
        details_obj = objects.Result(**data)
        super().__setattr__("details", details_obj.details)
        return details_obj.details


@dataclass
class Results(SessionMixin, Iterable[Result]):
    """
    Interfaces with the evaluations of smartschool.

    To reproduce: "Ga naar" > "Resultaten", it'll be one of the XHR calls then.

    Example:
    -------
    >>> for result in Results():
    >>>     print(result.name)
    Repetitie hoofdstuk 1

    """

    def __iter__(self) -> Iterator[Result]:
        for page_nr in count(start=1):  # pragma: no branch
            data = self.session.json(f"/results/api/v1/evaluations/?pageNumber={page_nr}&itemsOnPage={RESULTS_PER_PAGE}")
            for result in data:
                pyd = objects.Result(**result)
                yield Result(session=self.session, **pyd.__dict__)

            if len(data) < RESULTS_PER_PAGE:
                break
