import psutil
import socket
import wmi
import logging
import platform
import subprocess
import re
import pythoncom
from typing import List, Dict, Optional, Tuple

class InterfaceInfo:
    """
    Classe responsável por coletar informações detalhadas das interfaces de rede.
    Utiliza psutil para informações básicas e WMI (Windows Management Instrumentation) 
    para detalhes avançados no Windows.
    """
    def __init__(self):
        # WMI não deve ser instanciado globalmente se for usado em threads diferentes
        self.wmi_client = None

    def _get_wmi(self):
        """
        Inicializa e retorna o cliente WMI com tratamento correto de threads (COM).
        """
        if platform.system() == "Windows":
            try:
                pythoncom.CoInitialize()
                return wmi.WMI()
            except Exception as e:
                logging.error(f"Erro ao inicializar WMI: {e}")
                return None
        return None

    def get_interfaces(self) -> List[str]:
        """
        Retorna uma lista de nomes de interfaces de rede disponíveis, priorizando 
        interfaces Ethernet/Físicas.

        Returns:
            List[str]: Lista de nomes das interfaces.
        """
        # WMI não é usado aqui, apenas psutil
        all_interfaces = list(psutil.net_if_addrs().keys())
        ethernet_interfaces = []
        other_interfaces = []
        
        # Palavras-chave heurísticas simples para Windows
        # Preferimos nomes que não pareçam Loopback, VMWare, VirtualBox, Pseudo, Teredo
        priority_keywords = ["Ethernet", "Local Area Connection"]
        ignore_keywords = ["Loopback", "VMware", "VirtualBox", "Pseudo", "Teredo", "WSL", "Hyper-V"]
        
        for iface in all_interfaces:
            # Verificar lista de ignorados
            if any(k.lower() in iface.lower() for k in ignore_keywords):
                other_interfaces.append(iface)
                continue
                
            # Verificar lista de prioridade
            if any(k.lower() in iface.lower() for k in priority_keywords):
                ethernet_interfaces.append(iface)
            else:
                other_interfaces.append(iface)
                
        # Ordenar interfaces Ethernet para colocar "Ethernet" primeiro
        ethernet_interfaces.sort()
        
        # Combinar
        return ethernet_interfaces + other_interfaces

    def get_interface_details(self, interface_name: str) -> Dict[str, any]:
        """
        Recupera informações detalhadas para uma interface específica.

        Args:
            interface_name (str): O nome da interface a ser consultada.

        Returns:
            Dict[str, any]: Dicionário com detalhes (IP, Máscara, Gateway, DNS, MAC, etc).
        """
        details = {
            "name": interface_name,
            "status": "UNKNOWN",
            "speed": "Unknown",
            "duplex": "Unknown",
            "ip": "N/A",
            "mask": "N/A",
            "gateway": "N/A",
            "dns": [],
            "mac": "N/A"
        }

        # Status e Informações Básicas via psutil
        stats = psutil.net_if_stats().get(interface_name)
        if stats:
            details["status"] = "UP" if stats.isup else "DOWN"
            details["speed"] = f"{stats.speed} Mbps" if stats.speed > 0 else "Unknown"
            # psutil duplex muitas vezes não está disponível ou é impreciso no Windows
            if stats.duplex == psutil.NIC_DUPLEX_FULL:
                details["duplex"] = "Full Duplex"
            elif stats.duplex == psutil.NIC_DUPLEX_HALF:
                details["duplex"] = "Half Duplex"
            else:
                details["duplex"] = "Auto/Unknown"

        # Configuração de IP via psutil
        addrs = psutil.net_if_addrs().get(interface_name, [])
        for addr in addrs:
            if addr.family == socket.AF_INET:
                details["ip"] = addr.address
                details["mask"] = addr.netmask
            elif addr.family == psutil.AF_LINK:
                details["mac"] = addr.address

        # Gateway e DNS são mais complicados.
        # No Windows, podemos usar WMI ou parsear ipconfig. WMI é mais limpo.
        wmi_client = self._get_wmi()
        if wmi_client and details["mac"] != "N/A":
            try:
                # Consulta WMI para corresponder à descrição da interface
                # O nome do psutil geralmente é o UUID ou nome amigável.
                # Tentamos corresponder pelo endereço MAC primeiro, pois é mais único.
                normalized_mac = details["mac"].replace("-", ":").upper()
                
                # Consultar NetworkAdapterConfiguration
                configs = wmi_client.Win32_NetworkAdapterConfiguration(IPEnabled=True)
                
                for config in configs:
                    if config.MACAddress and config.MACAddress.upper() == normalized_mac:
                        if config.DefaultIPGateway:
                            details["gateway"] = config.DefaultIPGateway[0]
                        if config.DNSServerSearchOrder:
                            details["dns"] = list(config.DNSServerSearchOrder)
                        
                        break
                        
            except Exception as e:
                logging.error(f"Erro ao consultar WMI: {e}")

        return details

    def get_wifi_info(self) -> Dict[str, str]:
        """
        Coleta informações da conexão Wi-Fi atual (se disponível) utilizando o utilitário
        nativo do Windows "netsh wlan show interfaces".
        
        Suporta parseamento flexível para ambientes com diferentes idiomas e formatos de saída.
        
        Returns:
            Dict[str, str]: Dicionário com SSID, BSSID (MAC do AP), método de autenticação e sinal.
        """
        info = {
            "ssid": "N/A",
            "bssid": "N/A",
            "auth": "N/A",
            "signal": "N/A",
        }

        if platform.system() != "Windows":
            return info

        try:
            # Executa o comando netsh wlan show interfaces
            # CREATE_NO_WINDOW impede que uma janela de console pisque para o usuário
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            output = subprocess.check_output(
                ["netsh", "wlan", "show", "interfaces"],
                encoding="utf-8",
                errors="ignore",
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
                startupinfo=startupinfo
            )
        except Exception as e:
            logging.error(f"Erro ao executar netsh wlan show interfaces: {e}")
            return info

        # Parseamento robusto linha a linha
        lines = output.splitlines()
        for line in lines:
            line = line.strip()
            if not line or ":" not in line:
                continue
                
            parts = line.split(":", 1)
            key = parts[0].strip().lower()
            value = parts[1].strip()
            
            # SSID (Nome da Rede)
            if key == "ssid":
                info["ssid"] = value
            
            # BSSID (MAC do Rádio do AP)
            # Pode aparecer como "BSSID" ou "BSSID 1" em alguns drivers
            elif "bssid" in key:
                info["bssid"] = value
                
            # Autenticação
            elif "authentication" in key or "autenticação" in key:
                info["auth"] = value
                
            # Sinal
            elif "signal" in key or "sinal" in key:
                info["signal"] = value

        return info

    def get_gateway_mac(self, gateway_ip: Optional[str]) -> str:
        """
        Obtém o endereço MAC associado ao gateway padrão, utilizando a tabela ARP
        do sistema operacional.

        Args:
            gateway_ip (Optional[str]): Endereço IP do gateway.

        Returns:
            str: Endereço MAC no formato de texto ou "N/A" se não encontrado.
        """
        if not gateway_ip or gateway_ip == "N/A":
            return "N/A"

        if platform.system() != "Windows":
            return "N/A"

        try:
            output = subprocess.check_output(
                ["arp", "-a", gateway_ip],
                encoding="utf-8",
                errors="ignore",
            )
        except Exception as e:
            logging.error(f"Erro ao executar arp -a para {gateway_ip}: {e}")
            return "N/A"

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
                
            # Verificar se a linha começa com o IP exato
            # Ex: "192.168.1.1   00-11-..."
            parts = line.split()
            if len(parts) >= 2 and parts[0] == gateway_ip:
                for part in parts:
                    if re.match(r"^[0-9a-fA-F:-]{17,}$", part):
                        return part

        return "N/A"
