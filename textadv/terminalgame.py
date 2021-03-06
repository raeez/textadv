# terminalgame.py

# Contains an object which can be used for io in the terminal.

import re
import textwrap

class TerminalGameIO(object) :
    """This class may be replaced in the GameContext by anything which
    implements the following two methods."""
    def __init__(self) :
        self.data = []
    def get_input(self, prompt=">") :
        self.flush()
        return raw_input("\n"+prompt + " ")
    def write(self, *data) :
        self.data.extend(data)
    def set_status_var(self, *args, **kwargs) :
        pass
    def flush(self) :
        d = " ".join(self.data)
        self.data = []
        d = " ".join(re.split("\\s+", d))
        d = re.sub('<[^<]+?>', '', d) # strip out html
        pars = d.replace("[newline]", "\n\n").replace("[break]", "\n").replace("[indent]","  ").split("\n")
        wrapped = ["\n".join(textwrap.wrap(p)) for p in pars]
        print "\n".join(wrapped),
        return
        paragraphs = re.split("\n\\s*\n", " ".join(data))
        to_print = []
        for p in paragraphs :
            fixed = " ".join([l.strip() for l in p.strip().split("\n")])
            one_p = []
            for f in fixed.split("<br>") :
                one_p.append("\n".join(textwrap.wrap(f)))
            to_print.append("\n".join(one_p))
        print string.replace("\n\n".join(to_print)+"\n", "&nbsp;", " ")
