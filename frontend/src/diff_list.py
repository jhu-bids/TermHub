
from functools import reduce
import math
# from math import factorial

code_counts = [ 1, 198, 1973, 8268, 19899, 24030, 31517, 40842, 48597, ]

nCr = lambda n,r: reduce(int.__mul__, range(n-r+1, n+1), 1) // math.factorial(r)

r = 3
for n in code_counts:
  c = nCr(n, r)
  print(f'{n:,} choose {r:,} = {c:,}')
  # for logr in range(0, 3):
  #   r = 10**logr
  #   print(f'{n:,} choose {r:,} = {c:,}')

pass