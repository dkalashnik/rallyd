#!/usr/bin/python

import argparse
import json
import os
import urlparse

import requests


class RallydClient(object):
    def __init__(self, base_url=None):
        self.base_url = base_url
        self.session = requests.Session()

    def set_base_url(self, base_url):
        self.base_url = base_url

    def request(self, url, method, headers=None, body=None, **kwargs):
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        r = requests.request(method, urlparse.urljoin(self.base_url, url),
                             headers=headers, data=body, **kwargs)

        if r.headers.get('Content-Type') == 'application/json':
            body = json.loads(r.content)

        return r.headers, body

    def post(self, url, body=None, **kwargs):
        return self.request(url, "POST", body=json.dumps(body), **kwargs)

    def get(self, url, **kwargs):
        return self.request(url, "GET", **kwargs)

    def put(self, url, body=None, **kwargs):
        return self.request(url, "PUT", body=json.dumps(body), **kwargs)

    def delete(self, url, **kwargs):
        return self.request(url, "DELETE", **kwargs)

    def recreate_db(self):
        headers, body = self.post("/db")
        return body

    def create_deployment(self, auth_url, username, password, tenant_name):
        request = {"auth_url": auth_url,
                   "username": username,
                   "password": password,
                   "tenant_name": tenant_name}

        headers, body = self.post("/deployments", body=request)
        return body

    def list_deployments(self):
        headers, body = self.get("/deployments")
        return body

    def get_deployemnt(self, deployment_uuid):
        headers, body = self.get("/deployments/{0}".format(deployment_uuid))
        return body

    def recreate_deployment(self, deployment_uuid):
        headers, body = self.put("/deployments/{0}".format(deployment_uuid))
        return body

    def delete_deployment(self, deployment_uuid):
        headers, body = \
            self.delete("/deployments/{0}".format(deployment_uuid))
        return body

    def create_task(self, task_filename, task_params=None, tag=None,
                    deployment_uuid=None, abort_on_sla_failure=False):
        request = {
            "task_config": json.loads(file(task_filename).read()),
            "task_params": task_params if task_params is not None else {},
            "tag": tag,
            "deployment_uuid": deployment_uuid,
            "abort_on_sla_failure": abort_on_sla_failure}

        headers, body = self.post("/tasks", body=request)
        return body

    def list_tasks(self):
        headers, body = self.get("/tasks")
        return body

    def get_task(self, task_uuid):
        headers, body = self.get("/tasks/{0}".format(task_uuid))
        return body

    def get_task_log(self, task_uuid, start_line=-10, end_line=None):
        payload = {"start_line": start_line}
        if end_line is not None:
            payload.update({"end_line": end_line})
        headers, body = self.get("/tasks/{0}/log".format(task_uuid),
                                 params=payload)
        return body

    def get_task_result(self, task_uuid, download_dir="."):
        headers, body = self.get("/tasks/{0}/result".format(task_uuid))
        path = os.path.join(download_dir,
                            "{0}-detailed-result.log".format(task_uuid))
        with open(path, "wb") as result:
            result.write(body)

    def get_task_report(self, task_uuid, report_format='html', download_dir="."):
        headers, body = self.get("/tasks/{0}/result".format(task_uuid),
                                 params={"format": report_format})
        path = os.path.join(download_dir,
                            "{0}.{1}".format(task_uuid, report_format))
        with open(path, "wb") as result:
            result.write(body)

    def delete_task(self, task_uuid):
        headers, body = self.delete("/tasks/{0}".format(task_uuid))
        return body

    def install_tempest(self, deployment_uuid=None, tempest_source=None):
        request = {"deployment_uuid": deployment_uuid,
                   "tempest_source": tempest_source}
        headers, body = self.post("/verification", body=request)
        return body

    def run_tempest(self, deployment_uuid, set_name, regex,
                    tempest_config=None):
        request = {"set_name": set_name,
                   "regex": regex,
                   "tempest_config": tempest_config}
        headers, body = \
            self.post("/verification/{0}/run".format(deployment_uuid),
                      body=request)
        return body

    def delete_tempest(self, deployment_uuid):
        headers, body = \
            self.delete("/verification/{0}".format(deployment_uuid))
        return body

def parse_args(client):
    parser = argparse.ArgumentParser(
        description="Rallyd control utility", prog="rallyd-cmd")
    parser.add_argument(
        "--endpoint", help="rallyd endpoint", default="http://127.0.0.1:8001")

    subparsers = parser.add_subparsers(
        title='Command', dest='command', metavar='<command>')

    recreate_db = subparsers.add_parser(
        'recreate-db', help='Recreate Rally database')
    recreate_db.set_defaults(func=client.recreate_db)

    create_deployment = subparsers.add_parser(
        'deployment-create', help='Add new deployment to Rally')
    create_deployment.add_argument(
        "--auth_url", default=os.environ.get("OS_AUTH_URL"),
        help="OpenStack auth url")
    create_deployment.add_argument(
        "--username", default=os.environ.get("OS_USERNAME"),
        help="Username for OpenStack admin user")
    create_deployment.add_argument(
        "--password", default=os.environ.get("OS_PASSWORD"),
        help="Password for OpenStack admin user")
    create_deployment.add_argument(
        "--tenant_name", default=os.environ.get("OS_TENANT_NAME"),
        help="Tenant name of OpenStack admin user")
    create_deployment.set_defaults(func=client.create_deployment)

    list_deployments = subparsers.add_parser(
        "deployment-list", help="Print list of rally deployments")
    list_deployments.set_defaults(func=client.list_deployments)

    create_task = subparsers.add_parser(
        "task-create", help="Start new rally task")
    create_task.add_argument(
        "--task_filename", help="Path to task file", required=True)
    create_task.add_argument(
        "--task_param", action="append",
        help="Key=value formatted params to render rally task."
             "Not implemented.")
    create_task.add_argument(
        "--tag", help="Tag for rally task")
    create_task.add_argument(
        "--deployment_uuid", help="UUID of deployemnt to run task")
    create_task.add_argument(
        "--abort_on_sla_failure", action="store_true",
        help="Abort task on SLA failure")
    create_task.set_defaults(func=client.create_task)

    list_tasks = subparsers.add_parser(
        "task-list", help="List Rally tasks")
    list_tasks.set_defaults(func=client.list_tasks)

    get_task = subparsers.add_parser(
        "task-get", help="Print Rally task info")
    get_task.add_argument(
        "--task_uuid", help="UUID of Rally task", required=True)
    get_task.set_defaults(func=client.get_task)

    get_task_log = subparsers.add_parser(
        "task-log", help="Print log of Rally task")
    get_task_log.add_argument(
        "--task_uuid", help="UUID of Rally task", required=True)
    get_task_log.add_argument(
        "--start_line", type=int, help="Start line from log")
    get_task_log.add_argument(
        "--end_line", type=int, help="End line from log")
    get_task_log.set_defaults(func=client.get_task_log)

    get_task_result = subparsers.add_parser(
        "task-result", help="Download task result (table with stats)")
    get_task_result.add_argument(
        "--task_uuid", help="UUID of Rally task", required=True)
    get_task_result.add_argument(
        "--download_dir", help="Directory for downloading")
    get_task_result.set_defaults(func=client.get_task_result)

    get_task_report = subparsers.add_parser(
        "task-report", help="Download task report")
    get_task_report.add_argument(
        "--task_uuid", help="UUID of Rally task", required=True)
    get_task_report.add_argument(
        "--task_format", help="Format of report", choises=["html", "junit"])
    get_task_report.add_argument(
        "--download_dir", help="Directory for downloading")
    get_task_report.set_defaults(func=client.get_task_report)

    return parser.parse_args()


def main():
    rallyd_client = RallydClient()
    args = parse_args(rallyd_client)
    rallyd_client.set_base_url(args.endpoint)

    print args.func(**args)


if __name__ == '__main__':
    main()
