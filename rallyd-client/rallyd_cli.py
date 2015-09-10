import argparse
import os
import json
import pprint

import prettytable

import rallyd_client as client


collection_headers = \
    {
        "deployments": [
            "uuid",
            "name",
            "status",
            "created_at",
        ],
        "tasks": [
            "uuid",
            "tag",
            "status",
            "created_at",
        ],
        "verifications": [
            "uuid",
            "set_name",
            "status",
            "tests",
            "errors",
            "failures",
            "created_at",
        ]
    }

resource_fields = \
    {
        "deployment": [
            "uuid",
            "name",
            "created_at",
            "updated_at",
            "started_at",
            "completed_at",
            "parent_uuid",
            "config",
        ],
        "task": [
            "uuid",
            "tag",
            "status",
            "created_at",
            "updated_at",
            "deployment_uuid",
            "verification_log",
        ],
        "verification": [
            "uuid",
            "set_name",
            "status",
            "tests",
            "failures",
            "errors",
            "time",
            "created_at",
            "updated_at",
            "deployment_uuid"]
    }

class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


def print_collection_table(collection_name, collection_list):
    headers = collection_headers[collection_name]
    table = prettytable.PrettyTable(headers)

    for resource in collection_list:
        row = [resource.get(field, "") for field in headers]
        table.add_row(row)

    print table


def print_resource_table(resource_name, resource):
    fields = resource_fields[resource_name]
    resource_headers = ["Property", "Value"]

    table = prettytable.PrettyTable(resource_headers)
    for header in resource_headers:
        table.align[header] = "l"

    values = [pprint.pformat(resource.get(field, '')) for field in fields]
    for row in zip(fields, values):
        table.add_row(row)
    print table

def parse_args(client):
    parser = argparse.ArgumentParser(
        description="Rallyd control utility", prog="rallyd-cmd")
    parser.add_argument(
        "--endpoint", help="rallyd endpoint", default="http://127.0.0.1:10000")
    parser.add_argument(
        "--json", help="Print pure-json output", action="store_true")

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
        "deployment_uuid", help="UUID of deployemnt to run task")
    create_task.add_argument(
        "task_filename", help="Path to task file")
    create_task.add_argument(
        "--task-params", action="append",
        help="Key=value formatted params to render rally task."
             "Not implemented.")
    create_task.add_argument(
        "--tag", help="Tag for rally task")
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
        "task_uuid", help="UUID of Rally task")
    get_task.set_defaults(func=client.get_task)

    get_task_log = subparsers.add_parser(
        "task-log", help="Print log of Rally task")
    get_task_log.add_argument(
        "task_uuid", help="UUID of Rally task")
    get_task_log.add_argument(
        "--start-line", type=int, help="Start line from log")
    get_task_log.add_argument(
        "--end-line", type=int, help="End line from log")
    get_task_log.set_defaults(func=client.get_task_log)

    get_task_result = subparsers.add_parser(
        "task-result", help="Download task result (table with stats)")
    get_task_result.add_argument(
        "task_uuid", help="UUID of Rally task")
    get_task_result.add_argument(
        "--download-dir", help="Directory for downloading", default=".")
    get_task_result.set_defaults(func=client.get_task_result)

    get_task_report = subparsers.add_parser(
        "task-report", help="Download task report")
    get_task_report.add_argument(
        "task_uuid", help="UUID of Rally task")
    get_task_report.add_argument(
        "--report-format", help="Format of report",
        choices=["html", "junit"], default="html")
    get_task_report.add_argument(
        "--download-dir", help="Directory for downloading", default=".")
    get_task_report.set_defaults(func=client.get_task_report)

    install_tempest = subparsers.add_parser(
        "tempest-install", help="Install tempest for deployment")
    install_tempest.add_argument(
        "deployment_uuid", help="Deployment UUID")
    install_tempest.add_argument(
        "--tempest-source", help="Source for tempest installation")
    install_tempest.set_defaults(func=client.install_tempest)

    check_tempest = subparsers.add_parser(
        "tempest-check", help="Check tempest for deployment")
    check_tempest.add_argument(
        "deployment_uuid", help="Deployment UUID")
    check_tempest.set_defaults(func=client.check_tempest)

    reinstall_tempest = subparsers.add_parser(
        "tempest-reinstall", help="Reinstall tempest for deployment")
    reinstall_tempest.add_argument(
        "deployment_uuid", help="Deployment UUID")
    reinstall_tempest.set_defaults(func=client.reinstall_tempest)

    uninstall_tempest = subparsers.add_parser(
        "tempest-uninstall", help="Uninstall tempest for deployment")
    uninstall_tempest.add_argument(
        "deployment_uuid", help="Deployment UUID")
    uninstall_tempest.set_defaults(func=client.uninstall_tempest)

    run_verification = subparsers.add_parser(
        "verification-start", help="Run Tempest agains deployment")
    run_verification.add_argument("deployment_uuid")
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
        "verification_uuid", help="UUID of verification run")
    get_verification.set_defaults(func=client.get_verification)

    get_verification_result = subparsers.add_parser(
        "verification-result", help="Show tempest result")
    get_verification_result.add_argument(
        "verification_uuid", help="UUID of verification run")
    get_verification_result.add_argument(
        "--detailed", action="store_true",
        help="Enable verbose raw json output")
    get_verification_result.set_defaults(func=client.get_verification_result)

    get_verification_report = subparsers.add_parser(
        "verification-report", help="Download tempest run report")
    get_verification_report.add_argument(
        "verification_uuid", help="UUID of verification run")
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
    rallyd_client = client.RallydClient()
    args = vars(parse_args(rallyd_client))

    command = args.pop("func")
    json_enabled = args.pop("json")
    rallyd_client.set_base_url(args.pop("endpoint"))
    result = command(**args)

    if json_enabled:
        print json.dumps(result)
        return

    if not isinstance(result, dict):
        pprint.pprint(result)
        return

    if "msg" in result:
        pprint.pprint(result["msg"])
        return

    key, value = result.popitem()

    if key in collection_headers:
        print_collection_table(key, value)
        return

    if key in resource_fields:
        print_resource_table(key, value)
        return

    pprint.pprint(result)


if __name__ == '__main__':
    main()
