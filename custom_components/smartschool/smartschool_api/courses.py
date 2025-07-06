from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias, overload

# from logprise import logger
import logging

from . import objects
from .common import (
    bs4_html,
    convert_to_datetime,
    create_filesystem_safe_filename,
    create_filesystem_safe_path,
    natural_sort,
    parse_mime_type,
    parse_size,
    save_test_response,
)
from .exceptions import SmartSchoolException, SmartSchoolParsingError
from .objects import Course
from .session import SessionMixin

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    from bs4 import BeautifulSoup, Tag
    from requests import Response

logger = logging.getLogger(__name__) # Use a logger instance
__all__ = ["CourseCondensed", "Courses", "DocumentOrFolderItem", "FileItem", "FolderItem", "InternetShortcut", "TopNavCourses"]


@dataclass
class CourseCondensed(objects.CourseCondensed, SessionMixin):
    def __str__(self):
        return f"{self.name} (Teacher: {self.teacher})"

    @property
    def items(self) -> list[DocumentOrFolderItem]:
        return FolderItem(session=self.session, parent=None, course=self, name="(Root)").items


@dataclass
class TopNavCourses(SessionMixin):
    """
    Retrieves a list of the courses which are available from the top navigation bar.

    This structure is different from the `Courses` results.

    Example:
    -------
    >>> for course in TopNavCourses(session):
    >>>     print(course.name)
    Aardrijkskunde_3_LOP_2023-2024
    bibliotheek

    """

    @cached_property
    def _list(self) -> list[CourseCondensed]:
        return [CourseCondensed(session=self.session, **course) for course in self.session.json("/Topnav/getCourseConfig", method="post")["own"]]

    def __iter__(self) -> Iterator[CourseCondensed]:
        yield from self._list


@dataclass
class Courses(SessionMixin):
    """
    Retrieves a list of the courses.

    This structure is different from the `TopNavCourses` results.

    To reproduce: go to "Results", one of the XHR calls is this one

    Example:
    -------
    >>> for course in Courses(session):
    >>>     print(course.name)
    Aardrijkskunde
    Biologie

    """

    @cached_property
    def _list(self) -> list[Course]:
        return [Course(**course) for course in self.session.json("/results/api/v1/courses/")]

    def __iter__(self) -> Iterator[Course]:
        yield from self._list


@dataclass
class FileItem(SessionMixin):
    """Represents a file within a course document folder."""

    parent: FolderItem = field(repr=False)
    id: int
    name: str
    mime_type: str
    size_kb: float | str
    last_modified: datetime | str
    download_url: str | None = None
    view_url: str | None = None

    def __post_init__(self):
        self.mime_type = parse_mime_type(self.mime_type)
        self.size_kb = parse_size(self.size_kb)
        self.last_modified = convert_to_datetime(self.last_modified)

    @cached_property
    def _suffix(self) -> str:
        match self.mime_type:
            case "docx" | "word":
                return ".docx"
            case "doc":
                return ".doc"
            case "xlsx" | "excel" | "xls":
                return ".xlsx"
            case "odt":
                return ".odt"
            case "pdf":
                return ".pdf"
            case "powerpointpresentatie" | "pptx":
                return ".pptx"
            case "ppt":
                return ".ppt"
            case "video" | "m4v" | "mp4":
                return ".mp4"
            case "wmv":
                return ".wmv"
            case "audio" | "mp3":
                return ".mp3"
            case "zip":
                return ".zip"
            case "rar":
                return ".rar"
            case "7z":
                return ".7z"
            case "text" | "txt":
                return ".txt"
            case "jpg" | "jpeg":
                return ".jpg"
            case "png":
                return ".png"
            case "html":
                return ".html"
            case "ascii":
                return ".txt"
            case "potx":
                return ".potx"

        logger.warning(f"Unknown mime type: {self.mime_type}")
        return f".{self.mime_type}"

    @cached_property
    def filename(self) -> str:
        filename = self.name
        if "." not in self.name:
            filename += self._suffix

        return create_filesystem_safe_filename(filename)

    def download_to_dir(self, target_directory: Path, *, overwrite: bool = False) -> Path:
        return self.download(target_directory / self.filename, overwrite=overwrite)

    @overload
    def download(self, to_file: Path | str, *, overwrite: bool) -> Path: ...

    @overload
    def download(self) -> bytes: ...

    def _real_download(self, target: Path | None) -> bytes | Path:
        if target:
            logger.debug(f"Downloading file: {target.name}")
        response: Response = self.session.get(self.download_url)
        response.raise_for_status()

        if match := re.search(r'filename="([^"]+)"', response.headers.get("Content-Disposition") or ""):
            found_filename = Path(match.group(1))
            if found_filename.suffix != self._suffix:
                logger.warning(f"Expected suffix {self._suffix}, got {found_filename.suffix}")

        save_test_response(response)

        if target:
            target.write_bytes(response.content)
            return target

        return response.content

    def download(self, to_file: Path | str | None = None, *, overwrite: bool = False) -> bytes | Path:
        target = None
        if to_file:
            target = create_filesystem_safe_path(to_file)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not overwrite and target.exists():
                return target

        return self._real_download(target)


@dataclass
class InternetShortcut(FileItem):
    """Represents an internet shortcut file within a course document folder."""

    link: str = ""

    def __post_init__(self):
        super().__post_init__()

        if not self.link:
            raise SmartSchoolException("No link found in internet shortcut")

    def _real_download(self, target: Path | None) -> bytes | Path:
        content = "\r\n".join(
            [
                "[InternetShortcut]",
                f"URL={self.link}",
            ]
        ).encode("utf8")
        if target:
            target.write_bytes(content)
            return target

        return content

    @cached_property
    def filename(self) -> str:
        name = self.name
        if "." in name:
            name = name.rsplit(".", 1)[0]

        return create_filesystem_safe_filename(name + ".url")


@dataclass
class FolderItem(SessionMixin):
    """Represents a subfolder within a course document folder."""

    parent: FolderItem | None = field(repr=False)
    course: CourseCondensed = field(repr=False)
    name: str = field()
    browse_url: str | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.browse_url is None:
            self.browse_url = f"/Documents/Index/Index/courseID/{self.course.id}/ssID/{self.course.platformId}"

    def _get_folder_html(self) -> BeautifulSoup:
        """Fetch HTML content for a specific folder."""
        try:
            response = self.session.get(
                self.browse_url,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": self.session.create_url("/"),
                },
            )
            response.raise_for_status()
            save_test_response(response)
            return bs4_html(response)
        except Exception as e:
            raise SmartSchoolException(f"Failed to fetch folder HTML: {e}") from e

    def _get_mime_from_row_image(self, row: Tag) -> str | None:
        for entry in row.select_one("div.smsc_cm_body_row_block").get("style").split(";"):
            if not entry.strip():
                continue
            first, second = entry.split(":", 1)
            if first.strip() == "background-image":
                return re.search("/mime_[^_]+_([^/_]+)", second).group(1)

        return None

    def _parse_document_row(self, row: Tag) -> FileItem:
        """Parse a single table row into a file item."""
        id_ = int(row.get("id")[6:])
        mime_block = row.select_one("div.smsc_cm_body_row_block_mime").get_text(strip=True, separator="\n")
        _, size_kb, last_modified = mime_block.split(" - ")
        mime_style = self._get_mime_from_row_image(row)

        link_texts = [link_text for r in row.select("a") if (link_text := r.get_text(strip=True, separator="\n"))]
        if len(link_texts) == 0:
            raise AssertionError("Expected exactly one link text, got None")

        filename = link_texts[0]

        inline_links = row.select("div.smsc_cm_body_row_block_inline a,div.smsc_cm_body_row_block_inline iframe")
        if inline_links:
            inline_link = inline_links[0]
            if inline_link.name == "iframe":
                final_link = inline_link["src"]
            elif inline_link.name == "a":
                final_link = inline_link["href"]
            else:
                raise AssertionError(f"Unknown inline link type: {inline_link.name}")

            return InternetShortcut(
                session=self.session,
                parent=self,
                id=0,
                name=link_texts[0],
                mime_type=mime_style,
                size_kb=size_kb,
                last_modified=last_modified,
                link=final_link,
            )

        dl_link, view_link, onclick_link = self._figure_out_item_links(row)
        if onclick_link is not None:
            return InternetShortcut(
                session=self.session,
                parent=self,
                id=id_,
                name=link_texts[0],
                mime_type=mime_style,
                size_kb=size_kb,
                last_modified=last_modified,
                link=onclick_link,
            )

        return FileItem(
            session=self.session,
            parent=self,
            id=id_,
            name=filename,
            mime_type=mime_style,
            size_kb=size_kb,
            last_modified=last_modified,
            download_url=dl_link,
            view_url=view_link,
        )

    def _extract_url_from_onclick(self, onclick: str) -> str | None:
        """Extract URL from window.open onclick JavaScript."""
        match = re.search(r'window\.open\(["\']([^"\']+)["\']', onclick)
        return match.group(1) if match else None

    def _figure_out_item_links(self, row):
        """Extract download and view links from row elements."""
        links = row.select("a")
        dl_link, view_link, onclick_link = None, None, None

        for link in links:
            classes = link.get("class") or []
            href = link.get("href")
            onclick = link.get("onclick")

            if any(
                dlclass in classes
                for dlclass in [
                    "download-link",
                    "smsc-download__icon",
                    "smsc-download__icon--large-margin",
                    "smsc-download__icon--download",
                ]
            ):
                dl_link = href
            elif "smsc-download__link" in classes:
                view_link = href
            elif "smsc_cm_link" in classes and onclick:
                onclick_link = self._extract_url_from_onclick(onclick)

        return dl_link, view_link, onclick_link

    def _parse_folder_row(self, row: Tag) -> FolderItem:
        """Parse a single table row into a folder item."""
        for link in row.select("a"):
            classes = link.get("class") or []
            if "smsc_cm_link" in classes:
                browse_url = link["href"]
                name = link.get_text(strip=True, separator="\n")
                return FolderItem(
                    session=self.session,
                    parent=self,
                    course=self.course,
                    name=name,
                    browse_url=browse_url,
                )

        raise SmartSchoolParsingError("No browse URL found")

    def _parse_row(self, row: Tag) -> DocumentOrFolderItem | None:
        """Parse a single table row into a file or folder item."""
        if row.get("id") and row.get("id").lower().startswith("docid_"):
            return self._parse_document_row(row)
        return self._parse_folder_row(row)

    @cached_property
    def items(self) -> list[DocumentOrFolderItem]:
        """Fetch items from this folder."""
        soup = self._get_folder_html()
        rows = soup.select("div.smsc_cm_body_row", recursive=False)

        items = [item for row in rows if (item := self._parse_row(row))]
        return sorted(items, key=lambda x: (0 if isinstance(x, FolderItem) else 1,) + natural_sort(x.name))


DocumentOrFolderItem: TypeAlias = FileItem | FolderItem | InternetShortcut
