# Auto-generated stub file
from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime
from typing import Literal

from . import objects
from .objects import Component, Course, Feedback, FeedbackFull, Period, ResultDetails, ResultGraphic, Teacher
from .session import SessionMixin, Smartschool

class Result(objects.Result, SessionMixin):
    session: Smartschool
    identifier: str
    type: Literal["normal"]
    name: str
    graphic: ResultGraphic
    date: datetime
    gradebookOwner: Teacher
    component: Component | None
    courses: list[Course]
    period: Period
    feedback: list[Feedback]
    feedbacks: list[FeedbackFull]
    availabilityDate: datetime
    isPublished: bool
    doesCount: bool
    deleted: bool
    details: ResultDetails | None
    def __init__(
        self,
        session: Smartschool,
        identifier: str,
        type: Literal["normal"],
        name: str,
        graphic: ResultGraphic,
        date: datetime,
        gradebookOwner: Teacher,
        component: Component | None,
        courses: list[Course],
        period: Period,
        feedback: list[Feedback],
        feedbacks: list[FeedbackFull],
        availabilityDate: datetime,
        isPublished: bool,
        doesCount: bool,
        deleted: bool = False,
        details: ResultDetails | None = None,
    ): ...
    def __getattribute__(
        self,
        name: str,
    ): ...

class Results(SessionMixin, Iterable[Result]):
    session: Smartschool
    def __init__(
        self,
        session: Smartschool,
    ): ...
    def __iter__(
        self,
    ) -> Iterator[Result]: ...
