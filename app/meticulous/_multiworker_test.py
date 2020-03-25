"""
Testing for multithread management
"""

from unittest import mock

from meticulous._multiworker import main, update_workload


@mock.patch("meticulous._multiworker.get_json_value")
def test_empty_load(get_mock):
    """
    Check updating an empty task list adds 3 repository load tasks
    """
    # Setup
    initial = []
    get_mock.return_value = {}
    # Exercise
    result = update_workload(initial)
    # Verify
    check = [1 for elem in result if elem["name"] == "repository_load"]
    assert len(check) == 4  # noqa=S101 # nosec


@mock.patch("meticulous._multiworker.get_json_value")
@mock.patch("meticulous._multiworker.set_json_value")
@mock.patch("meticulous._controller.Controller.run")
def test_main(run_mock, set_mock, get_mock):
    """
    Main task should load from storage, update the workload and pass off
    handling to the controller and on termination save the result
    """
    # Setup
    final = []

    def saver(_, workload):
        final.extend(workload)
        return workload

    run_mock.return_value = [{}]
    get_mock.return_value = []
    set_mock.side_effect = saver
    # Exercise
    main(None)
    # Verify
    assert len(final) > 0  # noqa=S101 # nosec
