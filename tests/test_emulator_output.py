# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: T201 `print` found

from __future__ import annotations

from nxdk_pgraph_test_runner._emulator_output import parse_emulator_info

_XEMU_STDERR = [
    "xemu_version: 0.8.10",
    "xemu_branch: master",
    "xemu_commit: 5896b9dc91d2b8b94b2b30570e1e329b161c1453",
    "xemu_date: Wed Jan 29 19:14:08 UTC 2025",
    "xemu_settings_get_base_path: base path: /base_path/xemu/",
    "xemu_settings_get_path: config path: /base_path/xemu/xemu.toml",
    "CPU: ",
    "OS_Version: Version 14.6.1 (Build 23G93)",
    "GL_VENDOR: Apple",
    "GL_RENDERER: Apple M3 Max",
    "GL_VERSION: 4.1 Metal - 88.1",
    "GL_SHADING_LANGUAGE_VERSION: 4.10",
]


def test_parse_xemu_no_error():
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_STDERR)

    assert version == "xemu-0.8.10-master-5896b9dc91d2b8b94b2b30570e1e329b161c1453"
    assert machine_info == "\n".join(_XEMU_STDERR)
    assert not failure_info


def test_parse_xemu_with_error():
    errors = ["Some error", "another error"]
    version, machine_info, failure_info = parse_emulator_info(stdout=[], stderr=_XEMU_STDERR + errors)

    assert version == "xemu-0.8.10-master-5896b9dc91d2b8b94b2b30570e1e329b161c1453"
    assert machine_info == "\n".join(_XEMU_STDERR)
    assert failure_info == "\n".join(errors)
