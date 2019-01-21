from shipper.lib import ShipperJob, GitCheckoutTask, SshConnection


job = ShipperJob()

# SSH private key files are used to authenticate against a git repo
job.default_connection(SshConnection(None, None, key="/Users/dave/.ssh/id_rsa"))
job.add_task(GitCheckoutTask("ssh://git@git.davepedu.com:223/dave/shipper.git", "code1", branch="master"))

# Git clone URLs with a username and password can also be used
job.add_task(GitCheckoutTask("https://dave:mypassword@git.davepedu.com/dave/shipper.git", "code2", branch="master"))
