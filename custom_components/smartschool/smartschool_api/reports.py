from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from . import objects
from .session import SessionMixin

__all__ = ["Report", "Reports"]


@dataclass
class Report(objects.Report, SessionMixin):
    def download(self) -> bytes:
        data = self.session.json(self.downloadUrl)
        return self.session.get(data["url"]).content


@dataclass
class Reports(SessionMixin, Iterable[Report]):
    """
    Interfaces with the reports part of the evaluations of smartschool.

    To reproduce: "Ga naar" > "Resultaten" > "Rapporten", it'll be one of the XHR calls then.

    Example:
    -------
    >>> for report in Reports(session):
    >>>     print(report.name)
    Rapport 1

    """

    def __iter__(self) -> Iterator[Report]:
        data = self.session.json("/results/api/v1/reports")
        for result in data:
            pyd = objects.Report(**result)
            yield Report(session=self.session, **pyd.__dict__)
