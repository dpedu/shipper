#!/usr/bin/env python3
import os
import importlib
import argparse
import json
from tempfile import TemporaryDirectory


def load_task(srcfile):
    spec = importlib.util.spec_from_file_location("job", srcfile)
    job = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(job)
    return job


def main():
    parser = argparse.ArgumentParser(description="Shipper task runner")

    parser.add_argument('jobfile', help="Job file to run")
    parser.add_argument('args', help="JSON args")

    args = parser.parse_args()

    job = load_task(args.jobfile)
    params = json.loads(args.args)

    with TemporaryDirectory() as d:
        os.chdir(d)
        job.job.run(params)


if __name__ == '__main__':
    main()
