# Fix CVXPY as some adversaries use cvxpy==0.4.11

import cvxpy

if not hasattr(cvxpy, 'mul_elemwise'):
    cvxpy.mul_elemwise = lambda c, x: c * x

from . import adversaries
from . import learners
from . import tests
from . import utils
