from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from features.autostart import _resolve_target

RESTART_FLAG = "--restarted"
KEEP_AWAKE_FLAG = "--keep-awake="  # followed by the mode

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_BREAKAWAY_FROM_JOB = 0x01000000


def spawn_new_instance(keep_awake_mode: str) -> None:
    """Start a fresh copy of the app, detached from this one, the same way the
    autostart .vbs does (pythonw.exe main.py, or the built .exe). The caller
    quits right after; the new copy waits for the single-instance lock."""
    target, _args, workdir = _resolve_target()
    cmd = [target]
    if not getattr(sys, "frozen", False):
        cmd.append(str(Path(workdir) / "main.py"))
    cmd.append(RESTART_FLAG)
    if keep_awake_mode != "off":
        cmd.append(KEEP_AWAKE_FLAG + keep_awake_mode)
    flags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    try:
        # Leave any job object this copy was started in, so the new one does
        # not die with it.
        subprocess.Popen(cmd, cwd=workdir, close_fds=True,
                         creationflags=flags | CREATE_BREAKAWAY_FROM_JOB)
    except OSError:
        # The job does not allow breakaway; start it inside the job instead.
        subprocess.Popen(cmd, cwd=workdir, close_fds=True, creationflags=flags)
