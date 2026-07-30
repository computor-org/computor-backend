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
tracked = republish(tracked, directory);

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
        'Key', '', ...
        'Published', false); %#ok<AGROW> - one row per new figure, a handful at most
end
end


function number = allocateNumber(tracked, figureHandle)
%ALLOCATENUMBER The file number for a figure: its own, or the lowest free one.
%   Sticking to the MATLAB figure number keeps `figure(3)` and fig-000003.png
%   the same thing to a student, and means re-running a script updates its
%   plots instead of piling up new ones. Figures without a number (uifigure)
%   get a slot no tracked figure is using.
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


function tracked = republish(tracked, directory)
%REPUBLISH Write out every figure whose fingerprint has moved, and honour a PNG
%   deleted from outside as a request to close the figure.
keep = true(1, numel(tracked));

for k = 1:numel(tracked)
    entry = tracked(k);
    pngPath = figurePath(directory, entry.Number, '.png');

    % The viewer's close button deletes the PNG. That is the whole protocol for
    % closing a figure from outside, so act on it before anything else —
    % republishing first would resurrect the file the student just closed.
    if entry.Published && ~isfile(pngPath)
        withdraw(directory, entry.Number);
        delete(entry.Figure);
        keep(k) = false;
        continue;
    end

    [key, contentCount] = readFingerprint(entry);
    if contentCount < 1
        % Nothing in it yet. `figure` and `plot(x, y)` are two statements and
        % the first one flushes MATLAB's event queue, so a tick does land in
        % between (measured) — and a blank picture in the viewer is worse than
        % waiting a second for the real one.
        continue;
    end
    if entry.Published && strcmp(key, entry.Key)
        continue;
    end

    if publishFigure(directory, entry)
        entry.Published = true;
        % Taken after the export, not before: rendering settles properties that
        % the fingerprint deliberately leaves out, and should some release
        % settle one it does read, this is what keeps that from becoming a
        % permanent export loop. MATLAB runs this tick between the student's
        % statements, so nothing of theirs can slip in between the two.
        entry.Key = readFingerprint(entry);
    end

    tracked(k) = entry;
end

tracked = tracked(keep);
end


function [key, contentCount] = readFingerprint(entry)
%READFINGERPRINT The figure's fingerprint and how much it has in it.
%   A figure whose properties cannot be read is left alone rather than exported
%   blindly: guessing would mean either a blank picture or an export on every
%   tick, and this feature has already starved the workspace once.
try
    [key, contentCount] = fingerprint(entry.Figure);
catch err
    warnOnce('figurewatch:fingerprint', ...
        'Figure %d is not being published: %s', entry.Number, err.message);
    key = '';
    contentCount = 0;
end
end


function published = publishFigure(directory, entry)
%PUBLISHFIGURE Write the figure and its metadata, metadata first.
%   The viewer keys off the PNG, so by the time it sees the image the sidecar
%   it reads is already in place.
published = false;
figureHandle = entry.Figure;

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
cleanup = onCleanup(@() deleteIfPresent(temporaryPath)); % also on error

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
cleanup = onCleanup(@() fclose(fileId)); % closes on error too
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
%   warning every second would bury the student's own output.
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
