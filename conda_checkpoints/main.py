from __future__ import annotations

import io
import os
from contextlib import redirect_stdout
from datetime import datetime, UTC
from logging import getLogger
from pathlib import Path

from conda.base.context import context
from conda.cli.main_list import print_explicit

from . import __version__

logger = getLogger(f"conda.{__name__}")
COMMANDS = {"create", "install", "update", "remove"}


def plugin_hook_implementation(command: str):
    """
    post-command hook to dump a lockfile in the target environment
    after it has been modified.
    """
    if os.environ.get("CONDA_BUILD_STATE") == "BUILD":
        return
    if context.dry_run:
        return
    if command not in COMMANDS:
        raise ValueError(f"command {command} not recognized.")
    now = datetime.now(tz=UTC)
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
    target_prefix = Path(context.target_prefix)
    lockfile_contents = f"# Lockfile generated on {now} by conda-checkpoints v{__version__}\n"
    lockfile_contents += explicit(target_prefix)
    if not env_changed(target_prefix, lockfile_contents):
        return
    lockfile_path = target_prefix / "conda-meta" / "checkpoints" / f"{timestamp}.txt"
    lockfile_path.parent.mkdir(parents=True, exist_ok=True)
    lockfile_path.write_text(lockfile_contents)


def explicit(prefix: Path) -> str:
    memfile = io.StringIO()
    with redirect_stdout(memfile):
        print_explicit(prefix, add_md5=True)
    memfile.seek(0)
    return memfile.read()


def env_changed(prefix: Path, current_contents: str) -> bool:
    all_checkpoints = sorted((prefix / "conda-meta" / "checkpoints").glob("*.txt"))
    if not all_checkpoints:
        return True
    last_contents = all_checkpoints[-1].read_text()
    last_state = "".join([line for line in last_contents.splitlines() if not line.startswith("#")])
    current_state = "".join(
        [line for line in current_contents.splitlines() if not line.startswith("#")]
    )
    if last_state == current_state:
        return False
    return True
