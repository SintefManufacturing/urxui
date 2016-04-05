#! /usr/bin/env python3

import sys
import threading
import time

from PyQt5.QtCore import pyqtSignal, QTimer, QSettings
from PyQt5.QtWidgets import QMainWindow,  QApplication

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
        self.setWindowTitle("Urx ( address:{}, running:{} )".format(self.ui.addressLineEdit.text(), "Not connected"))

        self.settings = QSettings("UrxUi", "urxui")
        self.ui.addressLineEdit.setText(self.settings.value("address", "localhost"))
        self.ui.csysLineEdit.setText(self.settings.value("csys", ""))

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.disconnectButton.clicked.connect(self.disconnect)

        self.ui.plusXButton.clicked.connect(self._inc_x)
        self.ui.minusXButton.clicked.connect(self._dec_x)
        self.ui.plusYButton.clicked.connect(self._inc_y)
        self.ui.minusYButton.clicked.connect(self._dec_y)

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
        self.settings.setValue("address", self.ui.addressLineEdit.text())
        self.disconnect()
        event.accept()

    def connect(self):
        if self.robot:
            try:
                self.disconnect()
            except:
                print("Error while disconnecting")
        try:
            self.robot = urx.Robot(self.ui.addressLineEdit.text())
            self.ui.csysLineEdit.setText(str(self.robot.csys.pose_vector.tolist()))
        except Exception as ex:
            self.show_error(ex)
            raise
        print("Connected to ", self.robot)

    def disconnect(self):
        if self.robot:
            self.robot.close()
        self.robot = None
        print("Disconnected")

    def update_csys(self):
        csys = self.ui.csysLineEdit.text()
        try:
            csys = eval(csys)
            csys = m3d.Transform(csys)
            self.robot.set_csys(csys)
        except Exception as ex:
            self.show_error(ex)
            raise

    def _update_state(self, running, pose, joints):
        self.ui.poseLineEdit.setText(pose)
        self.ui.jointsLineEdit.setText(joints)
        self.ui.stateLineEdit.setText(running)
        self.setWindowTitle("Urx ( address:{}, running:{} )".format(self.ui.addressLineEdit.text(), running))

    def _updater(self):
        while not self._stopev:
            time.sleep(0.5)
            if self.robot:
                # it should never crash... we will see
                running = str(self.robot.is_running())
            else:
                running = "Not connected"
            try:
                pose = self.robot.getl()
                pose = [round(i, 3) for i in pose]
                pose = str(pose)
                joints = self.robot.getj()
                joints = [round(i, 4) for i in joints]
                joints = str(joints)
            except Exception:
                pose = ""
                joints = ""
            self.update_state.emit(running, pose, joints)

    def _inc_x(self):
        p = self.robot.get_pos()
        p.x += 0.1
        self.robot.set_pos(p)

    def _dec_x(self):
        p = self.robot.get_pos()
        p.x -= 0.1
        self.robot.set_pos(p)

    def _inc_y(self):
        p = self.robot.get_pos()
        p.x += 0.1
        self.robot.set_pos(p)

    def _dec_y(self):
        p = self.robot.get_pos()
        p.y -= 0.1
        self.robot.set_pos(p)

    def _inc_z(self):
        p = self.robot.get_pos()
        p.z += 0.1
        self.robot.set_pos(p)

    def _dec_z(self):
        p = self.robot.get_pos()
        p.z -= 0.1






def main():
    app = QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
