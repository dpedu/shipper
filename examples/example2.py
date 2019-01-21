from shipper.lib import ShipperJob, SshConnection, CmdTask, RsyncTask, GitCheckoutTask


job = ShipperJob()

# We have a username and private key file this time. Keyfile paths are relative to the script dir.
job.default_connection(SshConnection("192.168.1.60", "dave", key="keyfile.pem"))

# Checkout some code
# Note that this will use the keyfile specified above.
# connection=SshConnection(...) can also be specified on GitCheckoutTask. Clone URLs starting with 'ssh' will require
# a private key; urls starting with 'https' will require a username & password.
job.add_task(GitCheckoutTask("ssh://git@git.davepedu.com:223/dave/shipper.git", "code", branch="master"))

# Inspect the code locally
job.add_task(CmdTask("ls -la code/"))
job.add_task(CmdTask("du -sh code"))

# Copy the code to some other host (using the ssh key above and username here for auth)
job.add_task(RsyncTask("./code/", "user@host:/var/deploy/"))
