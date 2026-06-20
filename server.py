import time
import grpc
import flwr as fl
from typing import Dict, List, Tuple, Optional, Union
from flwr.common import Metrics

from auth import verify_credentials

# Interceptor gRPC para validação de autenticação
class AuthInterceptor(grpc.ServerInterceptor):
    def __init__(self):
        def abort(context, details):
            context.abort(grpc.StatusCode.UNAUTHENTICATED, details)
        self._abort_fn = abort

    def intercept_service(self, continuation, handler_call_details):
        metadata = dict(handler_call_details.invocation_metadata)
        
        # O gRPC converte chaves dos metadados para minúsculo
        username = metadata.get("auth-username")
        client_hash = metadata.get("auth-hash")
        
        print(f"\n[gRPC Interceptor] Nova tentativa de conexão recebida.")
        print(f"[gRPC Interceptor] Username enviado: {username}")
        print(f"[gRPC Interceptor] Hash SHA-256 enviado: {client_hash}")
        
        if not username or not client_hash:
            print("[gRPC Interceptor] Acesso negado: Credenciais ausentes nos metadados.")
            return grpc.unary_unary_rpc_method_handler(
                lambda request, context: self._abort_fn(context, "Credenciais de autenticação ausentes")
            )
            
        if not verify_credentials(username, client_hash):
            print("[gRPC Interceptor] Acesso negado: Hash SHA-256 incorreto para o usuário.")
            return grpc.unary_unary_rpc_method_handler(
                lambda request, context: self._abort_fn(context, "Autenticação falhou")
            )
            
        print(f"[gRPC Interceptor] Acesso concedido para o usuário '{username}'.")
        return continuation(handler_call_details)

# Aplicar o Monkey Patch no gRPC Server antes que o Flower inicialize
original_grpc_server = grpc.server

def patched_grpc_server(*args, **kwargs):
    interceptors = kwargs.get("interceptors", [])
    if interceptors is None:
        interceptors = []
    else:
        interceptors = list(interceptors)
    
    # Adicionar o interceptor de autenticação
    interceptors.append(AuthInterceptor())
    kwargs["interceptors"] = interceptors
    
    return original_grpc_server(*args, **kwargs)

grpc.server = patched_grpc_server

# Estratégia de Agregação Customizada com simulação do Google Antigravity
class AntigravityFedAvg(fl.server.strategy.FedAvg):
    def aggregate_fit(
        self,
        server_round: int,
        results: List[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes]],
        failures: List[Union[Tuple[fl.server.client_proxy.ClientProxy, fl.common.FitRes], BaseException]],
    ) -> Tuple[Optional[fl.common.Parameters], Dict[str, fl.common.Scalar]]:
        
        print(f"\n[Antigravity Server] --- Fim da Rodada {server_round} ---")
        print(f"[Antigravity Server] Clientes que completaram com sucesso: {len(results)}")
        print(f"[Antigravity Server] Falhas/Desconexões: {len(failures)}")
        
        # Simula barreira de concorrência ou latência na agregação dos parâmetros
        print("[Antigravity Server] Processando agregação de tensores e validando consistência...")
        time.sleep(1.0)
        
        # Chama a agregação original do FedAvg
        return super().aggregate_fit(server_round, results, failures)

# Função para extrair métricas personalizadas durante o treinamento
def fit_metrics_aggregation(metrics: List[Tuple[int, Metrics]]) -> Metrics:
    # Agrega a acurácia média ponderada pelo número de exemplos do cliente
    accuracies = [num_examples * m["accuracy"] for num_examples, m in metrics if "accuracy" in m]
    examples = [num_examples for num_examples, m in metrics if "accuracy" in m]
    
    if not examples:
        return {}
        
    avg_accuracy = sum(accuracies) / sum(examples)
    print(f"\n[Metrics Aggregation] Acurácia Média Federada: {avg_accuracy:.4f}")
    return {"accuracy": avg_accuracy}

if __name__ == "__main__":
    print("=========================================================")
    print(" Servidor de Treinamento Federado Flower.ai Iniciado")
    print(" Porta padrão de escuta: localhost:8080")
    print(" Autenticação gRPC Ativada (SHA-256)")
    print("=========================================================")
    
    # Definindo a estratégia
    strategy = AntigravityFedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=1,
        min_evaluate_clients=1,
        min_available_clients=1,
        fit_metrics_aggregation_fn=fit_metrics_aggregation,
        on_fit_config_fn=lambda server_round: {
            "epochs": 3,
            "batch_size": 32,
            "server_round": server_round
        }
    )
    
    # Inicia o servidor Flower
    fl.server.start_server(
        server_address="0.0.0.0:8080",
        config=fl.server.ServerConfig(num_rounds=3),
        strategy=strategy,
    )
