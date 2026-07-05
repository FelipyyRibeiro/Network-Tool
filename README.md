# NetDiag Tool v3.0

Ferramenta de diagnóstico e descoberta de rede para técnicos e administradores.

##  Visão Geral
O **NetDiag Tool** é uma aplicação Windows desenvolvida para simplificar a identificação de problemas em redes corporativas. Com uma interface moderna e intuitiva, ele permite:
*   Identificar rapidamente informações da porta do Switch (LLDP/CDP).
*   Testar a conectividade com Gateway e Internet.
*   Visualizar detalhes da interface de rede local.

##  Funcionalidades

### 1. Informações da Interface
Exibe detalhes cruciais da placa de rede selecionada:
*   Endereço IP e Máscara
*   Endereço MAC
*   Status do Link

### 2. Testes de Conectividade
Realiza testes automáticos de ping para validar a conexão:
*   **Gateway Padrão**: Verifica a comunicação com o roteador local.
*   **Internet (8.8.8.8)**: Verifica a saída para a internet.
*   Exibe latência e status (OK/Falha).

### 3. Descoberta de Switch (LLDP/CDP)
Utiliza protocolos de descoberta (LLDP e CDP) para identificar onde o cabo de rede está conectado:
*   **Nome do Switch**
*   **IP de Gerência**
*   **Porta ID** (Porta do Switch)
*   **VLAN**
*   **Protocolo Identificado**

##  Requisitos do Sistema

*   **Sistema Operacional**: Windows 10 ou Windows 11 (64-bit).
*   **Privilégios**: Execução como **Administrador** (necessário para escuta de pacotes de rede).
*   **Dependência Externa**: **Npcap** (Driver de captura de pacotes).
    *   Necessário para a funcionalidade de "Descoberta de Switch".
    *   Geralmente instalado junto com Wireshark ou Nmap.
    *   Pode ser baixado em: [https://npcap.com/](https://npcap.com/) (Instalar em modo "WinPcap API-compatible").

##  Segurança e Auditoria
O projeto foi desenvolvido seguindo práticas de segurança para minimizar riscos em ambientes corporativos.
- **Execução Offline**: O executável contém todas as dependências necessárias, não exigindo acesso à internet para baixar componentes do Flet.
- **Sem Telemetria**: Nenhuma informação é enviada para servidores externos.
- **Validação**: Entradas de dados são validadas para evitar execução de comandos arbitrários.
- **Documentação de Segurança**: Consulte o arquivo [SECURITY.md](SECURITY.md) para detalhes técnicos sobre privilégios, portas e fluxo de dados.

##  Instalação
1.  Certifique-se de ter o **Npcap** instalado ([https://npcap.com/](https://npcap.com/)).
2.  Baixe o executável `NetDiagTool.exe` (ou use o instalador).
3.  Execute como **Administrador**.

##  Como Usar
1.  Abra o **NetDiag Tool** (como Administrador).
2.  Selecione a **Interface de Rede** desejada no menu suspenso.
3.  Clique no botão **"INICIAR DIAGNÓSTICO COMPLETO"**.
4.  Aguarde a execução dos testes (a descoberta de switch pode levar até 60 segundos).
5.  Visualize os resultados nos cartões abaixo.

---
**Desenvolvido por:** Felipe Ribeiro | email: felipyribeiro24@gmail.com

