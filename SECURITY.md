# Política de Segurança e Arquitetura - NetDiag Tool v3.0

Este documento descreve os aspectos de segurança, arquitetura e requisitos de privilégios da ferramenta NetDiag Tool, visando auditorias de segurança da informação.

## 1. Visão Geral da Arquitetura
O NetDiag Tool é uma aplicação desktop desenvolvida em Python que fornece diagnósticos de rede locais.
- **Frontend**: Utiliza o framework [Flet](https://flet.dev) (baseado em Flutter) para a interface gráfica.
- **Backend**: Utiliza bibliotecas Python nativas e de terceiros para interagir com o sistema operacional e hardware de rede.
- **Distribuição**: Empacotado como um executável único (`.exe`) via PyInstaller, contendo todas as dependências necessárias.

## 2. Requisitos de Privilégios
Para funcionamento completo, a aplicação requer privilégios de **Administrador** (Windows) ou **Root** (Linux).

### Justificativa:
- **Raw Sockets (Scapy)**: A funcionalidade de descoberta de switch (LLDP/CDP) utiliza "raw sockets" para capturar pacotes da camada 2. O sistema operacional restringe esse acesso apenas a usuários privilegiados.
- **ICMP (Ping)**: Em algumas configurações, o envio de pacotes ICMP personalizados pode exigir elevação, embora o comando `ping` do sistema seja invocado como subprocesso.
- **WMI (Windows Management Instrumentation)**: A coleta detalhada de informações da interface de rede acessa o subsistema WMI, que pode ter restrições de leitura para usuários comuns.

## 3. Fluxo de Dados e Conectividade
A aplicação opera localmente e minimiza conexões externas.

### 3.1. Tráfego de Rede Gerado
- **ICMP Ping**: Envia pacotes ICMP para o Gateway Padrão (local) e para o servidor DNS do Google (`8.8.8.8`) para testar conectividade com a internet.
- **Escuta Passiva (Sniffing)**: A interface de rede é colocada em modo promíscuo (via driver Npcap/WinPcap) para capturar pacotes de broadcast/multicast dos protocolos LLDP (Link Layer Discovery Protocol) e CDP (Cisco Discovery Protocol).
  - **Nota**: A aplicação *não* injeta pacotes maliciosos nem realiza varreduras de portas (port scanning) ofensivas.

### 3.2. Acesso à Internet
- A aplicação **não** envia dados de telemetria, logs ou informações do usuário para servidores externos.
- A única conexão externa intencional é o teste de Ping para `8.8.8.8`.
- A interface gráfica (Flet) roda em um servidor web local (`localhost`) embutido no processo, sem expor portas para a rede externa.

## 4. Dependências e Bibliotecas
As principais bibliotecas de terceiros utilizadas são:
- **Flet**: Interface gráfica.
- **Scapy**: Manipulação e captura de pacotes de rede.
- **Psutil**: Informações do sistema e hardware.
- **PyWin32 (WMI)**: Interação com APIs do Windows.

## 5. Armazenamento de Dados
- **Logs de Erro**: Erros fatais são gravados localmente em um arquivo `error_log.txt` no mesmo diretório do executável.
- **Sem Persistência Sensível**: A aplicação não armazena credenciais, senhas ou histórico de varreduras em disco.

## 6. Considerações sobre o Executável (PyInstaller)
O executável gerado contém o interpretador Python e o código fonte compilado (`.pyc`).
- **Engenharia Reversa**: Embora o código esteja "congelado", ele pode ser extraído. Não há ofuscação de código aplicada, pois a ferramenta não contém segredos comerciais ou chaves de API privadas.
- **Integridade**: Recomenda-se verificar o hash do executável se distribuído em larga escala.

## 7. Mitigações de Segurança Implementadas
- **Validação de Entrada**: Entradas de hostname/IP são validadas para evitar injeção de comandos.
- **Tratamento de Erros**: Exceções são capturadas para evitar falhas silenciosas ou exposição de stack traces na UI (embora logadas em arquivo para debug).
- **Execução Offline**: O build foi ajustado para incluir binários do Flet, permitindo execução em ambientes corporativos sem acesso à internet ou atrás de proxies restritivos.
