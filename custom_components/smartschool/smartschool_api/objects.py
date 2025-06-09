from __future__ import annotations

import base64
from datetime import date, datetime
from functools import cached_property
from typing import Annotated, Literal, Optional, Union

from pydantic import AliasChoices, BeforeValidator, constr
from pydantic.dataclasses import Field, dataclass

from .common import as_float
from .session import session

# Keep the constr definition for Pydantic's use, but use 'str' for type hints
String = constr(strip_whitespace=True)


def convert_to_datetime(x: str | datetime) -> datetime:
    if isinstance(x, datetime):
        if x.tzinfo is None:
            raise ValueError("No timezone information found in this date")
        return x

    try:
        return datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:  # 2023-11-16 08:24
        return datetime.strptime(x, "%Y-%m-%d %H:%M")


def convert_to_date(x: Optional[str]) -> date:
    """Convert a date string in YYYY-MM-DD format to a date object."""
    if x is None:
        return date.today()  # Return today's date if input is None
    return datetime.strptime(x, "%Y-%m-%d").date()


Url = Annotated[str, BeforeValidator(lambda x: session.create_url(x))]
Date = Annotated[date, BeforeValidator(convert_to_date)]
DateTime = Annotated[datetime, BeforeValidator(convert_to_datetime)]


@dataclass
class CourseGraphic:
    type: Literal["icon"]
    value: str


@dataclass
class ResultGraphic:
    """Represents the graphical part of a result."""

    color: Literal["green", "red", "yellow"]
    symbol: str

    @cached_property
    def achieved_points(self) -> float:
        return as_float(self.description.split("/")[0])

    @cached_property
    def total_points(self) -> float:
        return as_float(self.description.split("/")[1])

    @property
    def percentage(self) -> float:
        return self.achieved_points / self.total_points


@dataclass
class PersonDescription:
    startingWithFirstName: str = ""
    startingWithLastName: str = ""


@dataclass
class _User:
    id: str
    pictureHash: str
    pictureUrl: Url
    description: PersonDescription
    name: PersonDescription
    sort: str


@dataclass
class DateRange:
    start: DateTime
    end: DateTime


@dataclass
class SkoreWorkYear:
    id: int
    dateRange: DateRange


@dataclass
class Class_:
    identifier: str
    id: int
    platformId: int
    name: str
    type: str
    icon: str


@dataclass
class Period:
    id: int
    name: str
    icon: str
    skoreWorkYear: SkoreWorkYear
    isActive: bool
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class Component:
    id: int
    name: str
    abbreviation: str


Teacher = _User
Student = _User


@dataclass
class Course:
    id: int
    name: str
    graphic: CourseGraphic
    teachers: list[Teacher]
    skoreClassId: int
    parentCourseId: None | int
    skoreWorkYear: SkoreWorkYear
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class Feedback:
    text: str
    user: Teacher


@dataclass
class FeedbackFull:
    attachments: list[str]
    changedAt: DateTime
    createdAt: DateTime
    evaluationId: str
    id: str
    student: Student
    teacher: Teacher
    text: str


@dataclass
class Result:
    identifier: str
    type: Literal["normal"]
    name: str
    graphic: ResultGraphic
    date: DateTime

    gradebookOwner: Teacher
    component: Component
    courses: list[Course]
    period: Period
    feedback: list[Feedback]
    feedbacks: list[FeedbackFull]
    availabilityDate: DateTime
    isPublished: bool
    doesCount: bool


@dataclass
class ResultDetails:
    centralTendencies: list[str]
    teachers: list[Teacher]
    dateChanged: DateTime
    userChanged: Teacher
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class ResultWithDetails(Result):
    details: ResultDetails


@dataclass
class CourseCondensed:
    name: str
    teacher: str
    url: Url

    descr: str = Field(repr=False, default="")
    icon: str = Field(repr=False, default="")


@dataclass
class FutureTaskOneTask:
    label: str
    description: str
    icon: str
    warning: bool
    click_handle: str
    activityID: int
    dateID: str
    assignmentID: str
    endMomentTS: str | None
    startMomentID: str
    endMomentID: str
    lessonID: str
    type: str
    classID: str
    course: str
    date: Date
    hourID: str


@dataclass
class FutureTaskOneItem:
    tasks: list[FutureTaskOneTask]
    materials: list[str]


@dataclass
class FutureTaskOneCourse:
    lessonID: str
    hourID: str
    classID: str
    course_title: str
    items: FutureTaskOneItem


@dataclass
class FutureTaskOneDay:
    date: Date
    pretty_date: str
    courses: list[FutureTaskOneCourse]


@dataclass
class FutureTasks:
    """
    Class that interfaces the retrieval of any task that needs to be made in the near future.

    Example:
    -------
    >>> for day in FutureTasks().days:
    >>>     for course in day.courses:
    >>>         print("Course:", course.course_title)
    >>>         for task in course.items.tasks:
    >>>             print("Task:", task.description)
    Course: 2 - AAR1, Lotte Peeters
    Task: Toets 3. De koolstofcyclus in het systeem aarde pagina 42 - 47

    """

    days: list[FutureTaskOneDay] = Field(default_factory=list)
    last_assignment_id: int = 0
    last_date: Date = Field(default_factory=date.today)

    def __post_init__(self):
        """I need to do this here because when I do it in Agenda, it'll not lazily load it. But in this way, I load it on construction."""
        json = session.json(
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

        self.days = []
        for d in json["days"]:
            self.days.append(FutureTaskOneDay(**d))

        self.last_assignment_id = json["last_assignment_id"]
        self.last_date = convert_to_date(json["last_date"])


@dataclass
class AgendaHour:
    hourID: str
    start: str
    end: str
    title: str


@dataclass
class AgendaLesson:
    momentID: str
    lessonID: str
    hourID: str
    date: Date
    subject: str | None
    course: str
    courseTitle: str
    classroom: str | None
    classroomTitle: str | None
    teacher: str | None
    teacherTitle: str | None
    klassen: str
    klassenTitle: str
    classIDs: str
    bothStartStatus: str
    assignmentEndStatus: str
    testDeadlineStatus: str
    noteStatus: str
    note: str | None
    date_listview: str
    hour: str
    activity: str
    activityID: str | None
    color: str
    hourValue: str
    components_hidden: object
    freedayIcon: str
    someSubjectsEmpty: str | None

    @property
    def hour_details(self) -> AgendaHour:
        from .agenda import SmartschoolHours

        return SmartschoolHours().search_by_hourId(self.hourID)


@dataclass
class AgendaMomentInfoAssignment:
    startAssignment: str
    start: str
    end: str
    type: str
    description: str
    atdescription: str
    freedeadline: str
    warning: str
    assignmentInfo: str
    assignmentDeadline: str


@dataclass
class AgendaMomentInfo:
    className: str
    subject: str
    materials: str | None
    momentID: str
    assignments: list[AgendaMomentInfoAssignment]


@dataclass
class StudentSupportLink:
    id: str
    name: str
    description: str
    icon: str
    link: Url
    cleanLink: str
    isVisible: bool


@dataclass
class ShortMessage:
    id: int
    fromImage: Url
    subject: str
    date: DateTime
    status: int
    attachment: int
    unread: bool
    label: bool
    deleted: bool
    allowreply: bool
    allowreplyenabled: bool
    hasreply: bool
    hasForward: bool
    realBox: str
    sendDate: DateTime | None
    from_: str = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class FullMessage:
    id: int
    to: str | None
    subject: str
    date: DateTime
    body: str
    status: int
    attachment: int
    unread: bool
    label: bool
    receivers: list[str]
    ccreceivers: list[str]
    bccreceivers: list[str]
    senderPicture: str
    markedInLVS: None
    fromTeam: int
    totalNrOtherToReciviers: int
    totalnrOtherCcReceivers: int
    totalnrOtherBccReceivers: int
    canReply: bool
    hasReply: bool
    hasForward: bool
    sendDate: DateTime | None
    from_: str = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class Attachment:
    fileID: int
    name: str
    mime: str
    size: str
    icon: str
    wopiAllowed: bool
    order: int

    def download(self) -> bytes:
        resp = session.get(f"/?module=Messages&file=download&fileID={self.fileID}&target=0")
        return base64.b64decode(resp.content)


@dataclass
class MessageChanged:
    id: int
    new: int = Field(validation_alias=AliasChoices("status", "label", "new"))


@dataclass
class MessageDeletionStatus:
    msgID: int
    boxType: str
    is_deleted: bool = Field(validation_alias=AliasChoices("status", "is_deleted"))


@dataclass
class FileItem:
    """Represents a file within a course document folder."""
    id: int
    name: str
    description: str | None
    mime_type: str
    size_kb: float
    last_modified: datetime
    download_url: Url # URL to download the file directly
    view_url: Url | None # URL to view the file online (e.g., WOPI)


@dataclass
class FolderItem:
    """Represents a subfolder within a course document folder."""
    id: int
    name: str
    description: str | None
    browse_url: Url # URL to browse the contents of this folder

# Define the Union type for items found in document folders
DocumentOrFolderItem = Union[FileItem, FolderItem]
