import time
import os
import numpy as np
import flwr as fl

class SimulatedNumPyClient(fl.client.NumPyClient):
    def __init__(self, data_dir, cancel_event, signals_callback=None):
        """
        data_dir: Caminho para o diretório de dados selecionado.
        cancel_event: Evento threading.Event para controle de cancelamento.
        signals_callback: Dicionário contendo os callbacks/sinais para emitir dados para a GUI.
        """
        self.data_dir = data_dir
        self.cancel_event = cancel_event
        self.signals = signals_callback or {}
        
        # Parâmetros locais simulados (pesos de um modelo fictício)
        self.parameters = [np.array([0.1, 0.2, 0.3], dtype=np.float32)]
        
        # Validar diretório de dados na inicialização
        self._validate_data_dir()

    def _validate_data_dir(self):
        if not self.data_dir or not os.path.exists(self.data_dir):
            raise ValueError(f"O diretório selecionado não existe: {self.data_dir}")
        
        # Verificar se o diretório está vazio
        files = [f for f in os.listdir(self.data_dir) if os.path.isfile(os.path.join(self.data_dir, f))]
        if not files:
            raise ValueError(f"O diretório '{self.data_dir}' está vazio ou não possui arquivos válidos.")

    def get_parameters(self, config):
        # Simula consistência de tensores (Google Antigravity) injetando latência na transmissão
        self._log_gui("Transmitindo parâmetros (Simulando Antigravity Latency)...")
        time.sleep(1.0)
        return self.parameters

    def fit(self, parameters, config):
        self._log_gui("Iniciando rodada de treinamento local (fit)...")
        self.parameters = parameters
        
        # Lendo configurações enviadas pelo servidor (se houver)
        epochs = int(config.get("epochs", 3))
        batch_size = int(config.get("batch_size", 32))
        server_round = int(config.get("server_round", 0))
        
        if server_round > 0:
            self._update_gui_metric("round", server_round)

        # Simula o loop de épocas
        loss = 1.5
        accuracy = 0.5
        
        for epoch in range(1, epochs + 1):
            # Verificar se houve requisição de interrupção coordenada
            if self.cancel_event.is_set():
                self._log_gui("Treinamento cancelado graciosamente pelo operador.")
                raise Exception("Cancelamento solicitado pelo usuário durante o fit")
            
            # Simula processamento da época
            time.sleep(1.5)
            
            # Atualização fictícia de métricas (redução de perda e aumento de acurácia)
            loss -= 0.2 * (1 / epoch)
            accuracy += 0.08 * epoch
            accuracy = min(accuracy, 0.99)
            
            self._log_gui(f"Época {epoch}/{epochs} concluída - Loss: {loss:.4f} - Acc: {accuracy:.4f}")
            self._update_gui_metric("loss", loss)
            self._update_gui_metric("accuracy", accuracy)

        # Atualiza os pesos simulados
        self.parameters = [p + np.random.normal(0, 0.01, size=p.shape).astype(np.float32) for p in self.parameters]
        
        # Injeta latência de rede simulando o Antigravity antes de retornar os pesos
        self._log_gui("Enviando pesos atualizados para o servidor (Antigravity Latency)...")
        time.sleep(1.5)
        
        return self.parameters, 100, {"loss": loss, "accuracy": accuracy}

    def evaluate(self, parameters, config):
        self._log_gui("Iniciando avaliação local (evaluate)...")
        self.parameters = parameters
        
        # Verificar cancelamento
        if self.cancel_event.is_set():
            raise Exception("Cancelamento solicitado pelo usuário durante a avaliação")
            
        time.sleep(1.0)
        
        loss = 0.35
        accuracy = 0.88
        
        self._log_gui(f"Avaliação concluída - Loss: {loss:.4f} - Acc: {accuracy:.4f}")
        self._update_gui_metric("loss", loss)
        self._update_gui_metric("accuracy", accuracy)
        
        return float(loss), 100, {"accuracy": float(accuracy)}

    # Métodos auxiliares para interagir de forma segura com os callbacks da GUI
    def _log_gui(self, message):
        if "log" in self.signals:
            self.signals["log"](message)

    def _update_gui_metric(self, name, value):
        if "metric" in self.signals:
            self.signals["metric"](name, value)
