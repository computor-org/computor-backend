% Computor: publish this session's figures as files.
%
% Workspaces are containers without a desktop, so a MATLAB figure window has
% nowhere to appear and a student's `plot(x, y)` would produce nothing they
% can see. figurewatch mirrors every figure into the folder described in
% docs/figures.md, and the Computor VS Code extension shows what lands there.
%
% MATLAB runs this file at the start of every session in this image —
% including the background MATLAB that the MathWorks extension starts to run
% and debug code, which is the session a student's plots actually come from.

try
    computorMatlabPath = '/opt/computor/matlab';
    if isfolder(computorMatlabPath)
        addpath(computorMatlabPath);
    end
    figurewatch.start();
catch computorStartupError
    % Never let this stop MATLAB from coming up: without figures a student can
    % still write, run and debug code.
    warning('computor:figurewatch', ...
        'Figure publishing is off: %s', computorStartupError.message);
end

clear computorMatlabPath computorStartupError
