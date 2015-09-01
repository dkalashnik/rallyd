#!/usr/bin/python

import argparse
import json
import os
import pprint
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
        else:
            body = r.content

        return r.headers, body

    def post(self, url, body=None, **kwargs):
        return self.request(url, "POST", body=json.dumps(body), **kwargs)

    def get(self, url, **kwargs):
        return self.request(url, "GET", **kwargs)

    def put(self, url, body=None, **kwargs):
        return self.request(url, "PUT", body=json.dumps(body), **kwargs)

    def delete(self, url, **kwargs):
        return self.request(url, "DELETE", **kwargs)

    def recreate_db(self, **kwargs):
        headers, body = self.post("/db")
        return body

    def create_deployment(self, auth_url, username, password, tenant_name, **kwargs):
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
        headers, body = self.get("/tasks/{0}/result".format(task_uuid),
                                 stream=True)
        path = os.path.join(download_dir,
                            "{0}-detailed-result.log".format(task_uuid))
        with open(path, "wb") as result:
            result.write(body)
        return "Downloaded: {0}".format(path)

    def get_task_report(self, task_uuid,
                        report_format='html',
                        download_dir="."):
        headers, body = self.get("/tasks/{0}/report".format(task_uuid),
                                 params={"format": report_format},
                                 stream=True)
        path = os.path.join(download_dir,
                            "{0}.{1}".format(task_uuid, report_format))
        with open(path, "wb") as result:
            result.write(body)
        return "Downloaded: {0}".format(path)

    def delete_task(self, task_uuid):
        headers, body = self.delete("/tasks/{0}".format(task_uuid))
        return body

    def install_tempest(self, deployment_uuid=None, tempest_source=None):
        request = {"tempest_source": tempest_source}
        headers, body = \
            self.post("/deployments/{0}/tempest".format(deployment_uuid),
                      body=request)
        return body

    def check_tempest(self, deployment_uuid):
        headers, body = \
            self.get("/deployments/{0}/tempest".format(deployment_uuid))
        return body

    def reinstall_tempest(self, deployment_uuid):
        headers, body = self.put(
            "/deployments/{0}/tempest".format(deployment_uuid))
        return body

    def uninstall_tempest(self, deployment_uuid):
        headers, body = self.delete(
            "/deployments/{0}/tempest".format(deployment_uuid))
        return body

    def run_verification(self, deployment_uuid, set_name=None,
                         regex=None, tempest_config=None):
        request = {
            "deployment_uuid": deployment_uuid,
            "set_name": set_name,
            "regex": regex,
            "tempest_config": tempest_config}
        headers, body = self.post("/verifications", body=request)
        return body

    def list_verifications(self):
        headers, body = self.get("/verifications")
        return body

    def get_verification(self, verification_uuid):
        headers, body = \
            self.get("/verifications/{0}".format(verification_uuid))
        return body

    def get_verification_result(self, verification_uuid, detailed=False):
        payload = {}
        if detailed:
            payload.update({"detailed": 1})

        headers, body = \
            self.get("/verifications/{0}/result".format(verification_uuid),
                     params=payload)
        return body

    def get_verification_report(self, verification_uuid, report_format='html',
                                download_dir="."):
        payload = {"report_format": report_format}
        headers, body = \
            self.get("/verifications/{0}/report".format(verification_uuid),
                     params=payload, stream=True)

        path = os.path.join(download_dir,
                            "tempest_{0}.{1}".format(verification_uuid,
                                                     report_format))
        with open(path, "wb") as result:
            result.write(body)
        return "Downloaded: {0}".format(path)


def parse_args(client):
    parser = argparse.ArgumentParser(
        description="Rallyd control utility", prog="rallyd-cmd")
    parser.add_argument(
        "--endpoint", help="rallyd endpoint", default="http://127.0.0.1:8001")

    subparsers = parser.add_subparsers()

    recreate_db = subparsers.add_parser(
        'recreate-db', help='Recreate Rally database')
    recreate_db.set_defaults(func=client.recreate_db)

    create_deployment = subparsers.add_parser(
        'deployment-create', help='Add new deployment to Rally')
    create_deployment.add_argument(
        "--auth-url", default=os.environ.get("OS_AUTH_URL"),
        help="OpenStack auth url")
    create_deployment.add_argument(
        "--username", default=os.environ.get("OS_USERNAME"),
        help="Username for OpenStack admin user")
    create_deployment.add_argument(
        "--password", default=os.environ.get("OS_PASSWORD"),
        help="Password for OpenStack admin user")
    create_deployment.add_argument(
        "--tenant-name", default=os.environ.get("OS_TENANT_NAME"),
        help="Tenant name of OpenStack admin user")
    create_deployment.set_defaults(func=client.create_deployment)

    list_deployments = subparsers.add_parser(
        "deployment-list", help="Print list of rally deployments")
    list_deployments.set_defaults(func=client.list_deployments)

    create_task = subparsers.add_parser(
        "task-create", help="Start new rally task")
    create_task.add_argument(
        "--task-filename", help="Path to task file", required=True)
    create_task.add_argument(
        "--task-params", action="append",
        help="Key=value formatted params to render rally task."
             "Not implemented.")
    create_task.add_argument(
        "--tag", help="Tag for rally task")
    create_task.add_argument(
        "--deployment-uuid", help="UUID of deployemnt to run task")
    create_task.add_argument(
        "--abort-on-sla-failure", action="store_true",
        help="Abort task on SLA failure")
    create_task.set_defaults(func=client.create_task)

    list_tasks = subparsers.add_parser(
        "task-list", help="List Rally tasks")
    list_tasks.set_defaults(func=client.list_tasks)

    get_task = subparsers.add_parser(
        "task-get", help="Print Rally task info")
    get_task.add_argument(
        "--task-uuid", help="UUID of Rally task", required=True)
    get_task.set_defaults(func=client.get_task)

    get_task_log = subparsers.add_parser(
        "task-log", help="Print log of Rally task")
    get_task_log.add_argument(
        "--task-uuid", help="UUID of Rally task", required=True)
    get_task_log.add_argument(
        "--start-line", type=int, help="Start line from log")
    get_task_log.add_argument(
        "--end-line", type=int, help="End line from log")
    get_task_log.set_defaults(func=client.get_task_log)

    get_task_result = subparsers.add_parser(
        "task-result", help="Download task result (table with stats)")
    get_task_result.add_argument(
        "--task-uuid", help="UUID of Rally task", required=True)
    get_task_result.add_argument(
        "--download-dir", help="Directory for downloading", default=".")
    get_task_result.set_defaults(func=client.get_task_result)

    get_task_report = subparsers.add_parser(
        "task-report", help="Download task report")
    get_task_report.add_argument(
        "--task-uuid", help="UUID of Rally task", required=True)
    get_task_report.add_argument(
        "--report-format", help="Format of report",
        choices=["html", "junit"], default="html")
    get_task_report.add_argument(
        "--download-dir", help="Directory for downloading", default=".")
    get_task_report.set_defaults(func=client.get_task_report)

    install_tempest = subparsers.add_parser(
        "tempest-install", help="Install tempest for deployment")
    install_tempest.add_argument(
        "--deployment-uuid", help="Deployment UUID", required=True)
    install_tempest.add_argument(
        "--tempest-source", help="Source for tempest installation")
    install_tempest.set_defaults(func=client.install_tempest)

    check_tempest = subparsers.add_parser(
        "tempest-check", help="Check tempest for deployment")
    check_tempest.add_argument(
        "--deployment-uuid", help="Deployment UUID", required=True)
    check_tempest.set_defaults(func=client.check_tempest)

    reinstall_tempest = subparsers.add_parser(
        "tempest-reinstall", help="Reinstall tempest for deployment")
    reinstall_tempest.add_argument(
        "--deployment-uuid", help="Deployment UUID", required=True)
    reinstall_tempest.set_defaults(func=client.reinstall_tempest)

    uninstall_tempest = subparsers.add_parser(
        "tempest-uninstall", help="Uninstall tempest for deployment")
    uninstall_tempest.add_argument(
        "--deployment-uuid", help="Deployment UUID", required=True)
    uninstall_tempest.set_defaults(func=client.uninstall_tempest)

    run_verification = subparsers.add_parser(
        "verification-start", help="Run Tempest agains deployment")
    run_verification.add_argument("--deployment-uuid", required=True)
    run_verification.add_argument(
        "--set-name", help="full, smoke, scenario or api.")
    run_verification.add_argument(
        "--regex", help="regex mathing cases to run")
    run_verification.add_argument(
        "--tempest-config", help="Path to custom tempest config")
    run_verification.set_defaults(func=client.run_verification)

    list_verifications = subparsers.add_parser(
        "verification-list", help="List all verifications")
    list_verifications.set_defaults(func=client.list_verifications)

    get_verification = subparsers.add_parser(
        "verification-get", help="Get specific tempest run")
    get_verification.add_argument(
        "--verification-uuid", help="UUID of verification run", required=True)
    get_verification.set_defaults(func=client.get_verification)

    get_verification_result = subparsers.add_parser(
        "verification-result", help="Show tempest result")
    get_verification_result.add_argument(
        "--verification-uuid", help="UUID of verification run", required=True)
    get_verification_result.add_argument(
        "--detailed", action="store_true",
        help="Enable verbose raw json output")
    get_verification_result.set_defaults(func=client.get_verification_result)

    get_verification_report = subparsers.add_parser(
        "verification-report", help="Download tempest run report")
    get_verification_report.add_argument(
        "--verification-uuid", help="UUID of verification run", required=True)
    get_verification_report.add_argument(
        "--report-format",
        help="Format of report. HTML report will be saved to [download-dir],"
             "Json will be printed",
        choices=["html", "json"], default="html")
    get_verification_report.add_argument(
        "--download-dir", help="Directory for downloading", default=".")
    get_verification_report.set_defaults(func=client.get_verification_report)

    return parser.parse_args()


def main():
    rallyd_client = RallydClient()
    args = parse_args(rallyd_client)

    args = vars(args)
    command = args.pop("func")
    rallyd_client.set_base_url(args.pop("endpoint"))
    pprint.pprint(command(**args))


if __name__ == '__main__':
    main()
