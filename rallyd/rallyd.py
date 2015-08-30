#!/usr/bin/python

import json
import subprocess
import sys
import multiprocessing
import logging

import flask
from oslo_config import cfg
from rally import api
from rally.cli.commands import task as task_cli
from rally.common import db
from rally import plugins


CONF = cfg.CONF
CONF(sys.argv[1:], project="rally")
WORKDIR = '/tmp'


class Rallyd(flask.Flask):
    def __init__(self, *args, **kwargs):
        super(Rallyd, self).__init__(*args, **kwargs)


app = Rallyd(__name__)


@app.route("/db", methods=['POST'])
def recreate_db():
    subprocess.call("rally-manage db recreate".split())
    return flask.jsonify({"msg": "Db recreated"})


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
    deployment = api.Deployment.create(config,
                                       request.get("environment_name",
                                                   "Default"))
    return flask.jsonify(deployment)


@app.route("/deployments", methods=['GET'])
def list_deployments():
    return flask.jsonify(db.deployment_list())


@app.route("/deployments/<deployment_uuid>", methods=['GET'])
def get_deployment(deployment_uuid):
    deployment = api.Deployment.get(deployment_uuid)
    return flask.jsonify(deployment)

@app.route("/deployments/<deployment_uuid>", methods=['PUT'])
def recreate_deployment(deployment_uuid):
    api.Deployment.recreate(deployment_uuid)
    deployment = api.Deployment.get(deployment_uuid)
    return flask.jsonify(deployment)


@app.route("/deployments/<deployment_uuid>", methods=['DELETE'])
def delete_deployment(deployment_uuid):
    api.Deployment.destroy(deployment_uuid)
    return 'Deleted', 204


def find_deployment():
    deployments = db.deployment_list()
    if len(deployments) > 1:
        flask.abort(500)
    if len(deployments) == 0:
        flask.abort(500)
    return deployments[0].uuid


@app.route("/tasks", methods=['POST'])
def create_task():
    request = json.loads(flask.request.data)
    deployment_uuid = request.get('deployment_uuid', None)
    tag = request.get('tag', None)
    task_template = request.get('task_config')
    task_params = request.get('task_params', {})
    abort_on_sla_failure = request.get('abort_on_sla_failure', False)

    if deployment_uuid is None:
        deployment_uuid = find_deployment()

    task_config = api.Task.render_template(task_template, **task_params)
    api.Task.validate(deployment_uuid, task_config)
    task = api.Task.create(deployment_uuid, tag)

    formatter = logging.Formatter('%(asctime)s - %(name)s-%(process)s'
                                  ' - %(levelname)s - %(message)s')
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(logging.INFO)

    file_handler = logging.FileHandler('{1}/{0}.log'.format(WORKDIR,
                                                            task.uuid))
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)

    logger = logging.getLogger('rally')
    logger.setLevel(logging.DEBUG)
    logger.addHandler(stdout_handler)
    logger.addHandler(file_handler)

    multiprocessing.Process(target=api.Task.start,
                            name="rally",
                            args=(deployment_uuid,
                                  task_config,
                                  task,
                                  abort_on_sla_failure)).start()

    return flask.jsonify(task)


@app.route("/tasks", methods=['GET'])
def list_tasks():
    return flask.jsonify(db.task_list())


@app.route("/tasks/<task_uuid>", methods=['GET'])
def get_task(task_uuid):
    return flask.jsonify(db.task_get(task_uuid))


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

    with file('{0}/{1}.log'.format(WORKDIR, task_uuid), "r") as log:
        log_lines = log.readlines()
        return flask.jsonify({"task_id": task_uuid,
                              "total_lines": len(log_lines),
                              "from": start_line,
                              "to": end_line,
                              "data": log_lines[start_line:end_line]})


@app.route("/tasks/<task_uuid>/report", methods=['GET'])
def get_task_result(task_uuid):
    orig_stdout = sys.stdout
    detailed_filename = ("{0}/{1}-detailed-result.log"
                         .format(WORKDIR, task_uuid))
    with file(detailed_filename, 'w') as detailed_file:
        sys.stdout = detailed_file
        task_cli.TaskCommands().detailed(task_uuid)
    sys.stdout = orig_stdout
    return flask.send_from_directory(WORKDIR, detailed_file)


@app.route("/tasks/<task_uuid>/report", methods=['GET'])
def get_task_report(task_uuid):
    report_format = flask.request.args.get('format', 'html')
    report_filename = "{0}/{1}.{2}".format(WORKDIR, task_uuid, report_format)

    task_cli.TaskCommands().report(
        tasks=task_uuid,
        out=report_filename,
        out_format=report_format)

    return flask.send_from_directory(WORKDIR, report_filename)


@app.route("/tasks/<task_uuid>", methods=['DELETE'])
def delete_task(task_uuid):
    force = flask.request.args.get('force', False)
    if force:
        force = True
    api.Task.delete(task_uuid, force)
    return 'Deleted', 204


@app.route("/verification", methods=['POST'])
def install_tempest():
    request = json.loads(flask.request.data)
    deployment_uuid = request.get('deployment_uuid', None)
    tempest_source = request.get('tempest_source', None)

    if deployment_uuid is None:
        deployment_uuid = find_deployment()

    tempest = api.Verification.install_tempest(deployment_uuid,
                                               tempest_source)
    return flask.jsonify(tempest)


@app.route("/verification/<deployment_uuid>", methods=['PUT'])
def reinstall_tempest(deployment_uuid):
    tempest = api.Verification.reinstall_tempest(deployment_uuid)
    return flask.jsonify(tempest)


@app.route("/verification/<deployment_uuid>/run", methods=['POST'])
def run_tempest(deployment_uuid):
    request = json.loads(flask.request.data)
    set_name = request.get('set_name')
    regex = request.get('regex')
    tempest_config = request.get('tempest_config', None)

    api.Verification.verify(deployment_uuid, set_name, regex, tempest_config)
    return 'Started', 201


@app.route("/verification/<deployment_uuid>", methods=['DELETE'])
def uninstall_tempest(deployment_uuid):
    api.Verification.uninstall_tempest(deployment_uuid)
    return 'Deleted', 204


def main():
    print "start rallyd"
    plugins.load()
    print "plugins loaded"
    app.run("0.0.0.0", 8001, debug=True)


if __name__ == '__main__':
    main()
