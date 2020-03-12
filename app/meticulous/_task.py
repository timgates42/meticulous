"""
Classes for managing receiving user input
"""

class Task(object):
    def noninteractive(self):
        """
        Perform any noninteractive actions for the task and return as soon as
        user input is required.`
        """
    def collect_input(self):
        """
        Opportunity for a task to collect user input
        """

def needs_interactive(func):
    """
    Decorator to simplify converting a function into a task generator with a
    noninteractive section followed by interaction and then noniteraction
    followup.
    """
    interaction = []
    result = []
    stop = [False]
    iterobj = iter(func(result))
    class IterTask(Task):
        def noninteractive(self):
            """
            Call the first noninteractive section
            """
            del interaction[:]
            try:
                interaction.append(next(iterobj))
            except StopIteration:
                stop[0] = True
        def collect_input(self):
            """
            Call the interaction if provided
            """
            del result[:]
            for elem in interaction:
                if elem:
                    result.append(elem())
    while not stop[0]:
        yield IterTask()


