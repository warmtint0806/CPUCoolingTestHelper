# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 23:30:50 2022

@author: HPreal
"""
from PyQt5.QtWidgets import QApplication, QDialog, QMainWindow, QPushButton
from PyQt5 import uic
from PyQt5.QtCore import Qt

import requests

qtcreator_file  = "ext_dialog.ui" # Enter file here.
Ui_IPAddDialog_Window, QtBaseClass = uic.loadUiType(qtcreator_file)

class IPAddDialog(QDialog, Ui_IPAddDialog_Window):
    def __init__(self, parent=None, flag=Qt.Dialog, name=None):
        super().__init__(parent, flag)
        QDialog.__init__(self)
        Ui_IPAddDialog_Window.__init__(self)
        self.setupUi(self)
        self.ip=None
        self.sensorName=None
        self.addButton.clicked.connect(self.addButtonClicked)
        self.cancelButton.clicked.connect(lambda: self.close())
    def addButtonClicked(self):
        self.ip=str(self.ip1.value())+('.')+str(self.ip2.value())+('.')+str(self.ip3.value())+('.')+str(self.ip4.value())
        self.warningLabel.setText('fetching sensor data...')
        sensorinfo=self.check_ext_sensor_name(self.ip)
        if sensorinfo:
            self.sensorName=sensorinfo
            self.close()
        else:
            self.warningLabel.setText("failed to fetch the sensor data")
            self.ip=None
        
    def check_ext_sensor_name(self,ip):
        try:
            data=requests.get("http://"+ip).json()
            return data['name']
        except:
            return None