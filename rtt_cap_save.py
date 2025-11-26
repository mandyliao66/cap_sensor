import pylink
import time
import threading
import csv
import datetime
import tkinter as tk
from tkinter import filedialog
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button

# ------------------------
# Configuration
# ------------------------
TARGET = "NRF52832_XXAA"
CHANNEL = 0
READ_BYTES = 256

# ------------------------
# Global State
# ------------------------
cap_data = []
lock = threading.Lock()

# Recording State
is_recording = False
csv_file = None
csv_writer = None
start_time = None

# ------------------------
# J-Link Setup
# ------------------------
try:
    jlink = pylink.JLink()
    jlink.open()
    jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
    jlink.connect(TARGET)
    jlink.rtt_start()
    print("RTT connected!")
except Exception as e:
    print(f"Error connecting to J-Link: {e}")
    # We continue so you can see the GUI even if hardware isn't attached
    pass 

# ------------------------
# RTT Reader Thread
# ------------------------
def rtt_reader():
    global is_recording, csv_writer, start_time
    partial = ""

    while True:
        try:
            data = jlink.rtt_read(CHANNEL, READ_BYTES)
        except:
            time.sleep(0.1)
            continue

        if not data:
            time.sleep(0.005)
            continue

        if isinstance(data, list):
            data = bytes(data)

        try:
            s = data.decode(errors="ignore")
        except:
            continue

        partial += s
        lines = partial.split("\n")
        partial = lines[-1]

        with lock:
            for line in lines[:-1]:
                line = line.strip()
                if not line:
                    continue

                try:
                    cap = float(line)
                    cap_data.append(cap)
                    
                    # --- CSV LOGGING LOGIC ---
                    if is_recording and csv_writer:
                        # Calculate relative time or use absolute timestamp
                        t_stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                        elapsed = time.time() - start_time
                        csv_writer.writerow([t_stamp, round(elapsed, 4), cap])
                    # -------------------------

                except ValueError:
                    pass

reader = threading.Thread(target=rtt_reader, daemon=True)
reader.start()

# ------------------------
# Plot & UI Setup
# ------------------------
plt.style.use("ggplot")
fig, ax = plt.subplots()
plt.subplots_adjust(bottom=0.2) # Make room for buttons at the bottom

line_cap, = ax.plot([], [], label="Capacitance (pF)", color='tab:blue')
ax.legend(loc='upper left')
ax.set_title("Live RTT Data")
ax.set_ylim(-5, 1023)

# ------------------------
# Button Logic
# ------------------------
def start_logging(event):
    global is_recording, csv_file, csv_writer, start_time
    
    if is_recording:
        print("Already recording.")
        return

    # Initialize Tkinter safely to hide the main window
    root = tk.Tk()
    root.withdraw() 
    root.attributes('-topmost', True) # Bring dialog to front

    # Open File Dialog
    filepath = filedialog.asksaveasfilename(
        defaultextension=".csv",
        filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        title="Save Log File"
    )
    root.destroy() # Clean up Tkinter

    if not filepath:
        print("Save cancelled.")
        return

    try:
        # Open file in write mode (newline='' is best practice for CSV)
        csv_file = open(filepath, mode='w', newline='')
        csv_writer = csv.writer(csv_file)
        
        # Write Header
        csv_writer.writerow(["Timestamp", "Elapsed_Seconds", "Capacitance"])
        
        start_time = time.time()
        is_recording = True
        
        # Visual feedback
        ax.set_title(f"RECORDING: {filepath.split('/')[-1]}", color='red')
        print(f"Started recording to {filepath}")
        
    except Exception as e:
        print(f"Failed to open file: {e}")

def stop_logging(event):
    global is_recording, csv_file, csv_writer
    
    if not is_recording:
        return

    is_recording = False
    if csv_file:
        csv_file.close()
        csv_file = None
        csv_writer = None
    
    ax.set_title("Live RTT Data (Stopped)", color='black')
    print("Recording stopped.")

# Create Buttons (Axes for button placement)
ax_start = plt.axes([0.15, 0.05, 0.2, 0.075]) # [left, bottom, width, height]
ax_stop = plt.axes([0.4, 0.05, 0.2, 0.075])

btn_start = Button(ax_start, 'Start Rec', color='lightgreen', hovercolor='0.975')
btn_stop = Button(ax_stop, 'Stop Rec', color='salmon', hovercolor='0.975')

btn_start.on_clicked(start_logging)
btn_stop.on_clicked(stop_logging)

# ------------------------
# Animation Update
# ------------------------
def update(frame):
    with lock:
        xs = list(range(len(cap_data)))
        current_data = cap_data[:]

    if len(xs) < 2:
        return line_cap,

    window = 300
    xs = xs[-window:]
    current_data = current_data[-window:]

    line_cap.set_data(xs, current_data)
    
    if xs:
        ax.set_xlim(xs[0], xs[-1])

    return line_cap,

ani = FuncAnimation(fig, update, interval=30, blit=False)
plt.show()

# Cleanup on close
if csv_file:
    csv_file.close()