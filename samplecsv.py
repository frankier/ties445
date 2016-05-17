import random
import sys
import csv

rows = int(sys.argv[1])
input = open(sys.argv[2])
output = open(sys.argv[3], 'w')

input_csv = csv.reader(input)
output_csv = csv.writer(output)
header = next(input_csv)

sample = random.sample(list(input_csv), rows)

output_csv.writerow(header)
for s in sample:
    output_csv.writerow(s)
