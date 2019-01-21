import os
import cherrypy
import logging
import json
import queue
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from threading import Thread
import traceback
import base64
import sys
import subprocess


class AppWeb(object):
    def __init__(self):
        self.task = TaskWeb()

    @cherrypy.expose
    def index(self):
        yield "Hi! Welcome to the Shipper API server."


@cherrypy.popargs("task")
class TaskWeb(object):
    def __init__(self):
        pass

    @cherrypy.expose
    def index(self, task, **kwargs):
        cherrypy.engine.publish('task-queue', (task, kwargs))
        yield "OK"


class QueuedJob(object):
    def __init__(self, name, args):
        self.name = name
        self.args = args


class TaskExecutor(object):
    def __init__(self, runnerpath):
        self.q = queue.Queue()
        self.runnerpath = runnerpath
        self.runner = Thread(target=self.run, daemon=True)
        self.runner.start()

    def load_task(self, taskname):
        srcfile = taskname + ".py"
        spec = importlib.util.spec_from_file_location("job", srcfile)
        job = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(job)
        return job

    def enqueue(self, taskname, params):
        """
        validate & load task object, append to the work queue
        """
        # Load the job object
        job = self.load_task(taskname)

        # Extract post body if present - we decode json and pass through other types as-is
        payload = None
        print("Login: ", cherrypy.request.login)
        if cherrypy.request.method == "POST":
            cl = cherrypy.request.headers.get('Content-Length', None)
            if cl:
                payload = cherrypy.request.body.read(int(cl))
                ctype = cherrypy.request.headers.get('Content-Type', None)
                if ctype == "application/json":
                    payload = json.loads(payload)
        if payload:
            params["payload"] = payload

        # check auth if required by the job
        if hasattr(job, "auth"):
            auth = None
            auth_header = cherrypy.request.headers.get('authorization')
            if auth_header:
                authtype, rest = auth_header.split(maxsplit=1)
                if authtype.lower() == "basic":
                    auth = tuple(base64.standard_b64decode(rest.encode("ascii")).decode("utf-8").split(":"))

                print("{} not in {}: {}".format(auth, job.auth, auth not in job.auth))
                if auth not in job.auth:
                    cherrypy.serving.response.headers['www-authenticate'] = 'Basic realm="{}"'.format(taskname)
                    raise cherrypy.HTTPError(401, 'You are not authorized to access that job')
            params["auth"] = auth

        print("Queueing: {} with params {}".format(taskname, params))
        self.q.put(QueuedJob(taskname, params))

    def run(self):
        with ThreadPoolExecutor(max_workers=5) as pool:
            while True:
                pool.submit(self.run_job, self.q.get())

    def run_job(self, job):
        try:
            print("Executing task from {}.py".format(job.name))
            p = subprocess.Popen([sys.executable, self.runnerpath, job.name + ".py", json.dumps(job.args)])
            p.wait()
        except:
            print(traceback.format_exc())
            # TODO job logging and exception logging
        print("Task complete")


def main():
    import argparse
    import signal

    parser = argparse.ArgumentParser(description="Shipper API server")

    parser.add_argument('-p', '--port', default=8080, type=int, help="tcp port to listen on")
    parser.add_argument('-t', '--tasks', default="./", help="dir containing task files")
    parser.add_argument('--debug', action="store_true", help="enable development options")

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO if args.debug else logging.WARNING,
                        format="%(asctime)-15s %(levelname)-8s %(filename)s:%(lineno)d %(message)s")

    runnerpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "runjob.py")
    os.chdir(args.tasks)

    web = AppWeb()
    cherrypy.tree.mount(web, '/', {'/': {'tools.trailing_slash.on': False}})
    cherrypy.config.update({
        'tools.sessions.on': False,
        # 'tools.sessions.locking': 'explicit',
        # 'tools.sessions.timeout': 525600,
        'request.show_tracebacks': True,
        'server.socket_port': args.port,
        'server.thread_pool': 5,
        'server.socket_host': '0.0.0.0',
        # 'log.screen': False,
        'engine.autoreload.on': args.debug
    })

    executor = TaskExecutor(runnerpath)
    cherrypy.engine.subscribe('task-queue', lambda e: executor.enqueue(*e))

    def signal_handler(signum, stack):
        logging.critical('Got sig {}, exiting...'.format(signum))
        cherrypy.engine.exit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        cherrypy.engine.start()
        cherrypy.engine.block()
    finally:
        logging.info("API has shut down")
        cherrypy.engine.exit()


if __name__ == '__main__':
    main()
