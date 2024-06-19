from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from logging import getLogger
from pathlib import Path
from subprocess import run

from conda.base.context import context

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
    now = datetime.now(tz=timezone.UTC)
    timestamp = now.strftime("%Y-%m-%d-%H-%M-%S")
    target_prefix = Path(context.target_prefix)

    # @EXPLICIT lockfile
    lockfile_contents = f"# Lockfile generated on {now} by conda-checkpoints v{__version__}\n"
    lockfile_contents += explicit(target_prefix)
    if not env_changed(target_prefix, lockfile_contents):
        return
    lockfile_path = target_prefix / "conda-meta" / "checkpoints" / f"{timestamp}.txt"
    lockfile_path.parent.mkdir(parents=True, exist_ok=True)
    lockfile_path.write_text(lockfile_contents)



def explicit(prefix: Path) -> str:
    """
    Use subprocess to run the whole post_command plugin chain.
    """
    p = run(
        [sys.executable, "-m", "conda", "list", "-p", str(prefix), "--explicit", "--md5"],
        capture_output=True,
        text=True,
    )
    if p.returncode:
        contents = [f"# 'conda list -p {prefix}' failed:", f"# returncode: {p.returncode}"]
        for line in p.stdout.splitlines():
            contents.append(f"# stdout: {line}")
        for line in p.stderr.splitlines():
            contents.append(f"# stderr: {line}")
        logger.warning(
            "Could not obtain checkpoint!. Check files at %s for more details.",
            prefix / 'conda-meta' / 'checkpoints'
        )
        return "\n".join(contents)
    return p.stdout


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
