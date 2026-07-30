# Figures

Workspaces are containers without a desktop. Nothing in them can open a plot
window: the MathWorks VS Code extension renders MATLAB figures into a separate
desktop window that does not exist here, and Python is no different the moment
a student runs `python task.py` in a terminal. A student who writes
`plot(x, y)` would see nothing at all.

So plots are published as **files**. One folder, one naming convention, and a
viewer in the Computor VS Code extension. A static PNG is enough — the goal is
that a student sees their plot, not that they get a real figure window.

Because it is only files, anything that can write a PNG (Octave, C++, a shell
script) gets the same viewer, and it works no matter how the code was started:
terminal, Run button or debugger.

## The contract

**The folder** is named by `COMPUTOR_FIGURES_DIR`, defaulting to
`/tmp/computor-figures`. Both workspace images set it.

**Per figure, two files:**

| File | Contents |
|------|----------|
| `fig-NNNNNN.png` | The rendered figure. `NNNNNN` is the figure number, zero-padded to six digits. |
| `fig-NNNNNN.json` | `{"number": 1, "title": "Sales", "source": "matplotlib"}` |

`number` repeats the number in the file name, `title` is what the viewer labels
the figure with, and `source` names the producer (`matplotlib`, `matlab`, …).

**The rules:**

- **A new PNG is a new figure.** The viewer shows it and reveals itself,
  without taking keyboard focus.
- **An overwritten PNG is an update.** The viewer reloads that figure in place.
  Re-running a script therefore refreshes its plots instead of piling up new
  ones.
- **A deleted PNG closes the figure.** This is the only way to close one, and
  it works in both directions: `close(fig)` in MATLAB and `plt.close()` in
  Python delete the files, and the viewer's close button deletes the files,
  which the producer notices and closes its own figure to match.

**Two rules for anyone writing to the folder:**

1. **Write atomically.** Fill a temporary file in the same folder and rename it
   over the target. The viewer reacts to files appearing, so a PNG written in
   place would be read half-finished. Name the temporary file so it cannot be
   mistaken for a figure — the producers here use `.fig-NNNNNN.tmp.png`, and
   readers match `fig-NNNNNN.png` exactly.
2. **Write the sidecar first.** The viewer keys off the PNG; writing the JSON
   first means the metadata is already there when the image shows up. A figure
   whose sidecar is missing is still shown, just as "Figure N".

The number is whatever the producing session calls the figure — MATLAB's
`figure(3)` is `fig-000003.png` — so one folder belongs to one producer.
That is how the images are built: the `vscode` template has Python and no
MATLAB, the `matlab-vscode` template the other way round.

Files outlive the session that wrote them. A producer never clears the folder
on startup, because the VS Code extension restarts its background MATLAB and
that must not wipe the plot a student is looking at. Figures from an earlier
session are shown, but do not pop the viewer open.

## Who writes

### Python — `computor_figures`

[`ops/coder/templates/vscode/figures/computor_figures.py`](../ops/coder/templates/vscode/figures/computor_figures.py)
is a matplotlib backend derived from Agg. The `vscode` image installs it into
site-packages and sets `MPLBACKEND=module://computor_figures`, so the student
configures nothing:

- `plt.show()` publishes every open figure and returns. It never blocks —
  there is no event loop to block on, and the script's plots stay on screen
  after it exits.
- `plt.close(fig)` removes that figure from the folder.
- `plt.ion()` sessions republish on every change, so a REPL stays live.
- Interpreter shutdown does **not** withdraw anything. matplotlib closes every
  figure at exit, which would otherwise delete a script's plots the instant it
  finished.

Without `COMPUTOR_FIGURES_DIR` the backend behaves exactly like stock Agg and
writes nothing, so the same image can run gradings without littering the file
system.

**Notebooks keep their inline plots.** Without this, `MPLBACKEND` would apply
to ipykernel too and a notebook cell would write a file and render nothing.
The workspace's startup script writes
`~/.ipython/profile_default/ipython_config.py` with
`c.IPKernelApp.matplotlib = "inline"`. That trait is scoped to the kernel
application, so a notebook cell renders its plot under the cell while plain
`python` and terminal IPython keep publishing to the figure folder.

It has to be written at start rather than baked into the image: IPython reads
config from the profile directory under `IPYTHONDIR` and from nowhere else —
there is no `/etc/ipython` search path. The startup script only writes the file
when it is absent, so a student who edits it keeps their version.

### MATLAB — `+figurewatch`

[`ops/coder/templates/matlab-vscode/figures/+figurewatch`](../ops/coder/templates/matlab-vscode/figures/+figurewatch)
watches the session's figures on a timer and mirrors them into the folder.
`startup.m`, installed into `$MATLABROOT/toolbox/local`, starts it for every
MATLAB session in the image — including the background MATLAB that the
MathWorks extension launches to run and debug code, which is where a student's
plots actually come from.

Change detection is a `MarkedClean` listener on each of a figure's axes, which
covers every edit that shows (`hold on; plot(...)`, `title(...)`, a new limit),
plus a per-tick check for axes appearing or disappearing. The timer exports
only figures that are new or flagged, so an idle session costs nothing.

The startup script also brings up `Xvfb` on `:99` and exports `DISPLAY`. MATLAB
drives figure rendering through a display even when it draws nothing on screen,
and its offscreen export is only dependable with one attached. Everything
code-server starts inherits that `DISPLAY`.

### R — `computor_figures.R`

[`ops/coder/figures/r/computor_figures.R`](../ops/coder/figures/r/computor_figures.R)
makes the default device an offscreen PNG with its display list kept, and
publishes from `addTaskCallback` — after every top-level expression, while the
device is still alive. Source it from `Rprofile.site` and a plain `plot(x, y)`
publishes, `dev.off()` closes.

Most top-level expressions change nothing, so it compares the freshly rendered
image with the published one and only rewrites when they differ; otherwise the
viewer would reload on every keystroke. `computor_figure_title("…")` names a
figure — R carries no title on the device and the `main=` of a plot cannot be
read back, so without it a figure is "Figure N".

Only devices it opened are published: a student's own `png("out.png")` is their
business. Deleting the PNG closes the device, as everywhere else.

### Octave — `computor_figures.m`

[`ops/coder/figures/octave/computor_figures.m`](../ops/coder/figures/octave/computor_figures.m)
publishes on `computor_figures("sync")`, and an interactive session calls that
by itself through `add_input_event_hook`.

Octave is the awkward one, and the reason is worth writing down so nobody
re-derives it: **there is no hook that runs while a script's figures still hold
their content.** `atexit` and `onCleanup` both run *after* the graphics are torn
down (a figure's own `deletefcn` fires too late as well — `print` there fails
with "no axes object in figure to print"), plotting never routes through the
m-file `drawnow` so shadowing it does nothing, `newplot` wipes any listener put
on an axes, and Octave has no `timer`. All of that was measured, not assumed.

So `octave task.m` gets its sync from outside the script, via the
[`octave-computor`](../ops/coder/figures/octave/octave-computor) shim: install it
as `octave` ahead of the real binary on `PATH` and point
`COMPUTOR_OCTAVE_REAL` at the real one. The student still configures nothing.
(`--eval` and a script file are mutually exclusive in Octave, so the shim runs
the script through `run()`.)

Change detection is a fingerprint of what a student can see — object count,
axis limits and scales, every text object's string, and a summary of each
line's data. The strings and the data summary both have to be in there: an
`xlabel("time")` writes into a text object that already existed, and
`set(h, "ydata", …)` changes neither the object count nor the handles.

### C++ — `computor_figures.hpp`

C++ has no plotting library of its own, so
[`ops/coder/figures/cpp/computor_figures.hpp`](../ops/coder/figures/cpp/computor_figures.hpp)
is the publishing half only. Render however you like — a gnuplot pipe,
matplotplusplus, your own rasteriser — then hand the PNG over:

```cpp
#include <computor_figures.hpp>

std::system("gnuplot -e \"set terminal png; set output 'plot.png'; plot sin(x)\"");
computor::figures::publish("sin(x)", "plot.png");
```

Header-only, C++17, no dependencies. `publish` takes either a buffer or a path,
with or without an explicit figure number; `is_open` lets a long-running
program notice the viewer closed a figure; `withdraw` closes one.

### Wiring a producer into an image

A template's Docker build context is its own directory, so a Dockerfile can
only `COPY` from within it — which is why the Python and MATLAB producers live
under `ops/coder/templates/<template>/figures/`. The R, Octave and C++
producers live under `ops/coder/figures/<language>/` instead, because no image
ships those runtimes yet. To use one, copy its directory into the template that
needs it and, in the Dockerfile:

- **R** — `Rscript -e 'source("…/computor_figures.R")'` from `Rprofile.site`
- **Octave** — put `computor_figures.m` on the Octave path, install
  `octave-computor` as `octave`, and set `COMPUTOR_OCTAVE_REAL`
- **C++** — drop the header in `/usr/local/include`

and set `COMPUTOR_FIGURES_DIR` as the existing templates do.

### Anything else

Write the two files by the rules above and the viewer will show them. Pick a
`source` string of your own.

## Who reads

The Computor VS Code extension:

- `src/services/FigureFolderWatcher.ts` — watches the folder and reports what
  it holds.
- `src/ui/panels/FiguresPanel.ts` — the "Figures" panel: a thumbnail strip over
  the selected figure in full, opened beside the editor. Closing a figure
  deletes its PNG, which is what closes it at the producer.

The viewer only runs where there is something to watch: `COMPUTOR_FIGURES_DIR`
set, or the default folder already present. On a lecturer's own machine it
stays out of the way, command palette included.

Images travel to the webview as `data:` URIs rather than through
`asWebviewUri`, for the same reason `renderWebviewPage` inlines CSS and JS:
those URIs are served through a service worker that Firefox blocks under
code-server, which is what left webviews blank in issue #267.

## Troubleshooting

**A plot never appears.** Check that the folder exists and is being written to:

```bash
ls -l "${COMPUTOR_FIGURES_DIR:-/tmp/computor-figures}"
```

Files there but nothing in the panel means the viewer side; no files means the
producer side.

**Python writes nothing.** `python3 -c "import matplotlib; print(matplotlib.get_backend())"`
must print `module://computor_figures`, and `COMPUTOR_FIGURES_DIR` must be set
in that shell.

**MATLAB writes nothing.** In the MATLAB terminal, `figurewatch.start()` reports
why it cannot start. `timerfind('Name', 'ComputorFigureWatch')` shows whether
the watcher is running. If exports fail, `echo $DISPLAY` should print `:99` and
`/tmp/xvfb.log` says whether Xvfb came up.
