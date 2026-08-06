# Especificação Técnica Completa: Sistema de Treinamento Federado com Flower.ai

**Versão:** 3.2 (Revisada com Interrupção Graciosa - Adaptada ao Modelo Spec-Driven Development - SDD)  
**Status:** Documento de Engenharia de Software
**Metodologia:** Desenvolvimento Orientado por Especificações (SDD)  

---

## Fase 1: Especificar

Esta fase define rigorosamente as capacidades e as fronteiras do sistema do ponto de vista funcional e de qualidade, servindo como a única fonte da verdade para o desenvolvimento guiado por IA.

### 1.1. Resumo
Este sistema desktop simula um ambiente de treinamento federado distribuído e assíncrono integrado às diretrizes de carga do Google Antigravity e orquestrado pelo framework Flower.ai. Ele permite que múltiplos clientes isolados se autentiquem em um servidor central por meio de credenciais e chaves SHA-256 (via metadados gRPC) e executem rotinas locais de machine learning utilizando uma abstração de `NumPyClient` sobre diretórios locais, sem expor os dados brutos na rede.

### 1.2. Histórias do Usuário
* **Como operador do servidor central,** quero validar cada nó cliente Flower utilizando dados de login mockados e chaves criptográficas SHA-256 exclusivas anexadas ao handshake gRPC para garantir a integridade e o isolamento do pool de treinamento.
* **Como cientista de dados (operador do cliente),** quero usar uma interface gráfica amigável em PyQt para selecionar a pasta local de dados, configurar minhas credenciais e comandar o início ou término do cliente Flower sem que a aplicação trave ou sofra corrupção de memória.

### 1.3. Critérios de Aceitação
* O servidor e os clientes devem rodar de forma isolada em processos distintos, utilizando o framework Flower.ai sobre o protocolo de rede gRPC.
* A interface gráfica (GUI) do cliente deve ser em PyQt e conter um seletor nativo de arquivos/pastas, inicializando o loop do `flwr.client.start_client` em segundo plano quando comandado.
* A autenticação deve rejeitar somariamente qualquer cliente cujo token SHA-256 divirja por apenas um caractere da chave gerada pelo servidor, sendo essa validação processada obrigatoriamente por um gRPC Interceptor antes de atingir a estratégia de agregação.
* A interrupção do processamento local por parte do cliente deve ser realizada de forma coordenada (graceful), impedindo o encerramento abrupto da thread que executa bindings em C++ (gRPC).

### 1.4. Requisitos Funcionais
Especificações técnicas detalhadas das operações, fluxos e manipulação de pacotes:

| ID | Categoria | Descrição do Requisito |
| :--- | :--- | :--- |
| **RF-001** | Orquestração Flower | Utilização do ecossistema Flower.ai para gerenciar ciclos de vida federados, sincronização de pesos e agregação centralizada. |
| **RF-002** | Autenticação gRPC | Validação de login/senha e Hash SHA-256 interceptados nativamente no pipeline gRPC do servidor antes de permitir o registro do nó. |
| **RF-003** | Interface de Abstração | O cliente PyQt deve expor os estados internos do Flower (Rodada Atual, Perda Local, Acurácia) disparados por callbacks do ciclo de treinamento vinculados de forma thread-safe à interface gráfica. |
| **RF-004** | Controles PyQt GUI | Exibição de Botão Iniciar, Botão Parar (com interrupção coordenada via flag de cancelamento e sem terminação abrupta de thread) e Folder Picker nativo (`QFileDialog`). |

### 1.5. Requisitos Não-Funcionais
* **Isolamento de Threads do Flower:** O método de inicialização do cliente Flower (`start_client`) é blocante. Portanto, ele deve obrigatoriamente rodar encapsulado em uma `QThread` do PyQt.
* **Comunicação Inter-Thread PyQt/Flower:** O acoplamento entre a lógica de treino (`NumPyClient`) e a interface deve ser feito por meio de injeção de dependência de callbacks de sinais (`pyqtSignal`) e uma flag de cancelamento compartilhada (ex: `threading.Event`), permitindo que métodos internos como `fit()` enviem atualizações de telemetria e verifiquem requisições de parada de forma segura, sem causar falhas de segmentação de memória (segfault) ou violar a restrição de manipulação direta da Main UI Thread.
* **Consistência de Tensores (Google Antigravity):** O pipeline de carga do Antigravity deve ser simulado limitando a banda ou injetando latência na transmissão dos parâmetros NumPy coletados pelo Flower.

### 1.6. Casos Extremos
* Queda de conexão gRPC no meio de uma rodada de atualização (`fit`) deve fazer o cliente Flower disparar uma tentativa de reconexão controlada por até 3 vezes antes de emitir um sinal de erro terminal para a interface gráfica.
* Diretórios de dados vazios ou corrompidos selecionados na interface devem disparar uma exceção de leitura imediata no método `fit()` do cliente Flower, abortando a participação do nó naquela rodada específica e notificando a GUI via sinal.
* Acionamento do Botão Parar no meio do treinamento local deve sinalizar o `threading.Event` de cancelamento. O método `fit()` interceptará a flag no início da próxima época, retornando um dicionário de parâmetros vazio ou lançando uma exceção tratada para que o Flower encerre a rodada graciosamente e libere os recursos.

---

## Fase 2: Planejar

Esta fase dita a arquitetura técnica adotada e a lógica de engenharia para atingir a especificação.

### 2.1. Visão Geral da Arquitetura
O sistema adotará a arquitetura padrão do Flower.ai com modificações de infraestrutura. Para permitir a segurança via tokens gRPC, o Servidor Central não usará o inicializador genérico `start_server`, mas instanciará manualmente um `flwr.server.Server` amarrado a um servidor gRPC nativo (`grpc.server`) com gRPC Interceptors injetados. Os clientes desktop PyQt implementarão uma subclasse de `flwr.client.NumPyClient`. O componente Google Antigravity atuará na camada de controle de concorrência do Flower, ditando o descarte ou priorização de clientes mais lentos (*stragglers*). A interrupção segura será garantida pelo monitoramento ativo de primitivas de sincronização entre a Thread do Worker PyQt e o Cliente Flower.

### 2.2. Pilha de Tecnologia e Principais Decisões
* **Linguagem:** Python 3.10+
* **Framework Federado:** Flower.ai (`flwr`) e biblioteca `grpcio` nativa para customização de interceptores.
* **Interface Gráfica:** PyQt6 ou PyQt5 (Para manipulação nativa de janelas desktop).
* **Rede:** gRPC para transporte de alta performance de tensores.
* **Segurança/Hash:** Módulo `hashlib` e gRPC Server Interceptors para interceptação e validação rigorosa do cabeçalho de autenticação.
* **Sincronização:** Módulo `threading` (`threading.Event`) para controle thread-safe do estado de cancelamento sob demanda.

### 2.3. Sequência de Implementação
1. Instanciar o loop do servidor gRPC manual adicionando o Interceptor de segurança e acoplando a classe `flwr.server.Server` com a estratégia `FedAvg`.
2. Desenvolver a classe do cliente herdando de `flwr.client.NumPyClient` preparada para receber referências de sinais PyQt e do evento de cancelamento em seu construtor.
3. Desenvolver os layouts de tela do cliente via PyQt (Widgets e Dialogs de entrada).
4. Unir o loop do Flower à interface encapsulando o worker do cliente na estrutura de concorrência `QThread`, vinculando o evento de cancelamento ao gatilho do botão de parada.

### 2.4. Verificação da Constituição
*Constituição do Projeto:* "Nenhum arquivo ou dado bruto do cliente pode ser transmitido ao servidor." O framework Flower reforça inerentemente este pilar da nossa constituição, uma vez que apenas os coeficientes matemáticos modificados (pesos da rede convertidos em listas NumPy) trafegam pelo canal gRPC.

### 2.5. Suposições e Perguntas Abertas
* *Suposição:* Assume-se que o modelo local que roda dentro do método `fit` do cliente Flower está previamente instanciado (via PyTorch, TensorFlow ou Scikit-Learn) e é compatível com o formato de agregação do servidor e aceita interrupções por época.

---

## Fase 3: Tarefas

Conversão de alto nível em entregáveis acionáveis e testáveis divididos em sprints lógicas:

### Fase 1 – Fundação
* **Tarefa 1.1:** Inicializar o repositório do projeto, configurar o ambiente virtual (`venv`) e instalar as dependências de PyQt, gRPC e Flower (`pip install flwr pyqt6 grpcio`).
* **Tarefa 1.2:** Criar utilitário de geração e comparação de hashes SHA-256 para validação das sessões.

### Fase 2 – Funcionalidade Principal (Orquestração Flower)
* **Tarefa 2.1:** Implementar a classe gRPC Server Interceptor para interceptar handshakes, ler metadados e validar chaves. Inicializar o `flwr.server.Server` manualmente injetando esse interceptor no pipeline de rede.
* **Tarefa 2.2:** Desenvolver a classe cliente herdando de `flwr.client.NumPyClient`, implementando um construtor que aceite um canal de comunicação de telemetria e o objeto de cancelamento, mapeando os métodos obrigatórios (`get_parameters`, `fit`, `evaluate`) com checagem interna de interrupção.

### Fase 3 – Interface do Usuário (Front-End)
* **Tarefa 3.1:** Desenvolver a janela principal com campos de login, senha e hash usando `QLineEdit`.
* **Tarefa 3.2:** Implementar o botão de folder picker integrando com o componente `QFileDialog.getExistingDirectory`.


### Fase 4 – Segurança, Concorrência e Resiliência
* **Tarefa 4.1:** Criar uma classe `FlowerWorker(QThread)` contendo sinais PyQt (`pyqtSignal`) específicos para estados de treino e um `threading.Event` de cancelamento. Instanciar o `NumPyClient` passando esses sinais e o evento para dentro de seu escopo, executando o `flwr.client.start_client` em seguida. Vincular a ação do botão "Parar" ao método `.set()` do evento de cancelamento.
* **Tarefa 4.2:** Capturar exceções de conexão gRPC (como `grpc._channel._InactiveRpcError`) dentro da Thread e emitir sinais de erro mapeados para `QMessageBox` na interface visível.

### Fase 5 – Testes e Validação
* **Tarefa 5.1:** Validar o ciclo completo: Inicializar o Servidor gRPC/Flower customizado, abrir 2 instâncias do Cliente PyQt com hashes corretos (devem conectar e treinar atualizando a interface gráfica via sinais), acionar o botão "Parar" em um deles para homologar a desconexão graciosa sem travamento do app, e validar que uma instância com hash incorreto seja rejeitada de imediato.

---

## Fase 4: Implementar

O processo de codificação seguirá estritamente a ordem definida na Fase 3. A cada funcionalidade codificada, um teste de integração local deve validar se o critério de aceitação associado foi preenchido. Caso um novo comportamento de rede ou uma especificação de concorrência do Google Antigravity mude, o desenvolvedor deve pausar a codificação, atualizar este documento na Fase 1 ou 2, ajustar as tarefas da Fase 3 e reiniciar o ciclo iterativo.
