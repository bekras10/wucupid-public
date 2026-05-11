import os



def worker_int(worker):
    """Set worker ID environment variable"""
    os.environ['GUNICORN_WORKER_ID'] = str(worker.nr)

def on_starting(server):
    """Set main process as worker 0"""
    os.environ['GUNICORN_WORKER_ID'] = '0' 