## Publish figures to the Computor figure folder from R.
##
## Workspaces are containers without a desktop, so R's interactive devices
## (x11, quartz) have nowhere to draw and a student's plot(x, y) would produce
## nothing they can see. This makes the default device an offscreen one that
## mirrors itself into the folder described in docs/figures.md, where the
## Computor VS Code extension picks it up.
##
## Enable it for every session by sourcing this file from Rprofile.site. The
## student configures nothing: a plain plot(x, y) publishes, dev.off() closes.
##
## Without COMPUTOR_FIGURES_DIR nothing here activates, so the same image can
## run gradings without leaving figure files behind.

.computor_figures <- new.env(parent = emptyenv())
.computor_figures$tracked <- list()   # device number (as character) -> entry

#' The figure folder, or NULL when publishing is switched off.
computor_figures_dir <- function() {
  configured <- trimws(Sys.getenv("COMPUTOR_FIGURES_DIR", unset = ""))
  if (nzchar(configured)) configured else NULL
}

.computor_stem <- function(number) sprintf("fig-%06d", number)

.computor_path <- function(folder, number, extension) {
  file.path(folder, paste0(.computor_stem(number), extension))
}

.computor_next_number <- function() {
  taken <- vapply(.computor_figures$tracked, function(entry) entry$number, integer(1))
  number <- 1L
  while (number %in% taken) number <- number + 1L
  number
}

#' Name a figure. Without this it is labelled "Figure N", because R carries no
#' title on the device itself and the `main=` of a plot is not readable back.
computor_figure_title <- function(title, which = grDevices::dev.cur()) {
  key <- as.character(which)
  entry <- .computor_figures$tracked[[key]]
  if (!is.null(entry)) {
    entry$title <- as.character(title)[1]
    entry$published <- FALSE   # force a rewrite of the sidecar
    .computor_figures$tracked[[key]] <- entry
  }
  invisible(title)
}

#' The device R opens when a plot needs one. An offscreen PNG with its display
#' list kept, so the page can be re-rendered to a file whenever it changes.
computor_figures_device <- function(width = 7, height = 5, res = 110, ...) {
  opened <- FALSE
  for (type in c("cairo", NA_character_)) {
    opened <- tryCatch({
      if (is.na(type)) {
        grDevices::png(tempfile(fileext = ".png"), width = width, height = height,
                       units = "in", res = res, ...)
      } else {
        grDevices::png(tempfile(fileext = ".png"), width = width, height = height,
                       units = "in", res = res, type = type, ...)
      }
      TRUE
    }, error = function(e) FALSE)
    if (opened) break
  }
  if (!opened) {
    stop("computor_figures: no usable PNG device (is cairo available?)")
  }

  grDevices::dev.control("enable")

  # Only devices opened here are published. A student's own png("out.png") is
  # their business and must not be hijacked.
  device <- grDevices::dev.cur()
  .computor_figures$tracked[[as.character(device)]] <- list(
    number = .computor_next_number(), title = NULL, published = FALSE,
    width = width, height = height, res = res
  )
  invisible(device)
}

.computor_withdraw <- function(folder, number) {
  unlink(.computor_path(folder, number, ".png"))
  unlink(.computor_path(folder, number, ".json"))
}

.computor_write_atomically <- function(folder, number, extension, write) {
  ## The viewer reacts to files appearing, so it must never get to read a
  ## half-written PNG. A rename inside the folder is atomic. The temporary name
  ## starts with a dot so it is not mistaken for a figure -- readers match
  ## fig-NNNNNN.png exactly.
  temporary <- file.path(folder, paste0(".", .computor_stem(number), ".tmp", extension))
  on.exit(unlink(temporary), add = TRUE)
  write(temporary)
  file.rename(temporary, .computor_path(folder, number, extension))
}

.computor_read_raw <- function(path) {
  if (!file.exists(path)) return(NULL)
  readBin(path, "raw", n = file.size(path))
}

.computor_publish <- function(folder, device, entry) {
  grDevices::dev.set(device)

  rendered <- tempfile(fileext = ".png")
  on.exit(unlink(rendered), add = TRUE)
  grDevices::dev.copy(grDevices::png, filename = rendered, width = entry$width,
                      height = entry$height, units = "in", res = entry$res)
  grDevices::dev.off()   # closes the copy, not the figure

  bytes <- .computor_read_raw(rendered)
  if (is.null(bytes)) return(entry)

  ## Every top-level expression triggers a sync, but most of them change
  ## nothing. Re-publishing an identical image would tell the viewer the figure
  ## updated and make it reload on every keystroke, so compare first.
  if (entry$published &&
      identical(bytes, .computor_read_raw(.computor_path(folder, entry$number, ".png")))) {
    return(entry)
  }

  title <- if (is.null(entry$title)) paste("Figure", entry$number) else entry$title
  metadata <- sprintf('{"number":%d,"title":%s,"source":"r"}',
                      entry$number, .computor_json_string(title))

  ## Metadata first: the viewer keys off the PNG, so by the time it sees the
  ## image the sidecar it reads is already in place.
  .computor_write_atomically(folder, entry$number, ".json",
                             function(path) writeLines(metadata, path, useBytes = TRUE))
  .computor_write_atomically(folder, entry$number, ".png",
                             function(path) writeBin(bytes, path))
  entry$published <- TRUE
  entry
}

.computor_json_string <- function(text) {
  escaped <- gsub("\\", "\\\\", text, fixed = TRUE)
  escaped <- gsub('"', '\\"', escaped, fixed = TRUE)
  escaped <- gsub("\n", "\\n", escaped, fixed = TRUE)
  escaped <- gsub("\r", "\\r", escaped, fixed = TRUE)
  escaped <- gsub("\t", "\\t", escaped, fixed = TRUE)
  paste0('"', escaped, '"')
}

#' Bring the folder in step with this session's devices.
#'
#' `closing` is FALSE while R is shutting down: R closes every device on the
#' way out, and treating that as "the student closed their plots" would delete
#' the figures of a script the instant it finished -- the opposite of what the
#' folder is for.
computor_figures_sync <- function(closing = TRUE) {
  folder <- computor_figures_dir()
  if (is.null(folder)) return(invisible(FALSE))
  if (!dir.exists(folder)) dir.create(folder, recursive = TRUE, showWarnings = FALSE)

  open <- grDevices::dev.list()
  keys <- if (is.null(open)) character(0) else as.character(open)
  previous <- grDevices::dev.cur()

  if (closing) {
    for (key in setdiff(names(.computor_figures$tracked), keys)) {
      .computor_withdraw(folder, .computor_figures$tracked[[key]]$number)
      .computor_figures$tracked[[key]] <- NULL
    }
  }

  for (key in intersect(names(.computor_figures$tracked), keys)) {
    entry <- .computor_figures$tracked[[key]]
    device <- as.integer(key)

    ## The viewer's close button deletes the PNG. That is the whole protocol
    ## for closing a figure from outside.
    if (closing && entry$published &&
        !file.exists(.computor_path(folder, entry$number, ".png"))) {
      .computor_withdraw(folder, entry$number)
      .computor_figures$tracked[[key]] <- NULL
      try(grDevices::dev.off(device), silent = TRUE)
      next
    }

    .computor_figures$tracked[[key]] <- tryCatch(
      .computor_publish(folder, device, entry),
      error = function(e) {
        message("computor_figures: cannot publish figure ", entry$number, ": ", conditionMessage(e))
        entry
      }
    )
  }

  ## Never restore the null device (1): dev.set(1) does not select "no device",
  ## it opens a fresh one through options(device=) -- which is this very
  ## function, so closing the last figure would silently spawn an empty one.
  if (previous != 1L && previous %in% grDevices::dev.list()) {
    try(grDevices::dev.set(previous), silent = TRUE)
  }
  invisible(TRUE)
}

#' Start publishing this session's figures. Safe to call twice.
computor_figures_start <- function() {
  if (is.null(computor_figures_dir())) return(invisible(FALSE))

  options(device = computor_figures_device)

  if (is.null(.computor_figures$callback)) {
    ## Runs after every top-level expression -- the moment a plot is finished
    ## and the device still exists. This is what makes both a script and an
    ## interactive session publish without the student asking.
    .computor_figures$callback <- addTaskCallback(
      function(expr, value, ok, visible) {
        try(computor_figures_sync(), silent = TRUE)
        TRUE
      },
      name = "computor_figures"
    )
  }
  invisible(TRUE)
}

#' Stop publishing. Figures already in the folder stay: a later session simply
#' overwrites the files it reuses.
computor_figures_stop <- function() {
  if (!is.null(.computor_figures$callback)) {
    removeTaskCallback("computor_figures")
    .computor_figures$callback <- NULL
  }
  invisible(TRUE)
}

computor_figures_start()
