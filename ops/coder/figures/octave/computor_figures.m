function varargout = computor_figures(action, ~)
%COMPUTOR_FIGURES Publish this session's figures to the Computor figure folder.
%   Workspaces are containers without a desktop, so an Octave figure window has
%   nowhere to appear. This mirrors every figure into the folder described in
%   docs/figures.md, where the Computor VS Code extension shows it.
%
%   computor_figures("start")  begin publishing, and keep publishing while the
%                              session sits at the prompt
%   computor_figures("sync")   bring the folder in step with the figures right
%                              now -- the whole job in one call
%   computor_figures("stop")   stop publishing (files already written stay)
%
%   Octave gives no hook that runs while a *script's* figures still hold their
%   content: atexit and onCleanup both run after the graphics are torn down,
%   plotting never routes through the m-file drawnow, and newplot wipes any
%   listener put on an axes. So an interactive session publishes by itself, via
%   add_input_event_hook, while a script needs a "sync" after it -- which the
%   octave wrapper in this folder does, so a student still configures nothing.

  persistent tracked = struct("number", {}, "figure", {}, "fingerprint", {});

  if nargin < 1 || ~ischar(action)
    action = "sync";   % add_input_event_hook calls us with its own argument
  end

  switch lower(action)
    case "start"
      folder = figures_folder();
      if isempty(folder)
        varargout{1} = false;
        return;
      end
      if ~isfolder(folder)
        mkdir(folder);
      end
      computor_figures("stop");
      add_input_event_hook("computor_figures");
      varargout{1} = true;
      return;

    case "stop"
      try
        remove_input_event_hook("computor_figures");
      catch
        % Not registered. Nothing to take back.
      end
      varargout{1} = true;
      return;

    case "sync"
      tracked = sync(tracked);
      if nargout > 0
        varargout{1} = numel(tracked);
      end
      return;

    otherwise
      error("computor_figures:action", "Unknown action '%s'", action);
  end
end


function folder = figures_folder()
%FIGURES_FOLDER The figure folder, or "" when publishing is switched off.
  folder = strtrim(getenv("COMPUTOR_FIGURES_DIR"));
end


function tracked = sync(tracked)
%SYNC Publish what changed, drop what closed, honour what the viewer removed.
  folder = figures_folder();
  if isempty(folder)
    return;
  end
  if ~isfolder(folder)
    mkdir(folder);
  end

  open = get(0, "children");            % handle-visible figures only
  open = open(:)';

  % Figures closed in Octave take their files with them.
  keep = true(1, numel(tracked));
  for k = 1:numel(tracked)
    if ~any(open == tracked(k).figure)
      withdraw(folder, tracked(k).number);
      keep(k) = false;
    end
  end
  tracked = tracked(keep);

  keep = true(1, numel(tracked));
  for k = 1:numel(open)
    handle = open(k);
    index = find([tracked.figure] == handle, 1);

    if isempty(index)
      entry = struct("number", allocate_number(tracked, handle), ...
                     "figure", handle, "fingerprint", "");
      tracked(end + 1) = entry;
      index = numel(tracked);
      keep(end + 1) = true;
    end

    entry = tracked(index);

    % The viewer's close button deletes the PNG. That is the whole protocol for
    % closing a figure from outside, so act on it before republishing -- which
    % would otherwise resurrect the file the student just closed.
    if ~isempty(entry.fingerprint) && ...
        ~isfile(figure_path(folder, entry.number, ".png"))
      withdraw(folder, entry.number);
      close(entry.figure);
      keep(index) = false;
      continue;
    end

    current = fingerprint(handle);
    if strcmp(current, entry.fingerprint)
      continue;   % nothing a student could see has changed
    end

    if publish(folder, entry.number, handle)
      entry.fingerprint = current;
      tracked(index) = entry;
    end
  end

  tracked = tracked(keep);
end


function number = allocate_number(tracked, handle)
%ALLOCATE_NUMBER The file number for a figure: its own, or the lowest free one.
%   Octave figure handles are the numbers a student sees, so figure(3) and
%   fig-000003.png stay the same thing to them.
  taken = [];
  if ~isempty(tracked)
    taken = [tracked.number];
  end

  number = handle;
  if isscalar(number) && number >= 1 && number == fix(number) && ~any(taken == number)
    return;
  end

  number = 1;
  while any(taken == number)
    number = number + 1;
  end
end


function text = fingerprint(handle)
%FINGERPRINT A cheap stand-in for "has this figure changed?".
%   Octave offers no change event that survives a plot: newplot resets the axes
%   and takes any listener with it. Rendering every figure on every tick would
%   cost a full print each time, so the visible state is summarised instead --
%   which objects exist, and what the axes show.
  parts = {sprintf("%d", numel(findall(handle))), flatten(get(handle, "name"))};

  allAxes = findall(handle, "type", "axes");
  for k = 1:numel(allAxes)
    axesHandle = allAxes(k);
    parts{end + 1} = sprintf("%.17g,", ...
        [get(axesHandle, "xlim"), get(axesHandle, "ylim"), get(axesHandle, "zlim")]);
    parts{end + 1} = sprintf("%s|%s", get(axesHandle, "xscale"), get(axesHandle, "yscale"));
    kids = get(axesHandle, "children");
    parts{end + 1} = sprintf("%.17g|", kids(:)');
  end

  % Every piece of text the student can see. The title, the axis labels and a
  % legend are text objects that already exist before they say anything, so
  % counting objects would miss xlabel("time") entirely.
  texts = findall(handle, "type", "text");
  for k = 1:numel(texts)
    parts{end + 1} = flatten(get(texts(k), "string"));
  end

  % The plotted numbers. Rewriting a line's ydata changes neither the object
  % count nor the handles, so the data has to be summarised in here too.
  kinds = {"line", "patch", "surface", "image"};
  for k = 1:numel(kinds)
    drawn = findall(handle, "type", kinds{k});
    for j = 1:numel(drawn)
      parts{end + 1} = data_summary(drawn(j));
    end
  end

  text = strjoin(parts, ";");
end


function text = data_summary(handle)
%DATA_SUMMARY Enough of an object's data to notice it changed, cheaply.
  pieces = {};
  props = {"xdata", "ydata", "zdata", "cdata"};
  for k = 1:numel(props)
    try
      values = get(handle, props{k});
    catch
      continue;   % this kind of object has no such data
    end
    if ~isnumeric(values) || isempty(values)
      continue;
    end
    values = double(values(:));
    values = values(isfinite(values));
    % A weighted sum alongside the plain one, so reordering the same numbers
    % does not go unnoticed.
    weights = (1:numel(values))';
    pieces{end + 1} = sprintf("%d:%.17g:%.17g", ...
        numel(values), sum(values), sum(values .* weights));
  end
  text = strjoin(pieces, ",");
end


function text = flatten(value)
%FLATTEN One line of text out of a char matrix, cell or string property.
  if iscell(value)
    text = strjoin(cellfun(@flatten, value, "UniformOutput", false), " ");
  elseif ischar(value)
    text = strjoin(cellstr(value)', " ");
  else
    text = "";
  end
end


function ok = publish(folder, number, handle)
%PUBLISH Write the figure and its metadata, metadata first.
%   The viewer keys off the PNG, so by the time it sees the image the sidecar it
%   reads is already in place.
  ok = false;
  if isempty(findall(handle, "type", "axes"))
    return;   % nothing drawn yet; print would refuse
  end

  try
    metadata = jsonencode(struct("number", number, ...
                                 "title", figure_title(handle, number), ...
                                 "source", "octave"));
    write_atomically(folder, number, ".json", @(target) write_text(target, metadata));
    write_atomically(folder, number, ".png", ...
                     @(target) print(handle, target, "-dpng", "-r150"));
    ok = true;
  catch err
    warn_once("computor_figures:publish", ...
              "Cannot publish figure %d: %s", number, err.message);
  end
end


function text = figure_title(handle, number)
%FIGURE_TITLE The most specific human-readable name the figure carries.
  text = strtrim(flatten(get(handle, "name")));
  if ~isempty(text)
    return;
  end

  allAxes = findall(handle, "type", "axes");
  for k = 1:numel(allAxes)
    text = strtrim(flatten(get(get(allAxes(k), "title"), "string")));
    if ~isempty(text)
      return;
    end
  end

  text = sprintf("Figure %d", number);
end


function write_atomically(folder, number, extension, write)
%WRITE_ATOMICALLY Fill a temporary file next to the target, then rename it over.
%   The viewer reacts to files appearing, so it must never get to read a
%   half-written PNG. A rename inside the folder is atomic. The temporary name
%   keeps the real extension, because print picks the format from it, and starts
%   with a dot so it is not mistaken for a figure -- readers match
%   fig-NNNNNN.png exactly.
  target = figure_path(folder, number, extension);
  temporary = fullfile(folder, sprintf(".fig-%06d.tmp%s", number, extension));

  unwind_protect
    write(temporary);
    [ok, message] = movefile(temporary, target, "f");
    if ~ok
      error("computor_figures:write", "Cannot write '%s': %s", target, message);
    end
  unwind_protect_cleanup
    if isfile(temporary)
      delete(temporary);
    end
  end_unwind_protect
end


function write_text(target, text)
%WRITE_TEXT Write UTF-8 text, so a title with an umlaut survives the trip.
  fid = fopen(target, "w");
  if fid < 0
    error("computor_figures:write", "Cannot open '%s' for writing", target);
  end
  unwind_protect
    fprintf(fid, "%s\n", text);
  unwind_protect_cleanup
    fclose(fid);
  end_unwind_protect
end


function withdraw(folder, number)
%WITHDRAW Take a figure out of the folder. Deleting the PNG is what closes it.
  delete_if_present(figure_path(folder, number, ".png"));
  delete_if_present(figure_path(folder, number, ".json"));
end


function delete_if_present(path)
  if isfile(path)
    delete(path);   % a file the viewer removed in the same instant is not an error
  end
end


function path = figure_path(folder, number, extension)
  path = fullfile(folder, sprintf("fig-%06d%s", number, extension));
end


function warn_once(identifier, template, varargin)
%WARN_ONCE Say it the first time. A failing print fails on every tick, and the
%   repetition would bury the student's own output.
  persistent seen = {};
  if any(strcmp(seen, identifier))
    return;
  end
  seen{end + 1} = identifier;
  warning(identifier, template, varargin{:});
end
