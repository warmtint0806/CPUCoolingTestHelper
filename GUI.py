#!/usr/bin/env python
# coding: utf-8

import wmi
import os
import time
from datetime import datetime
import json
import pythoncom

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


# --- QDash

class QDash(QObject):
    def __init__(self, temp_fig, clock_fig, parent=None):
        super().__init__(parent)

        self._app = dash.Dash()
        self._app.layout = html.Div(html.Div([
                html.H4("It's a beautiful day for yet another experiment"),
                html.H5('CPU temperatures'),
                dcc.Graph(id='live-update-graph'),
                html.H5('CPU clocks'),
                dcc.Graph(id='live-update-graph2'),
                dcc.Interval(id='interval-component',
                             interval=1*2000,
                             n_intervals=0)
                ]))
        self.temp_fig=temp_fig
        self.clock_fig=clock_fig
    
        @self._app.callback(Output('live-update-graph', 'figure'),Input('interval-component','n_intervals'))
        def update_graph(n):
            return self.temp_fig
        
        @self._app.callback(Output('live-update-graph2', 'figure'),Input('interval-component','n_intervals'))
        def update_graph2(n):
            return self.clock_fig
    @property
    def app(self):
        return self._app

    def run(self, **kwargs):
        threading.Thread(target=self.app.run_server, kwargs=kwargs, daemon=True).start()

# ---- Collecting Workers 
        
qtcreator_file  = "main.ui" # Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtcreator_file)

class WorkerSignals(QObject): 
    finished=pyqtSignal()
    progress=pyqtSignal(tuple)
    inspectionDone=pyqtSignal(dict)

class Worker(QRunnable):
    def __init__(self,temp_fig,clock_fig,dt,totaltime,trialName,filepath,temp_sensors,clock_sensors):
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

    def add_fig_traces(self,fig,idx_names):
        for name in idx_names:
            data=go.Scatter(x=[],y=[],name=name)
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
        self.start_record2(self.temp_fig,self.clock_fig,self.dt,self.totaltime)
        self.signals.finished.emit()
        
    def start_record2(self, temp_fig, clock_fig, dt, totaltime):
        #dt=0.5
        #totaltime=60
        trial_name=self.trialName
        
        #data_name=[trial_name+'CPU Package Power','CPU Package T', 'C#1 T', 'C#2 T']
        data_name=self.temp_sensors.copy()
        data_name[0]=trial_name + '_' + data_name[0]
        self.add_fig_traces(temp_fig,data_name)
    
        #data_name=[trial_name + 'C#1 clock', 'C#2 clock']
        data_name=self.clock_sensors.copy()
        data_name[0]=trial_name + '_' + data_name[0]
        self.add_fig_traces(clock_fig,data_name)
    
        result={"time":[],"elp_time":[]}
        init_time=time.time()
        pythoncom.CoInitialize()
        self.w=wmi.WMI(namespace="root\OpenHardwareMonitor")
        
        while True: 
            current_time=time.time()
            elapsed=current_time-init_time
        
            self.record_data(result,current_time,elapsed,self.w.Sensor())
            
            data_to_draw=[]
            clock_data_to_draw=[]
            for temp_sensor in self.temp_sensors:
                data_to_draw.append(result[temp_sensor]['Temperature'][-1])
            for clock_sensor in self.clock_sensors:
                clock_data_to_draw.append(result[clock_sensor]['Clock'][-1])
            #data_to_draw=[
            #       #result['CPU Package']['Power'][-1],
            #       result['CPU Package']['Temperature'][-1],
            #       result['CPU Core #1']['Temperature'][-1],
            #       result['CPU Core #2']['Temperature'][-1]]
    
            #clock_data_to_draw=[
            #       result['CPU Core #1']['Clock'][-1],
            #       result['CPU Core #2']['Clock'][-1]]
    
            self.update_fig_traces(temp_fig,elapsed,data_to_draw)
            self.update_fig_traces(clock_fig,elapsed,clock_data_to_draw)
            
            time.sleep(dt)
            self.signals.progress.emit((elapsed,totaltime))
            
            if elapsed>totaltime: 
                break
        
        pythoncom.CoUninitialize()
        filename=self.filepath+'/'+trial_name+'_'+datetime.now().strftime('%Y%m%d-%H_%M_%S')+'.json'
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
        
class MyApp(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.temp_fig=go.Figure()
        self.temp_fig.update_layout(width=1000,height=450, 
                                    margin=dict(l=20, r=20, t=0, b=0), 
                                    transition={
                                        'duration': 500,
                                        'easing': 'cubic-in-out'
                                    })
        self.clock_fig=go.Figure()
        self.clock_fig.update_layout(width=1000,height=450, 
                                     margin=dict(l=20, r=20, t=0, b=0),
                                      transition={
                                        'duration': 500,
                                        'easing': 'cubic-in-out'
                                    })

        print(self.temp_fig)
        self.threadpool=QThreadPool()
        print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())
        
        #ui related
        self.runButton.clicked.connect(self.start_record)
        self.reloadButton.clicked.connect(self.open_graph_in_browser)
        self.dt_dial.valueChanged.connect(self.dt_dialChanged)
        
        self.set_filePathInit()
        self.pathButton.clicked.connect(self.set_filePath)
        
        self.qdash=QDash(temp_fig=self.temp_fig, clock_fig=self.clock_fig)
        self.qdash.run(debug=True, use_reloader=False)
        self.open_graph_in_browser()
        
        self.sensor_check()
        self.cpu_temperature_display_candidate_list=[]
        self.cpu_clock_display_candidate_list=[]
        
    def open_graph_in_browser(self):
        webbrowser.open('http://127.0.0.1:8050',1)
    
    def browser_reload(self): 
        print(self.reloadUrl.text())
        self.temp_graph_browser.load(QUrl(self.reloadUrl.text()))
        self.temp_graph_browser.show()
        
    def start_record(self):
        sensor_to_display=self.return_checked_sensor_list()
        self.worker=Worker(self.temp_fig, self.clock_fig, self.dt_dial.value() *0.5, self.totalTimeBox.value() * 60, 
                           self.trialNameBox.text(),self.pathLabel.text(),
                           sensor_to_display['Temperatures'], sensor_to_display['Clocks'])
        #self.worker.signals.progress.connect(self.show_temp_graph)
        self.worker.signals.progress.connect(self.progressBar_setValue)
        #self.worker.signals.progress.connect(self.show_clock_graph)
        self.threadpool.start(self.worker)
    
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

        print(result)
    
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



