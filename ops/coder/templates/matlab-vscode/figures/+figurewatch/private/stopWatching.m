function stopWatching()
%STOPWATCHING Tear down the watcher timer, if there is one.

state = watchState();
if isempty(state)
    return;
end

if ~isempty(state.Timer) && isvalid(state.Timer)
    stop(state.Timer);
    delete(state.Timer);
end

watchState([]);
end
