# -*- coding: utf-8 -*-
"""
Created on Mon Jan 31 21:31:34 2022

@author: HPreal
"""

import ext_manager
url_list=['http://192.168.184.60']
a=ext_manager.ext_sensor_collector(url_list)
print(a.get_data())