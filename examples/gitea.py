from shipper.lib import ShipperJob, SshConnection, GiteaCheckoutTask, CmdTask


job = ShipperJob()
job.default_connection(SshConnection(None, None, key="testkey.pem"))

# GiteaCheckoutTask will check out the repo and branch referenced by Gitea's webhook payload data
# Optionally, the job will be terminated unless the webhook references a branch in the allow_branches list.
job.add_task(GiteaCheckoutTask("code", allow_branches=["master"]))
job.add_task(CmdTask("ls -la"))
