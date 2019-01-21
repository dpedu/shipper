from shipper.lib import ShipperJob, PythonTask

# By default, jobs require no auth to run.
# Setting the 'auth' variable to a set of sets containing username and password pairs, passing one of these pairs
# becomes require when triggering the job
auth = (("foo", "password"),
        ("dave", "baz"))


def localfunc(job):
    print("Job props:", job.props)


job = ShipperJob()

# This task accepts a callback that is called during the job's execution. The job is passed as the only parameter
job.add_task(PythonTask(localfunc))
