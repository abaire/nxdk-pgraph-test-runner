# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: N802 Function name should be lowercase

from __future__ import annotations

import pytest

from nxdk_pgraph_test_runner._config import Config
from nxdk_pgraph_test_runner._nxdk_pgraph_tester_config import create_skip_config


@pytest.fixture
def config(tmp_path) -> Config:
    iso_path = tmp_path / "xiso.iso"
    with open(iso_path, "w") as outfile:
        print("test", file=outfile)

    return Config(emulator_command="foo bar", iso_path=iso_path)


def test__create_skip_config__with_empty_list():
    assert create_skip_config([]) == {"test_suites": {}}


def test__create_skip_config__with_valid_list():
    assert create_skip_config(
        ["this::test", "this::second_test", "that::test", "a suite with spaces::test", "suite::a test with spaces"]
    ) == {
        "test_suites": {
            "this": {
                "test": {"skipped": True},
                "second_test": {"skipped": True},
            },
            "that": {
                "test": {"skipped": True},
            },
            "a suite with spaces": {
                "test": {"skipped": True},
            },
            "suite": {
                "a test with spaces": {"skipped": True},
            },
        }
    }
