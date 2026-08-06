import sys
import os
import time
import collections
import threading
import grpc
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QFileDialog, QTextEdit,
    QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QIcon

import flwr as fl
from auth import generate_sha256_hash
from client_logic import SimulatedNumPyClient

# Dicionário global para armazenar as credenciais da thread ativa
CURRENT_CREDENTIALS = {
    "username": "",
    "hash": ""
}

# Interceptor gRPC para injetar metadados de autenticação
class AddHeaderClientInterceptor(
    grpc.UnaryUnaryClientInterceptor,
    grpc.UnaryStreamClientInterceptor,
    grpc.StreamUnaryClientInterceptor,
    grpc.StreamStreamClientInterceptor
):
    def __init__(self, username, client_hash):
        self.username = username
        self.client_hash = client_hash

    def _add_header(self, client_call_details):
        metadata = []
        if client_call_details.metadata is not None:
            metadata = list(client_call_details.metadata)
        metadata.append(('auth-username', self.username))
        metadata.append(('auth-hash', self.client_hash))
        
        class _ClientCallDetails(
            collections.namedtuple(
                '_ClientCallDetails',
                ('method', 'timeout', 'metadata', 'credentials', 'wait_for_ready')
            ),
            grpc.ClientCallDetails
        ):
            pass
            
        return _ClientCallDetails(
            client_call_details.method,
            client_call_details.timeout,
            metadata,
            client_call_details.credentials,
            client_call_details.wait_for_ready
        )

    def intercept_unary_unary(self, continuation, client_call_details, request):
        new_details = self._add_header(client_call_details)
        return continuation(new_details, request)

    def intercept_unary_stream(self, continuation, client_call_details, request):
        new_details = self._add_header(client_call_details)
        return continuation(new_details, request)

    def intercept_stream_unary(self, continuation, client_call_details, request_iterator):
        new_details = self._add_header(client_call_details)
        return continuation(new_details, request_iterator)

    def intercept_stream_stream(self, continuation, client_call_details, request_iterator):
        new_details = self._add_header(client_call_details)
        return continuation(new_details, request_iterator)


# Monkey Patch gRPC insecure_channel
original_insecure_channel = grpc.insecure_channel

def patched_insecure_channel(target, options=None, compression=None):
    channel = original_insecure_channel(target, options, compression)
    if CURRENT_CREDENTIALS["username"]:
        interceptor = AddHeaderClientInterceptor(
            CURRENT_CREDENTIALS["username"],
            CURRENT_CREDENTIALS["hash"]
        )
        channel = grpc.intercept_channel(channel, interceptor)
    return channel

grpc.insecure_channel = patched_insecure_channel


class FlowerWorker(QThread):
    log_signal = pyqtSignal(str)
    metric_signal = pyqtSignal(str, float)
    finished_signal = pyqtSignal(bool, str) # (success, message)

    def __init__(self, server_address, data_dir, username, client_hash):
        super().__init__()
        self.server_address = server_address
        self.data_dir = data_dir
        self.username = username
        self.client_hash = client_hash
        self.cancel_event = threading.Event()

    def run(self):
        # Atualizar credenciais globais da thread
        CURRENT_CREDENTIALS["username"] = self.username
        CURRENT_CREDENTIALS["hash"] = self.client_hash

        signals = {
            "log": lambda msg: self.log_signal.emit(msg),
            "metric": lambda name, val: self.metric_signal.emit(name, val)
        }

        retries = 3
        while retries > 0:
            if self.cancel_event.is_set():
                self.finished_signal.emit(False, "Treinamento cancelado pelo usuário.")
                return

            try:
                self.log_signal.emit(f"Conectando ao servidor Flower em {self.server_address}...")
                
                # Inicializar o cliente
                client = SimulatedNumPyClient(
                    data_dir=self.data_dir,
                    cancel_event=self.cancel_event,
                    signals_callback=signals
                )
                
                # Rodar o cliente Flower (esta chamada é blocante)
                fl.client.start_client(
                    server_address=self.server_address,
                    client=client.to_client()
                )
                
                self.finished_signal.emit(True, "Treinamento federado concluído com sucesso!")
                return

            except grpc.RpcError as e:
                status_code = e.code()
                if status_code == grpc.StatusCode.UNAUTHENTICATED:
                    self.finished_signal.emit(False, f"Falha de Autenticação: {e.details()}")
                    return
                
                retries -= 1
                self.log_signal.emit(f"Erro de conexão gRPC ({status_code}). Tentando reconectar ({3 - retries}/3)...")
                time.sleep(3.0)
                
            except Exception as e:
                self.finished_signal.emit(False, f"Erro operacional: {str(e)}")
                return
        
        self.finished_signal.emit(False, "Não foi possível conectar ao servidor Flower após 3 tentativas.")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Flower Federated Client - Google Antigravity Edition")
        self.resize(700, 600)
        self.setMinimumSize(600, 500)
        
        # Aplicar folha de estilo moderna (Dark Theme Premium)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121824;
            }
            QLabel {
                color: #A0AEC0;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            QLineEdit {
                background-color: #1E293B;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #FFFFFF;
                padding: 8px 12px;
                font-size: 14px;
                min-height: 36px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
                background-color: #0F172A;
                color: #FFFFFF;
            }
            QLineEdit::placeholder {
                color: #64748B;
            }
            QPushButton {
                background-color: #2563EB;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 12px 20px;
                font-size: 13px;
                font-family: 'Segoe UI', sans-serif;
            }
            QPushButton:hover {
                background-color: #3B82F6;
            }
            QPushButton:pressed {
                background-color: #1D4ED8;
            }
            QPushButton:disabled {
                background-color: #475569;
                color: #94A3B8;
            }
            #stopButton {
                background-color: #DC2626;
            }
            #stopButton:hover {
                background-color: #EF4444;
            }
            #stopButton:pressed {
                background-color: #B91C1C;
            }
            QTextEdit {
                background-color: #0B0F19;
                border: 1px solid #1E293B;
                border-radius: 8px;
                color: #38BDF8;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                padding: 12px;
            }
            QProgressBar {
                background-color: #1E293B;
                border-radius: 4px;
                text-align: center;
                color: white;
                font-weight: bold;
                min-height: 20px;
            }
            QProgressBar::chunk {
                background-color: #10B981;
                border-radius: 4px;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Cabeçalho da Aplicação
        header_frame = QFrame()
        header_layout = QVBoxLayout(header_frame)
        title_label = QLabel("Nó de Treinamento Federado")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #F8FAFC;")
        subtitle_label = QLabel("Flower.ai & Antigravity Client Engine")
        subtitle_label.setStyleSheet("color: #64748B; font-size: 12px;")
        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle_label)
        main_layout.addWidget(header_frame)

        # Seção de Credenciais
        cred_frame = QFrame()
        cred_frame.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;")
        cred_layout = QVBoxLayout(cred_frame)
        cred_layout.setContentsMargins(15, 15, 15, 15)
        cred_layout.setSpacing(10)

        cred_title = QLabel("Autenticação Segura (SHA-256)")
        cred_title.setStyleSheet("font-weight: bold; color: #F8FAFC; font-size: 14px;")
        cred_layout.addWidget(cred_title)

        inputs_layout = QHBoxLayout()
        
        user_vbox = QVBoxLayout()
        user_vbox.addWidget(QLabel("Usuário:"))
        self.user_input = QLineEdit("client1")
        user_vbox.addWidget(self.user_input)
        inputs_layout.addLayout(user_vbox)

        pass_vbox = QVBoxLayout()
        pass_vbox.addWidget(QLabel("Senha:"))
        self.pass_input = QLineEdit("flower_power_2026")
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        pass_vbox.addWidget(self.pass_input)
        inputs_layout.addLayout(pass_vbox)

        cred_layout.addLayout(inputs_layout)

        # Campo Hash SHA-256 e Botão de Geração
        hash_layout = QHBoxLayout()
        hash_vbox = QVBoxLayout()
        hash_vbox.addWidget(QLabel("Hash SHA-256 Gerado (Enviado via gRPC):"))
        self.hash_input = QLineEdit()
        self.hash_input.setReadOnly(True)
        self.hash_input.setPlaceholderText("Clique em 'Gerar Hash' para calcular o SHA-256")
        hash_vbox.addWidget(self.hash_input)
        hash_layout.addLayout(hash_vbox, 4)

        gen_hash_btn = QPushButton("Gerar Hash")
        gen_hash_btn.clicked.connect(self.on_generate_hash)
        gen_hash_btn.setStyleSheet("margin-top: 18px;")
        hash_layout.addWidget(gen_hash_btn, 1)
        cred_layout.addLayout(hash_layout)

        main_layout.addWidget(cred_frame)

        # Seção de Configuração de Dados e Servidor
        config_frame = QFrame()
        config_frame.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;")
        config_layout = QVBoxLayout(config_frame)
        config_layout.setContentsMargins(15, 15, 15, 15)
        config_layout.setSpacing(10)

        config_title = QLabel("Configuração de Conexão e Dados")
        config_title.setStyleSheet("font-weight: bold; color: #F8FAFC; font-size: 14px;")
        config_layout.addWidget(config_title)

        # Servidor
        server_layout = QHBoxLayout()
        server_layout.addWidget(QLabel("Servidor gRPC:"))
        self.server_input = QLineEdit("localhost:8080")
        server_layout.addWidget(self.server_input)
        config_layout.addLayout(server_layout)

        # Seletor de Pasta
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Pasta de Dados:"))
        self.folder_input = QLineEdit()
        self.folder_input.setReadOnly(True)
        folder_layout.addWidget(self.folder_input, 3)
        
        self.browse_btn = QPushButton("Selecionar")
        self.browse_btn.clicked.connect(self.on_browse_folder)
        folder_layout.addWidget(self.browse_btn, 1)
        config_layout.addLayout(folder_layout)

        main_layout.addWidget(config_frame)

        # Painel de Telemetria e Monitoramento
        monitor_frame = QFrame()
        monitor_frame.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;")
        monitor_layout = QVBoxLayout(monitor_frame)
        monitor_layout.setContentsMargins(15, 15, 15, 15)

        metrics_layout = QHBoxLayout()
        
        round_vbox = QVBoxLayout()
        round_vbox.addWidget(QLabel("Rodada Atual:"))
        self.round_label = QLabel("-")
        self.round_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8;")
        round_vbox.addWidget(self.round_label)
        metrics_layout.addLayout(round_vbox)

        loss_vbox = QVBoxLayout()
        loss_vbox.addWidget(QLabel("Perda Local:"))
        self.loss_label = QLabel("-")
        self.loss_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #F87171;")
        loss_vbox.addWidget(self.loss_label)
        metrics_layout.addLayout(loss_vbox)

        acc_vbox = QVBoxLayout()
        acc_vbox.addWidget(QLabel("Acurácia Local:"))
        self.acc_label = QLabel("-")
        self.acc_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #34D399;")
        acc_vbox.addWidget(self.acc_label)
        metrics_layout.addLayout(acc_vbox)

        monitor_layout.addLayout(metrics_layout)
        main_layout.addWidget(monitor_frame)

        # Console de Logs
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Console do Motor Flower...")
        main_layout.addWidget(self.log_output)

        # Barra de Progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # Indeterminado
        self.progress_bar.hide()
        main_layout.addWidget(self.progress_bar)

        # Botões de Ação
        actions_layout = QHBoxLayout()
        self.start_btn = QPushButton("Iniciar Treinamento")
        self.start_btn.clicked.connect(self.on_start_training)
        actions_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("Parar Treinamento")
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.on_stop_training)
        actions_layout.addWidget(self.stop_btn)

        main_layout.addLayout(actions_layout)

        # Conectar sinal de alteração de usuário para auto-detectar a pasta de dados
        self.user_input.textChanged.connect(self.auto_detect_folder)
        self.auto_detect_folder()

    def auto_detect_folder(self):
        user = self.user_input.text().strip().lower()
        # Normalizar cliente/client
        user_norm = user.replace("cliente", "client")
        if not user_norm:
            return
        
        # Verificar se existe pasta correspondente no diretório atual
        possible_folders = [
            user_norm,
            f"data_{user_norm}",
            user,
            f"data_{user}"
        ]
        for folder in possible_folders:
            path = os.path.abspath(folder)
            if os.path.exists(path) and os.path.isdir(path):
                self.folder_input.setText(path)
                break

    def on_generate_hash(self):
        user = self.user_input.text().strip()
        pwd = self.pass_input.text().strip()
        if not user or not pwd:
            QMessageBox.warning(self, "Campos Vazios", "Preencha Usuário e Senha para gerar o Hash.")
            return
        
        generated = generate_sha256_hash(user, pwd)
        self.hash_input.setText(generated)

    def on_browse_folder(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Selecionar Diretório de Dados")
        if dir_path:
            self.folder_input.setText(dir_path)

    def on_start_training(self):
        user = self.user_input.text().strip()
        pwd = self.pass_input.text().strip()
        server = self.server_input.text().strip()
        data_dir = self.folder_input.text().strip()
        
        # Gerar o hash dinamicamente se o campo estiver vazio
        if not self.hash_input.text():
            self.on_generate_hash()
            
        client_hash = self.hash_input.text()

        if not user or not pwd or not server or not data_dir:
            QMessageBox.warning(self, "Campos Faltando", "Todos os campos e a pasta de dados devem ser preenchidos.")
            return

        # Limpar telemetria
        self.round_label.setText("-")
        self.loss_label.setText("-")
        self.acc_label.setText("-")
        self.log_output.clear()
        
        # Instanciar a Worker Thread
        self.worker = FlowerWorker(server, data_dir, user, client_hash)
        self.worker.log_signal.connect(self.log_message)
        self.worker.metric_signal.connect(self.update_metric)
        self.worker.finished_signal.connect(self.on_training_finished)

        # Alterar estado da interface
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.browse_btn.setEnabled(False)
        self.progress_bar.show()

        self.log_message("Preparando thread em segundo plano...")
        self.worker.start()

    def on_stop_training(self):
        if self.worker and self.worker.isRunning():
            self.log_message("Enviando sinal de parada graciosa ao motor...")
            self.worker.cancel_event.set()
            self.stop_btn.setEnabled(False)

    def log_message(self, message):
        self.log_output.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    def update_metric(self, name, value):
        if name == "round":
            self.round_label.setText(str(int(value)))
        elif name == "loss":
            self.loss_label.setText(f"{value:.4f}")
        elif name == "accuracy":
            self.acc_label.setText(f"{value:.4f}")

    def on_training_finished(self, success, message):
        self.progress_bar.hide()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.browse_btn.setEnabled(True)

        if success:
            QMessageBox.information(self, "Treinamento Finalizado", message)
        else:
            QMessageBox.critical(self, "Erro no Treinamento", message)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
