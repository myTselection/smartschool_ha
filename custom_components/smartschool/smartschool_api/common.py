from __future__ import annotations

import contextlib
import json
import operator
import platform
import re
import smtplib
import warnings
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal
from urllib.parse import parse_qs, quote_plus, urlparse

from bs4 import BeautifulSoup, FeatureNotFound, GuessedAtParserWarning
# from logprise import logger
import logging
from pydantic import RootModel
from pydantic.dataclasses import is_pydantic_dataclass
from requests import Response

__all__ = [
    "IsSaved",
    "as_float",
    "bs4_html",
    "get_all_values_from_form",
    "make_filesystem_safe",
    "save",
    "send_email",
    "xml_to_dict",
]

from .exceptions import SmartSchoolParsingError

if TYPE_CHECKING:
    from objects import String

_used_bs4_option = None

logger = logging.getLogger(__name__) # Use a logger instance

class IsSaved(Enum):
    NEW = auto()
    UPDATED = auto()
    SAME = auto()


def save(
    session: "Smartschool",  # noqa: UP037, F821
    type_: Literal["agenda", "punten", "todo"],
    course_name: str,
    id_: str,
    data: dict | str | Any,
    is_eq: Callable = operator.eq,
    extension: str = "json",
) -> IsSaved | dict | str:
    save_as = session.cache_path / f"_{type_}/{course_name}/{id_}.{extension}"

    save_as.parent.mkdir(exist_ok=True, parents=True)
    data_was_dict = isinstance(data, dict)
    data_was_object = is_pydantic_dataclass(data.__class__)

    if data_was_dict:
        to_write = json.dumps(data, indent=4)
    elif data_was_object:
        to_write = RootModel[data.__class__](data).model_dump_json(indent=4)
    else:
        to_write = data

    if not save_as.exists():
        save_as.write_text(to_write, encoding="utf8")
        return IsSaved.NEW

    old_data = save_as.read_text(encoding="utf8")
    if data_was_dict or data_was_object:
        old_data = json.loads(old_data)
    if data_was_object:
        old_data = data.__class__(**old_data)

    if is_eq(data, old_data):
        return IsSaved.SAME

    save_as.write_text(to_write, encoding="utf8")
    return old_data


def send_email(
    subject: str,
    text: str,
    email_to: list[str] | str,
    email_from: str,
):
    if isinstance(email_to, str):
        email_to = [email_to]

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = email_from
    message["To"] = ", ".join(email_to)
    message.attach(MIMEText(text, "plain", "utf8"))

    logger.info(f"Sending email >> {subject}")

    if platform.system() == "Windows":  # pragma: no cover
        logger.info("=================== On Linux we would have sent this: ===================")
        logger.info(f"Subject: {subject}")
        logger.info("")
        logger.info(text)
        logger.info("=========================================================================")
        return

    with smtplib.SMTP("localhost") as server:
        server.sendmail(
            from_addr=email_from,
            to_addrs=email_to,
            msg=message.as_string(),
        )


def bs4_html(html: str | bytes | Response) -> BeautifulSoup:
    global _used_bs4_option

    if isinstance(html, Response):
        html = html.text

    possible_options = [
        _used_bs4_option,
        {"parser": "html.parser", "features": "lxml"},
        {"features": "html5lib"},
        {"features": "html.parser"},
    ]

    for kw in possible_options:  # pragma: no branch
        if kw is None:
            continue

        with contextlib.suppress(FeatureNotFound):
            parsed = BeautifulSoup(html, **kw)
            _used_bs4_option = kw
            return parsed

    _used_bs4_option = {}
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=GuessedAtParserWarning)
        return BeautifulSoup(html)


def get_all_values_from_form(html: BeautifulSoup, form_selector: str):
    """Extract form input values from HTML."""
    form = html.select(form_selector)

    if len(form) != 1:
        raise AssertionError(f"We should have only 1 form. We got {len(form)}!")

    form = form[0]

    all_inputs = form.find_all(["input", "button", "textarea", "select"])

    inputs = []
    for input_tag in all_inputs:
        tag_name = input_tag.name.lower()
        attrs = input_tag.attrs

        if "name" not in attrs:
            continue

        form_element = {
            "name": attrs.get("name"),
            "value": attrs.get("value", ""),
        }

        if tag_name == "select":
            select_options = []
            form_element["values"] = select_options

            is_multiple = "multiple" in [attr.lower() for attr in attrs]
            selected_values = []

            for select_option in input_tag.find_all("option"):
                # Use value attribute if present, otherwise use text content
                option_value = select_option.attrs.get("value")
                if option_value is None:
                    option_value = select_option.get_text().strip()

                if option_value:  # Only add non-empty values
                    select_options.append(option_value)
                    # Case-insensitive check for selected attribute
                    if any(attr.lower() == "selected" for attr in select_option.attrs):
                        selected_values.append(option_value)

            # Handle value assignment based on multiple attribute
            if is_multiple:
                form_element["value"] = selected_values
            else:
                if selected_values:
                    form_element["value"] = selected_values[-1]  # Last selected wins for single select
                elif select_options:
                    form_element["value"] = select_options[0]
                else:
                    form_element["value"] = None

        inputs.append(form_element)
    return inputs


def fill_form(response: Response, form_selector, values: dict[str, str]) -> dict[str, str]:
    html = bs4_html(response)
    inputs = get_all_values_from_form(html, form_selector)

    data = {}
    values = values.copy()

    for input_ in inputs:
        name = input_["name"]
        for key, _value in values.items():
            if key in name:
                data[name] = values.pop(key)
                break
        else:
            data[name] = input_["value"]

    if len(values) != 0:
        raise AssertionError(f"You didn't use: {sorted(values)}")

    return data


def make_filesystem_safe(name: str) -> str:
    name = re.sub("[^-_a-z0-9.]+", "_", name, flags=re.IGNORECASE)
    name = re.sub("_{2,}", "_", name)
    return name


def as_float(txt: str) -> float:
    return float(txt.replace(",", "."))


def xml_to_dict(element, *, depth: int = 0):
    if depth == 0 and isinstance(element, str):
        element = ET.XML(element.strip())

    result = {}

    for child in element:
        tag = child.tag
        if len(child) == 0:  # Leaf node?
            child_data = child.text
        else:
            child_data = xml_to_dict(child)

        if tag in result:
            if not isinstance(result[tag], list):
                # If the tag already exists, convert it to a list
                result[tag] = [result[tag]]
            result[tag].append(child_data)
        else:
            result[tag] = child_data

    return result


def convert_to_datetime(x: str | String | date | datetime | None) -> datetime:
    if x is None:
        return datetime.now().astimezone()

    if isinstance(x, datetime):
        if x.tzinfo is None:
            raise ValueError("No timezone information found in this date")
        return x

    if isinstance(x, date):
        return datetime.combine(x, datetime.min.time()).astimezone()

    possible_formats = [
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in possible_formats:
        with contextlib.suppress(ValueError):
            x = datetime.strptime(x, fmt)
            if x.tzinfo is None:
                return x.astimezone()
            return x

    raise SmartSchoolParsingError(f"Cannot convert '{x}' to `datetime`")


def convert_to_date(x: str | String | date | datetime | None) -> date:
    if x is None:
        return date.today()
    if isinstance(x, datetime):
        return x.date()
    if isinstance(x, date):
        return x

    with contextlib.suppress(ValueError):
        return datetime.strptime(x, "%Y-%m-%d").date()

    raise SmartSchoolParsingError(f"Cannot convert '{x}' to `date`")


def parse_size(size_str: str | float) -> float | None:
    """Parse size string to KB value with support for binary units."""
    if isinstance(size_str, (int, float)):
        return size_str

    if not size_str or size_str.strip() in ("-", ""):
        return None

    match = re.search(r"([\d,.]+)\s*(Ki?B|Mi?B|Gi?B)", size_str, re.IGNORECASE)
    if not match:
        return None

    try:
        value = float(match.group(1).replace(",", "."))
        unit = match.group(2).upper()

        multipliers = {
            "KB": 1,
            "KIB": 1,
            "MB": 1_024,
            "MIB": 1_000,
            "GB": 1_024 * 1_024,
            "GIB": 1_000_000,
        }

        return value * multipliers.get(unit, 1)
    except ValueError:
        return None


def parse_mime_type(file_type_string: str) -> str:
    """Parse MIME type string to a standard format."""
    current = file_type_string.lower().strip().replace("-", " ")

    prev = None
    while current != prev:
        prev = current
        for extra in {"file", "bestand", "document", "fichier"}:
            current = current.removesuffix(extra).strip()

    return current


def create_filesystem_safe_path(path: Path | str) -> Path:
    """Create a filesystem-safe path with proper length and extension handling."""
    parts = list(Path(path).parts)

    # Don't modify drive letters (first part on Windows like 'C:')
    if parts and platform.system() == "Windows" and ":" in parts[0]:  # pragma: no cover
        safe_parts = [parts[0]] + [create_filesystem_safe_filename(part) for part in parts[1:]]
    else:
        safe_parts = [create_filesystem_safe_filename(part) for part in parts]

    return Path(*safe_parts).resolve().absolute()


def create_filesystem_safe_filename(filename: str) -> str:
    """Create a filesystem-safe filename with proper length and extension handling."""
    if not filename.strip():
        return "unnamed"

    # Split extension before processing
    path = Path(filename)
    name, ext = path.stem, path.suffix

    # Replace unsafe chars and normalize whitespace
    safe_name = name.replace('"', "'")
    safe_name = re.sub(r"\s*:\s*", " - ", safe_name).strip()
    safe_name = re.sub(r"[^-\w\s.']", "_", safe_name).strip()
    safe_name = re.sub(r"[\s_]{2,}", "_", safe_name)
    safe_name = re.sub(r"\.{2,}", ".", safe_name)

    # Remove leading/trailing dots and underscores
    safe_name = safe_name.strip("._- \r\n\t")

    if not safe_name:
        safe_name = "unnamed"

    # Truncate if too long (accounting for extension)
    max_len = 255 - len(ext)
    if len(safe_name) > max_len:
        safe_name = safe_name[:max_len].rstrip("._")

    return safe_name + ext


def save_test_response(response: Response) -> None:  # pragma: no cover
    """Save response content to test data directory."""
    request = response.request
    test_dir = Path(__file__).parent.parent.parent / "tests/requests" / request.method.lower()

    parsed_url = urlparse(request.url)

    if hasattr(request, "body") and request.body:
        try:
            xml = parse_qs(request.body)["command"][0]
            subsystem = re.search(r"<subsystem>(.*?)</subsystem>", xml).group(1)
            action = re.search(r"<action>(.*?)</action>", xml).group(1)
            file_path = test_dir / subsystem / f"{action}.xml"
        except (AttributeError, KeyError):
            path_parts = [p.lower() for p in parsed_url.path.split("/") if p]
            query_part = quote_plus(parsed_url.query) if parsed_url.query else ""
            file_path = test_dir / Path(*path_parts) / query_part / "response"
    else:
        path_parts = [p.lower() for p in parsed_url.path.split("/") if p]
        file_path = test_dir / Path(*path_parts) / "response"

    # Check Content-Disposition header for filename
    content_disposition = response.headers.get("content-disposition", "")
    filename_match = re.search(r'filename[*]?=["\']?([^"\';\s]+)', content_disposition)

    if filename_match:
        original_filename = filename_match.group(1)
        extension = Path(original_filename).suffix
        file_path = file_path.with_suffix(extension)
    else:
        content_type = response.headers.get("content-type", "").split(";")[0].strip()

        extension_map = {
            "application/json": ".json",
            "text/html": ".html",
            "text/xml": ".xml",
            "application/xml": ".xml",
            "text/plain": ".txt",
            "application/pdf": ".pdf",
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/zip": ".zip",
            "application/octet-stream": ".bin",
            "application/force-download": ".bin",
        }

        extension = extension_map.get(content_type, ".bin")
        file_path = file_path.with_suffix(extension)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(response.content)


def natural_sort(text: str, *, case_insensitive: bool = True) -> tuple[str | int, ...]:
    """Convert string to a natural sort key for human-friendly sorting."""
    if case_insensitive:
        text = text.lower()

    return tuple(int(chunk) if chunk.isdigit() else chunk for chunk in re.split(r"(\d+)", text))
