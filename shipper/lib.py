from contextlib import closing
import paramiko
import os
import subprocess


class ShipperJob(object):
    """
    Job representation class
    """
    def __init__(self):
        self.tasks = []
        self.props = {}

    def default_connection(self, connection):
        self.props["connection"] = connection

    def add_task(self, task):
        task.validate(self)
        self.tasks.append(task)

    def run(self, args):
        self.props.update(**args)
        while self.tasks:
            task = self.tasks.pop(0)
            print("******************************************************************************\n" +
                  "* {: <74} *\n".format(str(task)) +
                  "******************************************************************************")
            task.run(self)
            print()


class StopJob(Exception):
    pass


class ShipperConnection(object):
    pass


class SshConnection(ShipperConnection):
    """
    Connection description used for tasks reliant on SSH
    """
    def __init__(self, host, username, key=None, password=None, port=22):
        self.host = host
        self.username = username
        self.key = os.path.abspath(key)
        if key:
            assert os.path.exists(key)
        self.paramiko_key = paramiko.RSAKey.from_private_key_file(key) if key else None
        self.password = password
        self.port = port


class ShipperTask(object):
    def __init__(self):
        pass

    def validate(self, job):
        pass

    def run(self, job):
        raise NotImplementedError()


class CmdTask(ShipperTask):
    """
    Execute a command locally
    """
    def __init__(self, command):
        super().__init__()
        self.command = command

    def validate(self, job):
        assert self.command

    def run(self, job):
        subprocess.check_call(self.command, shell=not isinstance(self.command, list))

    def __repr__(self):
        return "<CmdTask cmd='{}'>".format(str(self.command)[0:50])


class SshTask(ShipperTask):
    """
    Execute a command over SSH
    """
    def __init__(self, command, connection=None):
        super().__init__()
        self.connection = connection
        self.command = command

    def validate(self, job):
        self.conn = self.connection or job.props.get("connection")
        assert self.conn

    def run(self, job):
        with closing(paramiko.SSHClient()) as client:
            client.set_missing_host_key_policy(paramiko.WarningPolicy)
            connargs = {"pkey": self.conn.paramiko_key} if self.conn.paramiko_key else {"password": self.conn.password}
            client.connect(hostname=self.conn.host, port=self.conn.port, username=self.conn.username, **connargs)
            # stdin, stdout, stderr = client.exec_command('ls -l')
            chan = client.get_transport().open_session()
            chan.set_combine_stderr(True)
            chan.get_pty()
            f = chan.makefile()
            chan.exec_command(self.command)
            print(f.read().decode("utf-8"))

    def __repr__(self):
        return "<SshTask cmd='{}'>".format(self.command[0:50])
# TODO something like SshTask that transfers a script file and executes it? A la jenkins ssh


from git import Repo


class GitCheckoutTask(SshTask):
    """
    Check out a git repo to the local disk
    """
    def __init__(self, repo, dest, branch="master", connection=None, gitopts=None):
        super().__init__(None, connection)
        self.repo = repo
        self.dest = dest
        self.gitopts = gitopts
        self.branch = branch

    def validate(self, job):
        assert (self.repo.startswith("ssh") and (self.connection or job.props.get("connection"))) \
            or self.repo.startswith("http")
        super().validate(job)

    def run(self, job):
        os.makedirs(self.dest, exist_ok=True)
        repo = Repo.init(self.dest)
        origin = repo.create_remote('origin', self.repo)
        fetch_env = {"GIT_TERMINAL_PROMPT": "0"}
        if self.repo.startswith("ssh"):
            fetch_env["GIT_SSH_COMMAND"] = "ssh -i {} -o StrictHostKeyChecking=no".format(self.conn.key)

        with repo.git.custom_environment(**fetch_env):
            origin.fetch()
            origin.pull(origin.refs[0].remote_head)

        repo.git.checkout(self.branch)
        print(repo.git.execute(["git", "log", "-1"]))
        print()
        print(repo.git.execute(["git", "log", "--pretty=oneline", "-10"]))

    def __repr__(self):
        return "<GitCheckoutTask repo='{}'>".format(self.repo)


class RsyncTask(SshTask):
    """
    Rsync a file tree from the local disk to some remote system
    """
    def __init__(self, src, dest, connection=None, exclude=None, delete=False, flags=None):
        super().__init__(None, connection)
        self.src = src
        self.dest = dest
        self.exclude = exclude
        self.delete = delete
        self.flags = flags

    def run(self, job):
        rsync_cmd = ["rsync", "-avzr"]

        if self.conn and self.conn.key:
            rsync_cmd += ["-e", "ssh -i '{}' -o StrictHostKeyChecking=no".format(self.conn.key)]

        if self.exclude:
            for item in self.exclude:
                rsync_cmd += ["--exclude={}".format(item)]

        if self.delete:
            rsync_cmd += ["--delete"]

        if self.flags:
            rsync_cmd += self.flags

        rsync_cmd += [self.src, self.dest]

        print(' '.join(rsync_cmd))
        subprocess.check_call(rsync_cmd)

    def __repr__(self):
        return "<RsyncTask dest='{}'>".format(self.dest)


class PythonTask(ShipperTask):
    """
    Call an arbitrary function passing a reference to the ShipperJob being executed
    """
    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self, job):
        self.func(job)

    def __repr__(self):
        return "<PythonTask func='{}'>".format(self.func)


class GiteaCheckoutTask(GitCheckoutTask):
    """
    Check out whatever git repo and branch the incoming data from Gitea referenced
    """
    def __init__(self, dest, connection=None, gitopts=None, allow_branches=None):
        super().__init__(None, dest, None, None, None)
        self.allow_branches = allow_branches

    def validate(self, job):
        self.conn = self.connection or job.props.get("connection")
        assert self.conn

    def run(self, job):
        data = job.props["payload"]
        if self.conn.key:
            self.repo = data["repository"]["ssh_url"]
        else:
            self.repo = data["repository"]["clone_url"]. \
                replace("://", "://{}:{}@".format(self.conn.username, self.conn.password))
        self.branch = data["ref"]
        if self.allow_branches:
            branch = self.branch
            if branch.startswith("refs/heads/"):
                branch = branch[len("refs/heads/"):]
            if branch not in self.allow_branches:
                raise StopJob("Branch '{}' is not whitelisted".format(branch))

        print(self.repo)
        super().run(job)

    def __repr__(self):
        return "<GiteaCheckoutTask>"


class LambdaTask(ShipperTask):
    """
    Run tasks generated by this task at execution time. Func should return a list of tasks.
    """
    def __init__(self, func):
        super().__init__()
        self.func = func

    def run(self, job):
        inserted = 0
        steps = self.func(job)
        if steps:
            for newstep in steps:
                job.tasks.insert(inserted, newstep)
                inserted += 1
        print("Prepended", inserted, "steps")

    def __repr__(self):
        return "<LambdaTask func='{}'>".format(self.func)


class DockerBuildTask(ShipperTask):
    def __init__(self, imagename=None, codedir=None):
        super().__init__()
        self.imagename = imagename
        self.codedir = codedir

    def run(self, job):
        imagename = self.imagename or job.props.get("docker_imagename")
        codedir = self.codedir or job.props.get("docker_codedir") or "code"
        cmd = ["docker", "build", "-t", imagename, codedir]
        print("Calling", cmd)
        # subprocess.check_call(cmd)

    def __repr__(self):
        return "<DockerBuildTask>"


class DockerPushTask(ShipperTask):
    def __init__(self, imagename=None):
        super().__init__()
        self.imagename = imagename

    def run(self, job):
        imagename = self.imagename or job.props.get("docker_imagename")
        cmd = ["docker", "push", imagename]
        print("Calling", cmd)
        # subprocess.check_call(cmd)

    def __repr__(self):
        return "<DockerPushTask>"


class DockerTagTask(ShipperTask):
    def __init__(self, imagename=None, tag=None):
        super().__init__()
        self.imagename = imagename
        self.tag = tag

    def run(self, job):
        imagename = self.imagename or job.props.get("docker_imagename")
        tag = self.tag or job.props.get("docker_tag")
        cmd = ["docker", "tag", imagename, tag]
        print("Calling", cmd)
        # subprocess.check_call(cmd)
        job.props["docker_imagename"] = tag

    def __repr__(self):
        return "<DockerTagTask>"