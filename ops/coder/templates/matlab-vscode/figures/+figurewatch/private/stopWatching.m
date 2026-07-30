function stopWatching()
%STOPWATCHING Tear down the watcher timer and its listeners, if any.

state = watchState();
if isempty(state)
    return;
end

if ~isempty(state.Timer) && isvalid(state.Timer)
    stop(state.Timer);
    delete(state.Timer);
end

for k = 1:numel(state.Tracked)
    listeners = state.Tracked(k).Listeners;
    delete(listeners(isvalid(listeners)));
end

watchState([]);
dirtyFigures(gobjects(1, 0));
end
