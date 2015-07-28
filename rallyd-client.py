#!/usr/bin/python

from __future__ import print_function

import argparse
import base64
import json
import os
import pprint
import urlparse

import requests


class HTTPClient(object):
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.session = requests.Session()

    def set_base_url(self, base_url):
        self.base_url = base_url

    def request(self, url, method, headers=None, body=None, **kwargs):
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        r = requests.request(method, urlparse.urljoin(self.base_url, url),
                             headers=headers, data=body,
                             **kwargs)
        return r.headers, json.loads(r.content)

    def post(self, url, body, headers=None, **kwargs):
        return self.request(url, "POST", headers, body=body, **kwargs)

    def get(self, url, headers=None, **kwargs):
        return self.request(url, "GET", headers, **kwargs)

    def get_raw(self, url, headers=None, **kwargs):
        return requests.request("GET", self.base_url + url, **kwargs)


class RallydClient(HTTPClient):
    def recreate_db(self):
        return self.post("/db", body=json.dumps({}))

    def deployment_create(self, auth_url, endpoint, username,
                          password, tenant_name, from_env,
                          *args, **kwargs):
        body = {"OS_AUTH_URL": auth_url,
                "OS_ENDPOINT": endpoint,
                "OS_USERNAME": username,
                "OS_PASSWORD": password,
                "OS_TENANT_NAME": tenant_name}

        if from_env:
            body = dict((key, os.environ.get(key)) for key in body)

        return self.post("/deployments", json.dumps(body))

    def scenario_create(self, scenario_file, scenario_type,
                        name=None, filename=None, *args, **kwargs):
        with file(scenario_file) as scenario:
            data = base64.b64encode(scenario.read())
        body = {"data": data,
                "type": scenario_type,
                "filename": filename,
                "name": name}
        return self.post("/scenarios",
                         body=json.dumps(body))

    def scenarios_list(self, *args, **kwargs):
        return self.get("/scenarios")

    def task_add(self, scenario_id, *args, **kwargs):
        return self.post("/tasks",
                         body=json.dumps({"scenario_id": scenario_id}))

    def task_list(self, *args, **kwargs):
        return self.get("/tasks")

    def task_get(self, task_id, *args, **kwargs):
        return self.get("/tasks/{0}".format(task_id))

    def run_create(self, task_ids, *args, **kwargs):
        return self.post("/runs", body=json.dumps({"task_ids": task_ids}))

    def run_list(self, *args, **kwargs):
        return self.get("/runs")

    def run_get(self, run_id, *args, **kwargs):
        return self.get("/runs/{0}".format(run_id))

    def task_result_download(self, filename):
        return self.get_raw("/result/{0}".format(filename), stream=True)

    def run_result_download(self, run_id, download_dir=".",
                            *args, **kwargs):
        resp, results = self.get("/runs/{0}/result".format(run_id))
        for filename in json.loads(results)["results"]:
            r = self.task_result_download(filename)
            path = os.path.join(download_dir, os.path.split(filename)[-1])
            with open(path, "wb") as result:
                for block in r.iter_content(1024):
                    result.write(block)
        return resp, results


if __name__ == "__main__":
    def add_command(name, func, base_args=None, advanced_args=None):
        if base_args is None:
            base_args = []

        if advanced_args is None:
            advanced_args = {}

        subcommand = command.add_parser(name, description=name)
        subcommand.set_defaults(func=func)

        for arg in base_args:
            subcommand.add_argument(arg)

        for args, kwargs in advanced_args:
            subcommand.add_argument(*args, **kwargs)

    main_parser = argparse.ArgumentParser(prog='PROG')
    command = main_parser.add_subparsers(title='Commands',
                                         dest='command',
                                         metavar='<command>')

    rally = RallydClient()

    main_parser.add_argument("--endpoint", help="rallyd endpoint")
    main_parser.add_argument("--json", dest="json", action="store_true",
                             help="Enable json output")

    add_command("db-recreate", rally.recreate_db)

    add_command("deployment-create", rally.deployment_create,
                base_args=['--auth-url', '--endpoint', '--username',
                           '--password', '--tenant_name'],
                advanced_args=[(('--from_env', ), {'dest': 'from_env',
                                                   'action': 'store_true'})])

    add_command("scenario-create", rally.scenario_create,
                base_args=['scenario_file', 'scenario_type',
                           '--filename', '--name'])
    add_command("scenario-list", rally.scenarios_list)

    add_command("task-create", rally.task_add,
                base_args=['scenario_id'])
    add_command("task-list", rally.task_list)
    add_command("task-show", rally.task_get,
                base_args=['task_id'])

    add_command(
        "run-start", rally.run_create,
        advanced_args=[(('task_ids', ), {'nargs': '+', 'type': str})])
    add_command("run-list", rally.run_list)
    add_command("run-show", rally.run_get,
                base_args=['run_id'])

    add_command("result", rally.run_result_download,
                base_args=['run_id', '--download_dir'])

    args = main_parser.parse_args()
    rally.set_base_url(args.endpoint)

    _, data = args.func(**vars(args))

    if args.json:
        print(json.dumps(data))
    else:
        pprint.pprint(data)
