"""
Load, save and pass off handling to the controller
"""

from meticulous._addrepo import interactive_add_one_new_repo
from meticulous._cleanup import remove_repo_for
from meticulous._controller import Controller
from meticulous._input import get_confirmation
from meticulous._input_queue import get_input_queue
from meticulous._processrepo import interactive_task_collect_nonwords
from meticulous._storage import get_json_value, set_json_value
from meticulous._submit import fast_prepare_a_pr_or_issue_for
from meticulous._threadpool import get_pool


def update_workload(workload):
    """
    Ensure the minimum number of repository tasks are present.
    """
    result = list(workload)
    load_count = count_names(workload, {"repository_load"})
    active_count = len(get_json_value("repository_map", {}))
    for _ in range(1 - active_count - load_count):
        result.append({"interactive": True, "name": "repository_load", "priority": 40})
    if count_names(workload, {"wait_threadpool"}) < 1:
        result.append({"interactive": True, "name": "wait_threadpool", "priority": 999})
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
        "collect_nonwords": collect_nonwords,
        "submit": submit,
        "cleanup": cleanup,
        "prompt_quit": prompt_quit,
        "wait_threadpool": wait_threadpool,
        "force_quit": force_quit,
    }


def repository_load(context):
    """
    Task to pull a repository
    """

    def handler():
        target = context.controller.target
        reponame = interactive_add_one_new_repo(target)
        context.controller.add(
            {
                "name": "collect_nonwords",
                "interactive": True,
                "priority": 50,
                "reponame": reponame,
            }
        )

    return handler


def collect_nonwords(context):
    """
    Task to collect nonwords from a repository until a typo is found or the
    repository is clean
    """

    def handler():
        target = context.controller.target
        reponame = context.taskjson["reponame"]
        if reponame in get_json_value("repository_map", {}):
            interactive_task_collect_nonwords(reponame, target)
        context.controller.add(
            {
                "name": "submit",
                "interactive": True,
                "priority": 60,
                "reponame": reponame,
            }
        )

    return handler


def submit(context):
    """
    Task to submit a pull request/issue
    repository is clean
    """

    def handler():
        reponame = context.taskjson["reponame"]
        repository_saves = get_json_value("repository_saves", {})
        if reponame in repository_saves:
            reposave = repository_saves[reponame]
            fast_prepare_a_pr_or_issue_for(reponame, reposave)
        context.controller.add(
            {
                "name": "cleanup",
                "interactive": True,
                "priority": 70,
                "reponame": reponame,
            }
        )

    return handler


def cleanup(context):
    """
    Task to collect nonwords from a repository until a typo is found or the
    repository is clean
    """

    def handler():
        reponame = context.taskjson["reponame"]
        repository_map = get_json_value("repository_map", {})
        if reponame in repository_map:
            reposave = repository_map[reponame]
            remove_repo_for(reponame, reposave, confirm=False)
        context.controller.add(
            {"name": "prompt_quit", "interactive": True, "priority": 40}
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
        if get_confirmation(message="Do you want to quit?", defaultval=True):
            context.controller.quit()
        else:
            context.controller.add(
                {"name": "repository_load", "interactive": True, "priority": 40}
            )

    return handler


def force_quit(context):
    """
    Force quit
    """

    def handler():
        context.controller.quit()

    return handler


def main(target):
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
        handlers=handlers, input_queue=input_queue, threadpool=threadpool, target=target
    )
    for task in workload:
        controller.add(task)
    result = controller.run()
    set_json_value(key, result)
