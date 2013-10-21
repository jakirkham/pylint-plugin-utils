

class NoSuchChecker(Exception):

    def __init__(self, checker_class):
        self.message = "Checker class %s was not found" % checker_class

    def __repr__(self):
        return self.message


def get_checker(linter, checker_class):
    for checker in linter.get_checkers():
        if isinstance(checker, checker_class):
            return checker
    raise NoSuchChecker(checker_class)


def augment_visit(linter, checker_method, augmentation):
    """
    Augmenting a visit enables additional errors to be raised (although that case is
    better served using a new checker) or to suppress all warnings in certain circumstances.

    Augmenting functions should accept a 'chain' function, which runs the checker method
    and possibly any other augmentations, and secondly an Astroid node. "chain()" can be
    called at any point to trigger the continuation of other checks, or not at all to
    prevent any further checking.
    """
    checker = get_checker(linter, checker_method.im_class)

    old_method = getattr(checker, checker_method.__name__)

    def augment_func(node):
        def chain():
            old_method(node)
        augmentation(chain, node)

    setattr(checker, checker_method.__name__, augment_func)


class Suppress(object):

    def __init__(self, linter):
        self._linter = linter
        self._suppress = []
        self._messages_to_append = []

    def __enter__(self):
        self._orig_add_message = self._linter.add_message
        self._linter.add_message = self.add_message
        return self

    def add_message(self, *args):
        self._messages_to_append.append(args)

    def suppress(self, msg_id):
        self._suppress.append(msg_id)

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._linter.add_message = self._orig_add_message
        for to_append in self._messages_to_append:
            if to_append[0] in self._suppress:
                continue
            self._linter.add_message(*to_append)


def supress_message(linter, checker_method, message_id, test_func):
    """
    This wrapper allows the suppression of a message if the supplied test function
    returns True. It is useful to prevent one particular message from being raised
    in one particular case, while leaving the rest of the messages intact.
    """
    def do_suppress(chain, node):
        with Suppress(linter) as s:
            if test_func(node):
                s.suppress(message_id)
            chain()
    augment_visit(linter, checker_method, do_suppress)