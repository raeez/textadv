# utilities.py
#
# some utilities like text processing

import string
import itertools
import re
from textadv.core.patterns import PVar
from textadv.gamesystem.relations import In, Has

def list_append(xs) :
    return itertools.chain.from_iterable(xs)

def serial_comma(nouns, conj="and", comma=",", force_comma=False) :
    conj = " " + conj + " "
    if len(nouns) == 1 :
        return nouns[0]
    elif len(nouns) == 2 :
        if force_comma :
            return nouns[0] + comma + conj + nouns[1]
        else :
            return nouns[0] + conj + nouns[1]
    else :
        comma_sp = comma + " "
        return comma_sp.join(nouns[:-1]) + comma + conj + nouns[-1]

def is_are_list(context, objs, conj="and", prop="indefinite_name") :
    objs = [context.world[o][prop] for o in objs]
    if len(objs) == 0 :
        return "is nothing"
    elif len(objs) == 1 :
        return "is "+objs[0]
    else :
        return "are "+serial_comma(objs, conj=conj)

DIRECTION_INVERSES = {"north" : "south",
                      "south" : "north",
                      "east" : "west",
                      "west" : "east",
                      "up" : "down",
                      "down" : "up",
                      "in" : "out",
                      "out" : "in"}

def inverse_direction(direction) :
    return DIRECTION_INVERSES[direction]

def remove_obj(obj) :
    """Removes an object from play by moving it to nowhere."""
    obj.world.delete("relations", Has(PVar("x"), obj))
    obj.world.delete("relations", In(obj, PVar("x")))


###
### Object interface for fancy strings
###

# "You aren't able to pick up the ball."
# "He isn't able to pick up the ball."
# str_with_objs("[as $actor]{You} {aren't} able to pick up [get $object definite_name][endas].",
#               actor=actor, object=the_ball)

# "The door is currently [if [get door open]]open[else]closed[endif]."

# see eval_str for more information.

def str_with_objs(input, **kwarg) :
    newkwarg = dict()
    for key, value in kwarg.iteritems() :
        if type(value) == str :
            newkwarg[key] = value
        else :
            newkwarg[key] = value.id
    return string.Template(input).safe_substitute(newkwarg)

def as_actor(input, actor) :
    if type(actor) != str :
        actor = actor.id
    return "[as %s]%s[endas]" % (actor, input)


###
### Implementation of fancy string parser.  Used in a Context
###

def _escape_str(match) :
    return "[char %r]" % ord(match.group())

def escape_str(input) :
    """Just makes it so the string won't be evaluated oddly in eval_str."""
    return re.sub(r"\[|\]|\$|{|}", _escape_str, input)

def eval_str(input, context) :
    """Takes a string and evaluates constructs to reflect the state of
    the game world.
    
    [get $objname $property] => context.world[objname][property]
    [if $pred]$cons[endif]
    [if $pred]$cons[else]$alt[endif]
    [true]
    [false]
    [not $logic]
    [char num] => chr(num)
    {$word} => rewrites $word to make sense in the current context
    """
    # first we need to parse the string
    parsed, i = _eval_parse(input)
    code = ["append"]
    i = 0
    try :
        while i < len(parsed) :
            i, val = _collect_structures(parsed, i)
            code.append(val)
    except MalformedException as x :
        print "eval_str: Offending input is"
        print input
        raise x
    evaled = _eval(code, context, context.actor)
    return "".join([str(o) for o in evaled])

def _eval_parse(input, i=0, in_code=False) :
    """Pulls out [] and {} expressions, labeling them as such.  Also
    makes it so [] expressions split by whitespace."""
    parsed = []
    j = i
    while i < len(input) :
        if input[i] == "[" :
            if i > j :
                parsed.append(input[j:i])
            parsed2, i2 = _eval_parse(input, i+1, in_code=True)
            parsed.append(("code", parsed2))
            i = i2
            j = i
        elif input[i] == "]" :
            if i > j :
                parsed.append(input[j:i])
            return (parsed, i+1)
        elif input[i] == "{" :
            if i > j :
                parsed.append(input[j:i])
            start = i + 1
            i += 1
            while input[i] != "}" : i += 1
            parsed.append(("reword", input[start:i].split("|")))
            i += 1
            j = i
        elif input[i] == "}" :
            raise Exception("Unmatched '}' in "+input)
        elif in_code and input[i] in string.whitespace :
            if i-1 > j :
                parsed.append(input[j:i])
            i += 1
            j = i
        else :
            i += 1
    if j < i :
        parsed.append(input[j:i])
    return (parsed, i)

def _is_else(expr) :
    return type(expr) == tuple and expr[0] == "code" and expr[1][0] == "else"
def _is_endif(expr) :
    return type(expr) == tuple and expr[0] == "code" and expr[1][0] == "endif"
def _is_endas(expr) :
    return type(expr) == tuple and expr[0] == "code" and expr[1][0] == "endas"

class MalformedException(Exception) :
    pass

def _collect_structures(expr, i=0) :
    """Finds [if ...]...[else]...[endif] and [as ...]...[endas]
    structures."""
    if type(expr[i]) == str :
        return i+1, ("lit", expr[i])
    else :
        t, val = expr[i]
        if t == "reword" :
            return i+1, expr[i]
        elif t == "code" :
            if val[0] == "if" :
                try :
                    _i, pred = _collect_structures(val,1)
                    conses = ("if", pred, ["append"], ["append"])
                    consind = 2
                    i += 1
                    while not _is_endif(expr[i]) :
                        if _is_else(expr[i]) :
                            # start making alternate action
                            consind += 1
                            i += 1
                        else :
                            i, v = _collect_structures(expr, i)
                            conses[consind].append(v)
                    return i+1, conses
                except IndexError :
                    raise MalformedException("Malformed if statement.")
            if val[0] == "as" :
                try :
                    actor = val[1]
                    content = ["append"]
                    i += 1
                    while not _is_endas(expr[i]) :
                        i, v = _collect_structures(expr, i)
                        content.append(v)
                    return i+1, ["as", actor, content]
                except IndexError :
                    raise MalformedException("Malformed as statement.")
            else :
                out = [val[0]]
                j = 1
                while j < len(val) :
                    j, o = _collect_structures(val,j)
                    out.append(o)
                return i+1, out
        else :
            raise Exception("What kind of structure is this?", expr)

def _eval(expr, context, actor) :
    if expr[0] == "lit" :
        return expr[1]
    elif expr[0] == "reword" :
        return reword(expr[1], context, actor)
    elif expr[0] == "if" :
        res = _eval(expr[1], context, actor)
        # res might be the empty list
        if res and res[0] :
            return _eval(expr[2], context, actor)
        else :
            return _eval(expr[3], context, actor)
    elif expr[0] == "as" :
        return _eval(expr[2], context, expr[1])
    elif _str_eval_functions.has_key(expr[0]) :
        try :
            args = [_eval(x, context, actor) for x in expr[1:]]
            return _str_eval_functions[expr[0]](context, *args)
        except TypeError :
            print "String evaluator tried",expr
            raise
    else :
        raise Exception("Unknown expr",expr)

_str_eval_functions = {}
def add_str_eval_func(name) :
    def _add_str_eval_func(f) :
        _str_eval_functions[name] = f
        return f
    return _add_str_eval_func

# treat args as lists, append args
_str_eval_functions["append"] = lambda context, *x : itertools.chain.from_iterable(x)
# evals to true
_str_eval_functions["true"] = lambda context : [True]
# evals to false
_str_eval_functions["false"] = lambda context : [False]
# negates arg
_str_eval_functions["not"] = lambda context, x : [not x[0]]
# get ob prop => gets property from object
_str_eval_functions["get"] = lambda context, ob, prop : [context.world[ob][prop]]
# gets definite_name property
_str_eval_functions["the"] = lambda context, ob : [context.world[ob]["definite_name"]]
# gets indefinite_name property
_str_eval_functions["a"] = lambda context, ob : [context.world[ob]["indefinite_name"]]
# gets definite_name property, capitalized
_str_eval_functions["The"] = lambda context, ob : [_cap(context.world[ob]["definite_name"])]
# gets indefinite_name property, capitalized
_str_eval_functions["A"] = lambda context, ob : [_cap(context.world[ob]["indefinite_name"])]
# capitalizes a word
_str_eval_functions["cap"] = lambda context, s : [_cap(s[0])+s[1:]]
# number to char
_str_eval_functions["char"] = lambda context, s : [chr(int(s))]

# gets subject_pronoun property
_str_eval_functions["he"] = lambda context, ob : [context.world[ob]["subject_pronoun"]]
# gets object_pronoun property
_str_eval_functions["him"] = lambda context, ob : [context.world[ob]["object_pronoun"]]
# gets subject_pronoun property, capitalized
_str_eval_functions["He"] = lambda context, ob : [_cap(context.world[ob]["subject_pronoun"])]
# gets object_pronoun property, capitalized
_str_eval_functions["Him"] = lambda context, ob : [_cap(context.world[ob]["object_pronoun"])]

def _cap(string) :
    return string[0].upper()+string[1:]

# if no first object, then default to actor (so one can write [when in
# box] instead of [when actor in box]
@add_str_eval_func("when")
def _str_eval_fn_when(context, *obs) :
    if len(obs) == 2 :
        ob1, relation, ob2 = context.actor, obs[0], obs[1]
    else :
        ob1, relation, ob2 = obs
    relation = relation.lower()
    return [context.world[ob1].s_R_x(_str_eval_fn_when_relations[relation], ob2)]

# concatenates list of objects, getting indefinite names, and puts proper is/are in front
@add_str_eval_func("is_are_list")
def _str_eval_fn_is_are_list(context, *obs) :
    return [is_are_list(context, list_append(o[0] for o in obs))]

_str_eval_fn_when_relations = {"in" : In, "has" : Has}
def str_eval_register_relation(code, relation) :
    _str_eval_fn_when_relations[code] = relation

###
### Reworder.  Makes is/are work out depending on context
###

# Rule: when doing {word}, write everything as if there was some guy
# named Bob doing the actions.  Bracket every word that should change
# depending on context.  We assume that if the actor of the context
# did the action, it should be reported in the second person.
#
# flags are specified by {word|flag1|flag2|...}
# flags:
# cap - capitalizes word (useful for start of sentences)
# obj - makes "bob" be the object of a sentence

def reword(args, context, actor) :
    word = args[0]
    flags = args[1:]
    is_me = context.actor == actor
    capitalized = word[0] in string.uppercase
    rewritten = _reword(word.lower(), flags, context.world[actor], is_me)
    if capitalized or "cap" in flags:
        return _cap(rewritten)
    else :
        return rewritten

# These are for going from 3rd person to 2nd person.  They are
# exceptions to the rule that 2nd person to 3rd person adds an 's' to
# the end.
_reword_replacements = {"is" : "are",
                        "has" : "have",
                        "hasn't" : "haven't",
                        "does" : "do",
                        "doesn't" : "don't",
                        "can" : "can",
                        "can't" : "can't",
                        "switches" : "switch",
                        }

def _reword(word, flags, actor, is_me) :
    if is_me :
        if word == "he" :
            return actor["subject_pronoun_if_me"]
        elif word == "him" :
            return actor["object_pronoun_if_me"]
        elif word == "bob" :
            if "obj" in flags :
                return actor["object_pronoun_if_me"]
            else :
                return actor["subject_pronoun_if_me"]
        elif word == "bob's" :
            return actor["possessive_if_me"]
        elif _reword_replacements.has_key(word) :
            return _reword_replacements[word]
        else : # assume it's a verb, take off s
            return word[0:-1]
    else :
        if word == "he" :
            return actor["subject_pronoun"]
        elif word == "him" :
            return actor["object_pronoun"]
        elif word == "bob" :
            return actor["printed_name"]
        elif word == "bob's" :
            return actor["possessive"]
        else : # we assume the word should stay as-is
            return word