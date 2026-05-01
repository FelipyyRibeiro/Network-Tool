from scapy.all import sniff, Ether, Dot3, conf, sendp
from scapy.layers.l2 import STP
from scapy.contrib.lldp import (
    LLDPDU,
    LLDPDUChassisID,
    LLDPDUPortID,
    LLDPDUPortDescription,
    LLDPDUTimeToLive,
    LLDPDUEndOfLLDPDU,
    LLDPDUManagementAddress,
    LLDPDUSystemName,
    LLDPDUSystemDescription,
    LLDPDUSystemCapabilities,
    LLDPDUGenericOrganisationSpecific
)
from scapy.contrib.cdp import (
    CDPv2_HDR, 
    CDPMsg, 
    CDPMsgDeviceID, 
    CDPMsgPortID, 
    CDPMsgNativeVLAN, 
    CDPMsgPower,
    CDPMsgAddr,
    CDPAddrRecordIPv4
)
import threading
import logging
import time
import scapy.packet

class SwitchDiscovery:
    """
    Classe responsável pela descoberta de switches e dispositivos de rede vizinhos
    usando protocolos de camada 2 (LLDP, CDP, EDP, STP).
    
    Requisitos de Segurança:
    - Requer privilégios administrativos (Admin) para abrir sockets brutos (raw sockets).
    - No Windows, requer driver Npcap instalado.
    """
    def __init__(self):
        self.results = {
            "switch_name": "Unknown",
            "switch_ip": "Unknown",
            "port_id": "Unknown",
            "vlan": "Unknown",
            "protocol": "None",
            "system_desc": "Unknown",
            
        }
        self.stop_sniffing = False
        self.first_discovery_time = None
        self.found_lldp = False
        self.lldp_wait_after_first = 20 # Tempo extra para coletar mais detalhes após o primeiro pacote

    def _safe_decode(self, value):
        """Decodifica bytes para string de forma segura, ignorando erros."""
        if isinstance(value, bytes):
            return value.decode('utf-8', errors='ignore')
        return str(value)

    def _decode_ip(self, value):
        """Decodifica bytes brutos para string IPv4 se possível."""
        try:
            if isinstance(value, bytes):
                # Caso comum: 4 bytes para IPv4
                if len(value) == 4:
                    return ".".join(str(b) for b in value)
                # Às vezes pode já ser uma string ou mais longo
                # Tentar decodificação padrão primeiro
                return value.decode('utf-8', errors='ignore')
            return str(value)
        except:
            return "Unknown"

    def _packet_callback(self, pkt):
        """
        Callback chamado para cada pacote capturado. Analisa LLDP, CDP, EDP e STP.
        """
        # Filtrar via software em vez de BPF para evitar problemas com Npcap no Windows
        allowed_macs = [
            "01:80:c2:00:00:0e", # LLDP
            "01:80:c2:00:00:03", # LLDP
            "01:80:c2:00:00:00", # LLDP / STP (Bridge Group)
            "01:00:0c:cc:cc:cc", # CDP
            "00:e0:2b:00:00:00"  # EDP
        ]

        # Verificar se o MAC de destino corresponde a algum protocolo de descoberta
        dst = getattr(pkt, "dst", "")
        if not isinstance(dst, str):
            dst = str(dst)
        dst = dst.lower()
        if dst not in allowed_macs:
            return

        # Ignorar pacotes enviados pela própria interface local (evita contar nosso próprio LLDP)
        src = getattr(pkt, "src", "")
        if not isinstance(src, str):
            src = str(src)
        src = src.lower()
        if getattr(self, "my_mac", None) and src == self.my_mac:
            return

        # Inicializar resultados para este pacote
        # Sobrescrever apenas se encontrarmos algo válido
        
        # Determinar Protocolo e resetar estado de varredura
        detected_protocol = None
        if pkt.haslayer(LLDPDU):
            detected_protocol = "LLDP"
        elif pkt.haslayer(CDPv2_HDR) or pkt.haslayer(CDPMsg):
            detected_protocol = "CDP"
        # Verificação EDP (Extreme Discovery Protocol)
        elif pkt.dst == "00:e0:2b:00:00:00": 
            detected_protocol = "EDP"
        # Verificação STP (Spanning Tree Protocol)
        elif pkt.dst == "01:80:c2:00:00:00" and pkt.haslayer(STP):
             detected_protocol = "STP"

        if detected_protocol:
            # Se já encontramos LLDP, ignorar outros protocolos para evitar sobrescrita com dados menos ricos
            if self.found_lldp and detected_protocol != "LLDP":
                return

            if self.first_discovery_time is None:
                self.first_discovery_time = time.time()
            if detected_protocol == "LLDP":
                self.found_lldp = True
            
            self.results["protocol"] = detected_protocol
            # Limpar campos de 'Scanning...' para 'Not Found' se encontrarmos um pacote válido
            for k in ["switch_name", "switch_ip", "port_id", "port_desc", "vlan", "poe_status", "system_desc", "capabilities"]:
                if self.results.get(k) == "Scanning...":
                    self.results[k] = "Not Found"
        
        # --- Análise LLDP ---
        if detected_protocol == "LLDP":
            try:
                # Iterar sobre TODAS as camadas para encontrar TLVs independentemente do aninhamento
                current_layer = pkt.getlayer(LLDPDU)
                
                while current_layer:
                    # 1. Nome do Sistema
                    if isinstance(current_layer, LLDPDUSystemName):
                        self.results["switch_name"] = self._safe_decode(current_layer.system_name)

                    # 1b. Descrição do Sistema
                    if isinstance(current_layer, LLDPDUSystemDescription):
                        self.results["system_desc"] = self._safe_decode(current_layer.description)

                    # 1c. Capacidades
                    if isinstance(current_layer, LLDPDUSystemCapabilities):
                        try:
                            caps_val = current_layer.capabilities
                            caps = []
                            if caps_val & 4: caps.append("Switch")
                            if caps_val & 16: caps.append("Router")
                            if caps_val & 8: caps.append("WLAN AP")
                            if caps_val & 32: caps.append("Phone")
                            self.results["capabilities"] = ", ".join(caps) if caps else str(caps_val)
                        except:
                            pass
                    
                    # 2. ID da Porta
                    if isinstance(current_layer, LLDPDUPortID):
                        self.results["port_id"] = self._safe_decode(current_layer.id)
                    
                    # 3. Descrição da Porta (Descrição da Interface no switch)
                    if isinstance(current_layer, LLDPDUPortDescription):
                        self.results["port_desc"] = self._safe_decode(current_layer.description)
                    
                    # 4. Endereço de Gerenciamento (IP)
                    if isinstance(current_layer, LLDPDUManagementAddress):
                        if current_layer.management_address_subtype == 1:
                            self.results["switch_ip"] = self._decode_ip(current_layer.management_address)

                    # 5. TLVs Específicos da Org (VLAN, PoE)
                    if isinstance(current_layer, LLDPDUGenericOrganisationSpecific):
                        # IEEE 802.1 (VLAN) -> OUI 0x0080c2
                        if current_layer.org_code == 0x0080c2:
                            # Subtipo 1 = ID da VLAN da Porta
                            if current_layer.subtype == 1:
                                try:
                                    # Valor geralmente é 2 bytes
                                    val = current_layer.data
                                    if isinstance(val, bytes):
                                        vlan_id = int.from_bytes(val, byteorder='big')
                                        self.results["vlan"] = str(vlan_id)
                                except:
                                    pass
                        
                        # IEEE 802.3 (PoE) -> OUI 0x0012bb
                        elif current_layer.org_code == 0x0012bb:
                            # Subtipo 2 = Energia via MDI
                            if current_layer.subtype == 2:
                                self.results["poe_status"] = "PoE Supported (IEEE 802.3)"

                    # 6. Campos Nativos do Scapy (Backup)
                    if hasattr(current_layer, 'vlan_id'):
                         self.results["vlan"] = str(current_layer.vlan_id)
                    elif hasattr(current_layer, 'port_vlan_id'):
                         self.results["vlan"] = str(current_layer.port_vlan_id)
                    
                    if hasattr(current_layer, 'power_value'):
                        p_val = current_layer.power_value
                        self.results["poe_status"] = f"Advertised: {p_val * 0.1:.1f} W"

                    current_layer = current_layer.payload
                    if not current_layer or isinstance(current_layer, (bytes, str, scapy.packet.Raw)):
                        break
                
            except Exception as e:
                logging.error(f"Error parsing LLDP: {e}")
                
        # Análise CDP
        elif detected_protocol == "CDP":
            try:
                # 1. Extração Direta de Camada (Método Scapy Robusto)
                
                # Nome do Switch (Device ID)
                if pkt.haslayer(CDPMsgDeviceID):
                     self.results["switch_name"] = self._safe_decode(pkt[CDPMsgDeviceID].val)
                
                # IP do Switch (Endereço)
                if pkt.haslayer(CDPMsgAddr):
                    for addr_rec in pkt[CDPMsgAddr].addr:
                        if hasattr(addr_rec, "addr"):
                             self.results["switch_ip"] = str(addr_rec.addr)
                             break # Pegar apenas o primeiro
                
                # ID da Porta
                if pkt.haslayer(CDPMsgPortID):
                     if hasattr(pkt[CDPMsgPortID], "iface"):
                         self.results["port_id"] = self._safe_decode(pkt[CDPMsgPortID].iface)
                     else:
                         self.results["port_id"] = self._safe_decode(pkt[CDPMsgPortID].val)

                # VLAN
                if pkt.haslayer(CDPMsgNativeVLAN):
                     self.results["vlan"] = str(pkt[CDPMsgNativeVLAN].vlan)

                # PoE
                if pkt.haslayer(CDPMsgPower):
                     self.results["poe_status"] = f"Advertised: {pkt[CDPMsgPower].power} mW"

                # Fallback: Iterar TLVs genéricos
                current = pkt.getlayer(CDPv2_HDR) if pkt.haslayer(CDPv2_HDR) else pkt.getlayer(CDPMsg)
                
                while current:
                    if hasattr(current, 'type') and hasattr(current, 'val'):
                         # Tipo 1: Device ID
                         if current.type == 1 and self.results["switch_name"] in ["Not Found", "Unknown"]:
                             self.results["switch_name"] = self._safe_decode(current.val)
                         # Tipo 3: Port ID
                         elif current.type == 3 and self.results["port_id"] in ["Not Found", "Unknown"]:
                             self.results["port_id"] = self._safe_decode(current.val)
                         # Tipo 10: Native VLAN
                         elif current.type == 10 and self.results["vlan"] in ["Not Found", "Unknown"]:
                              if isinstance(current.val, bytes) and len(current.val) == 2:
                                   self.results["vlan"] = str(int.from_bytes(current.val, byteorder='big'))
                              else:
                                   self.results["vlan"] = self._safe_decode(current.val)

                    current = current.payload
                    if not current or isinstance(current, (bytes, str)) or isinstance(current,  scapy.packet.Raw):
                        break
                        
            except Exception as e:
                logging.error(f"Error parsing CDP: {e}")
                
        # --- Análise EDP (Extreme Discovery Protocol) ---
        elif detected_protocol == "EDP":
            try:
                self.results["switch_name"] = "Extreme Switch (EDP Detected)"
                self.results["protocol"] = "EDP"
            except Exception as e:
                logging.error(f"Error parsing EDP: {e}")

        # Análise STP (Spanning Tree)
        elif detected_protocol == "STP":
            try:
                stp = pkt[STP]
                
                if hasattr(stp, "bridgemac"):
                     self.results["switch_name"] = f"Switch MAC: {stp.bridgemac}"
                
                # Tentar extrair VLAN do Bridge Priority (PVST+ / Cisco)
                if hasattr(stp, "bridgeid"):
                    try:
                        prio_val = int(stp.bridgeid)
                        potential_vlan = prio_val & 0xFFF
                        if potential_vlan > 0 and potential_vlan < 4095:
                            self.results["vlan"] = f"{potential_vlan} (via STP)"
                        else:
                            self.results["vlan"] = "1 / Default (STP)"
                    except:
                        pass

                # Port ID (número da porta STP)
                if hasattr(stp, "portid") and stp.portid is not None:
                    raw_port = int(stp.portid)
                    port_num = raw_port & 0xFFF
                    self.results["port_id"] = f"Port {port_num} (STP Raw: {raw_port})"

                self.results["protocol"] = "STP (Fallback)"
                
                if self.results["poe_status"] in ["Scanning...", "Unknown", "Unknown/Not Detected"]:
                    self.results["poe_status"] = "N/A (Hardware Required)"

            except Exception as e:
                logging.error(f"Error parsing STP: {e}")

    def send_lldp_announcement(self, interface_obj, mac_address):
        """
        Envia pacotes LLDP para anunciar presença (Descoberta Ativa).
        Pode ajudar a 'acordar' o switch para enviar informações de volta.
        
        Args:
            interface_obj: Objeto da interface Scapy.
            mac_address (str): Endereço MAC de origem.
        """
        try:
            # LLDP 
            if hasattr(interface_obj, 'description'):
                port_id_str = interface_obj.description
            elif hasattr(interface_obj, 'name'):
                port_id_str = interface_obj.name
            else:
                port_id_str = str(interface_obj)

            # Contrução de pacote LLDP
            chassis_id = LLDPDUChassisID(subtype=4, id=mac_address) # 4 = MAC Address
            port_id = LLDPDUPortID(subtype=7, id=port_id_str) # 7 = Local
            ttl = LLDPDUTimeToLive(ttl=120)
            end = LLDPDUEndOfLLDPDU()
            
            pkt_lldp = Ether(dst="01:80:c2:00:00:0e", src=mac_address, type=0x88cc) / \
                  LLDPDU() / chassis_id / port_id / ttl / end
            
            sendp(pkt_lldp, iface=interface_obj, verbose=0)
            logging.info("Sent LLDP Announcement")
            
        except Exception as e:
            logging.warning(f"Failed to send announcements: {e}")

    def stop(self):
        """Sinaliza para parar o sniffer."""
        self.stop_sniffing = True
        logging.info("Discovery stop signal received.")

    def _stop_filter(self, pkt):
        """Callback interno para determinar se devemos parar o sniffer."""
        if self.stop_sniffing:
            return True
            
        # Parada antecipada se encontrar um protocolo robusto (LLDP, CDP)
        if self.found_lldp:
            return True
            
        if self.first_discovery_time is None:
            return False
            
        # Timeout relativo após primeira descoberta
        elapsed = time.time() - self.first_discovery_time
        if elapsed >= self.lldp_wait_after_first:
            return True
        return False

    def start_discovery(self, interface_name, mac_address=None, timeout=60):
        """
        Inicia o processo de descoberta (sniffing) na interface especificada.
        
        Args:
            interface_name (str): Nome da interface (ex: "Ethernet").
            mac_address (str, opcional): Endereço MAC da interface.
            timeout (int): Tempo máximo de espera em segundos.
            
        Returns:
            Dict: Dicionário com os resultados da descoberta.
        """
        self.results = {
            "switch_name": "Scanning...",
            "switch_ip": "Scanning...",
            "port_id": "Scanning...",
            "port_desc": "Scanning...",
            "vlan": "Scanning...",
            "poe_status": "Scanning...",
            "protocol": "Scanning...",
            "system_desc": "Scanning...",
            "capabilities": "Scanning..."
        }
        self.first_discovery_time = None
        self.found_lldp = False
        self.stop_sniffing = False
        
        logging.info(f"Starting discovery on {interface_name} (MAC: {mac_address}) for {timeout}s")
        
        target_iface = interface_name
        self.my_mac = mac_address.replace("-", ":").lower() if mac_address else None
        
        # Interface Robusta: Se fornecido o MAC, tenta resolver para a interface Scapy correspondente
        if mac_address:
            try:
                if hasattr(conf, 'ifaces'):
                    conf.ifaces.reload()
                mac_clean = mac_address.lower().replace("-", ":")
                found_iface = None
                for iface in conf.ifaces.data.values():
                    # Tentar corresponder pelo MAC
                    if hasattr(iface, 'mac') and iface.mac:
                        if iface.mac.lower() == mac_clean:
                            found_iface = iface
                            break
                    # Tentar corresponder pelo nome/descrição como fallback
                    if iface.name == interface_name or iface.description == interface_name:
                         found_iface = iface
                
                if found_iface:
                    target_iface = found_iface
                    logging.info(f"Resolved Scapy interface: {found_iface.name}")
                    
                    # Tentar enviar anúncio para acelerar descoberta
                    threading.Thread(target=self.send_lldp_announcement, args=(found_iface, mac_clean), daemon=True).start()
            except Exception as e:
                logging.error(f"Error resolving interface via Scapy: {e}")

        try:
            # Iniciar Sniffing
            sniff(
                iface=target_iface,
                prn=self._packet_callback,
                store=0,
                stop_filter=self._stop_filter,
                timeout=timeout
            )
        except Exception as e:
            logging.error(f"Sniffing error: {e}")
            self.results["protocol"] = "Error"
            self.results["system_desc"] = f"Sniff failed: {str(e)}"

        # Limpeza final dos resultados
        for k, v in self.results.items():
            if v == "Scanning...":
                self.results[k] = "Not Found"
                
        return self.results
