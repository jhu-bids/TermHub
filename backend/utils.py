import json


def cnt(vals):
  return len(set(vals))


def commify(n):
  return f'{n:,}'


def pdump(o):
  print(json.dumps(o, indent=2))


