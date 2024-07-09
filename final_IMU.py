import serial
import sys
from PyQt5 import QtWidgets
import pyqtgraph as pg
import numpy as np
import socket

# Set up serial connection
ser = serial.Serial('COM4', 230400)  # Change 'COM9' to the correct port

# Set up TCP connection
TCP_IP = '127.0.0.1'  # Server IP address
TCP_PORT = 5005       # Server port
BUFFER_SIZE = 1024

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((TCP_IP, TCP_PORT))

# Get screen size
screen_width, screen_height = 1920, 1080  # Replace with your screen dimensions if needed

vel_x = 0
vel_y = 0

mouse_x = screen_width / 2
mouse_y = screen_height / 2

a = 4

# PyQt Application
app = QtWidgets.QApplication([])

# Main loop to read data and print the values
def update():
    global mouse_x, mouse_y, vel_x, vel_y

    if ser.in_waiting > 0:
        line = ser.readline().decode('utf-8').strip()
        if line.startswith("Yaw:"):
            parts = line.split()
            yaw = float(parts[1])
            pitch = float(parts[3])
            roll = float(parts[5])

            if roll > 30:
                vel_y = a
            elif roll < -30:
                vel_y = -a
            else:
                vel_y = 0

            if 270 < yaw < 330:
                vel_x = -a
            elif 90 > yaw > 30:
                vel_x = a
            else:
                vel_x = 0

            # Map yaw to screen width
            mouse_x = mouse_x + vel_x
            mouse_y = mouse_y + vel_y

            # Keep within screen bounds
            mouse_x = np.clip(mouse_x, 0, screen_width)
            mouse_y = np.clip(mouse_y, 0, screen_height)

            # Print data
            print(f"mouse_x: {mouse_x}, mouse_y: {mouse_y}")

            # Send data to TCP server
            data = f"{mouse_x},{mouse_y}"
            sock.send(data.encode())

# Timer to update and print values
timer = pg.QtCore.QTimer()
timer.timeout.connect(update)
timer.start(50)  # Update every 50ms

# Start Qt event loop
if __name__ == '__main__':
    if (sys.flags.interactive != 1) or not hasattr(pg.QtCore, 'PYQT_VERSION'):
        QtWidgets.QApplication.instance().exec_()

    ser.close()
    sock.close()
    print("Serial and TCP connection closed.")
