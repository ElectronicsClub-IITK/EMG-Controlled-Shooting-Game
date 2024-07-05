import sys
import serial
import threading
import numpy as np
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from scipy.signal import butter, filtfilt, hilbert
import time
import socket
import time
from collections import deque


host, port = "127.0.0.1", 65432      
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))


def configure_serial(port, baud_rate):
    return serial.Serial(port, baud_rate, timeout=1)

# Function to create a lowpass filter
def butter_lowpass_filter(data, cutoff, fs, order):
    nyq = 0.5 * fs
    normal_cutoff = cutoff / nyq
    b, a = butter(order, normal_cutoff, btype='low', analog=False)
    y = filtfilt(b, a, data)
    return y

# Function to calculate envelope using Hilbert transform
def calculate_envelope(data):
    analytic_signal = hilbert(data)
    envelope = np.abs(analytic_signal)
    return envelope

# Serial configuration
ser = configure_serial('COM10', 230400)  # Replace with your serial port
# Filter parameters
fs = 512     # sample rate, Hz
cutoff = 9
order = 5

# Threshold for detecting sudden changes in the envelope
THRESHOLD_HIGH = 15
THRESHOLD_HIGH2 = 10 # Adjust as needed based on your signal characteristics
THRESHOLD_LOW = 6

# Create application instance
app = pg.mkQApp()

# Create a window and plot
win = pg.GraphicsLayoutWidget(show=True, title="Real-time Data Plot")
win.setWindowTitle('Real-time Data Plot')

# Create plots for the two data channels
plot1 = win.addPlot(title="Real-time Data Channel 1")
curve_raw1 = plot1.plot(pen='y', name='Raw Data 1')
curve_env1 = plot1.plot(pen='g', name='Envelope 1')
plot1.showGrid(x=True, y=True)
reference_line1_ch1 = pg.InfiniteLine(angle=0, pos=THRESHOLD_LOW, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
reference_line2_ch1 = pg.InfiniteLine(angle=0, pos=0, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
reference_line3_ch1 = pg.InfiniteLine(angle=0, pos=THRESHOLD_HIGH, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
plot1.addItem(reference_line1_ch1)
plot1.addItem(reference_line2_ch1)
plot1.addItem(reference_line3_ch1)

plot2 = win.addPlot(title="Real-time Data Channel 2")
curve_raw2 = plot2.plot(pen='y', name='Raw Data 2')
curve_env2 = plot2.plot(pen='g', name='Envelope 2')
plot2.showGrid(x=True, y=True)
reference_line1_ch2 = pg.InfiniteLine(angle=0, pos=THRESHOLD_LOW, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
reference_line2_ch2 = pg.InfiniteLine(angle=0, pos=0, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
reference_line3_ch2 = pg.InfiniteLine(angle=0, pos=THRESHOLD_HIGH2, pen=pg.mkPen('r', style=pg.QtCore.Qt.DashLine))
plot2.addItem(reference_line1_ch2)
plot2.addItem(reference_line2_ch2)
plot2.addItem(reference_line3_ch2)

# Add plots vertically
win.nextRow()
win.addItem(plot1)
win.nextRow()
win.addItem(plot2)

data1 = []
data2 = []

# Function to read data from the serial port
def read_from_serial():
    global data1, data2
    while True:
        if ser.in_waiting:
            try:
                line = ser.readline().decode().strip()
                values = line.split(',')
                if len(values) == 2 and values[0].isdigit() and values[1].isdigit():
                    value1 = int(values[0])
                    value2 = int(values[1])
                    data1.append(value1)
                    data2.append(value2)
                    if len(data1) > 1000:
                        data1.pop(0)
                    if len(data2) > 1000:
                        data2.pop(0)
            except Exception as e:
                print(f"Error reading from serial: {e}")

# Function to detect sudden changes in envelope
def detect_changes(envelope):
    envelope_value = np.max(envelope[600:800])
    if envelope_value > THRESHOLD_HIGH:
        return 1
    elif THRESHOLD_LOW <= envelope_value <= THRESHOLD_HIGH:
        return 0

def detect_changes2(envelope):
    envelope_value = np.max(envelope[600:800])
    if envelope_value > THRESHOLD_HIGH2:
        return 1
    elif THRESHOLD_LOW <= envelope_value <= THRESHOLD_HIGH:
        return 0
# Function to update the plot and detect changes

def update_plot():
    global data1, data2
    if len(data1) > 0 and len(data2) > 0:
        # Process data for channel 1
        mean_value1 = np.mean(data1)
        centered_data1 = np.array(data1) - mean_value1
        filtered_data1 = butter_lowpass_filter(centered_data1, cutoff, fs, order)
        envelope1 = calculate_envelope(filtered_data1)
        curve_env1.setData(envelope1[50:950])
        # Process data for channel 2
        mean_value2 = np.mean(data2)
        centered_data2 = np.array(data2) - mean_value2
        filtered_data2 = butter_lowpass_filter(centered_data2, cutoff, fs, order)
        envelope2 = calculate_envelope(filtered_data2)
        curve_env2.setData(envelope2[50:950])
    
        x2 = detect_changes2(envelope2)
        x1 = detect_changes(envelope1)
        if x1 !=None and x2 != None:
            x2=0
            print(x2*2)
            x2=str(2*x2)
            sock.sendall(x2.encode("utf-8"))
        elif x2 is not None :
            if x1 is None :
                x2 =1
            print(x2*2)
            x2=str(2*x2)
            sock.sendall(x2.encode("utf-8"))
        elif x1 is not None :
            if x2 is None:
                x1 =1
            print(f"{x1}")
            x1=str(x1)
            sock.sendall(x1.encode("utf-8"))

# Set up a timer to call the update function
timer = QtCore.QTimer()
timer.timeout.connect(update_plot)
timer.start(50)

# Start the serial reading thread
serial_thread = threading.Thread(target=read_from_serial)
time.sleep(2)
serial_thread.daemon = True
serial_thread.start()

# Start the Qt event loop
if __name__ == '__main__':
    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        ser.close()
        sock.close()
        print("Serial port closed.")
