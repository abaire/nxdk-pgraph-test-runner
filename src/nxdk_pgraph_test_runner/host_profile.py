# SPDX-FileCopyrightText: 2025-present Erik Abair <erik.abair@bearbrains.work>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
import os
import platform
from dataclasses import dataclass

import glfw
from OpenGL import GL

logger = logging.getLogger(__name__)


@dataclass
class HostProfile:
    """Retrieves detailed information about the system."""

    os_name: str
    os_version: str
    cpu_model: str
    gl_vendor: str
    gl_renderer: str
    gl_version: str
    gl_shading_language_version: str

    def __init__(self) -> None:
        super().__init__()

        self.os_name = platform.system()
        self.os_version = os.uname().release
        self.cpu_model = platform.machine()

        gl_info = get_opengl_info()
        self.gl_vendor = gl_info.get("vendor", "unknown")
        self.gl_renderer = gl_info.get("renderer", "unknown")
        self.gl_version = gl_info.get("version", "unknown")
        self.gl_shading_language_version = gl_info.get("shading_language_version", "unknown")


def get_opengl_info() -> dict[str, str]:
    ret: dict[str, str] = {}
    if not glfw.init():
        logger.error("Failed to initialize OpenGL")
        return ret

    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 4)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 0)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    glfw.window_hint(glfw.OPENGL_FORWARD_COMPAT, glfw.TRUE)

    glfw.window_hint(glfw.VISIBLE, glfw.FALSE)
    window = glfw.create_window(1, 1, "pgraph-test-runner-host-profile", None, None)  # Small size is enough
    if not window:
        logger.error("Failed to initialize OpenGL - failed to create window")
        glfw.terminate()
        return ret

    try:
        glfw.make_context_current(window)

        ret["vendor"] = GL.glGetString(GL.GL_VENDOR).decode("utf-8").replace("/", "-")
        ret["renderer"] = GL.glGetString(GL.GL_RENDERER).decode("utf-8").replace("/", "-")
        ret["version"] = GL.glGetString(GL.GL_VERSION).decode("utf-8").replace("/", "-")
        ret["shading_language_version"] = (
            GL.glGetString(GL.GL_SHADING_LANGUAGE_VERSION).decode("utf-8").replace("/", "-")
        )

    except Exception:
        logger.exception("Failed to retrieve OpenGL info")

    finally:
        glfw.destroy_window(window)
        glfw.terminate()

    return ret
