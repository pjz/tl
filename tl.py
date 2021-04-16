#!/usr/bin/python
"""

tl.py - commandline todolist, based on ideas in todo.sh
Copyright 2007, Paul Jimenez
Released under the GPL

TODO: 
    archive
        Move done items from todo.txt to done.txt
    mvsub NUMBER1 [NUMBER2]
        Move subtask NUMBER1 to be under subtask NUMBER2 instead.
        If NUMBER2 isn't specified, move NUMBER1 to the top level.
    replace NUMBER "UPDATED TODO"
        Replaces todo NUMBER with UPDATED TODO.
    remdup
    dedup
    rmdup
        Removes exact duplicate lines from todo.txt.
    report
        Adds the number of open todo's and closed done's to report.txt.
    make rm/del take multiple arguments
    add 'notes' for tasks:
      note NUMBER "NOTE TO ADD"
          Append NOTE TO ADD to the note for NUMBER.
      show NUMBER
          Show task NUMBER, including notes and subtasks.
      rmnote NUMBER
          Remove the note from NUMBER

"""

import os
import re
import sys
import time
import getopt

if sys.version_info[0] < 2 or sys.version_info[1] < 4:
    print "%s requires python 2.4 or better" % sys.argv[0]
    sys.exit(0)

TODODIR = "/home/pj/.todo/"
TODOFILE = TODODIR + "todo.txt"
DONEFILE = TODODIR + "done.txt"
REPORTFILE = TODODIR + "report.txt"

PRIORITY_COLOR = {
  None : '\033[0m', # default
  'A' : "\033[1;31m", # bright red
  'B' : "\033[1;34m", # bright blue
#  'X' : "\033[1;30m"   # black
#  'X' : "\033[1;31m"   # red
#  'X' : "\033[1;32m"   # green
#  'X' : "\033[1;33m"   # brown
#  'X' : "\033[1;34m"   # blue
#  'X' : "\033[1;35m"   # purple
#  'X' : "\033[1;36m"   # cyan
#  'X' : "\033[0;37m"   # light grey
#  'X' : "\033[1;30m"   # grey
#  'X' : "\033[1;31m"   # bright red
#  'X' : "\033[1;32m"   # bright green
#  'X' : "\033[1;33m"   # yellow
#  'X' : "\033[1;34m"   # bright blue
#  'X' : "\033[1;35m"   # bright purple
#  'X' : "\033[1;36m"   # bright cyan
#  'Z' : "\033[1;37m"   # white
}


class Task:

    doneRegex = re.compile("x (\d\d\d\d-\d\d-\d\d) ")
    prioRegex = re.compile("\(([A-Za-z])\) ")

    def __init__(self, taskline):
        self.subtasks = []
        self.depth = 0
        self.done = None
        donematch = Task.doneRegex.match(taskline)
        if donematch is not None:
            self.done = donematch.group(1)
            taskline = taskline[3+len(self.done):]
        self.priority = None
        priomatch = Task.prioRegex.match(taskline)
        if priomatch is not None:
            self.priority = priomatch.group(1).upper()
            taskline = taskline[4:]
        self.depth = self._depth(taskline)
        self.text = taskline.strip()
        self.tasknum = -1
    
    def _depth(self, taskline):
        depth = 0
        for c in taskline:
            if c != " ": return depth
            depth += 1
        return 0

    def __str__(self):
        s = ""
        if self.done is not None:
            s += "x "+self.done+" "
        if self.priority is not None: 
            s = "(%s) " % self.priority.upper()
        s += " " * self.depth
        s += self.text
        s += os.linesep
        for t in self.subtasks:
           s += str(t)
        return s

    def setTasknum(self, n):
        self.tasknum = n
        i = 1
        for t in self.subtasks:
            t.setTasknum("%s.%d" % (n, i))
            i += 1

    def allTasks(self):
        toret = [ self ]
        for s in self.subtasks:
            toret += s.allTasks()
        return toret

    def _add(self, task, subsection=[]):
        if subsection == []:
            self.subtasks.append(task)
        else:
            self.subtasks[subsection[0]].add(task, subsection[1:])

    def add(self, task, subsection=''):
        if len(subsection) < 1:
            self.subtasks.append(task)
        else:
            parts = subsection.split('.',1)
            self.subtasks[int(parts[0])-1].add(task, '.'.join(parts[1:]))

    def setDone(self):
        self.done = time.strftime("%Y-%m-%d", time.localtime())
        for s in self.subtasks:
            if not s.done:
                s.setDone()

    def setPriority(self, p, recursive=False):
        self.priority = p
        if recursive:
            for s in self.subtasks:
                s.setPriority(p, recursive)

    def __getitem__(self, n):
        if type(n) == type(0):
            return self.subtasks[n]
        elif n == 'text':
            return self.text
        elif n == 'self':
            return self
        elif n == 'priority':
            if self.priority is not None:
               return "("+self.priority+")"
            else:
               return ""
        elif n == 'indent':
            return " " * self.depth
        elif n == 'color':
            try:
                return PRIORITY_COLOR[self.priority]
            except:
                return PRIORITY_COLOR[None]
        elif n == 'tasknum':
            return self.tasknum
        elif n == 'done':
            if self.done is not None:
                return "x "+self.done
            else:
                return ""



    def __setitem__(self, n, v):
        self.subtasks[n] = v


class TaskList(Task):

    def __init__(self):
        self.subtasks = []
        self.depth = -1
        self.priority = -1
        self.text = ''

    def __str__(self):
        return "".join([str(t) for t in self.subtasks])

    def lookup(self, subtask):
        parts = [ int(i) for i in subtask.split('.') ]
        cur = self.subtasks
        for i in parts:
            cur = cur[i-1]
        return cur

    def load(self, filename):
        if not os.path.isfile(filename):
            return
        count = []
        lastdepth = -1
        for line in file(filename):
            line = line.rstrip()
            if line.strip() == '': continue # skip blank lines            
            newtask = Task(line)
            if newtask.depth > lastdepth:
                lastdepth += 1
                count.append(1)
            elif newtask.depth == lastdepth:
                count[-1] += 1
            elif newtask.depth < lastdepth:
                lastdepth = newtask.depth
                count = count[:lastdepth + 1]
                count[-1] += 1
            tasknum = '.'.join([str(i) for i in count[:-1]])
            self.add(newtask, tasknum)

    def allTasks(self):
        return Task.allTasks(self)[1:]

    def setTasknum(self, n=''):
        for i in range(len(self.subtasks)):
            self.subtasks[i].setTasknum(str(i+1))

    def save(self, filename):
        outfile = open(filename, "w")
        outfile.write(str(self))
        outfile.close()



def showUsage():
    print """
  Usage: %s [action] [params...]

  Actions:
    add "THING I NEED TO DO"
        Add a new (top-level) task, THING I NEED TO DO
    addsub NUMBER "STEP TO DO THING"
        Add STEP TO DO THING as a subtask of NUMBER
    append NUMBER "TEXT TO APPEND"
        Add TEXT TO APPEND to the end of task NUMBER
    del NUMBER
    rm NUMBER
        Delete todo NUMBER from todo.txt.  Note this deletes
        all subtasks of NUMBER as well.
    do NUMBER
    done NUMBER
        Mark todo NUMBER done in todo.txt.  Note this marks
        all subtasks of NUMBER done as well.
    ls [TERM] [[TERM]...]
        List all tasks that contain TERM(s), or all if no TERMs are specified
    ls -A
        List with just the first (deepest) subtask
    ls -a
        List with all subtasks [DEFAULT]
    ls -c
        List with colors [DEFAULT]
    ls -C
        List without colors
    ls -d
        List including done items [DEFAULT]
    ls -D
        List without including done items
    ls -I
        List without indented subtasks
    ls -i
        List with indented subtasks [DEFAULT]
    ls -N
        List without prepended numbers
    ls -n
        List with prepended numbers [DEFAULT]
    ls -p [PRIORITY]
        List sorted by priority PRIORITY. If PRIORITY isn't
        specified, list all prioritized items.
    ls -P
        List without priority [DEFAULT]
    pri [-R] NUMBER PRIORITY
        Sets the priority of NUMBER to PRIORITY.  Specifying -R sets that
        same priority on all subtasks recursively.


"""


def str2sub(s):
    return [ int(x) for x in s.split('.') ]

if __name__ == '__main__':
    
    if len(sys.argv) < 2:
        showUsage()
        sys.exit()

    cmd = sys.argv[1].lower()
    args = sys.argv[2:]

    tasklist = TaskList()    
    tasklist.load(TODOFILE)
    tasklist.setTasknum()

    if cmd == 'add':
        newtask = Task(' '.join(args))
        tasklist.add(newtask)
        tasklist.save(TODOFILE)
    elif cmd == 'addsub':
        task = tasklist.lookup(args[0])
        newtasktext = ' '.join(args[1:])
        newtask = Task(newtasktext)
        newtask.depth = task.depth + 1
        task.add(newtask)
        tasklist.save(TODOFILE)
    elif cmd == 'append':
        task = tasklist.lookup(args[0])
        task.text += ' ' + ' '.join(args[1:])
        tasklist.save(TODOFILE)
    elif cmd == 'replace':
        task = tasklist.lookup(args[0])
        task.text = ' '.join(args[1:])
        tasklist.save(TODOFILE)
    elif cmd in [ 'del', 'rm' ]:
        task = tasklist.lookup(args[0])
        for t in [tasklist] + tasklist.allTasks():
            if task in t.subtasks:
                t.subtasks.remove(task)
        tasklist.save(TODOFILE)
    elif cmd in [ 'do', 'done' ]:
        task = tasklist.lookup(args[0])
        task.setDone()
        tasklist.save(TODOFILE)
    elif cmd == 'pri':
        recursive = '-R' in args
        args = [ x for x in args if x not in [ '-R' ] ]
        task = tasklist.lookup(args[0])
        priority = args[1][0].upper()
        task.setPriority(priority, recursive)
        tasklist.save(TODOFILE)
    elif cmd == 'ls' or cmd == 'list':

        try:
            opts, searches = getopt.getopt(args, "aAcCdDiInNpP")
        except:
            showUsage()
            sys.exit()

        ogiven = [ o for o, a in opts ]
        showall = '-A' not in ogiven
        withcolor = '-C' not in ogiven
        withdone = '-D' not in ogiven
        withindent = '-I' not in ogiven
        withnum = '-N' not in ogiven
        withpri = '-p' in ogiven
        prisearch = ''
        if withpri and len(searches) > 0 and len(searches[0]) == 1:
                prisearch = searches[0].upper()
                searches = searches[1:]

        formstr = ''
        if withnum:
            # add 0 in case there's no tasks
            mlen = max([len(t.tasknum) for t in tasklist.allTasks()]+[0])
            formstr = " %(tasknum)"+str(mlen)+"s:"
        if withdone:
            formstr += "%(done)s"
        if withpri:
            formstr += "%(priority)3s"
        if withindent:
            formstr += "%(indent)s"
        formstr += " %(text)s"
        if withcolor:
            formstr = "%(color)s"+formstr+PRIORITY_COLOR[None]

        #print "searching for: %s" % repr(searches)
        toshow = []
        for task in tasklist.allTasks():
            # skip tasks with non-matching searches
            skip = False
            for s in searches:
                #print "testing if %s contains %s" % (task.text, s)
                if task.text.find(s) == -1:
                    #print "skipping task %s" % repr(task)
                    skip = True
                    continue
            if skip: continue 
	    # skip done tasks
	    if not withdone and task.done is not None:
	        continue
            # skip tasks without the specified priority
            if prisearch != '' and task.priority != prisearch:
                continue
            # skip subtasks other than the first one
            if not showall:
                subsection = num.split(".")[:-1]
                if len(subsection) > 1 and subsection[-1] != '1':
                    continue 
            # output the task
            toshow.append(task)

        def prisort(a, b): 
            return cmp(a.priority, b.priority)
        prioritized = [ t for t in toshow if t.priority is not None ]
        nonprioritized = [ t for t in toshow if t not in prioritized ]
        prioritized.sort(cmp=prisort)

        for task in prioritized + nonprioritized:
            print formstr % task

