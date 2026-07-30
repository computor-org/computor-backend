function state = watchState(newState)
%WATCHSTATE Read or replace the watcher state.
%   The state lives in groot's application data so that it survives between
%   timer ticks and stays reachable from listener callbacks, without a global.
%   WATCHSTATE() returns [] when the watcher is not running.

KEY = 'ComputorFigureWatchState';

if nargin > 0
    setappdata(groot, KEY, newState);
end

if isappdata(groot, KEY)
    state = getappdata(groot, KEY);
else
    state = [];
end
end
