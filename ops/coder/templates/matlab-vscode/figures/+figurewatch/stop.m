function stop()
%STOP Stop publishing this session's figures.
%   FIGUREWATCH.STOP() stops the watcher. Figures already published stay in
%   the folder: MATLAB restarts (the VS Code extension restarts its background
%   MATLAB) must not wipe the plots a student is looking at. A later session
%   simply overwrites the files it reuses.
%
%   See also FIGUREWATCH.START.

% See start.m for why this goes through a private function.
stopWatching();
end
