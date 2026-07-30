function figures = dirtyFigures(newFigures)
%DIRTYFIGURES Read or replace the set of figures that changed since publishing.
%   Listener callbacks add to this set; the watcher tick drains it. Kept apart
%   from WATCHSTATE because a callback may fire in the middle of a tick, and
%   writing back the whole state from there would undo the tick's own work.

KEY = 'ComputorFigureWatchDirty';

if nargin > 0
    setappdata(groot, KEY, newFigures);
end

if isappdata(groot, KEY)
    figures = getappdata(groot, KEY);
else
    figures = gobjects(1, 0);
end

figures = figures(isvalid(figures));
end
