import datetime
import sys
import time

import ccxt
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
from binance.client import Client
from krakenex import API
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.dates import date2num
from mplfinance.original_flavor import candlestick_ohlc
from pykrakenapi import KrakenAPI
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QApplication, QComboBox, QDesktopWidget, QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QVBoxLayout, QWidget
from websocket import create_connection


class GraphWindow(QMainWindow):
    def __init__(self, api_key, secret_key, exchange, binance, kraken, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.secret_key = secret_key
        self.exchange = exchange
        self.binance_var = binance
        self.kraken_var = kraken
        self.figure = plt.figure()
        self.ax = self.figure.add_subplot(111)
        self.canvas = FigureCanvas(self.figure)
        self.setWindowTitle("Gráfica")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(628, 564)
        self.center()

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.addWidget(self.canvas)

        button_layout = QHBoxLayout()
        self.iniciar_button = QPushButton("Iniciar")
        self.finalizar_button = QPushButton("Finalizar")
        self.salir_button = QPushButton("Salir")
        self.bot_button = QPushButton("Bot")
        self.salir_button.clicked.connect(self.salir_graficas)
        self.iniciar_button.clicked.connect(self.abrir_ventana_trading)
        self.finalizar_button.clicked.connect(self.finalizar_trading)
        self.bot_button.clicked.connect(self.abrir_ventana_bot)
        button_layout.addWidget(self.iniciar_button)
        button_layout.addWidget(self.finalizar_button)
        button_layout.addWidget(self.salir_button)
        button_layout.addWidget(self.bot_button)
        layout.addLayout(button_layout)

        self.setCentralWidget(main_widget)

    def center(self):
        frame_geometry = self.frameGeometry()
        center_point = QDesktopWidget().availableGeometry().center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())

    def abrir_ventana_trading(self):
        trading_dialog = TradingDialog(self)
        if trading_dialog.exec_() == QDialog.Accepted:
            cantidad = float(trading_dialog.cantidad_input.text())
            tiempo = int(trading_dialog.tiempo_input.text())
            if not verificar_disponibilidad_dinero(self.api_key, self.secret_key, cantidad, self.exchange):
                QMessageBox.warning(self, 'Error', 'No tiene fondos suficientes en la cuenta.')
                return
            tiempo_segundos = tiempo * 60
            crear_archivo_trading()
            QMessageBox.information(self, 'Trading', f'Se ha iniciado el trading con {cantidad} durante {tiempo} minutos.')

            hacer_trading(self.api_key, self.secret_key, self.exchange, self.binance_var, cantidad, tiempo_segundos)

    def finalizar_trading(self):
        if verificar_trading_activo():
            QMessageBox.information(self, 'Trading', 'Se ha finalizado el trading.')
        else:
            QMessageBox.warning(self, 'Error', 'No se está realizando trading actualmente.')

    def abrir_ventana_bot(self):
        bot_dialog = BotDialog(self)
        if bot_dialog.exec_() == QDialog.Accepted:
            monto = float(bot_dialog.monto_input.text())
            precio_minimo = float(bot_dialog.precio_minimo_input.text())
            if not verificar_disponibilidad_dinero(self.api_key, self.secret_key, monto, self.exchange):
                QMessageBox.warning(self, 'Error', 'No tiene fondos suficientes en la cuenta.')
                return
            hacer_trading(self.api_key, self.secret_key, self.exchange, self.binance_var, monto, 0, precio_minimo)

    def limpiar_datos(self):
        self.api_key = None
        self.secret_key = None
        self.exchange = None
        self.binance_var = None
        self.kraken_var = None
        self.iniciar_button.setEnabled(True)
        self.finalizar_button.setEnabled(True)
        self.ax.clear()
        self.canvas.draw()
        QMessageBox.information(self, 'Datos eliminados', 'Los datos de la API han sido eliminados satisfactoriamente.')

    def disable_operar_button(self):
        self.iniciar_button.setEnabled(False)
        self.finalizar_button.setEnabled(False)

    def enable_operar_button(self):
        self.iniciar_button.setEnabled(True)
        self.finalizar_button.setEnabled(True)

    def mostrar_mensaje_claves_api(self):
        QMessageBox.warning(self, 'Error', 'Por favor, introduzca las claves API de la exchange seleccionada.')

    def salir_graficas(self):
        self.close()


class TradingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Trading")
        self.setWindowIcon(QIcon('logo.png'))
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)

        self.cantidad_label = QLabel("Cantidad para hacer trading:")
        self.cantidad_input = QLineEdit()
        self.tiempo_label = QLabel("Tiempo de duración (en minutos):")
        self.tiempo_input = QLineEdit()

        layout.addWidget(self.cantidad_label)
        layout.addWidget(self.cantidad_input)
        layout.addWidget(self.tiempo_label)
        layout.addWidget(self.tiempo_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()


class BotDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Bot")
        self.setWindowIcon(QIcon('logo.png'))
        self.setFixedSize(300, 150)

        layout = QVBoxLayout(self)

        self.monto_label = QLabel("Monto a tradear:")
        self.monto_input = QLineEdit()
        self.precio_minimo_label = QLabel("Precio mínimo:")
        self.precio_minimo_input = QLineEdit()

        layout.addWidget(self.monto_label)
        layout.addWidget(self.monto_input)
        layout.addWidget(self.precio_minimo_label)
        layout.addWidget(self.precio_minimo_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def accept(self):
        super().accept()

    def reject(self):
        super().reject()


def verificar_claves_api(api_key, secret_key, exchange):
    try:
        if exchange == "Kraken":
            api = API(key=api_key, secret=secret_key)
            kraken = KrakenAPI(api)
            balance = kraken.get_account_balance()
            return True
        else:  # Binance
            client = Client(api_key, secret_key)
            account_info = client.get_account()
            return account_info['canTrade']
    except:
        return False


def verificar_disponibilidad_dinero(api_key, secret_key, cantidad, exchange):
    if exchange == "Kraken":
        if secret_key.startswith("Kraken"):
            kraken_secret = secret_key.split(":")[1]
            ws = create_connection("wss://ws.kraken.com/")
            ws.send('{"event":"subscribe", "pair":["XBT/USD"], "subscription":{"name":"symbol"}}')
            response = ws.recv()
            ws.close()
            if response.startswith('{"event":"subscriptionStatus","status":"subscribed","subscription":{"name":"ticker"}}'):
                return True
    else:
        client = Client(api_key, secret_key)
        account_info = client.get_account()
        balances = account_info['balances']
        free_balance = 0.0
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


def hacer_trading(api_key, secret_key, exchange, binance, cantidad, tiempo, precio_minimo=None):
    exchange_ccxt = getattr(ccxt, exchange.lower())()
    symbol = binance

    def obtener_precio_actual():
        ticker = exchange_ccxt.fetch_ticker(symbol)
        return ticker['close']

    tiempo_actual = 0
    while tiempo_actual < tiempo:
        precio_actual = obtener_precio_actual()
        print(f"Precio actual: {precio_actual}")

        if precio_minimo is not None and precio_actual <= precio_minimo:
            print("El trading ha finalizado porque se alcanzó el precio mínimo establecido.")
            break

        if cantidad <= 0:
            print("El trading ha finalizado porque se agotó el monto de trading.")
            break

        if exchange == "Binance":
            cantidad -= 0.1
        elif exchange == "Kraken":
            pass

        time.sleep(60)
        tiempo_actual += 1


class TradingApp(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.api_key = None
        self.secret_key = None
        self.exchange = "Binance"
        self.binance_var = "BTCUSDT"
        self.kraken_var = "XBT/USD"
        self.graph_window = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.chart_update)
        self.bot_window = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.chart_update)
        self.client = None
        self.setWindowTitle("Trading App")
        self.setWindowIcon(QIcon('logo.png'))
        self.resize(310, 249)
        self.center()

        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        self.setCentralWidget(main_widget)

        self.exchange_label = QLabel('Exchange:')
        self.exchange_combo_box = QComboBox()
        self.exchange_combo_box.addItem("Binance")
        self.exchange_combo_box.addItem("Kraken")
        self.exchange_combo_box.currentTextChanged.connect(self.handle_exchange_change)

        self.validate_button = QPushButton('Validar Claves API')
        self.validate_button.clicked.connect(self.open_validation_dialog)
        self.limpiar_button = QPushButton("Limpiar datos")
        self.limpiar_button.clicked.connect(self.limpiar_datos)
        self.limpiar_button.setEnabled(False)

        self.menu_label = QLabel('Moneda a operar:')
        self.combo_box = QComboBox()
        self.combo_box.addItem("BTC")
        self.combo_box.addItem("ETH")
        self.combo_box.addItem("LTC")
        self.combo_box.currentTextChanged.connect(self.handle_combo_box_change)

        self.intervalo_label = QLabel('Intervalo de tiempo a graficar:')
        self.combo_box_interval = QComboBox()
        self.combo_box_interval.addItem("1 Hora")
        self.combo_box_interval.addItem("4 Horas")
        self.combo_box_interval.addItem("1 Día")
        self.combo_box_interval.currentTextChanged.connect(self.handle_interval_change)

        self.boton_operar = QPushButton('Operar')
        self.boton_operar.clicked.connect(self.abrir_ventana)
        self.boton_operar.setEnabled(False)

        self.boton_salir = QPushButton('Salir')
        self.boton_salir.clicked.connect(self.salir_programa)

        layout.addWidget(self.exchange_label)
        layout.addWidget(self.exchange_combo_box)
        layout.addWidget(self.validate_button)
        layout.addWidget(self.limpiar_button)
        layout.addWidget(self.menu_label)
        layout.addWidget(self.combo_box)
        layout.addWidget(self.intervalo_label)
        layout.addWidget(self.combo_box_interval)
        layout.addWidget(self.boton_operar)
        layout.addWidget(self.boton_salir)

        self.time_interval = Client.KLINE_INTERVAL_1HOUR
        self.validado = False

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
        if verificar_claves_api(api_key, secret_key, self.exchange):
            QMessageBox.information(self, 'Claves API válidas', 'Las claves API son válidas.')
            self.api_key = api_key
            self.secret_key = secret_key
            self.validado = True
            self.boton_operar.setEnabled(True)
            self.exchange_combo_box.setEnabled(False)
            self.validate_button.setEnabled(False)
            self.limpiar_button.setEnabled(True)
        else:
            QMessageBox.warning(self, 'Error', 'API Key o Secret Key inválidas.')
            self.client = None
            self.validado = False
            self.boton_operar.setEnabled(False)

        if self.exchange == "Binance":
            self.api_key = api_key
            self.secret_key = secret_key
            self.client = Client(api_key, secret_key)
        elif self.exchange == "Kraken":
            self.api_key = api_key
            self.secret_key = secret_key
            api = API(key=api_key, secret=secret_key)
            self.client = KrakenAPI(api)

    def limpiar_datos(self):
        self.api_key = None
        self.secret_key = None
        self.exchange = None
        self.binance_var = None
        self.kraken_var = None
        self.boton_operar.setEnabled(False)
        self.exchange_combo_box.setEnabled(True)
        self.validate_button.setEnabled(True)
        self.limpiar_button.setEnabled(False)
        if self.graph_window is not None:
            self.graph_window.close()
        self.graph_window = None
        QMessageBox.information(self, 'Datos eliminados', 'Los datos de la API han sido eliminados satisfactoriamente.')

    def handle_exchange_change(self, exchange):
        self.exchange = exchange

    def handle_combo_box_change(self, coin):
        if self.exchange == "Binance":
            if coin == "BTC":
                self.binance_var = "BTCUSDT"
            elif coin == "ETH":
                self.binance_var = "ETHUSDT"
            elif coin == "LTC":
                self.binance_var = "LTCUSDT"
        elif self.exchange == "Kraken":
            if coin == "BTC":
                self.kraken_var = "XBT/USD"
            elif coin == "ETH":
                self.kraken_var = "ETH/USDT"
            elif coin == "LTC":
                self.kraken_var = "LTC/USDT"

    def handle_interval_change(self, interval):
        if interval == "1 Hora":
            self.time_interval = Client.KLINE_INTERVAL_1HOUR
        elif interval == "4 Horas":
            self.time_interval = Client.KLINE_INTERVAL_4HOUR
        elif interval == "1 Día":
            self.time_interval = Client.KLINE_INTERVAL_1DAY

    def abrir_ventana(self):
        if not self.validado:
            self.mostrar_mensaje_claves_api()
            return

        if self.graph_window is None:
            self.graph_window = GraphWindow(self.api_key, self.secret_key, self.exchange, self.binance_var, self.kraken_var)
            self.timer.start(1000)
        
        self.graph_window.show()

    def chart_update(self):

        if self.client is None or self.graph_window is None:
            return

        symbol = self.binance_var
        limit = 500

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
        
            api = API(key=self.api_key, secret=self.secret_key)
            kraken = KrakenAPI(api)

            data, last = kraken.get_ohlc_data("XBT/USD")
            data.index = date2num(data.index.to_pydate_fmt())

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

            ohlc = data.loc[:, ['Open', 'High', 'Low', 'Close']]
            ohlc['Open'] = pd.to_numeric(ohlc['Open'])

            fig, ax = plt.subplots()
            candlestick_ohlc(ax, ohlc.values, width=0.6)
            ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, _: datetime.datetime.fromtimestamp(x/1000).strftime('%H:%M')))
            plt.show()

        candlestick_ohlc(self.graph_window.ax, ohlc, width=0.6)

        self.graph_window.ax.set_title("Trading")
        self.graph_window.ax.set_xlabel("Tiempo")
        self.graph_window.ax.set_ylabel("Precio")

        self.graph_window.ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: datetime.datetime.fromtimestamp(x/1000).strftime('%H:%M')))
        self.graph_window.ax.xaxis.set_minor_formatter(plt.FuncFormatter(lambda x, _: datetime.datetime.fromtimestamp(x/1000).strftime('%d/%m/%Y')))

        self.graph_window.canvas.draw()

    def salir_programa(self):
        reply = QMessageBox.question(self, 'Salir', '¿Estás seguro de que quieres salir del programa?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
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
        self.api_key_input = QLineEdit()
        self.secret_key_label = QLabel("Secret Key:")
        self.secret_key_input = QLineEdit()

        layout.addWidget(self.api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addWidget(self.secret_key_label)
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
    sys.exit(app.exec_())
