import pylink
import time
import threading
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

TARGET = "NRF52832_XXAA"       # or your exact target
CHANNEL = 0
READ_BYTES = 256

jlink = pylink.JLink()
jlink.open()
jlink.set_tif(pylink.enums.JLinkInterfaces.SWD)
jlink.connect(TARGET)
jlink.rtt_start()

print("RTT connected!")

cap_data = []
lock = threading.Lock()


# ------------------------
# RTT Reader Thread
# ------------------------
def rtt_reader():
    partial = ""

    while True:
        data = jlink.rtt_read(CHANNEL, READ_BYTES)

        if not data:
            time.sleep(0.005)
            continue

        # convert list → bytes (pylink sometimes returns list)
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

                # Expect ONLY capacitance value
                try:
                    cap = float(line)  # parse single number
                    cap_data.append(cap)
                except:
                    pass


reader = threading.Thread(target=rtt_reader, daemon=True)
reader.start()


# ------------------------
# Live Plot (Cap Only)
# ------------------------
plt.style.use("ggplot")
fig, ax = plt.subplots()
line_cap, = ax.plot([], [], label="Capacitance (pF)")
ax.legend()


def update(frame):
    with lock:
        xs = list(range(len(cap_data)))
        cap = cap_data[:]

    if len(xs) < 3:
        return line_cap,

    # Show last 300 samples
    window = 300
    xs = xs[-window:]
    cap = cap[-window:]

    line_cap.set_data(xs, cap)

    ax.set_xlim(xs[0], xs[-1])

    ax.set_ylim(-5, 1023)

    return line_cap,


ani = FuncAnimation(fig, update, interval=30)
plt.show()
