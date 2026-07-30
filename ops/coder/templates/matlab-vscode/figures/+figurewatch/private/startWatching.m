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

% BusyMode 'drop' matters: exporting a heavy figure can outlast the period,
% and queued-up ticks would then republish the same figure over and over.
watchTimer = timer( ...
    'Name', 'ComputorFigureWatch', ...
    'ExecutionMode', 'fixedSpacing', ...
    'Period', 0.5, ...
    'BusyMode', 'drop', ...
    'TimerFcn', @(~, ~) poll(), ...
    'ErrorFcn', @(timerObject, event) shutDownAfterError(timerObject, event));

watchState(struct( ...
    'Directory', directory, ...
    'Tracked', emptyTracked(), ...
    'Timer', watchTimer));
dirtyFigures(gobjects(1, 0));

start(watchTimer);
end


function shutDownAfterError(timerObject, event)
%SHUTDOWNAFTERERROR Give up rather than fail twice a second forever.
%   Whatever breaks a tick will break the next one too, and a warning every
%   half second would bury the student's own output. Publishing is a
%   convenience; MATLAB staying usable is not.
warning('figurewatch:tick', ...
    'Figure publishing stopped after an error: %s', event.Data.message);
if isvalid(timerObject)
    stop(timerObject);
    delete(timerObject);
end
end


function tracked = emptyTracked()
%EMPTYTRACKED The 0x0 struct array that one tracked figure is a row of.
tracked = struct( ...
    'Figure', {}, ...
    'Number', {}, ...
    'Axes', {}, ...
    'Listeners', {}, ...
    'Name', {}, ...
    'Published', {});
end
