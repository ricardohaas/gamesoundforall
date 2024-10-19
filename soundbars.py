import sys
import sounddevice as sd
import numpy as np
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QWidget, QProgressBar, QInputDialog, QMessageBox
from PyQt5.QtGui import QPainter, QColor
import ctypes

class ClickThroughWindow(QWidget):
    def __init__(self, pos_x, pos_y):
        super().__init__()
        self.initUI(pos_x, pos_y)

    def initUI(self, pos_x, pos_y):
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # Set window transparency and dimensions
        self.setGeometry(pos_x, pos_y, 100, 300)

        # Add a vertical progress bar for volume display
        self.volume_bar = QProgressBar(self)
        self.volume_bar.setGeometry(25, 50, 50, 200)
        self.volume_bar.setOrientation(Qt.Vertical)
        self.volume_bar.setMaximum(100)
        self.volume_bar.setValue(0)
        self.volume_bar.setStyleSheet("QProgressBar {border: 2px solid grey; border-radius: 5px; background: black;}")
        self.show()

    def update_volume(self, volume_level):
        """Update the progress bar with the new volume level."""
        self.volume_bar.setValue(volume_level)

    def paintEvent(self, event):
        # Create a translucent background
        painter = QPainter(self)
        painter.setBrush(QColor(0, 127, 127, 0))
        painter.drawRect(self.rect())

def make_click_through(hwnd):
    """Set the window as transparent to mouse clicks."""
    extended_style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
    ctypes.windll.user32.SetWindowLongW(hwnd, -20, extended_style | 0x80000 | 0x20)

def get_real_time_volume(data, channel):
    """Calculate the volume for the specified channel."""
    if data.size == 0:
        return 0
    volume_norm = np.linalg.norm(data[:, channel]) * 15  # Normalize volume for the channel
    return min(int(volume_norm), 100)  # Scale the volume to 0-100 range

def choose_device():
    """Prompt the user to choose an audio input device."""
    devices = sd.query_devices()  # List all available audio devices
    input_devices = [dev for dev in devices if dev['max_input_channels'] > 0]

    # Show a simple list of input devices
    msg = "\n".join([f"{i}: {dev['name']}" for i, dev in enumerate(input_devices)])
    print("Available input devices:\n" + msg)

    # Get device index from user input
    device_index, ok = QInputDialog.getInt(None, "Choose Input Device", "Enter device number:")
    if ok:
        return input_devices[device_index]['index']
    else:
        sys.exit("No device selected. Exiting...")

def main():
    app = QApplication(sys.argv)

    # Choose an input device
    device_index = choose_device()

    # Get screen dimensions
    screen = app.primaryScreen().geometry()
    screen_width = screen.width()
    screen_height = screen.height()

    # Set positions: left (0, center) and right (screen_width - window_width, center)
    window_width = 100
    window_height = 300
    left_x = 0
    right_x = screen_width - window_width
    center_y = (screen_height - window_height) // 2

    # Create two separate windows, one on the left and one on the right
    window1 = ClickThroughWindow(left_x, center_y)
    window2 = ClickThroughWindow(right_x, center_y)

    # Get the window handles and make them click-through
    hwnd1 = int(window1.winId())  # Cast winId to int for ctypes compatibility
    hwnd2 = int(window2.winId())

    # Apply the click-through effect to both windows
    make_click_through(hwnd1)
    make_click_through(hwnd2)

    # Open an audio stream with stereo channels
    def audio_callback(indata, frames, time, status):
        if status:
            print(status, file=sys.stderr)

        try:
            # Channel 1 (Left) for Window 1
            volume_left = get_real_time_volume(indata, 0)
            window1.update_volume(volume_left)

            # Channel 2 (Right) for Window 2
            volume_right = get_real_time_volume(indata, 1)
            window2.update_volume(volume_right)

        except Exception as e:
            print(f"Error in audio callback: {e}")

    try:
        # Open the InputStream with the user-selected device
        with sd.InputStream(callback=audio_callback, channels=2, device=device_index, blocksize=2048, samplerate=44100):
            # Start PyQt5 event loop
            sys.exit(app.exec_())
    except Exception as e:
        # Handle error gracefully
        QMessageBox.critical(None, "Error", f"Failed to open audio device: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
