import wx

import eos.db
import gui.mainFrame
from gui import globalEvents as GE
from gui.fitCommands.calc.cargo.add import CalcAddCargoCommand
from gui.fitCommands.calc.cargo.remove import CalcRemoveCargoCommand
from gui.fitCommands.calc.module.changeCharges import CalcChangeModuleChargesCommand
from gui.fitCommands.calc.module.localReplace import CalcReplaceLocalModuleCommand
from gui.fitCommands.helpers import CargoInfo, InternalCommandHistory, ModuleInfo
from service.fit import Fit


class GuiCargoToLocalModuleCommand(wx.Command):
    """
    Moves cargo to fitting window. Can either do a copy, move, or swap with current module
    If we try to copy/move into a spot with a non-empty module, we swap instead.
    To avoid redundancy in converting Cargo item, this function does the
    sanity checks as opposed to the GUI View. This is different than how the
    normal .swapModules() does things, which is mostly a blind swap.
    """

    def __init__(self, fitID, cargoItemID, modPosition, copy):
        wx.Command.__init__(self, True, 'Cargo to Local Module')
        self.internalHistory = InternalCommandHistory()
        self.fitID = fitID
        self.srcCargoItemID = cargoItemID
        self.dstModPosition = modPosition
        self.copy = copy
        self.addedModItemID = None
        self.removedModItemID = None

    def Do(self):
        sFit = Fit.getInstance()
        fit = sFit.getFit(self.fitID)
        srcCargo = next((c for c in fit.cargo if c.itemID == self.srcCargoItemID), None)
        if srcCargo is None:
            return
        dstMod = fit.modules[self.dstModPosition]
        # Moving charge from cargo to fit - just attempt to load charge into destination module
        if srcCargo.item.isCharge and not dstMod.isEmpty:
            cmd = CalcChangeModuleChargesCommand(
                fitID=self.fitID,
                projected=False,
                chargeMap={dstMod.modPosition: self.srcCargoItemID},
                commit=False)
            success = self.internalHistory.submit(cmd)
        # Copying item to empty slot
        elif srcCargo.item.isModule and self.copy and dstMod.isEmpty:
            cmd = CalcReplaceLocalModuleCommand(
                fitID=self.fitID,
                position=self.dstModPosition,
                newModInfo=ModuleInfo(itemID=self.srcCargoItemID),
                commit=False)
            success = self.internalHistory.submit(cmd)
            if success:
                self.addedModItemID = self.srcCargoItemID
        # Swapping with target module, or moving there if there's no module
        elif srcCargo.item.isModule and not self.copy:
            dstModItemID = dstMod.itemID
            if self.srcCargoItemID == dstModItemID:
                return False
            newModInfo = ModuleInfo.fromModule(dstMod)
            newModInfo.itemID = self.srcCargoItemID
            if dstMod.isEmpty:
                newCargoItemID = None
            elif dstMod.isMutated:
                newCargoItemID = dstMod.baseItemID
            else:
                newCargoItemID = dstMod.itemID
            commands = []
            commands.append(CalcRemoveCargoCommand(
                fitID=self.fitID,
                cargoInfo=CargoInfo(itemID=self.srcCargoItemID, amount=1),
                commit=False))
            if newCargoItemID is not None:
                commands.append(CalcAddCargoCommand(
                    fitID=self.fitID,
                    cargoInfo=CargoInfo(itemID=newCargoItemID, amount=1),
                    commit=False))
            commands.append(CalcReplaceLocalModuleCommand(
                fitID=self.fitID,
                position=self.dstModPosition,
                newModInfo=newModInfo,
                unloadInvalidCharges=True,
                commit=False))
            success = self.internalHistory.submitBatch(*commands)
            if success:
                self.addedModItemID = self.srcCargoItemID
                self.removedModItemID = dstModItemID
        else:
            return False
        eos.db.commit()
        sFit.recalc(self.fitID)
        events = []
        if self.removedModItemID is not None:
            events.append(GE.FitChanged(fitID=self.fitID, action='moddel', typeID=self.removedModItemID))
        if self.addedModItemID is not None:
            events.append(GE.FitChanged(fitID=self.fitID, action='modadd', typeID=self.addedModItemID))
        if not events:
            events.append(GE.FitChanged(fitID=self.fitID))
        for event in events:
            wx.PostEvent(gui.mainFrame.MainFrame.getInstance(), event)
        return success

    def Undo(self):
        success = self.internalHistory.undoAll()
        eos.db.commit()
        Fit.getInstance().recalc(self.fitID)
        events = []
        if self.addedModItemID is not None:
            events.append(GE.FitChanged(fitID=self.fitID, action='moddel', typeID=self.addedModItemID))
        if self.removedModItemID is not None:
            events.append(GE.FitChanged(fitID=self.fitID, action='modadd', typeID=self.removedModItemID))
        if not events:
            events.append(GE.FitChanged(fitID=self.fitID))
        for event in events:
            wx.PostEvent(gui.mainFrame.MainFrame.getInstance(), event)
        return success