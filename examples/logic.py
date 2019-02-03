from shipper.lib import ShipperJob, SshConnection, SshTask, GiteaCheckoutTask, CmdTask, LambdaTask


job = ShipperJob()
job.default_connection(SshConnection(None, None, key="testkey.pem"))
job.add_task(GiteaCheckoutTask("code", allow_branches=["master"]))


# LambdaTask lets you call a method while the job is running and insert new tasks into the queue. Tasks yielded from
# this function will be the next steps executed.
def dobuild(job):
    reponame = job.props["payload"]["repository"]["name"]
    print("Repo name is:", reponame)
    yield CmdTask("echo {}".format(reponame))


job.add_task(LambdaTask(dobuild))

