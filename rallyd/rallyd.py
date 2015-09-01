#!/usr/bin/python

import json
import datetime
import subprocess
import sys
import os
import logging
import threading
import uuid
import urllib

import flask
from oslo_config import cfg
from rally import api
from rally.cli.commands import task as task_cli
from rally.common import db
from rally.common import objects
from rally import plugins
from rally.verification.tempest import tempest
from rally.verification.tempest import json2html


class Rallyd(flask.Flask):
    def __init__(self, *args, **kwargs):
        super(Rallyd, self).__init__(*args, **kwargs)


class DateJSONEncoder(flask.json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return str(obj)
        return flask.json.JSONEncoder.default(self, obj)


class Tee(object):
    def __init__(self, name, mode):
        self.file = open(name, mode)
        self.stdout = sys.stdout
        sys.stdout = self

    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()

    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
        self.file.flush()


CONF = cfg.CONF
CONF(sys.argv[1:], project="rally")
WORKDIR = '/tmp'
app = Rallyd(__name__)
app.json_encoder = DateJSONEncoder


def setup_logging(log_filename_prefix, log_filename_suffix=''):
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(threadName)s - '
                                  '%(levelname)s - %(message)s')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - '
                                  '%(levelname)s - %(message)s')
    log_filename = "{0}_{1}.log".format(log_filename_prefix,
                                        log_filename_suffix)
    file_handler = logging.FileHandler(os.path.join(WORKDIR, log_filename))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger('rally')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

@app.route("/api_map", methods=['GET'])
def api_map():
    output = []
    for rule in app.url_map.iter_rules():

        options = {}
        for arg in rule.arguments:
            options[arg] = "[{0}]".format(arg)

        methods = ','.join(filter(lambda x: x not in ['OPTIONS', 'HEAD'],
                                  rule.methods))
        url = flask.url_for(rule.endpoint, **options)
        output.append((rule.endpoint, methods, url))
    output = sorted(output, key=lambda x: x[2])
    output = [
        urllib.unquote("{:25s} {:20s} {}".format(endpoint, methods, url))
        for endpoint, methods, url in output
        ]

    return flask.jsonify({"map": output})


@app.route("/db", methods=['POST'])
def recreate_db():
    subprocess.call("rally-manage db recreate".split())
    return flask.jsonify({"msg": "Db recreated"}), 201


@app.route("/deployments", methods=['POST'])
def create_deployment():
    request = json.loads(flask.request.data)
    config = {
        "type": "ExistingCloud",
        "auth_url": request.get("auth_url"),
        "admin": {
            "username": request.get("username"),
            "password": request.get("password"),
            "tenant_name": request.get("tenant_name")}}
    deployment = api.Deployment.create(
        config, request.get("environment_name",
                            "default-{0}".format(uuid.uuid4().__str__())))

    return flask.jsonify(deployment.deployment._as_dict()), 201


@app.route("/deployments", methods=['GET'])
def list_deployments():
    return flask.jsonify(
        {"deployments": [i._as_dict() for i in db.deployment_list()]})


@app.route("/deployments/<deployment_uuid>", methods=['GET'])
def get_deployment(deployment_uuid):
    deployment = api.Deployment.get(deployment_uuid)
    return flask.jsonify(deployment.deployment._as_dict())


@app.route("/deployments/<deployment_uuid>", methods=['PUT'])
def recreate_deployment(deployment_uuid):
    api.Deployment.recreate(deployment_uuid)
    deployment = api.Deployment.get(deployment_uuid)
    return flask.jsonify(deployment.deployment._as_dict()), 201


@app.route("/deployments/<deployment_uuid>", methods=['DELETE'])
def delete_deployment(deployment_uuid):
    api.Deployment.destroy(deployment_uuid)
    return 'Deleted', 204


@app.route("/deployments/<deployment_uuid>/tempest", methods=['POST'])
def install_tempest(deployment_uuid):
    request = json.loads(flask.request.data)
    tempest_source = request.get('tempest_source', None)

    setup_logging('tempest_installation', deployment_uuid)

    threading.Thread(target=api.Verification.install_tempest,
                     args=(deployment_uuid,
                           tempest_source)).start()

    return flask.jsonify({"msg": "Start installing tempest",
                          "deployment_uuid": deployment_uuid}), 201


@app.route("/deployments/<deployment_uuid>/tempest", methods=['GET'])
def get_tempest_status(deployment_uuid):
    verifier = tempest.Tempest(deployment_uuid)
    status = os.path.exists(verifier.path(".testrepository"))
    return flask.jsonify({"Installed": status})


@app.route("/deployments/<deployment_uuid>/tempest", methods=['PUT'])
def reinstall_tempest(deployment_uuid):
    api.Verification.reinstall_tempest(deployment_uuid)
    return flask.jsonify({"msg": "Tempest reinstalled",
                          "deployment_uuid": deployment_uuid}), 201


@app.route("/deployments/<deployment_uuid>/tempest", methods=['DELETE'])
def uninstall_tempest(deployment_uuid):
    api.Verification.uninstall_tempest(deployment_uuid)
    return 'Deleted', 204


@app.route("/tasks", methods=['POST'])
def create_task():
    def byteify(input_struct):
        if isinstance(input_struct, dict):
            return {byteify(key): byteify(value)
                    for key, value in input_struct.iteritems()}
        elif isinstance(input_struct, list):
            return [byteify(element) for element in input_struct]
        elif isinstance(input_struct, unicode):
            return input_struct.encode('utf-8')
        else:
            return input_struct

    request = json.loads(flask.request.data)
    request = byteify(request)
    deployment_uuid = request.get('deployment_uuid')
    tag = request.get('tag', None)
    task_config = request.get('task_config')
    abort_on_sla_failure = request.get('abort_on_sla_failure', False)

    task = api.Task.create(deployment_uuid, tag)

    setup_logging('task', task.task.uuid)

    threading.Thread(target=api.Task.start,
                     args=(deployment_uuid,
                           task_config,
                           task,
                           abort_on_sla_failure)).start()

    return flask.jsonify(task.task._as_dict()), 201


@app.route("/tasks", methods=['GET'])
def list_tasks():
    return flask.jsonify({"tasks": [i._as_dict() for i in db.task_list()]})


@app.route("/tasks/<task_uuid>", methods=['GET'])
def get_task(task_uuid):
    return flask.jsonify(db.task_get(task_uuid)._as_dict())


@app.route("/tasks/<task_uuid>/log", methods=['GET'])
def get_task_log(task_uuid):
    start_line = flask.request.args.get('start_line', None)
    end_line = flask.request.args.get('end_line', None)

    if start_line is None:
        return flask.redirect(flask.url_for('get_task_log',
                                            task_uuid=task_uuid,
                                            start_line=-10))
    else:
        start_line = int(start_line)
    if end_line is not None:
        end_line = int(end_line)

    task_log_filename = "task_{0}.log".format(WORKDIR, task_uuid)
    with open(os.path.join(WORKDIR, task_log_filename), "r") as log:
        log_lines = log.readlines()
        return flask.jsonify({"task_id": task_uuid,
                              "total_lines": len(log_lines),
                              "from": start_line,
                              "to": end_line,
                              "data": log_lines[start_line:end_line]})


@app.route("/tasks/<task_uuid>/result", methods=['GET'])
def get_task_result(task_uuid):
    detailed_filename = ("task_{0}_detailed.log".format(task_uuid))

    tee = Tee(detailed_filename, "w")
    with open(os.path.join(WORKDIR,
                           detailed_filename), 'w') as detailed_file:
        sys.stdout = detailed_file
        task_cli.TaskCommands().detailed(task_uuid)

    return flask.send_from_directory(WORKDIR, detailed_filename)


@app.route("/tasks/<task_uuid>/report", methods=['GET'])
def get_task_report(task_uuid):
    report_format = flask.request.args.get('format', 'html')

    task_report_filename = "task_{0}.{1}".format(task_uuid, report_format)

    task_cli.TaskCommands().report(
        tasks=task_uuid,
        out=os.path.join(WORKDIR, task_report_filename),
        out_format=report_format)

    return flask.send_from_directory(WORKDIR, task_report_filename)


@app.route("/tasks/<task_uuid>", methods=['DELETE'])
def delete_task(task_uuid):
    force = flask.request.args.get('force', False)
    if force:
        force = True
    api.Task.delete(task_uuid, force)
    return 'Deleted', 204


@app.route("/verifications", methods=['POST'])
def run_verification():
    def verify(verifier, verification_uuid, set_name, regex):
        tempest_log_filename = "tempest_{0}.log".format(verification_uuid)
        tee = Tee(os.path.join(WORKDIR, tempest_log_filename), 'w')
        verifier.verify(set_name, regex)

    request = json.loads(flask.request.data)
    deployment_uuid = request.get('deployment_uuid')
    set_name = request.get('set_name', 'smoke')
    regex = request.get('regex', None)
    tempest_config = request.get('tempest_config', None)

    verification = objects.Verification(deployment_uuid=deployment_uuid)
    verifier = tempest.Tempest(deployment_uuid, verification=verification,
                               tempest_config=tempest_config)

    if not verifier.is_installed():
        flask.abort(500)

    threading.Thread(target=verify,
                     args=(verifier,
                           verification.uuid,
                           set_name,
                           regex)).start()

    return flask.jsonify(verification._as_dict()), 201


@app.route("/verifications", methods=['GET'])
def list_verifications():
    return flask.jsonify(
        {"verifications": [i._as_dict() for i in db.verification_list()]})


@app.route("/verifications/<verification_uuid>", methods=['GET'])
def get_verification(verification_uuid):
    verification = db.verification_get(verification_uuid)
    return flask.jsonify(verification._as_dict())


@app.route("/verifications/<verification_uuid>/result", methods=['GET'])
def get_verification_results(verification_uuid):
    detailed = flask.request.args.get('detailed', False) and True

    verification = db.verification_get(verification_uuid)['data']
    results = db.verification_result_get(verification_uuid)

    if detailed:
        return flask.jsonify(results._as_dict())
    else:
        return flask.jsonify(verification._as_dict())


@app.route("/verifications/<verification_uuid>/report", methods=['GET'])
def get_verification_report(verification_uuid):
    report_format = flask.request.args.get('report_format', 'html')

    results = db.verification_result_get(verification_uuid)["data"]
    output_file = "tempest_{0}.{1}".format(verification_uuid,
                                           report_format)

    if report_format == 'json':
        result = json.dumps(results, sort_keys=True, indent=4)
    else:
        result = json2html.HtmlOutput(results).create_report()
    with open(os.path.join(WORKDIR, output_file), "wb") as f:
        f.write(result)

    return flask.send_from_directory(
        WORKDIR, output_file, mimetype="application/octet-stream")


def main():
    plugins.load()
    app.run("0.0.0.0", 8001, debug=True, use_reloader=False)


if __name__ == '__main__':
    main()
