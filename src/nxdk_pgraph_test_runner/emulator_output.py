# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: T201 `print` found

from __future__ import annotations

import re
from dataclasses import dataclass

_XEMU_VERSION_RE = re.compile(R"xemu_version:\s*(.+)")
_XEMU_BRANCH_RE = re.compile(R"xemu_branch:\s*(.+)")
_XEMU_COMMIT_RE = re.compile(R"xemu_commit:\s*(.+)")


@dataclass
class EmulatorOutput:
    """Models information about execution of an xbox emulator."""

    emulator_version: str
    machine_info: str
    failure_info: str

    @classmethod
    def parse(cls, stdout: list[str], stderr: list[str]) -> EmulatorOutput:
        """Extracts information from the stdout and stderr from running an emulator."""
        return cls(*parse_emulator_info(stdout, stderr))


def parse_emulator_info(stdout: list[str], stderr: list[str]) -> tuple[str, str, str]:
    """Attempts to parse (emulator_version, machine_info, failure_info) from the emulator output."""
    del stdout
    if stderr:
        while stderr and "AppImage" in stderr[0]:
            stderr.pop(0)
        if stderr and stderr[0].startswith("xemu"):
            return _parse_xemu_info(stderr)

    return "", "", ""


def _parse_xemu_info(stderr: list[str]) -> tuple[str, str, str]:
    """Parses xemu stderr output for (emulator_version, machine_info, failure_info)."""

    version_components = ["xemu"]

    def parse_component(regex):
        for line in stderr:
            match = regex.match(line)
            if not match:
                continue
            version_components.append(match.group(1))

    parse_component(_XEMU_VERSION_RE)
    parse_component(_XEMU_BRANCH_RE)
    parse_component(_XEMU_COMMIT_RE)

    machine_info: list[str] = []
    failure_info: list[str] = []
    target = machine_info

    for line in stderr:
        target.append(line)
        if line.startswith("GL_SHADING_LANGUAGE_VERSION:"):
            target = failure_info

    version = "-".join(version_components)
    return version, "\n".join(machine_info), "\n".join(failure_info)
