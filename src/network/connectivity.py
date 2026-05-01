import subprocess
import platform
import re
from typing import Dict

class ConnectivityTester:
    """
    Classe responsável pelos testes de conectividade de rede (Ping).
    """
    def __init__(self):
        """
        Inicializa o testador de conectividade detectando o sistema operacional.
        """
        self.os_name = platform.system()

    def ping_host(self, host: str, count: int = 4) -> Dict[str, str]:
        """
        Realiza um teste de ping ICMP para um host especificado.

        Args:
            host (str): O endereço IP ou hostname a ser testado.
            count (int): O número de pacotes a serem enviados. Padrão é 4.

        Returns:
            Dict[str, str]: Um dicionário contendo:
                - host: O host testado.
                - status: "OK", "Fail" ou "Error".
                - latency: A latência média (se disponível).
                - details: Detalhes adicionais ou mensagem de erro.
        """
        # Validação básica de entrada para evitar injeção de comandos
        # Embora o uso de lista no subprocess evite shell injection, é boa prática validar.
        if not self._is_valid_host(host):
             return {
                "host": host,
                "status": "Error",
                "latency": "N/A",
                "details": "Invalid host format"
            }

        param = '-n' if self.os_name == 'Windows' else '-c'
        # Construção segura do comando como lista
        command = ['ping', param, str(count), host]
        
        try:
            # Executar comando ping
            # Usando codificação específica para Windows (frequentemente cp850 ou cp1252 no Brasil)
            # shell=False é o padrão e é mais seguro
            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding='cp850' if self.os_name == 'Windows' else 'utf-8'
            )
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                # Analisar saída para latência (Média)
                latency = "Unknown"
                if self.os_name == 'Windows':
                    # Procurando por "Média = 12ms" ou "Average = 12ms"
                    match = re.search(r'(Média|Average)\s*=\s*(\d+ms)', stdout)
                    if match:
                        latency = match.group(2)
                else:
                    match = re.search(r'time=(\d+\.?\d*) ms', stdout)
                    if match:
                        latency = f"{match.group(1)} ms" 
                
                return {
                    "host": host,
                    "status": "OK",
                    "latency": latency,
                    "details": "Ping successful"
                }
            else:
                return {
                    "host": host,
                    "status": "Fail",
                    "latency": "N/A",
                    "details": "Request timed out or host unreachable"
                }
                
        except Exception as e:
            return {
                "host": host,
                "status": "Error",
                "latency": "N/A",
                "details": str(e)
            }

    def test_gateway_connectivity(self, gateway_ip: str) -> Dict[str, str]:
        """
        Testa a conectividade com o Gateway padrão.

        Args:
            gateway_ip (str): O IP do gateway.

        Returns:
            Dict[str, str]: Resultado do ping.
        """
        if not gateway_ip or gateway_ip == "N/A":
            return {"host": "Gateway", "status": "Skipped", "details": "No Gateway IP"}
        return self.ping_host(gateway_ip)

    def test_internet_connectivity(self, public_ip: str = "8.8.8.8") -> Dict[str, str]:
        """
        Testa a conectividade com a Internet (padrão: Google DNS).

        Args:
            public_ip (str): IP público para teste. Padrão 8.8.8.8.

        Returns:
            Dict[str, str]: Resultado do ping.
        """
        return self.ping_host(public_ip)

    def _is_valid_host(self, host: str) -> bool:
        """
        Valida se o host parece ser um IP ou hostname válido.
        Isso é uma camada extra de segurança.
        """
        # Verificação simples de caracteres permitidos em hostnames/IPs
        # Alfanuméricos, pontos, hífens.
        return bool(re.match(r'^[a-zA-Z0-9.-]+$', host))
