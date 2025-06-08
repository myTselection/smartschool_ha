import logging

from .agenda import SmartschoolHours, SmartschoolLessons, SmartschoolMomentInfos
from .courses import (
    Courses,
    TopNavCourses,
    CourseDocuments,
    FolderItem,
    FileItem,
    DocumentOrFolderItem
)
from .credentials import EnvCredentials, PathCredentials, Credentials, AppCredentials
from .exceptions import (
    SmartSchoolException, # Corrected casing
    SmartSchoolAuthenticationError, # Corrected casing
    SmartSchoolParsingError, # Corrected casing
    SmartSchoolDownloadError # Corrected casing
)
from .file_fetch import download_document
from .logger import setup_logger
from .messages import (
    AdjustMessageLabel,
    Attachments,
    BoxType,
    MarkMessageUnread,
    Message,
    MessageHeaders,
    MessageLabel,
    MessageMoveToArchive,
    MessageMoveToTrash,
    SortField,
    SortOrder,
)
from .objects import FutureTasks
from .periods import Periods
from .results import ResultDetail, Results
from .session import Smartschool
from .student_support import StudentSupportLinks

__all__ = [
    "PathCredentials",
    "EnvCredentials",
    "AppCredentials",
    "Credentials",
    "Smartschool",
    "logger",
    "Courses",
    "TopNavCourses",
    "CourseDocuments",
    "FolderItem",
    "FileItem",
    "DocumentOrFolderItem",
    "Results",
    "Periods",
    "FutureTasks",
    "SortField",
    "SortOrder",
    "BoxType",
    "MessageHeaders",
    "StudentSupportLinks",
    "SmartschoolHours",
    "SmartschoolLessons",
    "SmartschoolMomentInfos",
    "Message",
    "Attachments",
    "MarkMessageUnread",
    "AdjustMessageLabel",
    "MessageMoveToArchive",
    "MessageMoveToTrash",
    "MessageLabel",
    "ResultDetail",
    "download_document",
    # Exceptions
    "SmartSchoolException", # Corrected casing
    "SmartSchoolAuthenticationError", # Corrected casing
    "SmartSchoolParsingError", # Corrected casing
    "SmartSchoolDownloadError", # Corrected casing
]

logger = setup_logger(logging.DEBUG)
