"""
Load, save and pass off handling to the controller
"""

from meticulous._controller import Controller
from meticulous._input import get_confirmation
from meticulous._input_queue import get_input_queue
from meticulous._storage import get_json_value, set_json_value
from meticulous._threadpool import get_pool


def update_workload(workload):
    """
    Ensure the minimum number of repository tasks are present.
    """
    result = list(workload)
    load_count = count_names(workload, {"repository_load"})
    for _ in range(3 - load_count):
        result.append({"interactive": False, "name": "repository_load"})
    if count_names(workload, {"prompt_quit"}) < 1:
        result.append({"interactive": True, "name": "prompt_quit", "priority": 999})
    if count_names(workload, {"force_quit"}) < 1:
        result.append({"interactive": True, "name": "force_quit", "priority": 1000})
    return result


def count_names(workload, names):
    """
    Get the number of tasks matching the name collection
    """
    count = 0
    for elem in workload:
        if elem["name"] in names:
            count += 1
    return count


def get_handlers():
    """
    Obtain the handler factory lookup
    """
    return {
        "repository_load": repository_load,
        "prompt_quit": prompt_quit,
        "force_quit": force_quit,
    }


def repository_load(_):
    """
    Task to pull a repository
    """

    def handler():
        pass

    return handler


def prompt_quit(context):
    """
    Interactive request to quit
    """

    def handler():
        if get_confirmation(message="Do you want to quit?", defaultval=True):
            context.controller.quit()

    return handler


def force_quit(context):
    """
    Force quit
    """

    def handler():
        context.controller.quit()

    return handler


def main():
    """
    Main task should load from storage, update the workload and pass off
    handling to the controller and on termination save the result
    """
    key = "multiworker_workload"
    workload = get_json_value(key, deflt=[])
    workload = update_workload(workload)
    handlers = get_handlers()
    input_queue = get_input_queue()
    threadpool = get_pool(handlers)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool
    )
    for task in workload:
        controller.add(task)
    result = controller.run()
    set_json_value(key, result)
