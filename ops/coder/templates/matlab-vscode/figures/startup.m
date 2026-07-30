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

% OFF unless COMPUTOR_FIGUREWATCH says otherwise. This has taken the workspace
% down twice and has never run under test — there is no MATLAB to test it on —
% so switching it on is a deliberate, reversible experiment on one workspace
% rather than a surprise for everyone. The same variable gates the virtual
% display in the workspace startup script.
try
    computorFigurewatch = lower(strtrim(getenv('COMPUTOR_FIGUREWATCH')));
    if ~any(strcmp(computorFigurewatch, {'1', 'true', 'on', 'yes'}))
        % Silent: this is the normal state, and startup.m runs for every
        % session including the extension's background MATLAB.
    else
        computorMatlabPath = '/opt/computor/matlab';
        if isfolder(computorMatlabPath)
            addpath(computorMatlabPath);
        end
        figurewatch.start();
    end
catch computorStartupError
    % Never let this stop MATLAB from coming up: without figures a student can
    % still write, run and debug code.
    warning('computor:figurewatch', ...
        'Figure publishing is off: %s', computorStartupError.message);
end

clear computorMatlabPath computorStartupError computorFigurewatch
