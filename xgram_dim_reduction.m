clear, close all

load('finnstats.merged.mat');

data = bigrams;

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

gutenb_dists    = pdist(gutenb_s, 'cityblock');
gutenb_2        = mdscale(gutenb_dists, 2, 'Start', 'random');

punk_dists      = pdist(punk_s, 'cityblock');
punk_2          = mdscale(punk_dists, 2, 'Start', 'random');

yle_dists       = pdist(yle_s, 'cityblock');
yle_2           = mdscale(yle_dists, 2, 'Start', 'random');

figure, scatter(gutenb_2(:,1), gutenb_2(:,2), 'r', 'o')
hold on
scatter(punk_2(:,1), punk_2(:,2), 'b', 'o')
hold on
scatter(yle_2(:,1), yle_2(:,2), 'k', 'o')