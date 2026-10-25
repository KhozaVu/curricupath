function make_uncertainty_figures()
%MAKE_UNCERTAINTY_FIGURES Evidence sufficiency, abstention and wording-level figures (test set v1).
%   Reads sufficiency_split.csv, abstention.csv and wording_levels.csv from this folder or
%   ../results_uncertainty. Population: the frozen 40-case subset. Labels: School registration
%   reference (adopted; no independent reviewer). "After grid" figures are development-informed and
%   partly circular (labels and rules share the registration grid).

here = fileparts(mfilename("fullpath"));
base = "";
for d = {here, fullfile(here, "..", "results_uncertainty")}
    if isfile(fullfile(d{1}, "sufficiency_split.csv")), base = d{1}; break; end
end
if base == "", error("sufficiency_split.csv not found"); end
outDir = fullfile(base, "figures"); if ~isfolder(outDir), mkdir(outDir); end
suff = readtable(fullfile(base, "sufficiency_split.csv"), "TextType", "string");
abst = readtable(fullfile(base, "abstention.csv"), "TextType", "string");
word = readtable(fullfile(base, "wording_levels.csv"), "TextType", "string");

sys = ["handbook_rag", "structured_rules_llm", "rules_only_before_grid", "curricupath_before_grid", ...
       "rules_only_after_grid", "curricupath_after_grid"];
names = ["Handbook RAG", "Structured-rules LLM", "Rules only (before grid)", "CurricuPath (before grid)", ...
         "Rules only (after grid)*", "CurricuPath (after grid)*"];
cols = [0.80 0.47 0.65; 0.84 0.37 0.00; 0.60 0.60 0.60; 0.00 0.45 0.70; 0.35 0.35 0.35; 0.35 0.70 0.90];
note = "Frozen 40-case subset of test set v1. Labels: School registration reference (adopted, no independent reviewer). * after the grid fix: development-informed, partly circular.";

% ---- Fig A: accuracy when the handbook can vs cannot answer -------------------------------------
fig = new_figure([100 100 1050 560]);
vals = nan(numel(sys), 2); counts = strings(numel(sys), 2);
for i = 1:numel(sys)
    for j = 1:2
        s = ["source_sufficient", "source_insufficient"];
        r = suff(suff.system == sys(i) & suff.level == "pooled" & suff.stratum == s(j), :);
        vals(i, j) = 100 * r.accuracy; counts(i, j) = sprintf("%d/%d", r.correct, r.n);
    end
end
b = bar(vals, "grouped"); b(1).FaceColor = [0.30 0.69 0.29]; b(2).FaceColor = [0.89 0.10 0.11];
for j = 1:2
    text(b(j).XEndPoints, b(j).YEndPoints, counts(:, j)', "HorizontalAlignment", "center", "VerticalAlignment", "bottom", "FontSize", 8, "Color", "k");
end
set(gca, "XTickLabel", names, "FontSize", 9, "TickLabelInterpreter", "none"); xtickangle(18);
ylim([0 112]); ylabel("Correct decisions (%)"); grid on; box on;
legend(["Handbook can answer", "Handbook cannot answer"], "Location", "southoutside", "Orientation", "horizontal");
title("Accuracy by evidence sufficiency (3 wordings pooled)"); subtitle(note, "FontSize", 7);
save_figure(fig, outDir, "un_fig1_accuracy_by_sufficiency");

% ---- Fig B: unsafe eligible answers by sufficiency ---------------------------------------------
fig = new_figure([100 100 1050 560]);
u = nan(numel(sys), 2);
for i = 1:numel(sys)
    for j = 1:2
        s = ["source_sufficient", "source_insufficient"];
        r = suff(suff.system == sys(i) & suff.level == "pooled" & suff.stratum == s(j), :);
        u(i, j) = r.unsafe_eligible;
    end
end
b = bar(u, "grouped"); b(1).FaceColor = [0.30 0.69 0.29]; b(2).FaceColor = [0.89 0.10 0.11];
for j = 1:2
    text(b(j).XEndPoints, b(j).YEndPoints, string(u(:, j))', "HorizontalAlignment", "center", "VerticalAlignment", "bottom", "FontSize", 9, "Color", "k");
end
set(gca, "XTickLabel", names, "FontSize", 9, "TickLabelInterpreter", "none"); xtickangle(18);
ylabel("Answered eligible when the reference is not (count)"); grid on; box on;
legend(["Handbook can answer", "Handbook cannot answer"], "Location", "southoutside", "Orientation", "horizontal");
title("Unsupported 'eligible' answers by evidence sufficiency"); subtitle(note, "FontSize", 7);
save_figure(fig, outDir, "un_fig2_unsafe_by_sufficiency");

% ---- Fig C: abstention ---------------------------------------------------------------------------
fig = new_figure([100 100 1050 560]);
m = nan(numel(sys), 4);
for i = 1:numel(sys)
    r = abst(abst.system == sys(i) & abst.level == "low", :);
    m(i, :) = 100 * [num(r.defer_precision), r.defer_recall, r.over_referral_rate, r.under_referral_rate];
end
b = bar(m, "grouped");
mc = [0.00 0.45 0.70; 0.30 0.69 0.29; 0.95 0.70 0.10; 0.89 0.10 0.11];
for k = 1:4, b(k).FaceColor = mc(k, :); end
set(gca, "XTickLabel", names, "FontSize", 9, "TickLabelInterpreter", "none"); xtickangle(18);
ylim([0 112]); ylabel("%"); grid on; box on;
legend(["Defer precision", "Defer recall", "Over-referral (deferred but decidable)", "Under-referral (decided but needed review)"], ...
    "Location", "southoutside", "NumColumns", 2);
title("Abstention: deferring to manual review (course-code wording)");
subtitle(note + newline + "Defer = manual_review_required. Blank precision = the system never deferred. 6 reference cases need review.", "FontSize", 7);
save_figure(fig, outDir, "un_fig3_abstention");

% ---- Fig D: accuracy by wording level ------------------------------------------------------------
fig = new_figure([100 100 950 560]); hold on; grid on; box on;
mk = ["d", "^", "s", "o", "s", "o"];
for i = 1:numel(sys)
    y = nan(1, 3);
    for l = 1:3
        lv = ["low", "medium", "high"];
        r = word(word.system == sys(i) & word.level == lv(l), :);
        y(l) = 100 * r.accuracy;
    end
    ls = "-"; if contains(sys(i), "rules_only"), ls = "--"; end
    plot(1:3, y, ls, "Marker", mk(i), "Color", cols(i, :), "LineWidth", 1.8, "MarkerFaceColor", cols(i, :), "MarkerSize", 7);
end
set(gca, "XTick", 1:3, "XTickLabel", ["Low (course code)", "Medium (module name)", "High (informal)"], "FontSize", 10);
xlim([0.8 3.2]); ylim([0 105]); ylabel("Correct decisions (%)"); xlabel("Wording of the question");
legend(names, "Location", "southoutside", "NumColumns", 2, "Interpreter", "none");
title("Accuracy by wording level"); subtitle(note + newline + "Medium has 3 and high 4 sentence templates; CurricuPath medium/high measured after the parser fix.", "FontSize", 7);
save_figure(fig, outDir, "un_fig4_accuracy_by_wording");
fprintf("Figures written to %s\n", outDir);
end

function v = num(x)
if isnumeric(x), v = x; else, v = str2double(x); end
if isnan(v), v = 0; end
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
