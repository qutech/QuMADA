import sys
import threading
import multiprocessing as mp
import logging
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QSpinBox, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt, QObject, QMetaObject, Q_ARG, pyqtSlot

# Set up logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
class Parent:
    def __init__(self, name):
        self.name = name

class Parameter:
    def __init__(self, name, parent):
        self.name = name
        self._parent = parent

    def __call__(self):
        return 42  # Beispielwert

    def cached_value(self):
        return 42  # Beispielwert





class Worker(QObject):
    data_ready = pyqtSignal(list)

    def __init__(self, interval, parameters):
        super().__init__()
        self.interval = interval
        self.parameters = parameters
        self.running = True
        self.timer = QTimer()
        self.timer.timeout.connect(self.run)
        self.timer.start(self.interval)
        logging.debug("Worker initialized with interval %d ms", self.interval)

    def run(self):
        if self.running:
            data = [str(param()) for param in self.parameters]
            self.data_ready.emit(data)
            logging.debug("Worker emitted data: %s", data)
            QTimer.singleShot(self.interval, self.run)

    def stop(self):
        self.running = False
        self.timer.stop()
        logging.debug("Worker stopped")

class MeasurementGUI(QWidget):
    def __init__(self, parameters, data_queue):
        super().__init__()
        self.parameters = parameters
        self.data_queue = data_queue
        self.initUI()
        self.start_worker()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Tabelle für Parameter
        self.table = QTableWidget(len(self.parameters), 2)
        self.table.setHorizontalHeaderLabels(["Parameter", "Value"])
        self.layout.addWidget(self.table)

        self.update_table()

        # Intervall-Einstellung
        self.interval_label = QLabel("Intervall (ms):")
        self.layout.addWidget(self.interval_label)

        self.interval_spinbox = QSpinBox()
        self.interval_spinbox.setRange(100, 10000)  # Bereich für das Intervall
        self.interval_spinbox.setValue(1000)  # Standardwert
        self.layout.addWidget(self.interval_spinbox)

        # Platzhalter für gecachte Werte
        self.cached_value_button = QPushButton("Gecachte Werte anzeigen")
        self.cached_value_button.clicked.connect(self.show_cached_values)
        self.layout.addWidget(self.cached_value_button)

        self.setLayout(self.layout)
        self.setWindowTitle('Messsoftware GUI')
        self.show()

        self.interval_spinbox.valueChanged.connect(self.update_interval)
        logging.debug("MeasurementGUI initialized")

    def start_worker(self):
        self.worker_thread = QThread()
        self.worker = Worker(self.interval_spinbox.value(), self.parameters)
        self.worker.moveToThread(self.worker_thread)
        self.worker.data_ready.connect(self.handle_data_ready)
        self.worker_thread.start()
        logging.debug("Worker thread started")

    def update_interval(self):
        self.worker.interval = self.interval_spinbox.value()
        logging.debug("Update interval to %d ms", self.interval_spinbox.value())

    @pyqtSlot(list)
    def handle_data_ready(self, data):
        logging.debug("Handling data ready in main thread: %s", data)
        QMetaObject.invokeMethod(self, "update_table_items", Qt.QueuedConnection, Q_ARG(list, data))

    @pyqtSlot(list)
    def update_table_items(self, data):
        logging.debug("Updating table items in main thread: %s", data)
        for row, value in enumerate(data):
            item = self.table.item(row, 1)
            if item is None:
                self.table.setItem(row, 1, QTableWidgetItem(value))
            else:
                item.setText(value)

    def update_table(self):
        logging.debug("Update table called")
        for row, param in enumerate(self.parameters):
            param_name = f"Param: {param._parent.name} {param.name}"
            self.table.setItem(row, 0, QTableWidgetItem(param_name))
            self.table.setItem(row, 1, QTableWidgetItem(str(param())))

    def show_cached_values(self):
        logging.debug("Show cached values called")
        cached_values = [str(param.cached_value()) for param in self.parameters]
        QMetaObject.invokeMethod(self, "update_table_items", Qt.QueuedConnection, Q_ARG(list, cached_values))

    def closeEvent(self, event):
        logging.debug("Close event called")
        self.worker.stop()
        self.worker_thread.quit()
        self.worker_thread.wait()
        event.accept()
        self.data_queue.put('QUIT')

def start_gui(parameters, data_queue):
    app = QApplication(sys.argv)
    ex = MeasurementGUI(parameters, data_queue)
    ex.show()
    logging.debug("GUI started")
    app.exec_()

def gui_process_main(parameters, data_queue):
    gui_process = mp.Process(target=start_gui, args=(parameters, data_queue))
    gui_process.start()
    return gui_process

def open_gui(parameters):
    data_queue = mp.Queue()
    gui_process = gui_process_main(parameters, data_queue)

    def data_listener():
        while True:
            try:
                data = data_queue.get()
                if data == 'QUIT':
                    break
                print("Received data:", data)
            except KeyboardInterrupt:
                data_queue.put('QUIT')
                gui_process.join()
                break

    listener_thread = threading.Thread(target=data_listener, daemon=True)
    listener_thread.start()

if __name__ == '__main__':
    parent1 = Parent("Parent1")
    parent2 = Parent("Parent2")

    parameters = [
        Parameter("Parameter1", parent1),
        Parameter("Parameter2", parent1),
        Parameter("Parameter3", parent2),
    ]

    open_gui(parameters)












