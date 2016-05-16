import sys
import scipy.io as io
import numpy

inputs = sys.argv[1:-1]
output = sys.argv[-1]
d = {}

for input in inputs:
    mat = io.loadmat(input)
    for k in mat:
        if k.startswith('_'):
            continue
        print(k)
        if k in d:
            d[k] = numpy.concatenate((d[k], mat[k]))
        else:
            d[k] = mat[k]

io.savemat(output, d, appendmat=False)
