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

% There is no graphics card in a container, so MATLAB announces that it has
% "disabled some advanced graphics rendering features by switching to software
% OpenGL" the first time anything draws. Software rendering is the only mode
% this image can run in, figures export from it perfectly well, and the link
% the message offers leads to advice about display drivers that nobody here
% can act on — so it is silenced rather than left to alarm students.
warning('off', 'MATLAB:hg:AutoSoftwareOpenGL');

% COMPUTOR_FIGUREWATCH=0 turns publishing off, for the workspace where it turns
% out to be the problem rather than the fix. Anything else, including unset,
% leaves it on.
try
    computorFigurewatch = strtrim(getenv('COMPUTOR_FIGUREWATCH'));
    if any(strcmpi(computorFigurewatch, {'0', 'false', 'off', 'no'}))
        % Silent: startup.m runs for every session in the image, and a session
        % that was told not to publish should not talk about it.
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
