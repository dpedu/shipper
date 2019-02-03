from shipper.lib import ShipperJob, SshConnection, GiteaCheckoutTask, LambdaTask, \
    DockerBuildTask, DockerTagTask, DockerPushTask


# This job accepts gitea webooks and builds docker images. If the "imagename" parameter is passed, it will be used to
# name the image. Otherwise, a repo named "docker-image-name" would builds/pushes a docker image called "image-name".


job = ShipperJob()
job.default_connection(SshConnection(None, None, key="testkey.pem"))
job.add_task(GiteaCheckoutTask("code", allow_branches=["master"]))


def getimgname(job):
    if "imagename" in job.props:  # prefer "imagename" url param
        imagename = job.props["imagename"]
    else:  # fall back to repo name, stripping 'docker-' prefix if needed.
        imagename = job.props["payload"]["repository"]["name"]  # Expecting a repo name like "docker-nginx"
        if imagename.startswith("docker-"):  # strip the "docker-" repo name prefix
            imagename = imagename[len("docker-"):]

    job.props["docker_imagename"] = "dpedu/" + imagename  # we'll build the image locally as this
    job.props["docker_tag"] = "apps2reg:5000/dpedu/" + imagename  # then tag and push it as this


job.add_task(LambdaTask(getimgname))

job.add_task(DockerBuildTask())
job.add_task(DockerTagTask())
job.add_task(DockerPushTask())
