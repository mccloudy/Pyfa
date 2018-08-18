import wx
from service.fit import Fit

import gui.mainFrame
from gui import globalEvents as GE
#from .helpers import ModuleInfoCache
from eos.saveddata.module import Module, State
import eos.db
from logbook import Logger
pyfalog = Logger(__name__)
from eos.saveddata.implant import Implant

class FitToggleFighterCommand(wx.Command):
    """"
    from sFit.toggleFighter
    """
    def __init__(self, fitID, position):
        wx.Command.__init__(self, True, "Cargo add")
        self.fitID = fitID
        self.position = position

    def Do(self):
        pyfalog.debug("Toggling fighters for fit ID: {0}", self.fitID)
        fit = eos.db.getFit(self.fitID)
        f = fit.fighters[self.position]
        f.active = not f.active

        eos.db.commit()
        return True

    def Undo(self):
        cmd = FitToggleFighterCommand(self.fitID, self.position)
        return cmd.Do()