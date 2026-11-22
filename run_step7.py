"""Public demo has no network refresh workflow."""
def execute(*args,**kwargs):
 raise RuntimeError('External refresh is disabled in the fictional public demo.')
