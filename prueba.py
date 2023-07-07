import sys
import datetime
import matplotlib.pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QComboBox, QMessageBox, QSizePolicy
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from binance.client import Client
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

API_KEY = 'cxLiDspThfkx3HSlFpJ0ram9hazMEs8RtoYbemp6WTIXPQjUBDF1xOmWp6Nco9T9'
API_SECRET = 'zkhLKoxC3jACEx6ibVOXdKe2pIusyyNyn5BO2mAkWoSZqoPy18vRwJsNKdIq2f0E'
SYMBOL_VAR = "BTCUSDT"

class GraphWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.setWindowTitle("Gráfica")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(620, 520)

        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        layout.addWidget(self.canvas)
        layout.addStretch()
        self.setCentralWidget(main_widget)

    def closeEvent(self, event):
        self.figure = None
        super().closeEvent(event)

class TradingApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.client = Client(API_KEY, API_SECRET)
        self.symbol_var = SYMBOL_VAR
        self.graph_window = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.chart_update)

        self.setWindowTitle("Trading App")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(240, 120)

        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        self.setCentralWidget(main_widget)

        self.menu_label = QLabel('Menu')
        layout.addWidget(self.menu_label)

        self.combo_box = QComboBox()
        self.combo_box.addItem("BTC")
        self.combo_box.addItem("ETH")
        self.combo_box.addItem("LTC")
        self.combo_box.currentTextChanged.connect(self.handle_symbol_change)
        layout.addWidget(self.combo_box)

        self.boton_graficas = QPushButton('Gráficas')
        self.boton_graficas.clicked.connect(self.abrir_ventana)
        layout.addWidget(self.boton_graficas)

        self.boton_salir = QPushButton('Salir')
        self.boton_salir.clicked.connect(self.salir_programa)
        layout.addWidget(self.boton_salir)

        self.setCentralWidget(main_widget)

    def handle_symbol_change(self, symbol):
        if symbol == "BTC":
            self.symbol_var = "BTCUSDT"
        elif symbol == "ETH":
            self.symbol_var = "ETHUSDT"
        elif symbol =="LTC":
            self.symbol_var = "LTCUSDT"

    def abrir_ventana(self):
        self.graph_window = GraphWindow()
        self.timer.start(1000)
        self.chart_update()
        self.graph_window.show()

    def chart_update(self):
        symbol = self.symbol_var
        klines = self.client.get_historical_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_1HOUR, start_str='1 day ago UTC')

        if self.graph_window.figure is not None:
            self.graph_window.figure.clf()
            ax = self.graph_window.figure.add_subplot(111)
            ohlc = []
            for entry in klines:
                timestamp = int(entry[0])
                close_price = float(entry[4])
                open_price = float(entry[1])
                high_price = float(entry[2])
                low_price = float(entry[3])

                ohlc.append([timestamp, open_price, high_price, low_price, close_price])

            candlestick_ohlc(ax, ohlc, width=0.6)

            ax.set_title("Trading")
            ax.set_xlabel("Time")
            ax.set_ylabel("Price")

            self.graph_window.canvas.draw()

    def salir_programa(self):
        reply = QMessageBox.question(self, 'Salir', '¿Estás seguro de que quieres salir del programa?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.graph_window is not None:
                self.graph_window.close()
            self.close()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    trading_app = TradingApp()
    trading_app.show()
    sys.exit(app.exec_())
