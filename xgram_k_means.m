clear, close all

load('finnstats.merged.corrected.mat');

data = trigrams;

gutenb  = data(strcmp(cellstr(squeeze(meta(:,2,1:9))), 'gutenberg'), :);
punk    = data(strcmp(cellstr(squeeze(meta(:,2,1:9))), 'punkinfin'), :);
yle     = data(strcmp(cellstr(squeeze(meta(:,2,1:3))), 'yle'), :);

sample_size = 100;
size_gutenb = size(gutenb);
size_punk   = size(punk);
size_yle    = size(yle);

gutenb_s    = gutenb(randsample(size_gutenb(1), sample_size), :);
punk_s      = punk(randsample(size_punk(1), sample_size), :);
yle_s       = yle(randsample(size_yle(1), sample_size), :);

merged      = [gutenb_s; punk_s; yle_s];

merged = bsxfun(@rdivide, merged, std(merged));
merged(isnan(merged)) = 0;

merged_dists    = pdist(merged, 'euclid');
merged_2        = mdscale(merged_dists, 2, 'Start', 'random');

[idx,C] = kmeans(merged_2, 3);
figure;
hold on
scatter(merged_2(idx==1, 1), merged_2(idx==1, 2), 'r', 'o')
scatter(merged_2(idx==2, 1), merged_2(idx==2, 2), 'b', 'o')
scatter(merged_2(idx==3, 1), merged_2(idx==3, 2), 'k', 'o')
scatter(C(:,1),C(:,2), 250, 'g', 'x', 'LineWidth', 20)
hold off