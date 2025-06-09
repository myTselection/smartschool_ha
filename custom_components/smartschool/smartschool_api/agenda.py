from __future__ import annotations

import time
from abc import ABC
from datetime import datetime, date, timedelta  # Added date import

from ._xml_interface import SmartschoolXML_WeeklyCache
from .objects import AgendaHour, AgendaLesson, AgendaMomentInfo


class AgendaPoster(SmartschoolXML_WeeklyCache, ABC):
    """Caches the information on a weekly basis, and posts to the mentioned URL."""

    _url: str = "/?module=Agenda&file=dispatcher"


class SmartschoolLessons(AgendaPoster):
    """
    Interface to the retrieval of lessons for a certain date.

    To reproduce: open the agenda, one of the XHR calls is this one.

    This includes (for an example check the tests):
    - momentID: a unique identifier for this specific lesson
    - lessonID: a group id
    - hourID: link to `AgendaHours`
    - date: YYYY-mm-dd
    - subject: explanation by the teacher
    - course
    - courseTitle
    - classroom: what classroom this is in
    - classroomTitle: same as `classroom`?
    - teacher: name of the teacher (Lastname + initial of firstname)
    - teacherTitle:
    - klassen
    - klassenTitle
    - classIDs
    - bothStartStatus
    - assignmentEndStatus
    - testDeadlineStatus
    - noteStatus
    - note
    - date_listview
    - hour
    - activity
    - activityID
    - color
    - hourValue
    - components_hidden
    - freedayIcon
    - someSubjectsEmpty
    """

    @property
    def _xpath(self) -> str:
        return ".//lesson"

    @property
    def _object_to_instantiate(self) -> type[AgendaLesson]:
        return AgendaLesson

    @property
    def _subsystem(self) -> str:
        return "agenda"

    @property
    def _action(self) -> str:
        return "get lessons"

    @property
    def _params(self) -> dict:
        # Ensure we have a datetime object before calling timestamp()
        dt_to_use = self.timestamp_to_use or datetime.now()
        if isinstance(dt_to_use, date) and not isinstance(dt_to_use, datetime):
            # Convert date to datetime (assuming start of day)
            dt_to_use = datetime.combine(dt_to_use, datetime.min.time())

        now_ts = dt_to_use.timestamp()
        in_20_days_ts = now_ts + 20 * 24 * 3600

        return {
            "startDateTimestamp": now_ts,  # Use the calculated timestamp
            "endDateTimestamp": in_20_days_ts, # Use the calculated timestamp
            "filterType": "false",
            "filterID": "false",
            "gridType": "1",
            "classID": "0",
            "endDateTimestampOld": in_20_days_ts, # Use the calculated timestamp
            "forcedTeacher": "0",
            "forcedClass": "0",
            "forcedClassroom": "0",
            "assignmentTypeID": "1",
        }


class SmartschoolHours(AgendaPoster):
    """
    Interface to the retrieval of periods (called Hours in smartschool).

    To reproduce: open the agenda, one of the XHR calls is this one.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    @property
    def _xpath(self) -> str:
        return ".//hour"

    @property
    def _object_to_instantiate(self) -> type[AgendaHour]:
        return AgendaHour

    @property
    def _subsystem(self) -> str:
        return "grid"

    @property
    def _action(self) -> str:
        return "get hours"

    @property
    def _params(self) -> dict:
        return {"date": int(time.time())}

    def search_by_hourId(self, hourId: str):
        for hour in self._xml():
            if hour.hourID == hourId:
                return hour

        raise ValueError(f"Couldn't find {hourId}")


class SmartschoolMomentInfos(AgendaPoster):
    """
    Interface to the retrieval of one particular moment (a book-symbol in smartschool).

    To reproduce: open the agenda, click on a yellow/red book. This is the XHR call that appears.

    This includes (for an example check the tests):
    - hourID: unique identifier for this period
    - start: HH:MM starting time
    - end: HH:MM ending time
    - title: how it is called in the agenda
    """

    def __init__(self, moment_id: str):
        super().__init__()

        moment_id = str(moment_id).strip()
        if not moment_id:
            raise ValueError("Please provide a valid MomentID")

        self._moment_id = moment_id

    @property
    def _xpath(self) -> str:
        return ".//class"

    @property
    def _object_to_instantiate(self) -> type[AgendaMomentInfo]:
        return AgendaMomentInfo

    @property
    def _subsystem(self) -> str:
        return "agenda"

    @property
    def _action(self) -> str:
        return "get moment info"

    @property
    def _params(self) -> dict:
        return {
            "momentID": self._moment_id,
            "dateID": "",
            "assignmentIDs": "",
            "activityID": "0",
        }

    def _post_process_element(self, element: dict) -> None:
        """In this XML we have `assignments.assignment`, but I don't need that `assignment` tag."""
        if element["assignments"] is None:
            element["assignments"] = []
            return

        if isinstance(element["assignments"]["assignment"], list):
            element["assignments"] = element["assignments"]["assignment"]
        else:
            element["assignments"] = [element["assignments"]["assignment"]]
