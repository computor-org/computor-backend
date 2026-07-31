% Computor: publish this session's figures as files.
%
% Workspaces are containers without a desktop, so a MATLAB figure window has
% nowhere to appear and a student's `plot(x, y)` would produce nothing they
% can see. figurewatch mirrors every figure into the folder described in
% docs/figures.md, and the Computor VS Code extension shows what lands there.
%
% The Dockerfile appends this to $MATLABROOT/toolbox/local/matlabrc.m, so it
% runs at the start of every MATLAB session in this image — including the
% background MATLAB that the MathWorks extension starts to run and debug code,
% which is the session a student's plots actually come from.
%
% It is deliberately not a startup.m, which is where this belongs by
% convention and where it published nothing whatsoever. MATLAB runs the first
% `startup` it finds on the path, and the userpath — ~/Documents/MATLAB —
% comes before $MATLABROOT/toolbox/local. The MathWorks base image ships a
% startup.m there, a stub that copies proxy settings out of the environment,
% and the shared home volume has carried a copy of it since it was first
% seeded. So ours was shadowed in every session, in a terminal and under the
% extension alike, and no figure was ever published.
%
% matlabrc.m is the hook in the same directory that nothing else claims,
% precisely because MathWorks tells you not to edit it: nothing in a student's
% home is called that. It also runs before startup.m, so a student who writes
% one of their own keeps their figures.

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
        % Silent: matlabrc runs for every session in the image, and a session
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
