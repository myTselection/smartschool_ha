from __future__ import annotations

import contextlib
import functools
import inspect
import json
import operator
import platform
import re
import smtplib
import sys
import traceback
import warnings
import xml.etree.ElementTree as ET
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable, Literal

from bs4 import BeautifulSoup, FeatureNotFound, GuessedAtParserWarning
from pydantic import RootModel
from pydantic.dataclasses import is_pydantic_dataclass
from requests import Response

__all__ = [
    "send_email",
    "capture_and_email_all_exceptions",
    "save",
    "IsSaved",
    "bs4_html",
    "get_all_values_from_form",
    "make_filesystem_safe",
    "as_float",
    "xml_to_dict",
]

_used_bs4_option = None


class IsSaved(Enum):
    NEW = auto()
    UPDATED = auto()
    SAME = auto()


def save(
    type_: Literal["agenda", "punten", "todo"], course_name: str, id_: str, data: dict | str | Any, is_eq: Callable = operator.eq, extension: str = "json"
) -> IsSaved | dict | str:
    save_as = Path.cwd() / f".cache/_{type_}/{course_name}/{id_}.{extension}"
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

    print(f"Sending email >> {subject}")

    if platform.system() == "Windows":
        print("=================== On Linux we would have sent this: ===================")
        print(f"Subject: {subject}")
        print("")
        print(text)
        print("=========================================================================")
        return

    with smtplib.SMTP("localhost") as server:
        server.sendmail(
            from_addr=email_from,
            to_addrs=email_to,
            msg=message.as_string(),
        )


def capture_and_email_all_exceptions(
    email_from: str | list[str], email_to: str | list[str], subject: str = "[⚠Smartschool parser⚠] Something went wrong"
) -> Callable:
    def decorator(func):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            frm = inspect.stack()[1]
            module_name = Path(frm.filename)
            function_signature = f"{module_name.stem}.{func.__name__}"

            print(f"[{function_signature}] Start")
            try:
                result = func(*args, **kwargs)
            except Exception as ex:
                print(f"[{function_signature}] An exception happened: {ex}")

                send_email(
                    email_to=email_to,
                    email_from=email_from,
                    subject=subject,
                    text="".join(traceback.format_exception(None, ex, ex.__traceback__)),
                )

                sys.exit(1)

            print(f"[{function_signature}] Finished")
            return result

        return inner

    return decorator


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


def get_all_values_from_form(html, form_selector):
    form = html.select(form_selector)
    assert len(form) == 1, f"We should have only 1 form. We got {len(form)}!"
    form = form[0]

    # action = form.attrs.get("action").lower()
    # method = form.attrs.get("method", "get").lower()
    all_inputs = form.find_all(["input", "button", "textarea", "select"])

    inputs = []
    for input_tag in all_inputs:
        tag_name = input_tag.name.lower()
        attrs = input_tag.attrs

        if "name" not in attrs:
            continue

        if tag_name == "select":
            select_options = []
            value = ""
            for select_option in input_tag.find_all("option"):
                option_value = select_option.attrs.get("value")
                if option_value:
                    select_options.append(option_value)
                    if "selected" in select_option.attrs:
                        value = option_value
            if not value and select_options:
                # if the default is not set, and there are options, take the first option as default
                value = select_options[0]
            # add the select to the inputs list
            inputs.append({"name": attrs.get("name"), "values": select_options, "value": value})
        else:
            inputs.append(
                {
                    "name": attrs.get("name"),
                    "value": attrs.get("value", ""),
                }
            )

    return inputs


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
