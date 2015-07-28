#!/usr/bin/python

import base64
import datetime
import json
import os
import subprocess
import sys
import thread
import time
import uuid

import flask
from oslo_config import cfg
from rally import api
from rally.cli.commands import task as rally_task_commands
from rally import db
from rally import plugins


CONF = cfg.CONF
CONF(sys.argv[1:], project="rally")
plugins.load()
ENV_NAME = "haos"
WORK_DIR = "/tmp/"


class Resource(object):
    fields = []
    non_serializable = []

    def __init__(self, *args, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field, None))

        self.id = uuid.uuid4().__str__()

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def update(self):
        pass

    @property
    def data(self):
        self.update()
        return dict((field, getattr(self, field))
                    for field in self.fields
                    if field not in self.non_serializable)


class Scenario(Resource):
    fields = ['id', 'name', 'filename', 'type', 'args']

    def __init__(self, *args, **kwargs):
        super(Scenario, self).__init__(*args, **kwargs)

        self.id = uuid.uuid4().__str__()

        self.filename = (self.filename
                         if self.filename is not None
                         else self.id + ".json")
        self.filename = os.path.join(WORK_DIR, self.filename)

        with file(self.filename, mode="w") as sc_file:
            sc_file.write(base64.b64decode(kwargs.get('data')))


class Task(Resource):
    fields = ['id', 'scenario_id', 'task_args',
              'task', 'input_task', 'state']
    non_serializable = ['task', 'input_task']

    def __init__(self, *args, **kwargs):
        super(Task, self).__init__(*args, **kwargs)

        self.scenario_id = kwargs.get('scenario_id')
        scenario = app.scenarios.get_by_id(self.scenario_id)

        self.input_task = app.rally_task_commands._load_task(
            task_file=scenario.filename,
            task_args=self.task_args)
        self.rally_task = api.Task.create(ENV_NAME, scenario.type)
        self.id = self.rally_task['uuid']
        self.state = "new"

    def update(self):
        rally_task = db.task_get(self.id)
        self.state = rally_task['status']

    def start_task(self):
        api.Task.start(ENV_NAME, self.input_task,
                       task=self.rally_task,
                       abort_on_sla_failure=False)
        self.update()


class Run(Resource):
    fields = ['id', 'task_ids', 'state']

    def __init__(self, *args, **kwargs):
        super(Run, self).__init__(*args, **kwargs)

        self.state = 'new'

    def start(self):
        for task_id in self.task_ids:
            task = app.tasks.get_by_id(task_id)
            thread.start_new_thread(task.start_task, ())
            time.sleep(5)
            task.update()
        self.state = 'running'

    def update(self):
        tasks_states = []
        for task_id in self.task_ids:
            tasks_states.append(app.tasks.get_by_id(task_id)['state'])

        if all([i == 'finished' for i in tasks_states]):
            self.state = 'finished'


class Result(Resource):
    fields = ['filename']

    def __init__(self, *args, **kwargs):
        super(Result, self).__init__(*args, **kwargs)

        task = kwargs.get('task')
        self.filename = "{0}_{1}_{2}.html".format(
            app.scenarios.get_by_id(task.scenario_id).type,
            datetime.datetime.now(),
            task.id)

        app.rally_task_commands.report(
            task.id,
            out=os.path.join(WORK_DIR, self.filename),
            out_format="html")


class Container(list):
    def __init__(self, *args, **kwargs):
        super(Container, self).__init__(*args, **kwargs)

    def get_by_id(self, id):
        return filter(lambda elem: elem.id == id, self)[0]

    @property
    def data(self):
        return [elem.data for elem in self]


class Rallyd(flask.Flask):
    def __init__(self, *args, **kwargs):
        super(Rallyd, self).__init__(*args, **kwargs)
        self.scenarios = Container()
        self.tasks = Container()
        self.runs = Container()
        self.results = Container()
        self.rally_task_commands = rally_task_commands.TaskCommands()


app = Rallyd(__name__)


@app.route("/db", methods=['POST'])
def recreate_db():
    subprocess.call("rally-manage db recreate".split())
    return flask.jsonify({"msg": "Db recreated"})


@app.route("/deployments", methods=['POST'])
def create_deployment():
    request_data = json.loads(flask.request.data)
    config = {
        "type": "ExistingCloud",
        "auth_url": request_data.get("OS_AUTH_URL"),
        "endpoint": request_data.get("OS_ENDPOINT"),
        "admin": {
            "username": request_data.get("OS_USERNAME"),
            "password": request_data.get("OS_PASSWORD"),
            "tenant_name": request_data.get("OS_TENANT_NAME")}}
    api.Deployment.create(config, ENV_NAME)
    return flask.jsonify(config)


@app.route("/scenarios", methods=['POST'])
def upload_scenario():
    request_data = json.loads(flask.request.data)
    scenario = Scenario(**request_data)
    app.scenarios.append(scenario)
    return flask.jsonify(scenario.data)


@app.route("/scenarios", methods=['GET'])
def list_scenarios():
    return flask.jsonify({"scenarios": app.scenarios.data})


@app.route("/tasks", methods=['POST'])
def add_task():
    request_data = json.loads(flask.request.data)
    task = Task(**request_data)
    app.tasks.append(task)
    return flask.jsonify(task.data)


@app.route("/tasks", methods=['GET'])
def list_tasks():
    return flask.jsonify({"tasks": app.tasks.data})


@app.route("/tasks/<task_id>", methods=['GET'])
def get_task(task_id):
    return flask.jsonify(app.tasks.get_by_id(task_id).data)


@app.route("/runs", methods=['POST'])
def start_run():
    request_data = json.loads(flask.request.data)
    run = Run(**request_data)
    app.runs.append(run)
    run.start()
    return flask.jsonify(run.data)


@app.route("/runs", methods=['GET'])
def list_runs():
    return flask.jsonify({"runs": app.runs.data})


@app.route("/runs/<run_id>", methods=['GET'])
def get_run(run_id):
    return flask.jsonify(app.runs.get_by_id(run_id).data)


@app.route("/runs/<run_id>/result", methods=['GET'])
def get_result(run_id):
    run = app.runs.get_by_id(run_id)
    local_result_list = []

    for task_id in run.task_ids:
        result = Result(task=app.tasks.get_by_id(task_id))

        app.results.append(result)
        local_result_list.append(result)

    return flask.jsonify({"results": [result.filename
                                      for result in local_result_list]})


@app.route("/result/<filename>")
def get_single_result(filename):
    return flask.send_from_directory(WORK_DIR, filename)


@app.route("/verification", methods=['POST'])
def install_tempest():
    pass


@app.route("/verification/run", methods=['POST'])
def run_tempest():
    pass


@app.route("/verification/result", methods=['GET'])
def get_tempest_results():
    pass


if __name__ == "__main__":
    app.run("0.0.0.0", 8001, debug=True)
