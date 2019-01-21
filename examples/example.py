from shipper.lib import ShipperJob, SshConnection, SshTask


job = ShipperJob()

# We have a username/password combination we can SSH with
job.default_connection(SshConnection("192.168.1.60", "dave", password="foobar"))

# Run some commands on a remote host
job.add_task(SshTask("uptime"))
job.add_task(SshTask("uname -a"))
