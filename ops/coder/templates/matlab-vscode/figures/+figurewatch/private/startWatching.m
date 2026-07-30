function startWatching(directory)
%STARTWATCHING Set up the watcher state and start its timer.

stopWatching();

if ~isfolder(directory)
    [created, message] = mkdir(directory);
    if ~created
        error('figurewatch:directory', ...
            'Cannot create figure folder ''%s'': %s', directory, message);
    end
end

% Two seconds, and BusyMode 'drop'.
%
% The period buys two things and costs one. It is the floor on how often a
% figure can be exported, and an export costs 0.3 s of CPU warm, so a tighter
% period would let an animation loop spend a third of a core on pictures nobody
% asked for. It is also how often every open figure is fingerprinted, at 10 to
% 20 ms each (measured). What it costs is latency: a plot appears up to a period
% after the statement that drew it, on top of the export itself.
%
% Dropping matters for the same reason a period does: a heavy figure can outlast
% one, and queued ticks would republish it over and over.
watchTimer = timer( ...
    'Name', 'ComputorFigureWatch', ...
    'ExecutionMode', 'fixedSpacing', ...
    'Period', 2, ...
    'BusyMode', 'drop', ...
    'TimerFcn', @(~, ~) poll(), ...
    'ErrorFcn', @(timerObject, event) shutDownAfterError(timerObject, event));

watchState(struct( ...
    'Directory', directory, ...
    'Tracked', emptyTracked(), ...
    'Timer', watchTimer));

start(watchTimer);
end


function shutDownAfterError(timerObject, event)
%SHUTDOWNAFTERERROR Give up rather than fail twice a second forever.
%   Whatever breaks a tick will break the next one too, and a warning every
%   second would bury the student's own output. Publishing is a convenience;
%   MATLAB staying usable is not.
warning('figurewatch:tick', ...
    'Figure publishing stopped after an error: %s', event.Data.message);
if isvalid(timerObject)
    stop(timerObject);
    delete(timerObject);
end
end


function tracked = emptyTracked()
%EMPTYTRACKED The 0x0 struct array that one tracked figure is a row of.
%   Key is the fingerprint of the figure as it was published; the tick exports
%   again when the figure no longer matches it.
tracked = struct( ...
    'Figure', {}, ...
    'Number', {}, ...
    'Key', {}, ...
    'Published', {});
end
