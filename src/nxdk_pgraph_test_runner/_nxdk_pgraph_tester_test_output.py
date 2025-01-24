# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

# ruff: noqa: PLR2004 Magic value used in comparison

from __future__ import annotations

import glob
from typing import Any, NamedTuple


class NxdkPgraphTesterTestOutput(NamedTuple):
    """Models the outputs of a single test."""

    suite: str
    name: str
    duration_milliseconds: int
    artifacts: list[str]

    @classmethod
    def create(cls, full_test_name: str, duration_milliseconds: int, artifact_dir: str):
        components = full_test_name.split("::")
        if len(components) != 2:
            msg = f"Invalid fully qualified test name '{full_test_name}'"
            raise ValueError(msg)

        suite, name = components

        return cls(
            suite=suite,
            name=name,
            duration_milliseconds=duration_milliseconds,
            artifacts=_find_artifacts(artifact_dir, full_test_name),
        )

    @property
    def fully_qualified_name(self) -> str:
        return f"{self.suite}::{self.name}"

    def to_obj(self) -> dict[str, Any]:
        return {
            "suite": self.suite,
            "name": self.name,
            "duration_milliseconds": self.duration_milliseconds,
            "artifacts": self.artifacts,
        }


def _find_artifacts(artifact_dir: str, prefix: str) -> list[str]:
    primary_artifacts = glob.glob(prefix + ".png", root_dir=artifact_dir)
    z_buffer_artifacts = glob.glob(prefix + "_ZB.png", root_dir=artifact_dir)
    return primary_artifacts + z_buffer_artifacts
