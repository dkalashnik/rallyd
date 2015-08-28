#!/usr/bin/python

import json
import subprocess
import sys

import flask
from oslo_config import cfg
from rally import api
from rally.common import db
from rally import plugins


CONF = cfg.CONF
CONF(sys.argv[1:], project="rally")


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
    tag = request.get('tag', 'None')
    task_template = request.get('task_config')
    task_params = request.get('task_params', {})
    abort_on_sla_failure = request.get('abort_on_sla_failure', False)

    if deployment_uuid is None:
        deployment_uuid = find_deployment()

    task_config = api.Task.render_template(task_template, **task_params)
    api.Task.validate(deployment_uuid, task_config)
    task = api.Task.create(deployment_uuid, tag)

    # TODO: Wrap with multiprocessing
    api.Task.start(deployment_uuid, task_config, task, abort_on_sla_failure)
    return flask.jsonify(task)


@app.route("/tasks/<task_uuid>", methods=['DELETE'])
def delete_task(task_uuid):
    force = flask.request.args.get('force', False)
    if force:
        force = True
    api.Task.delete(task_uuid, force)


@app.route("/verification", methods=['POST'])
def install_tempest():
    request = json.loads(flask.request.data)
    deployment_uuid = request.get('deployment_uuid', None)
    tempest_source = request.get('tempest_source', None)

    if deployment_uuid is None:
        deployment_uuid = find_deployment()

    tempest = api.Verification.install_tempest(deployment_uuid, tempest_source)
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


@app.route("/verification/<deployment_uuid>", methods=['DELETE'])
def uninstall_tempest(deployment_uuid):
    api.Verification.uninstall_tempest(deployment_uuid)
    return 'Deleted', 204


def main():
    plugins.load()
    app.run("0.0.0.0", 8001, debug=True)



if __name__ == '__main__':
    main()
