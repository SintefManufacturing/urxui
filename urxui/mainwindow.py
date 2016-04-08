#! /usr/bin/env python3

import sys
import threading
import time
from functools import partial

from PyQt5.QtCore import pyqtSignal, QTimer, QSettings
from PyQt5.QtWidgets import QMainWindow, QApplication

import math3d as m3d
import urx

from urxui.mainwindow_ui import Ui_MainWindow


class Window(QMainWindow):
    update_state = pyqtSignal(str, str, str)

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # we only show statusbar in case of errors
        self.ui.statusBar.hide()

        self.setWindowTitle("Urx ( address:{}, running:{} )".format(self.ui.addrComboBox.currentText(), "Not connected"))

        self.settings = QSettings("UrxUi", "urxui")
        
        self._address_list = self.settings.value("address_list", ["localhost", "192.168.0.224"])
        for addr in self._address_list:
            self.ui.addrComboBox.insertItem(-1, addr)

        self._csys_list = self.settings.value("csys_list", ["[0, 0, 0, 0, 0, 0]"])
        for addr in self._csys_list:
            self.ui.csysComboBox.insertItem(-1, addr)

        self.ui.stepLineEdit.setText(self.settings.value("jog_step", "0.005"))
        self.ui.velLineEdit.setText(self.settings.value("jog_vel", "0.01"))
        self.ui.accLineEdit.setText(self.settings.value("jog_acc", "0.1"))

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.disconnectButton.clicked.connect(self.disconnect)
        self.ui.copyPoseButton.clicked.connect(self.copy_pose)
        self.ui.copyJointsButton.clicked.connect(self.copy_joints)

        self.ui.stopButton.clicked.connect(self.stop)

        self.timer = QTimer()
        self.timer.timeout.connect(self._timeout)
        self.timer.setSingleShot(False)
        self._move = None
        
        direction = -1
        axes = 0
        for button in [self.ui.minusXButton,
                       self.ui.plusXButton,
                       self.ui.minusYButton,
                       self.ui.plusYButton,
                       self.ui.minusZButton,
                       self.ui.plusZButton,
                       self.ui.minusRXButton,
                       self.ui.plusRXButton,
                       self.ui.minusRYButton,
                       self.ui.plusRYButton,
                       self.ui.minusRZButton,
                       self.ui.plusRZButton]:
            button.clicked.connect(partial(self._inc, axes, direction))
            button.pressed.connect(partial(self._pressed, axes, direction))
            button.released.connect(partial(self._released, axes, direction))
            if direction > 0:
                axes += 1
            direction = -direction

        self.update_state.connect(self._update_state)
        self.ui.csysButton.clicked.connect(self.update_csys)

        self.robot = None
        self._stopev = False

        self.thread = threading.Thread(target=self._updater)
        self.thread.start()

    def show_error(self, msg, level=1):
        print("showing error: ", msg, level)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def closeEvent(self, event):
        self._stopev = True
        self.settings.setValue("jog_acc", self.ui.accLineEdit.text())
        self.settings.setValue("jog_vel", self.ui.velLineEdit.text())
        self.settings.setValue("jog_step", self.ui.stepLineEdit.text())
        self.disconnect()
        event.accept()

    def connect(self):
        if self.robot:
            try:
                self.disconnect()
            except:
                print("Error while disconnecting")
        uri = self.ui.addrComboBox.currentText()
        try:
            self.robot = urx.Robot(uri)
            self.update_csys()
        except Exception as ex:
            self.show_error(ex)
            raise
        self._save_address_list()
        print("Connected to ", self.robot)

    def disconnect(self):
        if self.robot:
            self.robot.close()
        self.robot = None
        print("Disconnected")

    def stop(self):
        if self.robot:
            self.robot.stopj()

    def _save_address_list(self):
        uri = self.ui.addrComboBox.currentText()
        if uri == self._address_list[0]:
            return
        if uri in self._address_list:
            self._address_list.remove(uri)
        self._address_list.insert(0, uri)
        self._address_list = self._address_list[:int(self.settings.value("address_list_max_count", 10))]
        self.settings.setValue("address_list", self._address_list)

    def _save_csys(self):
        csys = self.ui.csysComboBox.currentText()
        if csys == self._csys_list[0]:
            return
        if csys in self._csys_list:
            self._csys_list.remove(csys)
        self._csys_list.insert(0, csys)
        max_count = int(self.settings.value("csys_max_count", 10))
        self._csys_list = self._csys_list[:max_count]
        self.settings.setValue("csys_list", self._csys_list)

    def copy_joints(self):
        QApplication.clipboard().setText(self.ui.jointsLineEdit.text())

    def copy_pose(self):
        QApplication.clipboard().setText(self.ui.poseLineEdit.text())

    def update_csys(self):
        csys = self.ui.csysComboBox.currentText()
        try:
            csys = eval(csys)
            csys = m3d.Transform(csys)
            self.robot.set_csys(csys)
        except Exception as ex:
            self.show_error(ex)
            raise
        self._save_csys()

    def _update_state(self, running, pose, joints):
        if self.ui.poseLineEdit.text() != pose:
            self.ui.poseLineEdit.setText(pose)
        if self.ui.jointsLineEdit.text() != joints:
            self.ui.jointsLineEdit.setText(joints)
        if self.ui.stateLineEdit.text() != running:
            self.ui.stateLineEdit.setText(running)
        self.setWindowTitle("Urx ( address:{}, running:{} )".format(self.ui.addrComboBox.currentText(), running))

    def _updater(self):
        while not self._stopev:
            time.sleep(0.5)
            self._update_robot_state()

    def _update_robot_state(self):
        if self.robot:
            # it should never crash... we will see
            running = str(self.robot.is_running())
        else:
            running = "Not connected"
        try:
            pose = self.robot.getl()
            pose = [round(i, 4) for i in pose]
            pose_str = str(pose)
            joints = self.robot.getj()
            joints = [round(i, 4) for i in joints]
            joints_str = str(joints)
        except Exception:
            pose_str = ""
            joints_str = ""
        self.update_state.emit(running, pose_str, joints_str)

    def _timeout(self):
        self.timer.setInterval(100)
        if not self.robot:
            return

        axes, direction = self._move
        vels = [0, 0, 0, 0, 0, 0]
        vel = float(self.ui.velLineEdit.text())
        min_time = self.timer.interval() / 1000 + 0.1
        acc = float(self.ui.accLineEdit.text())
        if direction > 0:
            vels[axes] = vel
        else:
            vels[axes] = -vel
        if self.ui.toolRefCheckBox.isChecked():
            self.robot.speedl_tool(vels, acc=acc, min_time=min_time)
        else:
            self.robot.speedl(vels, acc=acc, min_time=min_time)

    def _pressed(self, axes, direction):
        if not self.robot:
            self.show_error("No connection")
            return
        self._move = axes, direction
        self.timer.start(500)

    def _released(self, axes, direction):
        self.timer.stop()
        self._move = None
        self.robot.stopj()

    def _inc(self, axes, direction, checked):
        if self.timer.interval() < 300:
            # this was a long press returning
            return
        if not self.robot:
            self.show_error("No connection")
            return
        step = float(self.ui.stepLineEdit.text())
        if self.ui.toolRefCheckBox.isChecked():
            p = [0, 0, 0, 0, 0, 0]
            if direction > 0:
                p[axes] += step
            else:
                p[axes] -= step 
            self.robot.movel_tool(p, vel=float(self.ui.velLineEdit.text()), acc=float(self.ui.accLineEdit.text()), wait=False)
        else:
            p = self.robot.getl()
            if direction > 0:
                p[axes] += step
            else:
                p[axes] -= step 
            self.robot.movel(p, vel=float(self.ui.velLineEdit.text()), acc=float(self.ui.accLineEdit.text()), wait=False)








def main():
    app = QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
