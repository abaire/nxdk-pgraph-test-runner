# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import pytest

from nxdk_pgraph_test_runner.config import Config


def test_loads_empty():
    sut = Config.loads("")

    with pytest.raises(ValueError, match="Emulator command was not provided."):
        sut.build_emulator_command("foo_bar")


def test_loads():
    sut = Config.loads("""
    emulator_command = 'xemu foo'
    iso_path = '!iso_path!'
    """)

    assert sut.build_emulator_command("test") == ["xemu", "foo"]
    assert sut.iso_path == "!iso_path!"


def test_stores():
    sut = Config(emulator_command="foo bar", iso_path="/path to/xiso.iso")

    assert (
        sut.stores()
        == """work_dir = ""
output_dir = ""
emulator_command = "foo bar"
iso_path = "/path to/xiso.iso"
ftp_ip = ""
ftp_ip_override = ""
ftp_preferred_interface = ""
test_failure_retries = 1
"""
    )
