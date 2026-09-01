# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import subprocess
import sys
import time

import psutil

from nxdk_pgraph_test_runner.config import Config
from nxdk_pgraph_test_runner.runner import _TIMEOUT_STATUS, _execute_emulator, _kill_process_tree, entrypoint


def test_entrypoint_without_emulator_path():
    config = Config(emulator_command="")

    assert entrypoint(config) == 1


def test_entrypoint_without_iso_path():
    config = Config(emulator_command="/emulator ${ISO}")

    assert entrypoint(config) == 1


def test_kill_process_tree():
    script = (
        "import subprocess, sys, time\n"
        "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "time.sleep(60)\n"
    )
    process = subprocess.Popen([sys.executable, "-c", script])
    time.sleep(0.5)

    parent = psutil.Process(process.pid)
    children = parent.children(recursive=True)
    assert len(children) >= 1
    child_pid = children[0].pid

    _kill_process_tree(process)
    process.wait(timeout=2.0)

    time.sleep(0.2)
    assert not psutil.pid_exists(child_pid)
    assert not psutil.pid_exists(process.pid)


def test_execute_emulator_normal_exit():
    cmd = [sys.executable, "-c", "print('hello'); print('world')"]
    config = Config(emulator_command="dummy", timeout_seconds=10, stall_timeout_seconds=5)
    retcode, stdout, _stderr = _execute_emulator(cmd, config)

    assert retcode == 0
    assert stdout == ["hello", "world"]


def test_execute_emulator_stall_timeout_kills_nested_process():
    child_script = "import time; time.sleep(60)"
    parent_script = (
        f"import subprocess, sys, time\n"
        f"p = subprocess.Popen([sys.executable, '-c', {child_script!r}])\n"
        f"print('ready', flush=True)\n"
        f"p.wait()\n"
    )
    cmd = [sys.executable, "-c", parent_script]
    config = Config(emulator_command="dummy", timeout_seconds=0, stall_timeout_seconds=1)

    start = time.time()
    retcode, stdout, _stderr = _execute_emulator(cmd, config)
    duration = time.time() - start

    assert retcode == _TIMEOUT_STATUS
    assert "ready" in stdout
    assert duration < 10.0


def test_execute_emulator_overall_timeout():
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    config = Config(emulator_command="dummy", timeout_seconds=1, stall_timeout_seconds=0)

    start = time.time()
    retcode, _stdout, _stderr = _execute_emulator(cmd, config)
    duration = time.time() - start

    assert retcode == _TIMEOUT_STATUS
    assert duration < 10.0
