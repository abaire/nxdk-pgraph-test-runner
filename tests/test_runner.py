# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from nxdk_pgraph_test_runner._config import Config
from nxdk_pgraph_test_runner.runner import entrypoint


def test_entrypoint_without_emulator_path():
    config = Config(emulator_command="")

    assert entrypoint(config) == 1


def test_entrypoint_without_iso_path():
    config = Config(emulator_command="/emulator ${ISO}")

    assert entrypoint(config) == 1
