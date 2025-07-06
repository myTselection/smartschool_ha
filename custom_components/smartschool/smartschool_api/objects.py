# pylint: disable=invalid-name

from __future__ import annotations

import re
from datetime import date, datetime
from functools import cached_property
from typing import Annotated, Literal

from pydantic import AliasChoices, BeforeValidator, constr
from pydantic.dataclasses import Field, dataclass

from .common import as_float, convert_to_date, convert_to_datetime

String = constr(strip_whitespace=True)
UUID = constr(pattern=re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", flags=re.IGNORECASE))

Url = String
Date = Annotated[date, BeforeValidator(convert_to_date)]
DateTime = Annotated[datetime, BeforeValidator(convert_to_datetime)]


@dataclass
class CourseGraphic:
    type: Literal["icon"]
    value: String


@dataclass
class ResultGraphic:
    type: Literal["percentage"]
    color: Literal["green", "red", "olive", "yellow", "steel"]
    value: int
    description: String

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
    startingWithFirstName: String = ""
    startingWithLastName: String = ""


@dataclass
class _User:
    id: String
    pictureHash: String
    pictureUrl: Url
    description: PersonDescription
    name: PersonDescription
    sort: String
    deleted: bool = False


@dataclass
class _Group:
    identifier: String
    id: String
    platformId: int
    name: String
    type: String
    icon: String
    sort: String


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
    identifier: String
    id: int
    platformId: int
    name: String
    type: String
    icon: String


@dataclass
class Period:
    id: int
    name: String
    icon: String
    skoreWorkYear: SkoreWorkYear
    isActive: bool
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class Component:
    id: int
    name: String
    abbreviation: String


@dataclass
class Teacher(_User): ...


@dataclass
class Student(_User): ...


@dataclass
class Course:
    id: int
    name: String
    graphic: CourseGraphic
    teachers: list[Teacher]
    skoreClassId: int
    parentCourseId: None | int
    skoreWorkYear: SkoreWorkYear
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))

    def __str__(self):
        ret = f"{self.name} (Teacher"
        if len(self.teachers) != 1:
            ret += "s"
        ret += f": {', '.join(t.name.startingWithLastName for t in self.teachers)}"
        # ret += f", ID: {self.id}"
        return ret + ")"


@dataclass
class Feedback:
    text: String
    user: Teacher


@dataclass
class FeedbackFull:
    attachments: list[String]
    changedAt: DateTime
    createdAt: DateTime
    evaluationId: String
    id: String
    student: Student
    teacher: Teacher
    text: String


@dataclass
class Result:
    identifier: String
    type: Literal["normal"]
    name: String
    graphic: ResultGraphic
    date: DateTime

    gradebookOwner: Teacher
    component: Component | None
    courses: list[Course]
    period: Period
    feedback: list[Feedback]
    feedbacks: list[FeedbackFull]
    availabilityDate: DateTime
    isPublished: bool
    doesCount: bool
    deleted: bool = False

    details: ResultDetails | None = None


@dataclass
class ResultDetails:
    centralTendencies: list[String]
    teachers: list[Teacher]
    dateChanged: DateTime
    userChanged: Teacher
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))


@dataclass
class CourseCondensed:
    name: String
    teacher: String
    url: Url = Field()

    id: int | None = Field(repr=False, default=None)
    platformId: int | None = Field(repr=False, default=None)

    descr: String = Field(repr=False, default="")
    icon: String = Field(repr=False, default="")


@dataclass
class FutureTaskOneTask:
    label: String
    description: String
    icon: String
    warning: bool
    click_handle: String
    activityID: int
    dateID: String
    assignmentID: String
    endMomentTS: String | None
    startMomentID: String
    endMomentID: String
    lessonID: String
    type: String
    classID: String
    course: String
    date: Date
    hourID: String


@dataclass
class FutureTaskOneItem:
    tasks: list[FutureTaskOneTask]
    materials: list[String]


@dataclass
class FutureTaskOneCourse:
    lessonID: String
    hourID: String
    classID: String
    course_title: String
    items: FutureTaskOneItem


@dataclass
class FutureTaskOneDay:
    date: Date
    pretty_date: String
    courses: list[FutureTaskOneCourse]


@dataclass
class AgendaHour:
    hourID: String
    start: String
    end: String
    title: String


@dataclass
class AgendaLesson:
    momentID: String
    lessonID: String
    hourID: String
    date: Date
    subject: String | None
    course: String
    courseTitle: String
    classroom: String
    classroomTitle: String
    teacher: String
    teacherTitle: String
    klassen: String
    klassenTitle: String
    classIDs: String
    bothStartStatus: String
    assignmentEndStatus: String
    testDeadlineStatus: String
    noteStatus: String
    note: String | None
    date_listview: String
    hour: String
    activity: String
    activityID: String | None
    color: String
    hourValue: String
    components_hidden: object
    freedayIcon: String
    someSubjectsEmpty: String | None


@dataclass
class AgendaMomentInfoAssignment:
    startAssignment: String
    start: String
    end: String
    type: String
    description: String
    atdescription: String
    freedeadline: String
    warning: String
    assignmentInfo: String
    assignmentDeadline: String


@dataclass
class AgendaMomentInfo:
    className: String
    subject: String
    materials: String | None
    momentID: String
    assignments: list[AgendaMomentInfoAssignment]


@dataclass
class StudentSupportLink:
    id: String
    name: String
    description: String
    icon: String
    link: Url
    cleanLink: String
    isVisible: bool


@dataclass
class ShortMessage:
    id: int
    fromImage: Url
    subject: String
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
    realBox: String
    sendDate: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class FullMessage:
    id: int
    to: String | None
    subject: String
    date: DateTime
    body: String
    status: int
    attachment: int
    unread: bool
    label: bool
    receivers: list[String]
    ccreceivers: list[String]
    bccreceivers: list[String]
    senderPicture: String
    markedInLVS: None
    fromTeam: int
    totalNrOtherToReciviers: int
    totalnrOtherCcReceivers: int
    totalnrOtherBccReceivers: int
    canReply: bool
    hasReply: bool
    hasForward: bool
    sendDate: DateTime | None
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))


@dataclass
class Attachment:
    fileID: int
    name: String
    mime: String
    size: String
    icon: String
    wopiAllowed: bool
    order: int


@dataclass
class MessageChanged:
    id: int
    new: int = Field(validation_alias=AliasChoices("status", "label", "new"))


@dataclass
class MessageDeletionStatus:
    msgID: int
    boxType: String
    is_deleted: bool = Field(validation_alias=AliasChoices("status", "is_deleted"))


@dataclass
class PlannedElementPeriod:
    dateTimeFrom: datetime
    dateTimeTo: datetime
    wholeDay: bool
    deadline: bool


@dataclass
class PlannedElementOrganisers:
    users: list[_User]


@dataclass
class GroupFilters:
    filters: list
    additionalUsers: list[_User]


@dataclass
class PlannedElementParticipants:
    groups: list[_Group]
    users: list[_User]
    groupFilters: GroupFilters


@dataclass
class UserSeeProperties:
    id: bool
    platformId: bool
    period: bool
    organisers: bool
    participants: bool
    plannedElementType: bool
    isParticipant: bool
    capabilities: bool
    courses: bool
    locations: bool
    name: bool = False


@dataclass
class UserCapabilities:
    canUserTrash: bool
    canUserRestoreFromTrash: bool
    canUserDelete: bool
    canUserEdit: bool
    canUserReplace: bool
    canUserEditPresence: bool
    canUserReschedule: bool
    canUserChangeUserColor: bool
    canUserChangeUserViewMetadata: bool
    canUserSeeProperties: UserSeeProperties

    canUserChangeOrganisers: bool = False
    canUserChangeParticipants: bool = False
    canUserChangeParticipantGroupFilters: bool = False
    canUserChangeCourses: bool = False
    canUserChangeLocations: bool = False
    canUserCreateVideoCall: bool = False
    canUserSeeVideoCall: bool = False
    canUserManageVideoCall: bool = False


@dataclass
class PlannedElementCourseCluster:
    id: int
    name: String


@dataclass
class PlannedElementCourse:
    id: UUID
    platformId: int
    name: String
    scheduleCodes: list[String]
    icon: String
    courseCluster: PlannedElementCourseCluster
    isVisible: bool


@dataclass
class PlannedElementLocation:
    id: UUID
    platformId: int
    platformName: String
    number: String
    title: String
    icon: String
    type: String
    selectable: bool


@dataclass
class PlannedElementJoinIds:
    from_: String = Field(validation_alias=AliasChoices("from", "from_"))
    to: String = Field(alias="to")


@dataclass
class PlannedElementAssignmentType:
    id: UUID
    name: String
    abbreviation: String
    isVisible: bool
    weight: int


@dataclass
class PlannedElement:
    id: UUID
    platformId: int
    period: PlannedElementPeriod
    organisers: PlannedElementOrganisers
    participants: PlannedElementParticipants
    plannedElementType: String
    isParticipant: bool
    capabilities: UserCapabilities
    courses: list[PlannedElementCourse]
    locations: list[PlannedElementLocation]
    sort: String
    unconfirmed: bool
    pinned: bool
    color: String
    joinIds: PlannedElementJoinIds

    name: String = ""
    assignmentType: PlannedElementAssignmentType | None = None
    resolvedStatus: String = ""
    onlineSession: String | None = None


@dataclass
class ApplicableAssignmentType:
    id: UUID
    platformId: int
    name: String
    abbreviation: String
    isVisible: bool
    weight: float


@dataclass
class Report:
    id: int
    name: String
    icon: String
    date: DateTime
    downloadUrl: Url
    class_: Class_ = Field(validation_alias=AliasChoices("class", "class_"))
    schoolyearLabel: String = Field()
