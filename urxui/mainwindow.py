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
    update_state = pyqtSignal(str, str, str, int)

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

        self.ui.velLineEdit.setText(self.settings.value("lin_vel", "0.1"))
        self.ui.accLineEdit.setText(self.settings.value("lin_acc", "0.05"))
        self.ui.jointVelLineEdit.setText(self.settings.value("joint_vel", "0.4"))
        self.ui.jointAccLineEdit.setText(self.settings.value("joint_acc", "0.2"))

        self.ui.connectButton.clicked.connect(self.connect)
        self.ui.disconnectButton.clicked.connect(self.disconnect)
        self.ui.copyPoseButton.clicked.connect(self.copy_pose)
        self.ui.copyJointsButton.clicked.connect(self.copy_joints)

        self.dio_boxes = [self.ui.dio0CheckBox,
                          self.ui.dio1CheckBox,
                          self.ui.dio2CheckBox,
                          self.ui.dio3CheckBox,
                          self.ui.dio4CheckBox,
                          self.ui.dio5CheckBox,
                          self.ui.dio6CheckBox,
                          self.ui.dio7CheckBox]

        self.ui.stopButton.clicked.connect(self.stop)

        self.connect_linear_buttons()
        self.connect_joint_buttons()
        self.connect_dio()
        
        self.update_state.connect(self._update_state)
        self.ui.csysButton.clicked.connect(self.update_csys)

        self.robot = None
        self._stopev = False

        self.thread = threading.Thread(target=self._updater)
        self.thread.start()

    def connect_linear_buttons(self):
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
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(125)
            button.setAutoRepeatInterval(125)
            button.clicked.connect(partial(self._inc, axes, direction))
            if direction > 0:
                axes += 1
            direction = -direction

    def connect_joint_buttons(self):
        direction = -1
        joint = 0
        for button in [self.ui.decJ0Button,
                       self.ui.incJ0Button,
                       self.ui.decJ1Button,
                       self.ui.incJ1Button,
                       self.ui.decJ2Button,
                       self.ui.incJ2Button,
                       self.ui.decJ3Button,
                       self.ui.incJ3Button,
                       self.ui.decJ4Button,
                       self.ui.incJ4Button,
                       self.ui.decJ5Button,
                       self.ui.incJ5Button]:
            button.setAutoRepeat(True)
            button.setAutoRepeatDelay(125)
            button.setAutoRepeatInterval(125)
            button.clicked.connect(partial(self._jinc, joint, direction))
            if direction > 0:
                joint += 1
            direction = -direction

    def connect_dio(self):
        for idx, box in enumerate(self.dio_boxes):
            box.clicked.connect(partial(self._dio, idx))

    def show_error(self, msg, level=1):
        print("showing error: ", msg, level)
        self.ui.statusBar.show()
        self.ui.statusBar.setStyleSheet("QStatusBar { background-color : red; color : black; }")
        self.ui.statusBar.showMessage(str(msg))
        QTimer.singleShot(1500, self.ui.statusBar.hide)

    def closeEvent(self, event):
        self._stopev = True
        self.settings.setValue("lin_acc", self.ui.accLineEdit.text())
        self.settings.setValue("lin_vel", self.ui.velLineEdit.text())
        self.settings.setValue("joint_acc", self.ui.jointAccLineEdit.text())
        self.settings.setValue("joint_vel", self.ui.jointVelLineEdit.text())
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

    def _update_state(self, running, pose, joints, bits):
        if self.ui.poseLineEdit.text() != pose:
            self.ui.poseLineEdit.setText(pose)
        if self.ui.jointsLineEdit.text() != joints:
            self.ui.jointsLineEdit.setText(joints)
        if self.ui.stateLineEdit.text() != running:
            self.ui.stateLineEdit.setText(running)
        self._update_dio_ut(bits)

        self.setWindowTitle("Urx ( address:{}, running:{} )".format(self.ui.addrComboBox.currentText(), running))

    def _update_dio_ut(self, bits):
        io = 0
        for box in self.dio_boxes:
            self._update_diobox(box, bits, io)
            io += 1

    def _update_diobox(self, checkbox, bits, num):
        if bits & 1 << num:
            checkbox.setChecked(True)
        else:
            checkbox.setChecked(False)

    def _updater(self):
        while not self._stopev:
            time.sleep(0.5)
            self._update_robot_state()
            
    def _update_robot_state(self):
        pose_str = ""
        joints_str = ""
        bits = 0
        running = "Not connected"
        if self.robot:
            # it should never crash... we will see
            running = str(self.robot.is_running())
            try:
                pose = self.robot.getl()
                pose = [round(i, 4) for i in pose]
                pose_str = str(pose)
                joints = self.robot.getj()
                joints = [round(i, 4) for i in joints]
                joints_str = str(joints)
                bits = self.robot.get_digital_out_bits()
            except Exception as ex:
                print(ex)
        self.update_state.emit(running, pose_str, joints_str, bits)

    def _inc(self, axes, direction, checked):
        if not self.robot:
            self.show_error("No connection")
            return
        vels = [0, 0, 0, 0, 0, 0]
        vel = float(self.ui.velLineEdit.text())
        acc = float(self.ui.accLineEdit.text())
        if direction > 0:
            vels[axes] = vel
        else:
            vels[axes] = -vel
        if self.ui.toolRefCheckBox.isChecked():
            self.robot.speedl_tool(vels, acc=acc, min_time=0.2)
        else:
            self.robot.speedl(vels, acc=acc, min_time=0.2)

    def _jinc(self, joint, direction, checked):
        if not self.robot:
            self.show_error("No connection")
            return
        p = [0, 0, 0, 0, 0, 0]
        vel = float(self.ui.jointVelLineEdit.text())
        acc = float(self.ui.jointAccLineEdit.text())
        if direction > 0:
            p[joint] += vel
        else:
            p[joint] -= vel 
        self.robot.speedj(p, acc=acc, min_time=0.2)

    def _dio(self, io, val):
        try:
            print("Setting IO{} to {}".format(io, val))
            self.robot.set_digital_out(io, val)
        except Exception as ex:
            self.show_error(ex)









def main():
    app = QApplication(sys.argv)
    client = Window()
    client.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
