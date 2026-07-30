"""Matplotlib backend that publishes figures to the Computor figure folder.

Workspaces are containers without a desktop, so no matplotlib GUI backend can
work: a student who runs ``python task.py`` in the terminal and calls
``plt.show()`` would see nothing at all. This backend renders with Agg and
writes each figure into the folder described in ``docs/figures.md``; the
Computor VS Code extension watches that folder and shows the figures.

Enable it image-wide with ``MPLBACKEND=module://computor_figures``. The student
configures nothing — a plain ``plt.show()`` publishes, ``plt.close()`` closes.

Without ``COMPUTOR_FIGURES_DIR`` this behaves exactly like the stock Agg
backend and writes nothing, so the same image can run gradings without
littering the file system with figure files.
"""

from __future__ import annotations

import atexit
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Callable, Optional, Tuple

import matplotlib
from matplotlib import is_interactive
from matplotlib._pylab_helpers import Gcf
from matplotlib.backend_bases import FigureManagerBase, _Backend
from matplotlib.backends.backend_agg import FigureCanvasAgg

__all__ = ["FigureCanvas", "FigureManager", "show"]

#: Identifies who wrote a figure, for the ``source`` field of the metadata.
SOURCE = "matplotlib"

_DIR_ENV_VAR = "COMPUTOR_FIGURES_DIR"

# Interpreter shutdown runs ``Gcf.destroy_all`` (matplotlib registers it in
# _pylab_helpers), which destroys every manager exactly as ``plt.close()``
# does. Deleting the figure files there would wipe the student's plots the
# instant their script ended — the opposite of what the folder is for. So
# closing only deletes files while the interpreter is alive.
_shutting_down = False
_guard_armed = False


def _arm_shutdown_guard() -> None:
    """Register the shutdown flag, and register it *late*.

    ``atexit`` runs callbacks last-registered-first, so this has to be
    registered after matplotlib registered ``Gcf.destroy_all`` to run before
    it. Arming this from figure creation guarantees that ordering: by then
    ``matplotlib._pylab_helpers`` is long imported.
    """
    global _guard_armed
    if _guard_armed:
        return
    _guard_armed = True

    def _mark_shutting_down() -> None:
        global _shutting_down
        _shutting_down = True

    atexit.register(_mark_shutting_down)


def figures_dir() -> Optional[Path]:
    """The figure folder, or ``None`` when publishing is switched off."""
    configured = os.environ.get(_DIR_ENV_VAR, "").strip()
    return Path(configured) if configured else None


def _paths(directory: Path, number: int) -> Tuple[Path, Path]:
    stem = f"fig-{number:06d}"
    return directory / f"{stem}.png", directory / f"{stem}.json"


def _write_atomically(path: Path, write: Callable[[Path], None]) -> None:
    """Fill a sibling temp file, then rename it over *path*.

    The viewer reacts to files appearing and changing, so it must never get to
    read a half-written PNG. A rename within the folder is atomic.
    """
    handle, temp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    os.close(handle)
    temp_path = Path(temp_name)
    try:
        write(temp_path)
        os.replace(temp_path, path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def _title_of(figure, number: int) -> str:
    """The most specific human-readable name the figure carries."""
    suptitle = getattr(figure, "get_suptitle", None)
    if callable(suptitle):
        text = suptitle()
        if text:
            return text

    for axes in figure.axes:
        text = axes.get_title()
        if text:
            return text

    label = figure.get_label()
    if label:
        return label

    return f"Figure {number}"


def publish(manager: FigureManagerBase) -> None:
    """Write *manager*'s figure to the figure folder, or do nothing.

    Metadata is written before the image because the viewer keys off the PNG:
    by the time it sees the image, the sidecar it reads is already in place.
    """
    directory = figures_dir()
    if directory is None:
        return

    number = int(manager.num)
    figure = manager.canvas.figure

    try:
        directory.mkdir(parents=True, exist_ok=True)
        png_path, json_path = _paths(directory, number)
        metadata = {
            "number": number,
            "title": _title_of(figure, number),
            "source": SOURCE,
        }
        _write_atomically(
            json_path,
            lambda target: target.write_text(json.dumps(metadata) + "\n", encoding="utf-8"),
        )
        _write_atomically(png_path, lambda target: figure.savefig(target, format="png"))
    except OSError as error:
        # A full disk or a read-only folder must not take down the student's
        # script — publishing is a side channel, not the computation.
        print(f"computor_figures: could not publish figure {number}: {error}", file=sys.stderr)


def withdraw(number: int) -> None:
    """Remove a figure from the folder. Deleting the PNG is what closes it."""
    directory = figures_dir()
    if directory is None:
        return

    for path in _paths(directory, int(number)):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


class FigureManagerComputor(FigureManagerBase):
    """Publishes on ``show()``, withdraws on ``close()``."""

    def show(self) -> None:
        publish(self)

    def destroy(self) -> None:
        if not _shutting_down:
            withdraw(self.num)
        super().destroy()


class FigureCanvasComputor(FigureCanvasAgg):
    manager_class = FigureManagerComputor

    def draw_idle(self, *args, **kwargs) -> None:
        """Keep ``plt.ion()`` sessions live.

        In interactive mode pyplot marks a figure stale after every command
        that changes it and has the stale callback request a redraw here.
        Republishing on that signal is what makes a REPL session update the
        viewer without an explicit ``show()``. Outside interactive mode this
        stays a plain Agg redraw, so a script only publishes when it says so.
        """
        super().draw_idle(*args, **kwargs)
        if is_interactive() and self.manager is not None:
            publish(self.manager)


@_Backend.export
class _BackendComputorAgg(_Backend):
    FigureCanvas = FigureCanvasComputor
    FigureManager = FigureManagerComputor
    backend_version = matplotlib.__version__

    @classmethod
    def new_figure_manager_given_figure(cls, num, figure):
        _arm_shutdown_guard()
        return super().new_figure_manager_given_figure(num, figure)

    @classmethod
    def show(cls, *, block=None):  # noqa: ARG003 - there is nothing to block on
        """Publish every open figure and return.

        ``mainloop`` stays ``None``, so ``plt.show()`` never blocks: the
        student's script keeps running and its figures stay on screen in the
        viewer afterwards, which is what a terminal run in a container needs.
        """
        for manager in Gcf.get_all_fig_managers():
            manager.show()

    @classmethod
    def draw_if_interactive(cls) -> None:
        """Nothing to do: republishing is driven by `FigureCanvasComputor.draw_idle`.

        Publishing here as well would write the figure pyplot has only just
        created, before anything was drawn into it, and the viewer would flash
        an empty plot on every `plt.figure()` in an interactive session.
        """
