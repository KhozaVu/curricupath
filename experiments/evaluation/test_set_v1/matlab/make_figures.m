function make_figures(split)
%MAKE_FIGURES Figures for CurricuPath test set v1 from the scored CSV tables.
%   make_figures()          uses split "all" (headline)
%   make_figures("held_out") or make_figures("development")
%
%   Reads ../results/metrics_by_level.csv and ../results/confusion_long.csv written by
%   scripts/score_test_set_v1.py. Arms whose raw output does not yet cover every case are
%   labelled "(incomplete)" in every legend and title. Labels are the School registration
%   reference adopted with the set, not an independent academic review.

if nargin < 1, split = "all"; end
split = string(split);
here = fileparts(mfilename("fullpath"));
resultsDir = fullfile(here, "..", "results");
if ~isfile(fullfile(resultsDir, "metrics_by_level.csv"))
    resultsDir = here;  % flat layout, e.g. uploaded to MATLAB Online with the CSVs alongside
end
outDir = fullfile(resultsDir, "figures");
if ~isfolder(outDir), mkdir(outDir); end

metrics = readtable(fullfile(resultsDir, "metrics_by_level.csv"), "TextType", "string");
confusion = readtable(fullfile(resultsDir, "confusion_long.csv"), "TextType", "string");
metrics = metrics(metrics.split == split, :);
confusion = confusion(confusion.split == split, :);

levels = ["low", "medium", "high"];
levelNames = ["Low (course code)", "Medium (module name)", "High (informal)"];
armOrder = ["curricupath", "curricupath_no_clarification", "rules_only", ...
            "structured_rules_llm", "handbook_rag"];
armNames = containers.Map(armOrder, ["CurricuPath", "CurricuPath (no clarification)", ...
    "Rules only (reads no question)", "Structured-rules LLM", "Handbook RAG"]);
colours = [0.00 0.45 0.70; 0.35 0.70 0.90; 0.40 0.40 0.40; 0.84 0.37 0.00; 0.80 0.47 0.65];
markers = ["o", "s", "none", "^", "d"];
% Only systems with every case at every level are plotted; the rest are listed as pending,
% because a score from a handful of cases would be misleading.
arms = strings(0); pending = strings(0);
for arm = armOrder
    rows = metrics(metrics.arm == arm, :);
    if height(rows) == 3 && all(rows.complete == 1)
        arms(end + 1) = arm; %#ok<AGROW>
    else
        done = 0; if ~isempty(rows), done = sum(rows.n_scored); end
        pending(end + 1) = sprintf("%s (%d of %d runs)", armNames(arm), done, 3 * max(metrics.n_scored + metrics.n_missing)); %#ok<AGROW>
    end
end
subtitleText = sprintf("Test set v1, split = %s, n = %d cases per level. Reference: School registration reference (adopted, no independent reviewer).", ...
    split, max(metrics.n_scored + metrics.n_missing));
if ~isempty(pending)
    subtitleText = subtitleText + newline + "Baselines pending (Gemini quota): " + strjoin(pending, "; ");
end
noteFile = fullfile(resultsDir, "figure_note.txt");
if isfile(noteFile)
    subtitleText = subtitleText + newline + strtrim(string(fileread(noteFile)));
end

% ---- Figure 1: Macro-F1 vs ambiguity -----------------------------------------------------------
fig = new_figure([100 100 900 560]);
hold on; grid on; box on;
legendEntries = strings(0);
for a = 1:numel(arms)
    arm = arms(a); idx = find(armOrder == arm);
    rows = metrics(metrics.arm == arm, :);
    [~, order] = ismember(levels, rows.level);
    present = order > 0;
    y = nan(1, 3); lo = nan(1, 3); hi = nan(1, 3);
    y(present) = rows.macro_f1(order(present));
    lo(present) = rows.macro_f1_ci_low(order(present));
    hi(present) = rows.macro_f1_ci_high(order(present));
    complete = all(rows.complete == 1) && all(present);
    name = armNames(arm); if ~complete, name = name + " (incomplete)"; end
    if arm == "rules_only"
        plot([0.75 3.25], [y(1) y(1)], "--", "Color", colours(idx, :), "LineWidth", 1.8);
    else
        errorbar(1:3, y, y - lo, hi - y, "-", "Marker", markers(idx), "Color", colours(idx, :), ...
            "LineWidth", 1.8, "MarkerSize", 8, "MarkerFaceColor", colours(idx, :), "CapSize", 8);
    end
    legendEntries(end + 1) = name; %#ok<AGROW>
end
set(gca, "XTick", 1:3, "XTickLabel", levelNames, "FontSize", 11);
xlim([0.75 3.25]); ylim([0 1]);
ylabel("Macro-F1 (95% bootstrap interval)");
xlabel("Ambiguity of the question wording");
title("Macro-F1 by ambiguity level");
subtitle(subtitleText, "FontSize", 8);
legend(legendEntries, "Location", "southwest", "Interpreter", "none");
save_figure(fig, outDir, "fig1_macro_f1_by_ambiguity_" + split);

% ---- Figure 2: unsafe decision rate vs ambiguity -----------------------------------------------
fig = new_figure([100 100 900 560]);
hold on; grid on; box on;
legendEntries = strings(0);
for a = 1:numel(arms)
    arm = arms(a); idx = find(armOrder == arm);
    rows = metrics(metrics.arm == arm, :);
    [~, order] = ismember(levels, rows.level);
    present = order > 0;
    y = nan(1, 3);
    y(present) = rows.unsafe_rate(order(present));
    complete = all(rows.complete == 1) && all(present);
    name = armNames(arm); if ~complete, name = name + " (incomplete)"; end
    style = "-"; if arm == "rules_only", style = "--"; end
    plot(1:3, 100 * y, style, "Marker", markers(idx), "Color", colours(idx, :), ...
        "LineWidth", 1.8, "MarkerSize", 8, "MarkerFaceColor", colours(idx, :));
    legendEntries(end + 1) = name; %#ok<AGROW>
end
set(gca, "XTick", 1:3, "XTickLabel", levelNames, "FontSize", 11);
xlim([0.75 3.25]); ylim([0 100]);
ylabel("Unsafe decisions (%)");
xlabel("Ambiguity of the question wording");
title("Unsafe rate: answered eligible when the reference is ineligible or needs review");
subtitle(subtitleText, "FontSize", 8);
legend(legendEntries, "Location", "northwest", "Interpreter", "none");
save_figure(fig, outDir, "fig2_unsafe_rate_by_ambiguity_" + split);

% ---- Figure 3: confusion matrices (rows = systems, columns = levels) ---------------------------
refLabels = ["eligible", "ineligible", "manual_review_required"];
predLabels = ["eligible", "ineligible", "manual_review_required", "invalid"];
refShort = ["Eligible", "Ineligible", "Needs review"];
predShort = ["Eligible", "Ineligible", "Needs review", "No decision"];
fig = new_figure([50 50 1300 300 * numel(arms)]);
layout = tiledlayout(numel(arms), 3, "TileSpacing", "compact", "Padding", "compact");
for a = 1:numel(arms)
    for l = 1:3
        nexttile;
        cells = confusion(confusion.arm == arms(a) & confusion.level == levels(l), :);
        counts = zeros(3, 4);
        for r = 1:3
            for c = 1:4
                hit = cells.reference == refLabels(r) & cells.predicted == predLabels(c);
                if any(hit), counts(r, c) = cells.count(find(hit, 1)); end
            end
        end
        if isempty(cells)
            text(0.5, 0.5, "not yet run", "HorizontalAlignment", "center"); axis off;
        else
            h = heatmap(predShort, refShort, counts, "Colormap", parula, "ColorbarVisible", "off", ...
                "FontSize", 9);
            h.XLabel = "Predicted"; h.YLabel = "Reference";
            rows = metrics(metrics.arm == arms(a) & metrics.level == levels(l), :);
            suffix = ""; if ~isempty(rows) && rows.complete(1) == 0, suffix = " (incomplete)"; end
            h.Title = armNames(arms(a)) + " | " + levelNames(l) + suffix;
        end
    end
end
title(layout, "Confusion matrices (counts). Diagonal = agreement with the reference.");
save_figure(fig, outDir, "fig3_confusion_matrices_" + split);

% ---- Figure 4: grouped bars, Macro-F1 per system per level -------------------------------------
fig = new_figure([100 100 1000 620]);
values = nan(numel(arms), 3);
names = strings(1, numel(arms));
for a = 1:numel(arms)
    rows = metrics(metrics.arm == arms(a), :);
    for l = 1:3
        hit = rows.level == levels(l);
        if any(hit), values(a, l) = rows.macro_f1(find(hit, 1)); end
    end
    names(a) = armNames(arms(a));
    if any(rows.complete == 0) || sum(~isnan(values(a, :))) < 3, names(a) = names(a) + " (incomplete)"; end
end
b = bar(values, "grouped");
levelColours = [0.30 0.69 0.29; 1.00 0.60 0.00; 0.89 0.10 0.11];
for l = 1:3, b(l).FaceColor = levelColours(l, :); end
for l = 1:3
    xtips = b(l).XEndPoints; ytips = b(l).YEndPoints;
    labels = compose("%.2f", values(:, l)'); labels(isnan(values(:, l)')) = "";
    text(xtips, ytips, labels, "HorizontalAlignment", "center", "VerticalAlignment", "bottom", ...
        "FontSize", 8, "Color", "k");
end
set(gca, "XTickLabel", names, "FontSize", 10, "TickLabelInterpreter", "none");
xtickangle(15); ylim([0 1.05]); grid on; box on;
ylabel("Macro-F1");
legend(levelNames, "Location", "southoutside", "Orientation", "horizontal");
title("Macro-F1 per system at each ambiguity level");
subtitle(subtitleText, "FontSize", 8);
save_figure(fig, outDir, "fig4_macro_f1_grouped_" + split);

fprintf("Figures written to %s\n", outDir);
end

function fig = new_figure(position)
% Light theme regardless of the MATLAB desktop theme (MATLAB Online defaults to dark).
fig = figure("Color", "w", "Position", position);
if isprop(fig, "Theme"), fig.Theme = "light"; end
end

function save_figure(fig, outDir, name)
% Black text on every axes and legend so labels stay readable in exported images.
for ax = findall(fig, "Type", "axes")'
    set(ax, "Color", "w", "XColor", "k", "YColor", "k", "GridColor", [0.15 0.15 0.15]);
    ax.Title.Color = "k"; ax.Subtitle.Color = [0.25 0.25 0.25];
    ax.XLabel.Color = "k"; ax.YLabel.Color = "k";
end
for lg = findall(fig, "Type", "legend")'
    set(lg, "TextColor", "k", "Color", "w", "EdgeColor", [0.6 0.6 0.6]);
end
exportgraphics(fig, fullfile(outDir, name + ".png"), "Resolution", 200);
savefig(fig, fullfile(outDir, name + ".fig"));
close(fig);
end
