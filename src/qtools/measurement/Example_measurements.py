# -*- coding: utf-8 -*-
"""
Created on Tue Feb  9 19:08:46 2021

@author: till3
"""

#%%
import time
import qcodes as qc
from qtools.instrument_drivers.Harvard.FZJ_Decadac import Decadac
from qcodes.instrument_drivers.stanford_research.SR830 import SR830
from qcodes.instrument_drivers.tektronix.Keithley_2450 import Keithley2450
from qcodes.instrument_drivers.tektronix.Keithley_2400 import Keithley_2400
# from qcodes.instrument_drivers.ZI.ZIMFLI0 import ZIMFLI
import qcodes.instrument_drivers.Lakeshore.Model_325 as ls #Temperature sensor
import os
#Magnet Power Supply missing here
from qcodes.tests.instrument_mocks import DummyInstrument

from qcodes.plots.pyqtgraph import QtPlot
from qcodes.instrument.parameter import ManualParameter
from qcodes.instrument.parameter import Parameter
from qcodes.utils.validators import Numbers

from qcodes.plots.qcmatplotlib import MatPlot
#%%
from . import gate_mapping as gm
from . import get_from_station as gfs

import numpy as np

from importlib import reload
from qcodes.data import hdf5_format
from qcodes import actions

#%% Setup all instruments needed
qc.Instrument.close_all()

dac = Decadac('dac', 'ASRL4::INSTR', default_switch_pos=1) #-1=left, 0=middle, 1=right
#dac = Decadac('dac', 'ASRL10::INSTR', default_switch_pos=1) #-1=left, 0=middle, 1=right
dac.channels.switch_pos.set(1)
dac.channels.update_period.set(50)
dac.channels.ramp(0,0.3)


''' Issues:
    -Need to set switch_position manually for each channel after initalization
    -....ChanX.volt.set() is somewhy limited by the upper/lower ramp limit. You need to set
         ChanX._set_upper_limit(val of max volt in dac code (usually 65535)) in order to use the set command.
    -....ChanX.ramp(V,rate) does work, but requires ....ChanX.update_period() to
     be set manually beforehand

     -> Updated driver available?


'''


lockin=SR830("lockin",'GPIB1::12::INSTR')


#%%
keithley=Keithley_2400('keithley', 'GPIB1::26:INSTR')
# keithley=Keithley_2401('keithley', 'GPIB1::27::INSTR')
#keithley2=Keithley2450('keithley2', 'GPIB1::23::INSTR')

#%% Add dummy/virtual instruments here
t0=time.time()
def experiment_time(t0=t0):
      t= round((time.time()-t0),4)
      return t


clock = DummyInstrument (name="clock")#'runtime', gates=['clock1'])
clock.add_parameter('time', unit = 's', get_cmd= experiment_time)


#Add the clock to the station- it now works like a "real" instrument
#station.add_component(clock)

#Define a counter, that can be used in combination with the "sweep" function
#later in order to define the measurement loops
counter=DummyInstrument(name="dummy2")
counter.add_parameter('count', set_cmd=None)

#%% Add instruments to the station


station=qc.Station(dac, lockin, clock, counter, keithley)#, keithley2)

print('station is now set up with the following instruments:\n %s',
      station.components)



#%% Set location here

#I recommend to add a scheme for the folder structure as a comment here asap
location='C:/Users/lab2/data/Huckemann/IMEC/AL809789 D2 SD17/QBB16_6_3/4K/SET2/Cooldown1/Inducing/{counter}_{name}'
#location='data/IMEC/linetest'
# loc_provider = qc.data.location.FormatLocation(fmt=location)
# qc.data.data_set.DataSet.location_provider=loc_provider
loc_provider = qc.FormatLocation(location)
#%%
default_loc='data/IMEC/Sample3/G21QB01/4K/Cooldown/TestGates/G4_2D/{counter}_{name}'
default_form='#{counter}_{name}'

def set_location(folder, form):
    location=folder+form
    try:
        loc_provider = qc.data.location.FormatLocation(fmt=location)
        qc.data.data_set.DataSet.location_provider=loc_provider
        return None
    except:
        print("Exception in set_locatoin: Could not set location for saving data. Please check the format")
        return None




#%%
def ramp_keithley(value, device=keithley, step=0.1, wait=0.1):
      if keithley.IDN.get()['model'] == "2405":
          if not device.output_enabled.get():
                print("Device output is off. Please enable device output first")
                return False
          if not device.source_function.get()=='voltage':
                print("Ramping only supported for devices in voltage-source mode. Please set source_funtion to voltage")
                return False

          try:
                if device.source.voltage.get()==value:
                      print("Target value already reached")
                      return True
                if device.source.voltage.get()>value:
                      step*=-1


                set_value=device.source.voltage.get()
                while set_value<value-np.abs(step) or set_value>value+np.abs(step):
                      set_value+=step
                      device.source.voltage.set(set_value)

                      time.sleep(wait)

                device.source.voltage.set(value)

                return True
          except:
                print("Something went wrong")
      else:
          if not device.output.get():
                print("Device output is off. Please enable device output first")
                return False
          if not device.mode.get()=='VOLT':
                print("Ramping only supported for devices in voltage-source mode. Please set source_funtion to voltage")
                return False

          try:
                if device.volt.get()==value:
                      print("Target value already reached")
                      return True
                if device.volt.get()>value:
                      step*=-1


                set_value=device.volt.get()
                while set_value<value-np.abs(step) or set_value>value+np.abs(step):
                      set_value+=step
                      device.volt.set(set_value)

                      time.sleep(wait)

                device.volt.set(value)

                return True
          except:
                print("Something went wrong")






#%%

def sweep_1D(gate_channel, gate_volt_range, gate_volt_step, lockin, lockin_ampl, lockin_freq=None, lockin_mult=1, repetitions=1, location=loc_provider, delay=0.05):
    gate_channel.ramp(gate_volt_range[0],0.1)
    time.sleep(5)
    #Lock-in
    try:
        if lockin_freq!=None:
            lockin.frequency.set(lockin_freq)
    except:
        print("Exception in sweep_1D: Could not set lock-in frequency")
    try:
        lockin.amplitude.set(lockin_ampl)
    except:
        print("Exception in sweep_1D: Could not set lock-in amplitude")

    HDF_format = qc.data.hdf5_format.HDF5Format()
    sweep_up=qc.Loop(gate_channel.volt.sweep(gate_volt_range[0],gate_volt_range[1],gate_volt_step), delay=0.1).each(gate_channel.volt, lockin.R, clock.time)
    sweep_down=qc.Loop(gate_channel.volt.sweep(gate_volt_range[1],gate_volt_range[0],-gate_volt_step), delay=0.1).each(gate_channel.volt, lockin.R, clock.time)
    data_up=sweep_up.get_data_set(name="Pinchoff_up", location = loc_provider, formatter = HDF_format)
    data_down=sweep_down.get_data_set(name="Pinchoff_down", location =loc_provider, formatter = HDF_format)
    plot=qc.QtPlot()
    plot.add(data_up.lockin_R)
    plot.add(data_down.lockin_R)
    #myloop.run()
    sweep_up.with_bg_task(plot.update).run()
    sweep_down.with_bg_task(plot.update).run()
    HDF_format.close_file(data_up)
    HDF_format.close_file(data_down)


#%%

def sweep_topgate(gate_channel, gate_volt_range, gate_volt_step, lockin, lockin_ampl, lockin_freq=None, lockin_mult=1, repetitions=5, location=loc_provider, delay=0.05):
    gate_channel.output.set(1)
    gate_channel.volt.set(0)
    time.sleep(1)
    print("Ramped gate to "+str(gate_channel.volt.get())+ " Volt")

    #Lock-in
    try:
        if lockin_freq!=None:
            lockin.frequency.set(lockin_freq)
    except:
        print("Exception in sweep_1D: Could not set lock-in frequency")
    try:
        lockin.amplitude.set(lockin_ampl)
    except:
        print("Exception in sweep_1D: Could not set lock-in amplitude")

    plot=qc.QtPlot()
    HDF_format = qc.data.hdf5_format.HDF5Format()
    for i in range(0,repetitions):
        sweep_up=qc.Loop(gate_channel.volt.sweep(gate_volt_range[0],gate_volt_range[1],gate_volt_step), delay=0.1).each(gate_channel.volt, gate_channel.curr, lockin.R, lockin.P, clock.time)
        sweep_down=qc.Loop(gate_channel.volt.sweep(gate_volt_range[1],gate_volt_range[0],-gate_volt_step), delay=0.1).each(gate_channel.volt, gate_channel.curr, lockin.R, lockin.P, clock.time)
        data_up=sweep_up.get_data_set(name="sweep_up",
                                      location = loc_provider)#, formatter = HDF_format)
        data_down=sweep_down.get_data_set(name="sweep_down",
                                          location = loc_provider)#, formatter = HDF_format)

        plot.add(data_up.lockin_R, subplot=1)
        plot.add(data_down.lockin_R, subplot=1)
        plot.add(data_up.keithley_curr, subplot = 2)
        plot.add(data_down.keithley_curr, subplot = 2)
        plot.add(data_up.lockin_P, subplot = 3)
        plot.add(data_down.lockin_P, subplot = 3)

        #plot.add(x=data_down.dac_Slot0_Chan0_volt, y=data_down.lockin_X)



        sweep_up.with_bg_task(plot.update).run()
        sweep_down.with_bg_task(plot.update).run()
        HDF_format.close_file(data_up)
        HDF_format.close_file(data_down)

    return data_up, data_down



#%%

def sweep_topgate_keithley(keithley, gate_volt_range, gate_volt_step, lockin, lockin_ampl, lockin_freq=None, lockin_mult=1, repetitions=5, location=loc_provider, delay=0.05):

    """
    Sweep topgate with Keithley connected for checking topgate leakage

    """

    keithley.source_function.set('voltage')
    keithley.sense_function.set('current')
    volt=keithley.source.voltage
    current=keithley.sense.current
    volt.set(0)
    keithley.source.limit.set(0.5e-6)
    keithley.output_enabled.set(1)
    #Lock-in
    try:
        if lockin_freq!=None:
            lockin.frequency.set(lockin_freq)
    except:
        print("Exception in sweep_1D: Could not set lock-in frequency")
    try:
        lockin.amplitude.set(lockin_ampl)
    except:
        print("Exception in sweep_1D: Could not set lock-in amplitude")


    plot=qc.QtPlot()


    for i in range(0,repetitions):
        sweep_up=qc.Loop(volt.sweep(gate_volt_range[0],gate_volt_range[1],gate_volt_step), delay=0.1).each(current, lockin.R, lockin.P, clock.time)
        sweep_down=qc.Loop(volt.sweep(gate_volt_range[1],gate_volt_range[0],-gate_volt_step), delay=0.1).each(current, lockin.R, lockin.P , clock.time)
        data_up=sweep_up.get_data_set(name="sweep_up")
        data_down=sweep_down.get_data_set(name="sweep_down")

        plot.add(data_up.lockin_R, subplot=1)
        plot.add(data_down.lockin_R, subplot=1)
        plot.add(data_up.keithley_sense_current, subplot=2)
        plot.add(data_down.keithley_sense_current, subplot=2)
        plot.add(data_up.lockin_P, subplot=3)
        plot.add(data_down.lockin_P, subplot=3)
        #plot.add(x=data_down.dac_Slot0_Chan0_volt, y=data_down.lockin_X)


        sweep_up.with_bg_task(plot.update).run()
        sweep_down.with_bg_task(plot.update).run()




    #myloop.run()


#%%

def sweep_topgate_leakage(keithley, gate_volt_range, gate_volt_step, lockin, lockin_ampl, lockin_freq=None, lockin_mult=1, repetitions=5, location=set_location(default_loc, default_form), delay=0.05, barrier=keithley2):

    """
    Barriergates connecteced to another keithley to check barrier leakage as well
    """

    keithley.source_function.set('voltage')
    keithley.sense_function.set('current')
    volt=keithley.source.voltage
    current=keithley.sense.current
    current2=barrier.sense.current
    volt.set(0)
    keithley.source.limit.set(0.5e-6)
    keithley.output_enabled.set(1)
    #Lock-in
    try:
        if lockin_freq!=None:
            lockin.frequency.set(lockin_freq)
    except:
        print("Exception in sweep_1D: Could not set lock-in frequency")
    try:
        lockin.amplitude.set(lockin_ampl)
    except:
        print("Exception in sweep_1D: Could not set lock-in amplitude")


    plot=qc.QtPlot()


    for i in range(0,repetitions):
        sweep_up=qc.Loop(volt.sweep(gate_volt_range[0],gate_volt_range[1],gate_volt_step), delay=0.1).each(current, lockin.R, current2, clock.time)
        sweep_down=qc.Loop(volt.sweep(gate_volt_range[1],gate_volt_range[0],-gate_volt_step), delay=0.1).each(current, lockin.R, current2, clock.time)
        data_up=sweep_up.get_data_set(name="sweep_up")
        data_down=sweep_down.get_data_set(name="sweep_down")

        plot.add(data_up.lockin_R, subplot=1)
        plot.add(data_down.lockin_R, subplot=1)
        plot.add(data_up.keithley_sense_current, subplot=2)
        plot.add(data_down.keithley_sense_current, subplot=2)
        plot.add(data_up.keithley2_sense_current, subplot=2)
        plot.add(data_down.keithley2_sense_current, subplot=2)
        #plot.add(x=data_down.dac_Slot0_Chan0_volt, y=data_down.lockin_X)


        sweep_up.with_bg_task(plot.update).run()
        sweep_down.with_bg_task(plot.update).run()




    #myloop.run()


#%%
def sweep_2D(topgate_channel, topgate_volt, topgate_leakage, bar1_channel, bar2_channel, bar1_range, bar2_range, gate_volt_step, lockin, lockin_ampl, lockin_freq=None, lockin_mult=1, repetitions=5, location=loc_provider, delay=0.05,i=0):
      if topgate_volt>4.6:
            print("Exception: Topgate voltage to high.")
            if input("Do you want to continue [y/n]")!="y":
                  return None

      topgate_channel.set(topgate_volt)
      bar1_channel.ramp(0,0.2)
      bar2_channel.ramp(0,0.2)
      time.sleep(15)
      print("Done with waiting")
      HDF_format = qc.data.hdf5_format.HDF5Format()
      myloop=qc.Loop(bar1_channel.volt.sweep(bar1_range[0],bar1_range[1],gate_volt_step), delay=2).loop(bar2_channel.volt.sweep(bar2_range[0],bar2_range[1], gate_volt_step),delay=0.1).each(bar1_channel.volt, bar2_channel.volt, lockin.R,topgate_leakage,topgate_channel, clock.time)
      data=myloop.get_data_set(name="data", location = loc_provider, formatter = HDF_format)
      plot=qc.QtPlot()
      plot.add(data.lockin_R, subplot=1)
      plot.add(data.keithley_curr, subplot=2)
      myloop.with_bg_task(plot.update).run()


      #plot.save(default_loc+"plot"+str(i)+".png")
      # save=input("Do you want to save the plot? (y/n)")
      # if save=="y" or save=="Y":
      #       filename=input("Please enter a filename (with extension)")
      #       try:
      #             plot.save(default_loc+filename)
      #       except:
      #             print("Could not save as " + default_loc+filename)

#%% timetrace

dac.channels[0].ramp(0.480, 0.2)
dac.channels[1].ramp(0.522, 0.2)
time.sleep(10)

HDF_format = qc.data.hdf5_format.HDF5Format()

loop = qc.Loop(counter.count.sweep(0,600,1),delay=1).each(lockin.R, clock.time, lockin.X, lockin.phase, dac.channels[0].volt, dac.channels[1].volt)
data = loop.get_data_set(name = "data", location = loc_provider, formatter = HDF_format)
plot = qc.QtPlot()
plot.add(data.lockin_R)
loop.with_bg_task(plot.update).run()



#%% Differential 2D pinchoff
tg_voltages=[4.4, 4.45, 4.5, 4.4]

for i in tg_voltages:
      sweep_2D(topgate_channel=keithley.source.voltage, topgate_volt=i, topgate_leakage=keithley.sense.current, bar1_channel=dac.channels[0], bar2_channel=dac.channels[1], bar1_range=[0.85, 0.92], bar2_range=[0.99, 1.06], gate_volt_step=0.002, lockin=lockin, lockin_ampl=1, location=set_location(default_loc, '#{counter}_{name}_TG'+str(i)))


#%%
gate_voltages=[0.06, 0.09, 0.120, 0.15, 0.18, 0.15, 0.12, 0.09, 0.06]
for i in gate_voltages:
      dac.channels[6].ramp(i, 0.1)
      time.sleep(10)
      sweep_2D(topgate_channel=keithley.source.voltage, topgate_volt=4.5, topgate_leakage=keithley.sense.current, bar1_channel=dac.channels[0], bar2_channel=dac.channels[1], bar1_range=[0.9, 0.93], bar2_range=[1.02, 1.05], gate_volt_step=0.0005, lockin=lockin, lockin_ampl=1, location=set_location(default_loc, '#{counter}_{name}_G3_second_attempt'+str(i)))

dac.channels.ramp(0,0.1)
for j in gate_voltages:
      dac.channels[7].ramp(j, 0.1)
      time.sleep(10)
      sweep_2D(topgate_channel=keithley.source.voltage, topgate_volt=4.5, topgate_leakage=keithley.sense.current, bar1_channel=dac.channels[0], bar2_channel=dac.channels[1], bar1_range=[0.9, 0.93], bar2_range=[1.02, 1.05], gate_volt_step=0.0005, lockin=lockin, lockin_ampl=1, location=set_location(default_loc, '#{counter}_{name}_G4_'+str(j)))
#%%
loop=qc.Loop(lockin.amplitude.sweep(0.004,1,0.001),delay=0.05).each(keithley.sense.current, lockin.R)
data=loop.get_data_set(name="Leakage")
plot=qc.QtPlot()
plot.add(data.keithley_sense_current, subplot=1)
plot.add(data.lockin_R, subplot=2)
loop.with_bg_task(plot.update).run()

#%%
sweep_2D(keithley.source.voltage, 4.5, keithley.sense.current, dac.channels[1], dac.channels[0], [0.44,0.64], [0.44,0.64], 0.0005, lockin, 1, repetitions=1)

#%%
def sweep_diamonds(topgate_channel=keithley.source.voltage, topgate_volt=4.6, bar_channel=dac.channels[0], bar_range=[1.12,1.22], gate_volt_step=0.001, lockin=lockin, lockin_ampl_range=[0.02,3],lockin_step=0.02, lockin_freq=None, lockin_mult=1, repetitions=1, location=set_location(default_loc, default_form), delay=0.05):
      if topgate_volt>4.6:
            print("Exception: Topgate voltage to high.")
            return None
      topgate_channel.set(topgate_volt)
      bar_channel.ramp(bar_range[0],0.2)

      time.sleep(15)
      print("Done with waiting")

      myloop=qc.Loop(bar_channel.volt.sweep(bar_range[0],bar_range[1],gate_volt_step), delay=0.1).loop(lockin.amplitude.sweep(lockin_ampl_range[0],lockin_ampl_range[1], lockin_step),delay=0.1).each(bar_channel.volt, lockin.R,lockin.P, clock.time)
      data=myloop.get_data_set(name="data")
      plot=qc.QtPlot()
      plot.add(data.lockin_R)
      myloop.with_bg_task(plot.update).run()

      save=input("Do you want to save the plot? (y/n)")
      if save=="y" or save=="Y":
            filename=input("Please enter a filename (with extension)")
            try:
                  plot.save(default_loc+filename)
            except:
                  print("Could not save as " + default_loc+filename)





#%% Example: How to wait at the end of each iteration of the inner loop

testloop=qc.Loop(counter.count.sweep(0,5,1)).each(qc.Loop(lockin.amplitude.sweep(0.1,1,0.1),delay = 0.1).each(clock.time).then(Wait(10)))
data=testloop.get_data_set(name="mytest")
plot = qc.QtPlot()
plot.add(data.clock_time)
testloop.with_bg_task(plot.update).run()

#%%
for i in range(6, 9, 1):
    sweep_2D(topgate_channel = keithley.volt, topgate_volt = i/2, topgate_leakage= keithley.curr,
             bar1_channel=dac.channels[0], bar2_channel=dac.channels[1], bar1_range=[0.32,1.2], bar2_range=[0.32,1.2],
             gate_volt_step=0.02, lockin=lockin, lockin_ampl=1)

#%%

mytest = qc.Loop(counter.count.sweep(0,100,1), delay= 0.001).each(lockin.R, lockin.P, clock.time)
data = mytest.get_data_set(name = "lockin_Test")
plot = qc.QtPlot()
plot.add(data.lockin_R, subplot = 1)
plot.add(data.lockin_P, subplot = 2)
plot.add(data.clock_time, subplot = 3)

mytest.with_bg_task(plot.update).run()
