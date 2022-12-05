import json


def cnt(vals):
  return len(set(vals))


def commify(n):
  return f'{n:,}'


def pdump(o):
  print(json.dumps(o, indent=2))


class Bunch(object):    # dictionary to namespace, a la https://stackoverflow.com/a/2597440/1368860
  def __init__(self, adict):
    self.__dict__.update(adict)

  def to_dict(self):
    return self.__dict__
