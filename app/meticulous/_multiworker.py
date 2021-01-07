"""
Load, save and pass off handling to the controller
"""

import pprint

from meticulous import _input
from meticulous._addrepo import addrepo_handlers
from meticulous._cleanup import remove_repo_for
from meticulous._controller import Controller
from meticulous._input_queue import get_input_queue
from meticulous._processrepo import processrepo_handlers
from meticulous._storage import get_json_value, set_json_value
from meticulous._submit import submit_handlers
from meticulous._threadpool import get_pool

MAX_BUFFER_REPOS = 10


def update_workload(workload):
    """
    Ensure the minimum number of repository tasks are present.
    """
    print("Initial workload:")
    pprint.pprint(workload)
    result = list(workload)
    actions = {"cleanup"}
    actions.update(addrepo_handlers().keys())
    actions.update(processrepo_handlers().keys())
    actions.update(submit_handlers().keys())
    load_count = count_names(workload, actions)
    print(f"Load Count: {load_count}")
    for _ in range(MAX_BUFFER_REPOS - load_count):
        result.append({"interactive": False, "name": "repository_load", "priority": 5})
    if count_names(workload, {"wait_threadpool"}) < 1:
        result.append({"interactive": True, "name": "wait_threadpool", "priority": 999})
    if count_names(workload, {"force_quit"}) < 1:
        result.append({"interactive": True, "name": "force_quit", "priority": 1000})
    print("New workload:")
    pprint.pprint(result)
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
    handlers = {
        "cleanup": cleanup,
        "prompt_quit": prompt_quit,
        "wait_threadpool": wait_threadpool,
        "force_quit": force_quit,
    }
    handlers.update(addrepo_handlers())
    handlers.update(processrepo_handlers())
    handlers.update(submit_handlers())
    return handlers


def cleanup(context):
    """
    Task to remove a repository after processing
    """

    def handler():
        reponame = context.taskjson["reponame"]
        repository_map = get_json_value("repository_map", {})
        if reponame in repository_map:
            reposave = repository_map[reponame]
            remove_repo_for(reponame, reposave, confirm=False)
        context.controller.add(
            {"name": "prompt_quit", "interactive": True, "priority": 10}
        )

    return handler


def wait_threadpool(context):
    """
    Wait until all an input task is added to the queue or all tasks have
    completed processing.
    """

    def handler():
        with context.controller.condition:
            while True:
                tasks_empty = context.controller.tasks_empty()
                top = context.controller.peek_input()
                if top["priority"] < 999:
                    context.controller.add(
                        {
                            "interactive": True,
                            "name": "wait_threadpool",
                            "priority": 999,
                        }
                    )
                    return
                if tasks_empty:
                    print("All tasks complete and no new input - quiting.")
                    context.controller.quit()
                    return
                context.controller.condition.wait(60)

    return handler


def prompt_quit(context):
    """
    Interactive request to quit
    """

    def handler():
        if context.interaction.check_quit(context.controller):
            context.controller.quit()
        else:
            context.controller.add(
                {"name": "repository_load", "interactive": False, "priority": 5}
            )

    return handler


def force_quit(context):
    """
    Force quit
    """

    def handler():
        context.controller.quit()

    return handler


def clear_work_queue(target):  # pylint: disable=unused-argument
    """
    Remove the current workload to reset
    """
    key = "multiworker_workload"
    set_json_value(key, [])


def show_work_queue(target):  # pylint: disable=unused-argument
    """
    Dispay the current workload queue
    """
    key = "multiworker_workload"
    pprint.pprint(get_json_value(key, deflt=[]))


class Interaction:
    """
    Base kinds of interaction
    """

    def get_confirmation(self, message="Do you want to continue", defaultval=True):
        """
        Simple confirmation
        """
        raise NotImplementedError()

    def get_input(self, message):
        """
        Get arbitrary text input
        """
        raise NotImplementedError()

    def make_choice(self, choices, message="Please make a selection."):
        """
        Get arbitrary choice input
        """
        raise NotImplementedError()

    def check_quit(self, controller):
        """
        Check if time to quit
        """
        raise NotImplementedError()

    def send(self, message):
        """
        Display a message to the user
        """
        raise NotImplementedError()


class KeyboardInteraction(Interaction):
    """
    Terminal keyboard interaction
    """

    def get_input(self, message):
        return _input.get_input(message=message)

    def check_quit(self, controller):
        return _input.get_confirmation(message="Do you want to quit?", defaultval=True)

    def get_confirmation(self, message="Do you want to continue", defaultval=True):
        return _input.get_confirmation(message=message, defaultval=defaultval)

    def make_choice(self, choices, message="Please make a selection."):
        """
        Get arbitrary choice input
        """
        return _input.make_choice(choices=choices, message=message)

    def send(self, message):
        print(message)


def main(target):
    """
    Main task should load from storage, update the workload and pass off
    handling to the controller and on termination save the result
    """
    multiworker_core(KeyboardInteraction(), target)


def multiworker_core(interaction, target):
    """
    Support for different kinds of interaction with multiple worker processing
    """
    key = "multiworker_workload"
    workload = get_json_value(key, deflt=[])
    workload = update_workload(workload)
    handlers = get_handlers()
    input_queue = get_input_queue()
    threadpool = get_pool(handlers)
    controller = Controller(
        handlers=handlers, input_queue=input_queue, threadpool=threadpool, target=target
    )
    for task in workload:
        controller.add(task)
    result = controller.run(interaction)
    set_json_value(key, result)
