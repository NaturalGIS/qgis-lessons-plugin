from builtins import range
from builtins import object
# -*- coding: utf-8 -*-

import os
import traceback
import yaml
import difflib
import shutil

from qgis.core import QgsMessageLog

from lessons.utils import openProject, menuFromName, execute, getMenuPaths, qgisLocale

class Step(object):

    MANUALSTEP, AUTOMATEDSTEP = list(range(2))

    def __init__(self, name, description, function=None, prestep=None, endsignal=None,
                 endsignalcheck=None, endcheck=lambda:True, steptype=1):
        self.name = name
        self.description = description or ""
        self.function = function
        self.prestep = prestep
        self.endcheck = endcheck
        self.endsignal = endsignal
        self.endsignalcheck = endsignalcheck
        self.steptype = steptype

class Lesson(object):

    def __init__(self, name, group, description, folder = None):
        if folder is None:
            folder = os.path.dirname(traceback.extract_stack()[-2][0])
        self.folder = folder
        self.steps = []
        self.name = name
        self.group = group
        self.cleanup = lambda: None
        self.nextLessons = []
        self.description = self.resolveFile(description)
        self.style = ""
        path = os.path.join(self.folder, "style.css")
        if os.path.exists(path):
            with open(path) as f:
                self.style = "<style>\n" + "".join(f.readlines()) + "\n</style>\n"
        path = os.path.join(self.folder, "project.qgs")
        if os.path.exists(path):
            self.addStep("Open project", "Open project", lambda: openProject(path))

    def setCleanup(self,function):
        self.cleanup = function

    def addNextLesson(self, group, name):
        self.nextLessons.append((group,name))

    def resolveFile(self, f):
        if f is None:
            f = ""
        else:
            for i in [qgisLocale(), "en"]:
                if not os.path.exists(os.path.join(i, f)):
                    path = os.path.join(self.folder, i, f)
                    if os.path.exists(path):
                        f = path
                        break
        return f

    def addStep(self, name, description, function=None, prestep=None, endsignal=None,
                endsignalcheck=None, endcheck=lambda:True, steptype=1):
        description = self.resolveFile(description)
        if function is not None:
            _function = lambda: execute(function)
        else:
            _function = None
        step = Step(name, description, _function, prestep, endsignal, endsignalcheck, endcheck, steptype)
        self.steps.append(step)

    def addMenuClickStep(self, menuName, description=None):
        try:
            menu, action = menuFromName(menuName)
        except:
            closest = difflib.get_close_matches(menuName, getMenuPaths())
            if closest:
                menu, action = menuFromName(closest[0])
            else:
                QgsMessageLog.logMessage("Lesson contains a wrong menu name: %s" % menuName,
                                         level=QgsMessageLog.WARNING)
                return None

        name = "Click on '%s' menu item." % action.text().replace("&","")
        if description is None:
            description = "<p>Click on <b>%s</b> menu item.</p>" \
                          "<p>Once you click, the lesson will automatically move to the next step.</p>"\
                          % menuName.replace("/"," > ")

        def checkMenu(triggeredAction):
            return triggeredAction.text() == action.text()

        self.addStep(name, description, None, None, menu.triggered, checkMenu, None, Step.MANUALSTEP)

    def uninstall(self):
        shutil.rmtree(self.folder, True)

def lessonFromYamlFile(f):
    with open(f) as stream:
        lessonDict = yaml.load(stream)
    lesson = Lesson(lessonDict["name"], lessonDict["group"], lessonDict["description"],
                    os.path.dirname(f))
    for step in lessonDict["steps"]:
        if "menu" in step:
            if "description" in step:
                description = step["description"]
            else:
                description = None

            lesson.addMenuClickStep(step["menu"], description)

        else:
            lesson.addStep(step["name"], step["description"], steptype=Step.MANUALSTEP)

    if "nextLessons" in lessonDict:
        for nextLesson in lessonDict["nextLessons"]:
            lesson.addNextLesson(nextLesson["group"], nextLesson["name"])
    return lesson
