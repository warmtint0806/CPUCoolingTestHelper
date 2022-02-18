#!/usr/bin/env python
# coding: utf-8

import wmi
import os
import time
from datetime import datetime
import json
import pythoncom
import numpy as np

import plotly
import plotly.express as px
import plotly.graph_objects as go

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.figure_factory as ff
from dash.dependencies import Input, Output

import webbrowser

import sys,threading
from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import QObject, QRunnable, QThread, QThreadPool, pyqtSignal, pyqtSlot, QUrl, Qt 


# --- ext sensor manage

import ext_manager
import ext_sensor_add_GUI
import requests

# --- QDash

class QDash(QObject):
    def __init__(self, temp_fig, clock_fig, parent=None, ext_temp_fig=None, ext_humidity_fig=None):
        super().__init__(parent)

        self._app = dash.Dash()
        self.notUpdating=True
        self.clearGraph=False
        self._app.layout = html.Div(html.Div([
                html.H4("It's a beautiful day for yet another experiment"),
                html.H5('CPU temperatures'),
                dcc.Graph(id='live-update-graph'),
                html.H5('CPU clocks'),
                dcc.Graph(id='live-update-graph2'),
                html.H5('External Temperatures'),
                dcc.Graph(id='live-update-graph3'),
                html.H5('External Humidities'),
                dcc.Graph(id='live-update-graph4'),
                dcc.Interval(id='interval-component',
                             interval=1*2000,
                             n_intervals=0),
                dcc.Interval(id='interval-control-component',
                             interval=1*1000,
                             n_intervals=0)
                ]))
        self.temp_fig=temp_fig
        self.clock_fig=clock_fig
        self.ext_temp_fig=ext_temp_fig
        self.ext_humidity_fig=ext_humidity_fig
        
        self.clear_trial=0
    
        @self._app.callback(Output('interval-component', 'disabled'),Input('interval-control-component','n_intervals'))
        def toggleUpdating(n):
            if self.clearGraph:
                self.clearGraph=False
                self.clear_trial=3
                return False
            if self.clear_trial > 0:
                self.clear_trial=self.clear_trial-1
                return False
            return self.notUpdating
    
        @self._app.callback(Output('live-update-graph', 'figure'),Input('interval-component','n_intervals'))
        def update_graph(n):
            return self.temp_fig
        
        @self._app.callback(Output('live-update-graph2', 'figure'),Input('interval-component','n_intervals'))
        def update_graph2(n):
            return self.clock_fig
        
        @self._app.callback(Output('live-update-graph3', 'figure'),Input('interval-component','n_intervals'))
        def update_graph3(n):
            return self.ext_temp_fig
        
        @self._app.callback(Output('live-update-graph4', 'figure'),Input('interval-component','n_intervals'))
        def update_graph4(n):
            return self.ext_humidity_fig
    @property
    def app(self):
        return self._app

    def run(self, **kwargs):
        threading.Thread(target=self.app.run_server, kwargs=kwargs, daemon=True).start()

# ---- Collecting Workers 
        
qtcreator_file  = "main_ext.ui" # Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtcreator_file)

class WorkerSignals(QObject): 
    finished=pyqtSignal()
    progress=pyqtSignal(tuple)
    inspectionDone=pyqtSignal(dict)
    registerData=pyqtSignal(str)

class Worker(QRunnable):
    def __init__(self,temp_fig,clock_fig,dt,totaltime,trialName,filepath,temp_sensors,clock_sensors,data_name=None, 
                 ext_sensor_ip_list=None, ext_temp_fig=None, ext_humidity_fig=None):
        super(Worker, self).__init__()
        self.temp_fig=temp_fig
        self.clock_fig=clock_fig
        self.signals=WorkerSignals()
        self.dt=dt
        self.totaltime=totaltime
        self.trialName=trialName
        self.filepath=filepath
        self.temp_sensors=temp_sensors
        self.clock_sensors=clock_sensors
        
        self.ext_sensor_ip_list=ext_sensor_ip_list
        self.ext_sensor_collector=None
        self.ext_temp_fig=ext_temp_fig
        self.ext_humidity_fig=ext_humidity_fig
        if ext_sensor_ip_list:
            self.ext_sensor_collector=ext_manager.ext_sensor_collector(ext_sensor_ip_list)
        if (data_name):
            self.data_name=data_name
        else:
            self.data_name=self.trialName+'-'+datetime.now().strftime('%Y%m%d-%H_%M_%S')
    
    def record_ext_data(self,result,sensor_data_list):
        #result['time'].append(cur_time)
        #result['elp_time'].append(elp_time)
        for sensor in sensor_data_list:
            print(sensor)
            sensor_name=sensor['name']
            if sensor_name in result['ext']:
                    result['ext'][sensor_name]['h'].append(sensor['h'])
                    result['ext'][sensor_name]['t'].append(sensor['t'])
            else:
                result['ext'][sensor_name]={}
                result['ext'][sensor_name]['h']=[sensor['h']]
                result['ext'][sensor_name]['t']=[sensor['t']]
        
    
    def record_data(self,result,cur_time,elp_time,temperature_infos):
        result['time'].append(cur_time)
        result['elp_time'].append(elp_time)
        
        for sensor in temperature_infos:
            if sensor.Name.startswith("CPU"):
                if sensor.Name in result:
                    if sensor.SensorType in result[sensor.Name]:
                        result[sensor.Name][sensor.SensorType].append(sensor.Value)
                    else:
                        result[sensor.Name][sensor.SensorType]=[sensor.Value]
                else:
                    result[sensor.Name]={}
                    result[sensor.Name][sensor.SensorType]=[sensor.Value]

    def add_fig_traces(self,fig,idx_names, data_name='default'):
        for name in idx_names:
            data=go.Scatter(x=[],y=[],name=name,legendgroup=data_name)
            fig.add_trace(data)
    
    def update_fig_traces(self,fig,rcd_time,data_list):
        fig_cur_idx=len(fig.data)-len(data_list)
        data_cur_idx=0
        for data in data_list:
            idx=fig_cur_idx+data_cur_idx
            #print(fig.data[idx].x)
            fig.data[idx].x=fig.data[idx].x + (rcd_time,)
            fig.data[idx].y=fig.data[idx].y + (data,)
            data_cur_idx=data_cur_idx+1

    @pyqtSlot()
    def run(self):
        self.running=True
        self.start_record2(self.temp_fig,self.clock_fig,self.dt,self.totaltime)
        self.signals.finished.emit()
        
    def start_record2(self, temp_fig, clock_fig, dt, totaltime):
        #dt=0.5
        #totaltime=60
        
        trial_name=self.trialName
        
        #data_name=[trial_name+'CPU Package Power','CPU Package T', 'C#1 T', 'C#2 T']
        idx_name=self.temp_sensors.copy()
        idx_name[0]=trial_name + '_' + idx_name[0]
        self.add_fig_traces(temp_fig,idx_name,self.data_name)
    
        #data_name=[trial_name + 'C#1 clock', 'C#2 clock']
        idx_name=self.clock_sensors.copy()
        idx_name[0]=trial_name + '_' + idx_name[0]
        self.add_fig_traces(clock_fig,idx_name,self.data_name)
        
        #data_name=[trial_name + 'C#1 clock', 'C#2 clock']
        idx_name=self.ext_sensor_ip_list.copy()
        if(len(idx_name)>0):
            idx_name[0]=trial_name + '_' + idx_name[0]
            print(idx_name[0])
            self.add_fig_traces(self.ext_temp_fig,idx_name,self.data_name)
            
            idx_name=self.ext_sensor_ip_list.copy()
            idx_name[0]=trial_name + '_' + idx_name[0]
            self.add_fig_traces(self.ext_humidity_fig,idx_name,self.data_name)
    
        result={"time":[],"elp_time":[],'ext':{}}
        init_time=time.time()
        pythoncom.CoInitialize()
        self.w=wmi.WMI(namespace="root\OpenHardwareMonitor")
        
        while self.running: 
            current_time=time.time()
            elapsed=current_time-init_time
        
            self.record_data(result,current_time,elapsed,self.w.Sensor())
            if self.ext_sensor_collector:
                new_data=self.ext_sensor_collector.get_data()
                self.record_ext_data(result, new_data)
                print(new_data)
            
            data_to_draw=[]
            clock_data_to_draw=[]
            ext_temp_data_to_draw=[]
            ext_humidity_data_to_draw=[]
            
            for temp_sensor in self.temp_sensors:
                data_to_draw.append(result[temp_sensor]['Temperature'][-1])
            for clock_sensor in self.clock_sensors:
                clock_data_to_draw.append(result[clock_sensor]['Clock'][-1])
    
            for ext_sensor in result['ext']:
                ext_temp_data_to_draw.append(result['ext'][ext_sensor]['t'][-1])
                ext_humidity_data_to_draw.append(result['ext'][ext_sensor]['h'][-1])
                
            self.update_fig_traces(temp_fig,elapsed,data_to_draw)
            self.update_fig_traces(clock_fig,elapsed,clock_data_to_draw)
            self.update_fig_traces(self.ext_temp_fig,elapsed,ext_temp_data_to_draw)
            self.update_fig_traces(self.ext_humidity_fig,elapsed,ext_humidity_data_to_draw)
            
            time.sleep(dt)
            self.signals.progress.emit((elapsed,totaltime))
            
            if elapsed>totaltime: 
                break
        
        pythoncom.CoUninitialize()
        self.signals.registerData.emit(self.data_name)
        filename=self.filepath+'/'+self.data_name+'.json'
        with open(filename, 'w') as fp:
            json.dump(result, fp,  indent=4) 
        
        
class Init_Worker(QRunnable): 
    def __init__(self):
        super(Init_Worker,self).__init__()
        self.signals=WorkerSignals()
    
    def gather_data(self,temperature_infos):
        result={"Temperatures":[],"Clocks":[]}
        
        for sensor in temperature_infos:
            if sensor.Name.startswith("CPU"):
                if sensor.SensorType == "Temperature":     
                    result["Temperatures"].append(sensor.Name)
                elif sensor.SensorType == "Clock":
                    result["Clocks"].append(sensor.Name)
                    
        return result

    @pyqtSlot()
    def run(self): 
        pythoncom.CoInitialize()
        self.w=wmi.WMI(namespace="root\OpenHardwareMonitor")
        result=self.gather_data(self.w.Sensor())
        self.signals.inspectionDone.emit(result)
        pythoncom.CoUninitialize()
   
# ---- PyQt Main Window

def create_new_fig():
    new_fig=go.Figure()
    new_fig.update_layout(width=1600,height=450, 
                                    margin=dict(l=100, r=20, t=0, b=0), 
                                    transition={
                                        'duration': 500,
                                        'easing': 'cubic-in-out'
                                    })
    return new_fig

class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.temp_fig=create_new_fig()
        self.clock_fig=create_new_fig()
        self.ext_temp_fig=create_new_fig()
        self.ext_humidity_fig=create_new_fig() 

        #print(self.temp_fig)
        self.threadpool=QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        
        #ui related
        self.runButton.clicked.connect(self.start_record)
        self.stopButton.clicked.connect(self.activate_run_features)
        
        self.reloadButton.clicked.connect(self.open_graph_in_browser)
        self.dt_dial.valueChanged.connect(self.dt_dialChanged)
        
        self.set_filePathInit()
        self.pathButton.clicked.connect(self.set_filePath)
        
        self.qdash=QDash(temp_fig=self.temp_fig, clock_fig=self.clock_fig, 
                         ext_temp_fig=self.ext_temp_fig, ext_humidity_fig=self.ext_humidity_fig)
        self.qdash.run(debug=True, use_reloader=False)
        self.open_graph_in_browser()
        
        self.sensor_check()
        self.cpu_temperature_display_candidate_list=[]
        self.cpu_clock_display_candidate_list=[]
        
        #graph related
        self.clearGraphsButton.clicked.connect(self.clear_graphs)
        self.removeDataButton.clicked.connect(self.clear_selected_graph)
        
        #external sensor related
        self.addExtSensorButton.clicked.connect(self.open_ext_sensor_add_dialog)
     
    def open_ext_sensor_add_dialog(self): 
        dlg=ext_sensor_add_GUI.IPAddDialog()
        dlg.exec_()
        print((dlg.ip,dlg.sensorName))
        if (dlg.ip and dlg.sensorName):
            self.add_ext_sensor(dlg.ip,dlg.sensorName)
        
    def add_ext_sensor(self, ip, sensor_name=None):
        item=QtWidgets.QListWidgetItem(ip + ' | ' + sensor_name)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        item.setData(Qt.UserRole, (ip,sensor_name))
        self.extSensorList.addItem(item)    
    
    def return_ext_sensor_ip_list(self):
        sensor_ip_list=[]
        for index in range(self.extSensorList.count()):
            if self.extSensorList.item(index).checkState() == Qt.Checked:
                sensor_ip_list.append(self.extSensorList.item(index).data(Qt.UserRole)[0])
        return sensor_ip_list

    def open_graph_in_browser(self):
        webbrowser.open('http://127.0.0.1:8050',1)
    
    def browser_reload(self): 
        print(self.reloadUrl.text())
        self.temp_graph_browser.load(QUrl(self.reloadUrl.text()))
        self.temp_graph_browser.show()
        
    def start_record(self):
        sensor_to_display=self.return_checked_sensor_list()
        ext_sensor_ip_list=self.return_ext_sensor_ip_list()
        self.worker=Worker(self.temp_fig, self.clock_fig, self.dt_dial.value() *0.5, self.totalTimeBox.value() * 60, 
                           self.trialNameBox.text(),self.pathLabel.text(),
                           sensor_to_display['Temperatures'], sensor_to_display['Clocks'],
                           ext_sensor_ip_list=ext_sensor_ip_list, 
                           ext_temp_fig=self.ext_temp_fig, 
                           ext_humidity_fig=self.ext_humidity_fig)
        #self.worker.signals.progress.connect(self.show_temp_graph)
        
        self.worker.signals.registerData.connect(self.add_data_list)
        self.worker.signals.progress.connect(self.progressBar_setValue)
        #self.worker.signals.progress.connect(self.show_clock_graph)
        self.deactivate_run_features()
        self.worker.signals.finished.connect(self.activate_run_features)
        self.threadpool.start(self.worker)
    
    def deactivate_run_features(self):
        self.runButton.setDisabled(True)
        self.clearGraphsButton.setDisabled(True)
        self.stopButton.setEnabled(True)
        self.progressBar.setValue(0)
        self.pathButton.setDisabled(True)
        self.qdash.notUpdating=False
        self.removeDataButton.setDisabled(True)
    
    def activate_run_features(self):
        self.worker.running=False
        self.runButton.setEnabled(True)
        self.clearGraphsButton.setEnabled(True)
        self.stopButton.setDisabled(True)
        self.pathButton.setEnabled(True)
        self.qdash.notUpdating=True
        self.removeDataButton.setEnabled(True)
    
    def sensor_check(self):
        self.check_worker=Init_Worker()
        self.check_worker.signals.inspectionDone.connect(self.update_sensor_list)
        self.threadpool.start(self.check_worker)
    
    def update_sensor_list(self,result):
        for temp_sensor in result['Temperatures']:
            item=QtWidgets.QListWidgetItem(temp_sensor)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
    
            self.temperatureSensorList.addItem(item)
        for clock_sensor in result['Clocks']:
            item=QtWidgets.QListWidgetItem(clock_sensor)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            self.clockSensorList.addItem(item)
        
        self.temperatureSensorList.itemSelectionChanged.connect(self.return_checked_sensor_list)
        self.clockSensorList.itemSelectionChanged.connect(self.return_checked_sensor_list)

        print(result)
        
    def add_data_list(self, data_name):
        print(data_name)
        item=QtWidgets.QListWidgetItem(data_name)
        self.dataNameList.addItem(item)
    
    def remove_data_from_list(self,data_name):
        pass
        
    def return_checked_sensor_list(self): 
        checked_items={"Temperatures":[], "Clocks":[]}
        
        for index in range(self.temperatureSensorList.count()):
            if self.temperatureSensorList.item(index).checkState() == Qt.Checked:
                checked_items['Temperatures'].append(self.temperatureSensorList.item(index).text())
        
        for index in range(self.clockSensorList.count()):
            if self.clockSensorList.item(index).checkState() == Qt.Checked:
                checked_items['Clocks'].append(self.clockSensorList.item(index).text())
        print(checked_items)
        return checked_items
    
    def dt_dialChanged(self): 
        self.dt_label.setText(str(self.dt_dial.value()*0.5) + ' s')
    
    def progressBar_setValue(self, time_tuple):
        elapsed=time_tuple[0]
        totalTime=time_tuple[1]
        self.progressBar.setValue(min(elapsed/(totalTime+0.1)*100,100))
        self.progressLabel.setText(str(int(elapsed)) + '/' + str(int(totalTime)))
    def set_filePathInit(self):
        self.pathLabel.setText(os.getcwd())
    
    def set_filePath(self):
        folderName = QtWidgets.QFileDialog.getExistingDirectory(self, 'Choose the Save Directory')
        if (folderName):
            self.pathLabel.setText(folderName)
            print(folderName)
        
    ### graph related

    def clear_graphs(self):
        self.temp_fig.data=[]
        self.clock_fig.data=[]
        self.ext_temp_fig.data=[]
        self.ext_humidity_fig.data=[]
        self.qdash.clearGraph=True
        self.dataNameList.clear()
        
    def clear_selected_graph(self):
        it=self.dataNameList.takeItem(self.dataNameList.currentRow())
        if(it):
            data_name=str(it.text())
            del it
            self.clear_graph_with_data_name(self.temp_fig,data_name)
            self.clear_graph_with_data_name(self.clock_fig,data_name)
            self.clear_graph_with_data_name(self.ext_temp_fig,data_name)
            self.clear_graph_with_data_name(self.ext_humidity_fig,data_name)

            
    def clear_graph_with_data_name(self, fig, data_name):
        data_list=list(fig.data)
        filtered_data_list=[data for data in data_list if not(data.legendgroup == data_name) ]
        #print(filtered_data_list)
        fig.data=tuple(filtered_data_list)
        self.qdash.clearGraph=True
        
    def show_temp_graph(self):
        #self.temp_graph_browser.setHtml(self.temp_fig.to_html(include_plotlyjs='cdn'))
        print(self.temp_fig)
        
    def show_clock_graph(self):
        #self.clock_graph_browser.setHtml(self.clock_fig.to_html(include_plotlyjs='cdn'))
        print(self.clock_fig)

# ---- Main Loops
app = QtWidgets.QApplication(sys.argv)
window = MyApp()
window.show()
sys.exit(app.exec_())



