% Computor: route `doc` to the student's browser (computor-org/issues#312).
%
% The container has no browser. `doc size` resolved the right mathworks.com
% URL, then tried to launch `firefox`, found nothing, and swallowed the
% failure — so nothing at all happened. Pointing MATLAB's "system browser"
% at the computor-open shim hands the URL to the Computor VS Code extension,
% which opens it as a real browser tab. Forcing the system-browser branch
% also covers help pages that would otherwise ask for the display-bound
% in-MATLAB help viewer.
%
% TemporaryValue on purpose: it lasts exactly one session, and matlabrc runs
% at the start of every session in this image, so nothing sticks to the
% shared home volume.
try
    if exist('/usr/local/bin/computor-open', 'file') == 2
        computorDocSettings = settings;
        computorDocSettings.matlab.web.SystemBrowser.TemporaryValue = 'computor-open';
        matlab.internal.doc.ui.setSystemBrowserForDoc(true);
    end
catch computorDocError
    % Never let this stop MATLAB from coming up.
    warning('computor:docbrowser', ...
        'doc-in-browser is off: %s', computorDocError.message);
end
clear computorDocSettings computorDocError
