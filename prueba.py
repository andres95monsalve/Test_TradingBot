import sys
import datetime
import matplotlib.pyplot as plt
from mplfinance.original_flavor import candlestick_ohlc
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel, QComboBox, QMessageBox, QSizePolicy, QDialog, QDialogButtonBox, QHBoxLayout, QLineEdit, QDesktopWidget
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
from binance.client import Client
from websocket import create_connection
import pandas as pd

class GraphWindow(QMainWindow):
    def __init__(self, api_key, secret_key, exchange, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.secret_key = secret_key
        self.exchange = exchange
        self.figure = plt.figure()
        self.canvas = FigureCanvas(self.figure)
        self.setWindowTitle("Gráfica")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(628, 564)
        self.center()
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        layout.addWidget(self.canvas)
        layout.addStretch()
        button_layout = QHBoxLayout()
        layout.addLayout(button_layout)
        self.iniciar_button = QPushButton("Iniciar")
        self.iniciar_button.clicked.connect(self.abrir_ventana_trading)
        button_layout.addWidget(self.iniciar_button)
        button_layout.addStretch()
        self.finalizar_button = QPushButton("Finalizar")
        self.finalizar_button.clicked.connect(self.finalizar_trading)
        button_layout.addWidget(self.finalizar_button)
        self.setCentralWidget(main_widget)

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def closeEvent(self, event):
        self.figure = None
        super().closeEvent(event)

    def abrir_ventana_trading(self):
        trading_dialog = TradingDialog(self)
        if trading_dialog.exec_() == QDialog.Accepted:
            cantidad = float(trading_dialog.cantidad_input.text())
            tiempo = int(trading_dialog.tiempo_input.text())
            if not verificar_disponibilidad_dinero(self.api_key, self.secret_key, cantidad):
                QMessageBox.warning(self, 'Error', 'No tiene fondos suficientes en la cuenta.')
                return
            tiempo_segundos = tiempo * 60
            crear_archivo_trading()
            QMessageBox.information(self, 'Trading', f'Se ha iniciado el trading con {cantidad} durante {tiempo} minutos.')

    def finalizar_trading(self):
        if verificar_trading_activo():
            QMessageBox.information(self, 'Trading', 'Se ha finalizado el trading.')
        else:
            QMessageBox.warning(self, 'Error', 'No se está realizando trading actualmente.')


class TradingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trading")
        self.setWindowIcon(QIcon('logo.png'))
        self.setFixedSize(300, 150)
        layout = QVBoxLayout(self)
        self.cantidad_label = QLabel("Cantidad para hacer trading:")
        layout.addWidget(self.cantidad_label)
        self.cantidad_input = QLineEdit()
        layout.addWidget(self.cantidad_input)
        self.tiempo_label = QLabel("Tiempo de duración (en minutos):")
        layout.addWidget(self.tiempo_label)
        self.tiempo_input = QLineEdit()
        layout.addWidget(self.tiempo_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()


def verificar_claves_api(api_key, secret_key):
    try:
        if secret_key.startswith("Kraken"):
            kraken_secret = secret_key.split(":")[1]
            api_domain = "wss://ws.kraken.com/"
            ws = create_connection(api_domain)
            ws.send('{"event": "subscribe", "pair": ["XBT/USD"], "subscription": {"name": "ohlc"}}')
            response = ws.recv()
            ws.close()
            if response.startswith('{"event": "subscriptionStatus", "status": "subscribed", "subscription": {"name": "ohlc"}}'):
                return True
        else:
            client = Client(api_key, secret_key)
            return True
    except:
        return False


def verificar_disponibilidad_dinero(api_key, secret_key, cantidad):
    if secret_key.startswith("Kraken"):
        kraken_secret = secret_key.split(":")[1]
        ws = create_connection("wss://ws.kraken.com/")
        ws.send('{"event":"subscribe", "pair":["XBT/USD"], "subscription":{"name":"ticker"}}')
        response = ws.recv()
        ws.close()
        if response.startswith('{"event":"subscriptionStatus","status":"subscribed","subscription":{"name":"ticker"}}'):
            return True
    else:
        client = Client(api_key, secret_key)
        account_info = client.get_account()
        balances = account_info['balances']
        for balance in balances:
            if balance['asset'] == 'USDT':
                free_balance = float(balance['free'])
                break
        else:
            return False

    if free_balance >= cantidad:
        return True
    else:
        return False


def verificar_trading_activo():
    return False


def crear_archivo_trading():
    now = datetime.datetime.now()
    filename = f'Trading App {now.strftime("%Y-%m-%d %H-%M-%S")}.xls'
    df = pd.DataFrame({'Fecha': [now], 'Cantidad': [], 'Precio': []})
    df.to_excel(filename, index=False)


class TradingApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = None
        self.secret_key = None
        self.exchange = "Binance"
        self.graph_window = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.chart_update)
        self.setWindowTitle("Trading App")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(310, 249)
        self.center()
        main_widget = QWidget()
        layout = QVBoxLayout()
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)
        self.exchange_label = QLabel('Exchange:')
        layout.addWidget(self.exchange_label)
        self.exchange_combo_box = QComboBox()
        self.exchange_combo_box.addItem("Binance")
        self.exchange_combo_box.addItem("Kraken")
        self.exchange_combo_box.currentTextChanged.connect(self.handle_exchange_change)
        layout.addWidget(self.exchange_combo_box)
        self.validate_button = QPushButton('Validar Claves API')
        self.validate_button.clicked.connect(self.open_validation_dialog)
        layout.addWidget(self.validate_button)
        self.menu_label = QLabel('Moneda a operar:')
        layout.addWidget(self.menu_label)
        self.combo_box = QComboBox()
        self.combo_box.addItem("BTC")
        self.combo_box.addItem("ETH")
        self.combo_box.addItem("LTC")
        self.combo_box.currentTextChanged.connect(self.handle_symbol_change)
        layout.addWidget(self.combo_box)
        self.intervalo_label = QLabel('Intervalo de tiempo a graficar:')
        layout.addWidget(self.intervalo_label)
        self.combo_box_interval = QComboBox()
        self.combo_box_interval.addItem("1 Hora")
        self.combo_box_interval.addItem("4 Horas")
        self.combo_box_interval.addItem("1 Día")
        self.combo_box_interval.currentTextChanged.connect(self.handle_interval_change)
        layout.addWidget(self.combo_box_interval)
        self.boton_operar = QPushButton('Operar')
        self.boton_operar.clicked.connect(self.abrir_ventana)
        layout.addWidget(self.boton_operar)
        self.boton_salir = QPushButton('Salir')
        self.boton_salir.clicked.connect(self.salir_programa)
        layout.addWidget(self.boton_salir)
        self.setCentralWidget(main_widget)
        self.time_interval = Client.KLINE_INTERVAL_1HOUR
        self.validado = False
        self.boton_operar.setEnabled(False)

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def open_validation_dialog(self):
        validation_dialog = ValidationDialog(self)
        if self.exchange_combo_box.currentText() == "Kraken":
            validation_dialog.setWindowTitle("Validación de Claves API - Kraken")
            validation_dialog.api_key_label.setText("API Key de Kraken:")
            validation_dialog.secret_key_label.setText("Private Key de Kraken:")
        validation_dialog.exec_()

    def validate_keys(self, api_key, secret_key):
        if not verificar_claves_api(api_key, secret_key):
            QMessageBox.warning(self, 'Error', 'API Key o Secret Key inválidas.')
            self.client = None
            self.validado = False
            self.boton_operar.setEnabled(False)
            return

        self.api_key = api_key
        self.secret_key = secret_key
        if self.exchange == "Binance":
            self.client = Client(api_key, secret_key)
        elif self.exchange == "Kraken":
            ws = create_connection("wss://ws.kraken.com/")
            client = Client(api_key, secret_key)
            client.load_key('kraken.key')
            ws.close()
        self.validado = True
        self.boton_operar.setEnabled(True)
        QMessageBox.information(self, 'Éxito', 'API Key y Secret Key válidas.')

    def handle_exchange_change(self, exchange):
        self.exchange = exchange

    def handle_symbol_change(self, symbol):
        if symbol == "BTC":
            self.symbol_var = "BTCUSDT"
        elif symbol == "ETH":
            self.symbol_var = "ETHUSDT"
        elif symbol == "LTC":
            self.symbol_var = "LTCUSDT"

    def handle_interval_change(self, interval):
        if interval == "1 Hora":
            self.time_interval = Client.KLINE_INTERVAL_1HOUR
        elif interval == "4 Horas":
            self.time_interval = Client.KLINE_INTERVAL_4HOUR
        elif interval == "1 Día":
            self.time_interval = Client.KLINE_INTERVAL_1DAY

    def abrir_ventana(self):
        if not self.validado:
            QMessageBox.warning(self, 'Error', 'Debe validar las API Keys antes de realizar cualquier operación.')
            return

        if self.exchange == "Kraken":
            if self.api_key == "" or self.secret_key == "":
                QMessageBox.warning(self, 'Error', 'Debe introducir la API Key y la Private Key de Kraken.')
                return

        self.graph_window = GraphWindow(self.api_key, self.secret_key, self.exchange)
        self.timer.start(1000)
        self.chart_update()
        self.graph_window.show()

    def chart_update(self):
        if self.client is None or self.graph_window is None:
            return

        symbol = self.symbol_var

        end_time = datetime.datetime.now()
        start_time = end_time - datetime.timedelta(days=5)

        if self.exchange == "Binance":
            klines = self.client.get_historical_klines(
                symbol=symbol,
                interval=self.time_interval,
                start_str=start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_str=end_time.strftime("%Y-%m-%d %H:%M:%S")
            )
        elif self.exchange == "Kraken":
            ws = create_connection("wss://ws.kraken.com/")
            ws.send('{"event":"subscribe", "pair":["XBT/USD"], "subscription":{"name":"ohlc"}}')
            response = ws.recv()
            ws.close()
            klines = response.split('\n')[:-1]

        if self.graph_window.figure is not None:
            self.graph_window.figure.clf()
            ax = self.graph_window.figure.add_subplot(111)
            ohlc = []
            if self.exchange == "Binance":
                for entry in klines:
                    timestamp = int(entry[0])
                    close_price = float(entry[4])
                    open_price = float(entry[1])
                    high_price = float(entry[2])
                    low_price = float(entry[3])

                    ohlc.append([timestamp, open_price, high_price, low_price, close_price])
            elif self.exchange == "Kraken":
                for entry in klines:
                    if entry.startswith('['):
                        entry = entry.replace('[', '').replace(']', '').replace('"', '')
                        timestamp, open_price, high_price, low_price, close_price = entry.split(',')

                        ohlc.append([int(timestamp), float(open_price), float(high_price), float(low_price), float(close_price)])

            candlestick_ohlc(ax, ohlc, width=0.6)

            ax.set_title("Trading")
            ax.set_xlabel("Tiempo")
            ax.set_ylabel("Precio")

            ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda timestamp, _: datetime.datetime.fromtimestamp(timestamp/1000).strftime('%H:%M')))
            ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda timestamp, _: datetime.datetime.fromtimestamp(timestamp/1000).strftime('%d/%m/%Y')))

            self.graph_window.canvas.draw()

    def salir_programa(self):
        reply = QMessageBox.question(self, 'Salir', '¿Estás seguro de que quieres salir del programa?', QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if self.graph_window is not None:
                self.graph_window.close()
            self.close()


class ValidationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Validación de Claves API")
        self.setWindowIcon(QIcon('logo.png'))
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)

        self.api_key_label = QLabel("API Key:")
        layout.addWidget(self.api_key_label)

        self.api_key_input = QLineEdit()
        layout.addWidget(self.api_key_input)

        self.secret_key_label = QLabel("Secret Key:")
        layout.addWidget(self.secret_key_label)

        self.secret_key_input = QLineEdit()
        layout.addWidget(self.secret_key_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        api_key = self.api_key_input.text()
        secret_key = self.secret_key_input.text()
        parent = self.parent()
        parent.validate_keys(api_key, secret_key)
        super().accept()

    def reject(self):
        super().reject()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    trading_app = TradingApp()
    trading_app.show()
    sys.exit(app.exec())
