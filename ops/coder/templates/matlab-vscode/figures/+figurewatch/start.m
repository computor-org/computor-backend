function start(directory)
%START Publish this session's figures to the Computor figure folder.
%   FIGUREWATCH.START() watches every figure of this MATLAB session and keeps
%   the folder described in docs/figures.md in step with it: a new figure is
%   written as fig-NNNNNN.png, a changed figure overwrites its file, and a
%   closed figure has its file removed. Deleting a PNG from outside closes the
%   MATLAB figure — that is how the viewer's close button works.
%
%   FIGUREWATCH.START(DIRECTORY) publishes to DIRECTORY instead of the folder
%   named by COMPUTOR_FIGURES_DIR.
%
%   Workspaces are containers without a desktop, so MATLAB has no figure
%   window a student could look at. Publishing figures as files is what makes
%   plots visible at all — in the Computor VS Code extension, which watches
%   the same folder.
%
%   See also FIGUREWATCH.STOP.

if nargin < 1 || isempty(directory)
    directory = getenv('COMPUTOR_FIGURES_DIR');
end
if isempty(directory)
    directory = '/tmp/computor-figures';
end

% The real work lives in a private function because `start` is also the name
% of the timer method this needs to call, and inside start.m that name
% resolves to this function.
startWatching(char(directory));
end
