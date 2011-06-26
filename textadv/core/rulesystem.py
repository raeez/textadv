# rulesystem.py
#
# rule- and event-based programming
#
# What's here:
# Exceptions: NotHandled, AbortAction, ActionHandled, MultipleResults, FinishWith
# Classes: ActionTable, PropertyTable, EventTable

from patterns import NoMatchException, AbstractPattern, BasicPattern

class AbortAction(Exception) :
    """Raised when a handler wants to stop the action from being
    handled anymore.  Used to signal that something bad happened.
    Stores arguments so they may be used by the caller."""
    def __init__(self, *args, **kwargs) :
        self.args = args
        self.kwargs = kwargs
class ActionHandled(Exception) :
    """Raised when a handler wants to stop the action from being
    handled anymore.  Used to signal that it's ok we're done."""
    pass

class MultipleResults(Exception) :
    """Raised when a handler has multiple values to return (for
    ActionTables with accumulators)."""
    pass

class FinishWith(Exception) :
    """Raised when a handler wants to return multiple values and also
    use the accumulated values (ActionHandled ignores the accumulated
    values)."""
    pass

class NotHandled(Exception) :
    """Raised when an event wants to prematurely exit.  Used to signal
    skipping without affecting anything."""
    pass

def handler_requires(b) :
    """A predicate which simply raises NotHandled if the argument is
    false."""
    if not b :
        raise NotHandled()

class PropertyTable(object) :
    """Represents a table of properties whose keys are patterns (for
    instance Description("myobj")).  Executes in reverse definition
    order, and the first successful result is returned."""
    def __init__(self) :
        self.properties = dict() # dict for some optimization
        self.default_handler = None
    def set_property(self, item, value, call=False) :
        if not isinstance(item, AbstractPattern) :
            raise Exception("The only properties may be AbstractPatterns.")
        if not self.properties.has_key(item.file_under()) :
            self.properties[item.file_under()] = [(item, value, call)]
        else :
            self.properties[item.file_under()].insert(0, (item, value, call))
    def __setitem__(self, item, value) :
        self.set_property(item, value)
    def get_property(self, item, data) :
        if not isinstance(item, BasicPattern) :
            raise Exception("The only properties may be BasicPatterns.")
        if not self.properties.has_key(item.file_under()) :
            raise KeyError(item)
        for key,value,call in self.properties[item.file_under()] :
            try :
                matches = key.match(item, data=data)
                if call :
                    for k,v in data.iteritems() :
                        matches[k] = v
                    return value(**matches)
                else :
                    return value
            except NoMatchException : # on these exceptions, just try next one
                pass
            except NotHandled :
                pass
        if self.default_handler is None :
            raise KeyError(item)
        else :
            return self.default_handler(item, world)
    def handler(self, item) :
        """This is a decorator to add a function which should be
        called when getting a property."""
        def __handler(f) :
            self.set_property(item, f, call=True)
            return f
        return __handler
    def dump(self) :
        for props in self.properties.itervalues() :
            for item, value, call in props :
                if call :
                    print repr(item)+" calls "+repr(value)
                else :
                    print repr(item)+" = "+repr(value)

class ActionTable(object) :
    """Runs the actions one at a time until an AbortAction is raised
    or there are no more actions.  Actions are run in the order they
    were added to the ActionTable.  Accumulator is a function which
    takes the list of results to make a return value.  By default it's
    just the identity function.  Unlike the other tables in the
    rulesystem, the functions are not selected by a pattern."""
    def __init__(self, accumulator=None, reverse=False) :
        self.actions = []
        self.accumulator = accumulator or (lambda x : x)
        self.reverse = reverse
    def notify(self, args, data) :
        acc = []
        for f in self.actions :
            try :
                acc.append(f(*args, **data))
            except NotHandled :
                pass
            except ActionHandled as ix :
                return self.accumulator(ix.args)
            except MultipleResults as ix :
                acc.extend(ix.args)
            except FinishWith as ix :
                return self.accumulator(acc + ix.args)
            except AbortAction :
                return None
        return self.accumulator(acc)
    def add_handler(self, item) :
        """A function (which can be used as a decorator) which adds
        the function to the table."""
        if self.reverse :
            self.actions.insert(0, item)
        else :
            self.actions.append(item)
        return item

class EventTable(object) :
    """The action table is a bunch of "actions" which are all
    functions which take an event and supplementary data.  The
    variables are applied to each function.  If the action doesn't
    care about the event, then it may raise NotHandled.  If an event
    wants to stop all notification, then it should raise AbortAction.

    Actions are executed in reverse order.  That way, actions which
    are given later (and which are assumed to be more specific) get
    executed first."""
    def __init__(self, accumulator=None, reverse=True) :
        self.actions = []
        self.accumulator = accumulator or (lambda x : x)
        self.reverse = reverse
    def add_handler(self, pattern, f) :
        if self.reverse :
            self.actions.insert(0, (pattern, f))
        else :
            self.actions.append((pattern, f))
    def notify(self, event, data) :
        accum = []
        for (pattern, f) in self.actions :
            try :
                matches = pattern.match(event, data=data)
                for k,v in data.iteritems() :
                    matches[k] = v
                accum.append(f(**matches))
            except NoMatchException :
                pass
            except NotHandled :
                pass
            except ActionHandled as ix :
                return self.accumulator(ix.args)
            except MultipleResults as ix :
                acc.extend(ix.args)
            except FinishWith as ix :
                return self.accumulator(acc + ix.args)
            except AbortAction :
                return None
        return self.accumulator(accum)

##
## A class for holding ActionTables (see World)
##

class ActionHelperObject(object) :
    def __init__(self, handler) :
        self.__handler__ = handler
    def __getattr__(self, name) :
        def _caller(*args) :
            return self.__handler__.call(name, *args)
        return _caller

###
### Tests
###

import unittest

class TestEvents(unittest.TestCase) :
    class PEnters(BasicPattern) :
        def __init__(self, actor, place) :
            self.args = [actor, place]
    class PBefore(BasicPattern) :
        def __init__(self, event) :
            self.args = [event]
    class PAfter(BasicPattern) :
        def __init__(self, event) :
            self.args = [event]

    def test_table(self) :
        table = ActionTable()
        when = makeEventPatternDecorator(table)
        test = []
        x = PVar("x")
        data = dict()
        data[1] = 1
        
        @when(self.PEnters("kyle", x))
        def action1(x, data) :
            data[1] += 1
            test.append("action1:"+x)

        @when(self.PAfter(self.PEnters("kyle", x)))
        @when(self.PBefore(self.PEnters("kyle", x)))
        def action2(x, data) :
            data[1] += 1
            test.append("action2:"+x)

        table.notify(self.PBefore(self.PEnters("kyle", "vestibule")), data=data)
        table.notify(self.PEnters("kyle", "vestibule"), data=data)
        table.notify(self.PAfter(self.PEnters("kyle", "vestibule")), data=data)
        self.assertEqual(test,
                         ["action2:vestibule","action1:vestibule", "action2:vestibule"])

    def test_stopping_test(self) :
        table = ActionTable()
        when = makeEventPatternDecorator(table)
        test = []
        x = PVar("x")
        
        @when(self.PEnters("kyle", x))
        def action1(x) :
            raise AbortAction()
            test.append("action1:"+x)

        @when(self.PAfter(self.PEnters("kyle", x)))
        @when(self.PBefore(self.PEnters("kyle", x)))
        def action2(x) :
            test.append("action2:"+x)

        try :
            table.notify(self.PBefore(self.PEnters("kyle", "vestibule")))
            table.notify(self.PEnters("kyle", "vestibule"))
            table.notify(self.PAfter(self.PEnters("kyle", "vestibule")))
        except AbortAction :
            self.assertEqual(test, ["action2:vestibule"])

if __name__=="__main__" :
    unittest.main(verbosity=2)
