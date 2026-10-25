function make_clarification_figures()
%MAKE_CLARIFICATION_FIGURES Figures for the clarification test set (v2) from the scored CSVs.
%   Reads metrics_by_arm.csv and metrics_by_fact_type.csv from the same folder (or ../results).
%   Labels are developer-proposed and pending academic review; the set has no independent reviewer.

here = fileparts(mfilename("fullpath"));
dirs = {here, fullfile(here, "..", "results")};
base = "";
for d = 1:numel(dirs)
    if isfile(fullfile(dirs{d}, "metrics_by_arm.csv")), base = dirs{d}; break; end
end
if base == "", error("metrics_by_arm.csv not found next to the script or in ../results"); end
outDir = fullfile(base, "figures");
if ~isfolder(outDir), mkdir(outDir); end

arm = readtable(fullfile(base, "metrics_by_arm.csv"), "TextType", "string");
typ = readtable(fullfile(base, "metrics_by_fact_type.csv"), "TextType", "string");

armOrder = ["no_clarification", "assume_absent", "clarify", "oracle"];
armNames = ["No clarification (fact in text)", "Assume absent (guess)", "CurricuPath asks + scripted reply", "Oracle (facts given)"];
setName = "v2";
labelFile = fullfile(base, "set_label.txt");
if isfile(labelFile), setName = strtrim(string(fileread(labelFile))); end
note = "Clarification test set " + setName + ": 33 cases with one needed fact unknown. Labels are developer-proposed, pending academic review (not independent).";

% ---- Figure 1: what happens to the 33 'ask' cases (stacked outcomes) ---------------------------
fig = new_figure([100 100 980 560]);
ask = arm(arm.population == "ask", :);
counts = zeros(numel(armOrder), 3);
for i = 1:numel(armOrder)
    r = ask(ask.arm == armOrder(i), :);
    counts(i, :) = [r.correct, r.wrong_decision, r.unresolved];
end
b = bar(100 * counts ./ sum(counts, 2), "stacked");
b(1).FaceColor = [0.30 0.69 0.29]; b(2).FaceColor = [0.89 0.10 0.11]; b(3).FaceColor = [0.65 0.65 0.65];
set(gca, "XTickLabel", armNames, "FontSize", 10, "TickLabelInterpreter", "none"); xtickangle(12);
ylabel("Share of the 33 cases (%)"); ylim([0 100]); grid on; box on;
legend(["Correct final decision", "Wrong decision", "No decision (unresolved)"], "Location", "southoutside", "Orientation", "horizontal");
for i = 1:numel(armOrder)
    y = 0;
    for k = 1:3
        h = 100 * counts(i, k) / sum(counts(i, :));
        if h >= 6, text(i, y + h / 2, sprintf("%d", counts(i, k)), "HorizontalAlignment", "center", "Color", "k", "FontSize", 10); end
        y = y + h;
    end
end
title("Final decision when a needed student fact is missing");
subtitle(note, "FontSize", 8);
save_figure(fig, outDir, "cl_fig1_final_decision_outcomes");

% ---- Figure 2: accuracy by type of missing fact ------------------------------------------------
fig = new_figure([100 100 980 560]);
types = unique(typ.fact_type, "stable");
vals = nan(numel(types), numel(armOrder));
for t = 1:numel(types)
    for i = 1:numel(armOrder)
        r = typ(typ.fact_type == types(t) & typ.arm == armOrder(i), :);
        if ~isempty(r), vals(t, i) = 100 * r.accuracy; end
    end
end
b = bar(vals, "grouped");
cols = [0.60 0.60 0.60; 0.89 0.60 0.10; 0.00 0.45 0.70; 0.30 0.69 0.29];
for i = 1:numel(b), b(i).FaceColor = cols(i, :); end
nice = strrep(types, "_", " ");
set(gca, "XTickLabel", nice, "FontSize", 10); ylim([0 112]); grid on; box on;
ylabel("Correct final decisions (%)");
legend(armNames, "Location", "southoutside", "NumColumns", 2, "Interpreter", "none");
for i = 1:numel(b)
    xt = b(i).XEndPoints; yt = b(i).YEndPoints;
    text(xt, yt, compose("%.0f", vals(:, i)'), "HorizontalAlignment", "center", "VerticalAlignment", "bottom", "FontSize", 8, "Color", "k");
end
title("Accuracy by kind of missing fact");
subtitle(note, "FontSize", 8);
save_figure(fig, outDir, "cl_fig2_accuracy_by_fact_type");

% ---- Figure 3: questions asked when no question is needed --------------------------------------
fig = new_figure([100 100 900 520]);
none = arm(arm.population ~= "ask" & arm.arm == "clarify", :);
labels = ["Fact already known (33 matched controls)", "Unrelated module unknown (6)"];
rates = [none.question_rate(none.population == "control"), none.question_rate(none.population == "irrelevant")] * 100;
bar(rates, 0.5, "FaceColor", [0.84 0.37 0.00]);
set(gca, "XTickLabel", labels, "FontSize", 10); ylim([0 60]); grid on; box on;
ylabel("Cases where CurricuPath still asked a question (%)");
for k = 1:numel(rates), text(k, rates(k), sprintf("%.0f%%", rates(k)), "HorizontalAlignment", "center", "VerticalAlignment", "bottom", "Color", "k"); end
title("Unnecessary questions (lower is better)");
extraNote = "";
if any(rates > 0), extraNote = newline + "The extra questions all concern timetable-clash partners of the target module."; end
subtitle(note + extraNote, "FontSize", 8);
save_figure(fig, outDir, "cl_fig3_unnecessary_questions");
fprintf("Figures written to %s\n", outDir);
end

function fig = new_figure(position)
fig = figure("Color", "w", "Position", position);
if isprop(fig, "Theme"), fig.Theme = "light"; end
end

function save_figure(fig, outDir, name)
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
