# Especificação Técnica Completa: Sistema de Treinamento Federado com Flower.ai

**Versão:** 2.0 (Atualizada com a implementação da Fase 4 - Simulador GUI e Autenticação gRPC)  
**Status:** Documento de Engenharia de Software  
**Metodologia:** Desenvolvimento Orientado por Especificações (SDD)  

---

## Fase 1: Especificar

Esta fase define rigorosamente as capacidades e as fronteiras do sistema do ponto de vista funcional e de qualidade, servindo como a única fonte da verdade para o desenvolvimento guiado por IA.

### 1.1. Resumo
Este sistema desktop implementa um simulador de ambiente de treinamento federado distribuído e assíncrono integrado às diretrizes de carga do Google Antigravity e orquestrado pelo framework Flower.ai. Ele permite que múltiplos clientes se autentiquem em um servidor central por meio de credenciais e chaves SHA-256 (via metadados gRPC) e executem rotinas locais de machine learning utilizando uma abstração de `NumPyClient` sobre diretórios locais, sem expor os dados brutos na rede.

### 1.2. Histórias do Usuário
* **Como operador do servidor central,** quero validar cada nó cliente Flower utilizando dados de login e chaves criptográficas SHA-256 exclusivas anexadas ao handshake gRPC para garantir a integridade e o isolamento do pool de treinamento.
* **Como cientista de dados (operador do cliente),** quero usar uma interface gráfica amigável em PyQt para selecionar a pasta local de dados, configurar minhas credenciais e comandar o início ou término do cliente Flower sem que a aplicação trave ou sofra corrupção de memória.

### 1.3. Critérios de Aceitação
* O servidor e os clientes rodam de forma isolada em processos distintos, utilizando o framework Flower.ai sobre o protocolo de rede gRPC.
* A interface gráfica (GUI) do cliente é desenvolvida em PyQt (PyQt6) e contém um seletor nativo de diretórios, inicializando o loop do `flwr.client.start_client` em segundo plano quando comandado.
* A autenticação rejeita somariamente qualquer cliente cujo token SHA-256 divirja por apenas um caractere da chave gerada pelo servidor, sendo essa validação processada por um gRPC Interceptor (`AuthInterceptor`) antes de atingir a estratégia de agregação.
* A interrupção do processamento local por parte do cliente é realizada de forma coordenada (graceful) usando `threading.Event`, impedindo o encerramento abrupto da thread que executa bindings em C++ (gRPC).

### 1.4. Requisitos Funcionais

| ID | Categoria | Descrição do Requisito | Status |
| :--- | :--- | :--- | :--- |
| **RF-001** | Orquestração Flower | Utilização do ecossistema Flower.ai para gerenciar ciclos de vida federados, sincronização de pesos e agregação centralizada. | **Implementado** |
| **RF-002** | Autenticação gRPC | Validação de login/senha e Hash SHA-256 interceptados nativamente no pipeline gRPC do servidor antes de permitir o registro do nó. | **Implementado** |
| **RF-003** | Interface de Abstração | O cliente PyQt expõe os estados internos do Flower (Rodada Atual, Perda Local, Acurácia) disparados por callbacks do ciclo de treinamento vinculados de forma thread-safe à interface gráfica. | **Implementado** |
| **RF-004** | Controles PyQt GUI | Exibição de Botão Iniciar, Botão Parar (com interrupção coordenada via flag de cancelamento e sem terminação abrupta de thread) e Folder Picker nativo (`QFileDialog`). | **Implementado** |

### 1.5. Requisitos Não-Funcionais
* **Isolamento de Threads do Flower:** O método de inicialização do cliente Flower (`start_client`) é blocante. Ele roda encapsulado em uma `QThread` do PyQt (classe `FlowerWorker`).
* **Comunicação Inter-Thread PyQt/Flower:** O acoplamento entre a lógica do cliente (`SimulatedNumPyClient`) e a interface é feito por meio de callbacks passados via construtor do cliente e sinais do PyQt (`pyqtSignal`), atualizando a UI de forma assíncrona e thread-safe.
* **Consistência de Tensores (Google Antigravity):** A estratégia customizada `AntigravityFedAvg` no servidor e o cliente `SimulatedNumPyClient` simulam a latência e barreira de consistência de rede no envio e recebimento de tensores.

### 1.6. Casos Extremos
* **Queda de conexão gRPC:** Erros de comunicação de rede no meio do ciclo de treino finalizam o Worker e emitem mensagens apropriadas para o usuário na GUI.
* **Diretório de dados vazio ou inválido:** O cliente valida o diretório de dados na inicialização do `SimulatedNumPyClient`, impedindo a conexão caso a pasta esteja vazia ou inexistente.
* **Interrupção coordenada:** Acionamento do botão "Parar" sinaliza o `cancel_event` (`threading.Event`). O laço do método `fit()` verifica a flag a cada época, interrompendo o ciclo graciosamente.

---

## Fase 2: Planejar

Esta fase dita a arquitetura técnica adotada e os componentes que compõem o sistema atual.

### 2.1. Visão Geral da Arquitetura

O sistema é dividido nos seguintes componentes e arquivos correspondentes:

1. **Módulo de Autenticação ([auth.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/auth.py)):**
   Contém o dicionário de usuários autorizados e suas respectivas senhas em formato plain-text para simulação, além do gerador de hash SHA-256 e da rotina `verify_credentials(username, client_hash)`.

2. **Servidor Central ([server.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/server.py)):**
   - **`AuthInterceptor`**: Classe gRPC Interceptor que lê metadados gRPC (chaves `auth-username` e `auth-hash`) de cada chamada recebida e aborta conexões não autenticadas ou com hash divergente.
   - **Patch do Servidor gRPC**: Aplicação de monkey patch no inicializador do gRPC do Flower para injetar o interceptor de segurança de forma transparente.
   - **`AntigravityFedAvg`**: Subclasse de `flwr.server.strategy.FedAvg` que simula barreira de concorrência ou latência durante a agregação de pesos federados.
   - **Agregação de Métricas**: Coleta e calcula a acurácia federada ponderada por amostras por meio do callback `fit_metrics_aggregation`.

3. **Lógica do Cliente ([client_logic.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/client_logic.py)):**
   - **`SimulatedNumPyClient`**: Implementação de `flwr.client.NumPyClient`. Executa validações de pasta vazia, simula épocas locais com redução de loss e incremento de acurácia, reporta métricas para a GUI via callbacks (`_log_gui` e `_update_gui_metric`) e suporta interrupção controlada via `cancel_event`.

4. **Interface Gráfica ([client_gui.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/client_gui.py)):**
   - Roda a interface PyQt6 com duas telas principais: Tela de Configuração (login, hash correspondente, seletor de diretório de dados) e Tela do Simulador de Treino (exibindo rodada atual, logs em tempo real, progresso de loss e acurácia).
   - Gerencia a thread de execução do Flower através da classe `FlowerWorker(QThread)`, garantindo a segurança de threads no PyQt6.
   - Conecta o botão "Parar" ao sinalizador de encerramento do cliente Flower.

### 2.2. Pilha de Tecnologia
* **Linguagem:** Python 3.10+
* **Framework Federado:** Flower.ai (`flwr` v1.x) e biblioteca `grpcio` para interceptores.
* **Interface Gráfica:** PyQt6.
* **Segurança/Hash:** Módulo `hashlib` e gRPC Server Interceptors.
* **Sincronização:** Módulo `threading` (`threading.Event`) e concorrência PyQt (`QThread`, `pyqtSignal`).

---

## Fase 3: Tarefas

Status das sprints de desenvolvimento e entregas (v2.0):

### Fase 1 – Fundação
* **[x] Tarefa 1.1:** Inicializar o repositório do projeto, configurar o ambiente virtual (`venv`) e instalar as dependências de PyQt, gRPC e Flower.
* **[x] Tarefa 1.2:** Criar utilitário de geração e comparação de hashes SHA-256 para validação das sessões ([auth.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/auth.py)).

### Fase 2 – Funcionalidade Principal (Orquestração Flower)
* **[x] Tarefa 2.1:** Implementar a classe gRPC Server Interceptor para interceptar handshakes, ler metadados e validar chaves. Inicializar o `flwr.server.Server` com o interceptor de rede ([server.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/server.py)).
* **[x] Tarefa 2.2:** Desenvolver a classe cliente herdando de `flwr.client.NumPyClient`, implementando mapeamento de métodos obrigatórios com checagem interna de interrupção ([client_logic.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/client_logic.py)).

### Fase 3 – Interface do Usuário (Front-End)
* **[x] Tarefa 3.1:** Desenvolver a janela principal com campos de login, senha e exibição do hash SHA-256 gerado automaticamente ([client_gui.py](file:///c:/Users/Antony/Desktop/simulador_federado_flower/client_gui.py)).
* **[x] Tarefa 3.2:** Implementar o botão de folder picker integrando com o componente `QFileDialog` para definir a pasta de dados locais.

### Fase 4 – Segurança, Concorrência e Resiliência
* **[x] Tarefa 4.1:** Criar a classe `FlowerWorker(QThread)` contendo sinais PyQt específicos e um `threading.Event` de cancelamento. Vincular a ação do botão "Parar" ao cancelamento gracioso do cliente Flower.
* **[x] Tarefa 4.2:** Tratar exceções de desconexão, logins incorretos ou erro de validação de diretórios, refletindo o feedback visualmente na interface.

### Fase 5 – Testes e Validação
* **[x] Tarefa 5.1:** Validar o ciclo completo: Inicializar o Servidor gRPC/Flower, conectar os clientes autenticados com sucesso e verificar a parada coordenada sem travamentos.

---

## Fase 4: Próximos Passos (Próximas Versões)

* **Treinamento Real com CNN e TensorFlow:** Substituir o cliente de simulação (`SimulatedNumPyClient`) por uma versão real usando TensorFlow/Keras para ler dados de imagens locais, treinar uma arquitetura CNN localmente, transferir os parâmetros e agregar as métricas de forma real no servidor.
