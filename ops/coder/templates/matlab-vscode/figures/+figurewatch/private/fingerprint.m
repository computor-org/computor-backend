function [key, contentCount] = fingerprint(figureHandle)
%FINGERPRINT A hash of everything about a figure that shows in its image.
%   The watcher exports a figure when its fingerprint moves. Two figures with
%   the same fingerprint render to the same picture, so an unchanged figure is
%   never exported twice — which matters, because one export costs 1.5 s cold
%   and 0.3 s warm in the workspace image, and a needless one also makes the
%   viewer flash.
%
%   CONTENTCOUNT is how many of the hashed objects are things a student put
%   there, rather than the figure and the pane annotations live in. It is zero
%   for `figure` on its own, which is what stops a blank picture reaching the
%   viewer — see POLL.
%
%   This replaced a MarkedClean listener per axes, which was measured wrong in
%   both directions in a session with no display:
%
%     * R2024b, the release in the image, misses the two edits a student is
%       most likely to make — `set(h, 'YData', ...)` and `hold on; plot(...)`
%       both leave the published file stale — while catching title, xlim and
%       legend.
%     * R2025b fires it three times over an idle three seconds and not at all
%       for those same two edits, so the watcher exported every figure twice a
%       second forever: 7.5 s of CPU per 20 s of doing nothing.
%
%   Reading properties has neither problem. It costs 4 ms for a plot, 9 ms for
%   four subplots and 14 ms for a line of a million points, once per figure per
%   tick, and it cannot be blind to an edit that changed one of them.

persistent propertyCache
if isempty(propertyCache)
    % Which properties a class has does not change, and asking is dearer than
    % reading, so the answer is kept for the life of the session.
    propertyCache = containers.Map('KeyType', 'char', 'ValueType', 'any');
end

objects = drawnObjects(figureHandle);
contentCount = sum(~arrayfun(@isScaffolding, objects));

pieces = cell(2, numel(objects));
for k = 1:numel(objects)
    object = objects(k);
    className = class(object);
    if isKey(propertyCache, className)
        readable = propertyCache(className);
    else
        readable = readableProperties(object);
        propertyCache(className) = readable;
    end

    pieces{1, k} = className;
    if ~isempty(readable)
        % One get for the whole list: a call per property would triple the tick.
        pieces{2, k} = get(object, readable);
    end
end

key = sprintf('%u', keyHash(pieces));
end


function objects = drawnObjects(figureHandle)
%DRAWNOBJECTS The figure and everything under it that ends up in the image.
%   findall, not a walk over allchild: a title, an axis label and a colorbar
%   label are not among their parent's children, so a walk cannot see them and
%   `title('...')` would never be published (measured — it was).
%
%   What findall adds and this drops again is the interactive chrome: the
%   toolbar and its buttons, context menus, datatips. None of it appears in an
%   export, and reading its properties was 10 of the 14 ms of a tick.
objects = findall(figureHandle);
objects = objects(arrayfun(@isDrawn, objects));
end


function tf = isScaffolding(object)
%ISSCAFFOLDING Is this the figure or the frame an annotation would hang in?
%   Measured, in the workspace image: `figure` on its own walks to one object,
%   itself, and a figure with a plot in it walks to the figure, the pane that
%   holds annotations, an axes and a line per series. So anything beyond these
%   two is something to show — including an annotation, which is a child of the
%   pane rather than the pane itself.
tf = isa(object, 'matlab.ui.Figure') ...
    || isa(object, 'matlab.graphics.shape.internal.AnnotationPane');
end


function tf = isDrawn(object)
%ISDRAWN Is this part of the picture, or the chrome around it?
%   Named narrowly on purpose: matlab.ui.container also holds panels and
%   layouts, and those do draw.
chrome = { ...
    'matlab.ui.controls.', ...
    'matlab.ui.container.toolbar.', ...
    'matlab.ui.container.Toolbar', ...
    'matlab.ui.container.ContextMenu', ...
    'matlab.ui.container.Menu', ...
    'matlab.graphics.interaction.'};
tf = ~any(startsWith(class(object), chrome));
end


function names = readableProperties(object)
%READABLEPROPERTIES The candidate properties this object has and will hand over.
candidates = candidateProperties();
if isa(object, 'matlab.ui.Figure')
    % The figure's own geometry is the size of the exported image and the
    % student's to set. Inside the figure, geometry is computed by layout —
    % see candidateProperties.
    candidates = [candidates, {'Position'}];
end

names = candidates(cellfun(@(name) isprop(object, name), candidates));

% isprop says yes where get says no on some interactive objects, and a single
% unreadable name would fail the one get this whole design rests on.
keep = true(1, numel(names));
for k = 1:numel(names)
    try
        get(object, names{k});
    catch
        keep(k) = false;
    end
end
names = names(keep);
end


function candidates = candidateProperties()
%CANDIDATEPROPERTIES Every property that can change what a figure looks like.
%   A name no object has costs nothing — isprop filters it out once per class —
%   so this list errs towards too many.
%
%   Deliberately absent is the geometry inside the figure: Position,
%   InnerPosition, OuterPosition, TightInset, PlotBoxAspectRatio and
%   DataAspectRatio. MATLAB recomputes those when it renders, so they move on
%   their own after an export — four subplots shift by 2% of the figure height
%   about a second afterwards (measured) — and a fingerprint holding them would
%   export those figures for the rest of the session. Their *Mode* properties
%   are here instead, so `axis equal` and `axis manual` still register.
candidates = { ...
    ... % what is drawn
    'XData', 'YData', 'ZData', 'CData', 'RData', 'ThetaData', 'UData', ...
    'VData', 'WData', 'AlphaData', 'SizeData', 'Vertices', 'Faces', ...
    'LevelList', 'BinEdges', 'BinWidth', 'Values', 'XBinEdges', 'YBinEdges', ...
    ... % text
    'String', 'DisplayName', 'Interpreter', 'FontName', 'FontSize', ...
    'FontWeight', 'FontAngle', 'Rotation', 'HorizontalAlignment', ...
    'VerticalAlignment', 'TickLabelInterpreter', ...
    ... % colour and style
    'Color', 'BackgroundColor', 'FaceColor', 'EdgeColor', 'MarkerFaceColor', ...
    'MarkerEdgeColor', 'FaceAlpha', 'EdgeAlpha', 'LineStyle', 'LineWidth', ...
    'Marker', 'MarkerSize', 'Colormap', 'ColorOrder', 'AlphaMap', 'Visible', ...
    ... % axes
    'XLim', 'YLim', 'ZLim', 'CLim', 'ALim', 'XScale', 'YScale', 'ZScale', ...
    'XDir', 'YDir', 'ZDir', 'XTick', 'YTick', 'ZTick', 'XTickLabel', ...
    'YTickLabel', 'ZTickLabel', 'XGrid', 'YGrid', 'ZGrid', 'Box', 'View', ...
    'TickDir', 'Limits', 'Ticks', ...
    ... % modes: a flip is itself a change, and unlike the values they hold
    ... % still across a render
    'XLimMode', 'YLimMode', 'ZLimMode', 'CLimMode', 'XTickMode', ...
    'YTickMode', 'ZTickMode', 'XTickLabelMode', 'YTickLabelMode', ...
    'DataAspectRatioMode', 'PlotBoxAspectRatioMode', 'PositionConstraint', ...
    ... % legend, colorbar, layout, figure
    'Location', 'Orientation', 'TileSpacing', 'Padding', 'GridSize', ...
    'TileArrangement', 'Name'};
end
