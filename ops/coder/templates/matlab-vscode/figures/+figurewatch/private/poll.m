function poll()
%POLL One watcher tick: adopt new figures, republish changed ones, drop closed ones.

state = watchState();
if isempty(state)
    return;
end

directory = state.Directory;
% Handle-visible figures only. The MATLAB extension's own machinery keeps its
% windows out of the way with HandleVisibility 'off', and those are not the
% student's plots.
openFigures = findobj(groot, 'Type', 'figure');

tracked = dropClosed(state.Tracked, openFigures, directory);
tracked = adoptNew(tracked, openFigures);

changed = dirtyFigures();
tracked = republish(tracked, changed, directory);

% Exporting re-renders the figure, which fires MarkedClean again — so the
% flags are cleared after publishing, never before, or every figure would
% stay dirty forever and be re-exported on every single tick.
dirtyFigures(gobjects(1, 0));

state.Tracked = tracked;
watchState(state);
end


function tracked = dropClosed(tracked, openFigures, directory)
%DROPCLOSED Forget figures closed in MATLAB and take their files with them.
keep = true(1, numel(tracked));
for k = 1:numel(tracked)
    figureHandle = tracked(k).Figure;
    if isvalid(figureHandle) && any(openFigures == figureHandle)
        continue;
    end
    withdraw(directory, tracked(k).Number);
    listeners = tracked(k).Listeners;
    delete(listeners(isvalid(listeners)));
    keep(k) = false;
end
tracked = tracked(keep);
end


function tracked = adoptNew(tracked, openFigures)
%ADOPTNEW Start tracking figures that appeared since the last tick.
for k = 1:numel(openFigures)
    figureHandle = openFigures(k);
    if ~isempty(tracked) && any([tracked.Figure] == figureHandle)
        continue;
    end
    tracked(end + 1) = struct( ...
        'Figure', figureHandle, ...
        'Number', allocateNumber(tracked, figureHandle), ...
        'Axes', gobjects(1, 0), ...
        'Listeners', event.listener.empty(1, 0), ...
        'Name', '', ...
        'Published', false); %#ok<AGROW> - one row per new figure, a handful at most
end
end


function number = allocateNumber(tracked, figureHandle)
%ALLOCATENUMBER The file number for a figure: its own, or the lowest free one.
%   Sticking to the MATLAB figure number keeps `figure(3)` and fig-000003.png
%   the same thing to a student. Figures without one (uifigure) get a slot
%   that no tracked figure is using.
taken = [];
if ~isempty(tracked)
    taken = [tracked.Number];
end

number = figureHandle.Number;
if isscalar(number) && isnumeric(number) && number >= 1 && number == fix(number) ...
        && ~any(taken == number)
    return;
end

number = 1;
while any(taken == number)
    number = number + 1;
end
end


function tracked = republish(tracked, changed, directory)
%REPUBLISH Write out every figure that is new or has changed, and honour
%   a PNG deleted from outside as a request to close the figure.
keep = true(1, numel(tracked));

for k = 1:numel(tracked)
    entry = tracked(k);
    pngPath = figurePath(directory, entry.Number, '.png');

    % The viewer's close button deletes the PNG. That is the whole protocol
    % for closing a figure from outside, so act on it before anything else —
    % republishing first would resurrect the file the student just closed.
    if entry.Published && ~isfile(pngPath)
        withdraw(directory, entry.Number);
        delete(entry.Listeners(isvalid(entry.Listeners)));
        delete(entry.Figure);
        keep(k) = false;
        continue;
    end

    [entry, structureChanged] = refreshListeners(entry);
    isDirty = ~isempty(changed) && any(changed == entry.Figure);

    if ~entry.Published || structureChanged || isDirty
        if publishFigure(directory, entry)
            entry.Published = true;
        end
    end

    tracked(k) = entry;
end

tracked = tracked(keep);
end


function [entry, structureChanged] = refreshListeners(entry)
%REFRESHLISTENERS Keep a MarkedClean listener on each of the figure's axes.
%   MarkedClean fires whenever an axes is re-rendered, which is what catches
%   `hold on; plot(...)`, `title(...)`, a new limit — every edit that shows.
%   The axes themselves come and go, so the set is rechecked every tick, and a
%   change to it is itself a reason to republish.
figureHandle = entry.Figure;
axesNow = findobj(figureHandle, '-isa', 'matlab.graphics.axis.AbstractAxes');

% Compared as a set, not as a list: findobj is free to hand back the same
% axes in another order, and treating that as a change would re-export the
% figure on every single tick for the rest of the session.
sameAxes = numel(axesNow) == numel(entry.Axes) ...
    && all(arrayfun(@(candidate) any(entry.Axes == candidate), axesNow));
structureChanged = ~sameAxes || ~strcmp(entry.Name, figureHandle.Name);
if ~structureChanged
    return;
end

delete(entry.Listeners(isvalid(entry.Listeners)));
listeners = event.listener.empty(1, 0);
for k = 1:numel(axesNow)
    try
        listeners(end + 1) = addlistener(axesNow(k), 'MarkedClean', ...
            @(~, ~) markDirty(figureHandle)); %#ok<AGROW> - one per axes
    catch
        % Older or exotic axes types may not expose MarkedClean. Losing the
        % listener only costs live updates for that figure; the structural
        % check above still catches anything added or removed.
    end
end

entry.Listeners = listeners;
entry.Axes = axesNow;
entry.Name = figureHandle.Name;
end


function markDirty(figureHandle)
%MARKDIRTY Note that a figure needs republishing on the next tick.
if ~isvalid(figureHandle)
    return;
end
changed = dirtyFigures();
if isempty(changed) || ~any(changed == figureHandle)
    dirtyFigures([changed, figureHandle]);
end
end


function published = publishFigure(directory, entry)
%PUBLISHFIGURE Write the figure and its metadata, metadata first.
%   The viewer keys off the PNG, so by the time it sees the image the sidecar
%   it reads is already in place.
published = false;
figureHandle = entry.Figure;

if isempty(allchild(figureHandle))
    % A bare `figure()` has nothing to export yet, and exportgraphics would
    % refuse. Wait until the student draws into it.
    return;
end

try
    metadata = struct( ...
        'number', entry.Number, ...
        'title', figureTitle(figureHandle, entry.Number), ...
        'source', 'matlab');
    writeAtomically(directory, entry.Number, '.json', ...
        @(target) writeText(target, jsonencode(metadata)));
    writeAtomically(directory, entry.Number, '.png', ...
        @(target) exportgraphics(figureHandle, target, ...
            'Resolution', 150, 'BackgroundColor', 'white'));
    published = true;
catch err
    warnOnce('figurewatch:publish', ...
        'Cannot publish figure %d: %s', entry.Number, err.message);
end
end


function writeAtomically(directory, number, extension, write)
%WRITEATOMICALLY Fill a temporary file next to the target, then rename it over.
%   The viewer reacts to files appearing and changing, so it must never get to
%   read a half-written PNG. A rename inside the folder is atomic.
%
%   The temporary name keeps the real extension, because exportgraphics picks
%   the image format from it, and starts with a dot so it is not mistaken for
%   a figure — readers match fig-NNNNNN.png exactly.
targetPath = figurePath(directory, number, extension);
temporaryPath = fullfile(directory, sprintf('.fig-%06d.tmp%s', number, extension));
cleanup = onCleanup(@() deleteIfPresent(temporaryPath)); %#ok<NASGU> - also on error

write(temporaryPath);
[moved, message] = movefile(temporaryPath, targetPath, 'f');
if ~moved
    error('figurewatch:write', 'Cannot write ''%s'': %s', targetPath, message);
end
end


function writeText(targetPath, text)
%WRITETEXT Write UTF-8 text, so a title with an umlaut survives the trip.
fileId = fopen(targetPath, 'w', 'n', 'UTF-8');
if fileId < 0
    error('figurewatch:write', 'Cannot open ''%s'' for writing', targetPath);
end
cleanup = onCleanup(@() fclose(fileId)); %#ok<NASGU> - closes on error too
fprintf(fileId, '%s\n', text);
end


function withdraw(directory, number)
%WITHDRAW Take a figure out of the folder. Deleting the PNG is what closes it.
deleteIfPresent(figurePath(directory, number, '.png'));
deleteIfPresent(figurePath(directory, number, '.json'));
end


function deleteIfPresent(filePath)
if isfile(filePath)
    % A file the viewer removed in the same instant is not an error.
    delete(filePath);
end
end


function filePath = figurePath(directory, number, extension)
filePath = fullfile(directory, sprintf('fig-%06d%s', number, extension));
end


function text = figureTitle(figureHandle, number)
%FIGURETITLE The most specific human-readable name the figure carries.
text = strtrim(char(figureHandle.Name));
if ~isempty(text)
    return;
end

allAxes = findobj(figureHandle, '-isa', 'matlab.graphics.axis.AbstractAxes');
for k = 1:numel(allAxes)
    titleHandle = get(allAxes(k), 'Title');
    if isempty(titleHandle) || ~isvalid(titleHandle)
        continue;
    end
    % Multi-line titles are cell arrays or string arrays of lines.
    text = strtrim(strjoin(cellstr(string(titleHandle.String)), ' '));
    if ~isempty(text)
        return;
    end
end

text = sprintf('Figure %d', number);
end


function warnOnce(identifier, format, varargin)
%WARNONCE Say it the first time. A failing export fails on every tick, and a
%   warning twice a second would bury the student's own output.
persistent seen
if isempty(seen)
    seen = {};
end
if any(strcmp(seen, identifier))
    return;
end
seen{end + 1} = identifier;
warning(identifier, format, varargin{:});
end
