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

rng(666);
gutenb_s    = gutenb(randsample(size_gutenb(1), sample_size), :);
punk_s      = punk(randsample(size_punk(1), sample_size), :);
yle_s       = yle(randsample(size_yle(1), sample_size), :);

merged      = [gutenb_s; punk_s; yle_s];

% Try commenting out

mu = mean(merged);
sigma = std(merged);

merged = bsxfun(@rdivide, bsxfun(@minus, merged, mu), sigma);
merged(isnan(merged)) = 0;

merged_dists    = pdist(merged, 'euclid'); % or try cityblock
merged_2        = mdscale(merged_dists, 2, 'Start', 'random');

gutenb_2 = merged_2(1:sample_size,:);
punk_2 = merged_2(sample_size+1:2*sample_size,:);
yle_2 = merged_2(2*sample_size+1:end,:);

figure, scatter(gutenb_2(:,1), gutenb_2(:,2), 'r', 'o')
hold on
scatter(punk_2(:,1), punk_2(:,2), 'b', 'o')
hold on
scatter(yle_2(:,1), yle_2(:,2), 'k', 'o')
legend('gutenb','punk','yle')
