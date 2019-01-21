Shipper
=======

Automation API server

Jobs are written into individual python files. Their content will look like:


```
# instantiate job object
job = ShipperJob()

# Set the default information used with making connections (ssh, rsync, git, etc)
job.default_connection(SshConnection("192.168.1.60", "dave", key="foo.pem"))

# Check out some repo
job.add_task(GitCheckoutTask("ssh://git@git.davepedu.com:223/dave/shipper.git", "code", branch="testing"))

# Copy the files to a remote host
job.add_task(RsyncTask("./code/", "/tmp/deploy/"))

# SSH to the host and run some commands
job.add_task(SshTask("ls -la /tmp/deploy/"))
job.add_task(SshTask("uname -a"))
```

For more examples, see `examples/`.

If the above file is named "foo.py", this job would be triggered by making a request to http://host:port/task/foo. POST,
GET, and JSON Body data is made available to the job.

To run the server, install this module and execute:

* `shipperd -t jobfiledir/`
