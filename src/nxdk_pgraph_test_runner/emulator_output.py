# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

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

    @property
    def is_vulkan(self) -> bool:
        """Indicates whether this emulator output used the Vulkan renderer."""
        return is_vulkan_machine_info(self.machine_info)


def is_vulkan_machine_info(machine_info: str) -> bool:
    """Checks if the given machine info indicates that Vulkan was enabled."""
    return any(
        marker in machine_info
        for marker in (
            "\n- VK_",
            "\nSelected physical device",
            "\nAvailable physical devices:",
            "\nEnabled device extensions:",
            "\nVK geometry shader winding",
        )
    )


def parse_emulator_info(stdout: list[str], stderr: list[str]) -> tuple[str, str, str]:
    """Attempts to parse (emulator_version, machine_info, failure_info) from the emulator output."""
    del stdout
    if stderr:
        while stderr and "AppImage" in stderr[0]:
            stderr.pop(0)
        if stderr and stderr[0].startswith("xemu"):
            return _parse_xemu_info(stderr)

    return "", "", ""


_VULKAN_START_PREFIXES = (
    "Enabled instance extensions:",
    "Available physical devices:",
    "Selected physical device",
    "Enabled device extensions:",
)

_VULKAN_CONTINUATION_PREFIXES = (
    "Enabled instance extensions:",
    "Available physical devices:",
    "Selected physical device",
    "Enabled device extensions:",
    "VK geometry shader winding",
    "- ",
)


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
        # Discard paths that contain user info.
        if line.startswith(("xemu_settings_get_", "xemu_settings_set_")):
            continue
        # Raw image warning message may contain user info.
        if line.startswith("WARNING: Image format was not specified for"):
            continue

        # Handle 0.8.109 GL winding order output
        if target == failure_info and line.startswith("GL geometry shader winding"):
            machine_info.append(line)
            continue

        target.append(line)

        if line.startswith("GL_SHADING_LANGUAGE_VERSION:"):
            target = failure_info

    # Clean up Vulkan output (supports both older xemu with 'Enabled instance extensions:'
    # and newer xemu starting directly with 'Available physical devices:' etc.).
    if failure_info and any(failure_info[0].startswith(p) for p in _VULKAN_START_PREFIXES):
        vulkan_lines = []
        while failure_info and any(failure_info[0].startswith(p) for p in _VULKAN_CONTINUATION_PREFIXES):
            vulkan_lines.append(failure_info.pop(0))
        machine_info.extend(vulkan_lines)

    version = "-".join(version_components)
    return version, "\n".join(machine_info), "\n".join(failure_info)
