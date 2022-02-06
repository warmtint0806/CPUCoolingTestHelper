# -*- coding: utf-8 -*-
"""
Created on Thu Jan 27 16:52:39 2022

@author: HPreal
"""
import requests

class ext_sensor_collector():
    def __init__(self, ip_list):
        self.url_list=[]
        for ip in ip_list:
            self.url_list.append('http://' + ip)
    def get_data(self):
        data_list=[]
        for url in self.url_list:
            data=None
            try:
                data=requests.get(url).json()
            except:
                print("a connection error has occured")
            if data:
                data_list.append(data)
        return data_list