import flet as ft
import threading
import time
import sys
import os
import ctypes

# Adicionar o diretório raiz ao sys.path se executado diretamente
if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # src/gui -> src -> root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
    if project_root not in sys.path:
        sys.path.append(project_root)
    # Também adicionar o diretório src explicitamente se necessário, mas 'import src.xxx' requer o root
    sys.path.append(os.path.dirname(os.path.dirname(current_dir)))

from src.network.interface_info import InterfaceInfo
from src.network.connectivity import ConnectivityTester
from src.network.discovery import SwitchDiscovery

class NetDiagApp:
    """
    Classe principal da aplicação GUI baseada em Flet.
    Gerencia a interface do usuário e a orquestração dos testes de rede.
    """
    def __init__(self, page: ft.Page):
        self.page = page
        
        # Configurar AppUserModelID para o ícone da barra de tarefas (Windows)
        try:
            myappid = 'felipe.netdiagtool.v3.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        self.page.title = "NetDiag Tool v3.0"
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window_width = 800
        self.page.window_height = 800
        self.page.padding = 20
        self.page.vertical_alignment = ft.MainAxisAlignment.START

        # Configurar ícone da janela
        self.setup_window_icon()

        # Inicialização dos Módulos de Rede
        self.interface_info = InterfaceInfo()
        self.connectivity = ConnectivityTester()
        self.discovery = SwitchDiscovery()

        self.selected_interface = None
        self.is_running = False

        self.setup_ui()
        self.load_interfaces()

    def setup_window_icon(self):
        """Configura o ícone da janela do aplicativo, com suporte a execução congelada (PyInstaller)."""
        icon_name = "diagtool.ico"
        icon_path = None
        
        # 1. Verificar se estamos rodando como executável (PyInstaller)
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Caminho temporário do PyInstaller (_MEIPASS) - Embutido
            base_path = sys._MEIPASS
            potential_path = os.path.join(base_path, "icon", icon_name)
            if os.path.exists(potential_path):
                icon_path = potential_path
            else:
                # Tentar na pasta do executável (Externo)
                base_path = os.path.dirname(sys.executable)
                potential_path = os.path.join(base_path, "icon", icon_name)
                if os.path.exists(potential_path):
                    icon_path = potential_path
        else:
            # 2. Rodando como script (Desenvolvimento)
            # Estamos em src/gui/flet_app.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Subir 2 níveis: src/gui -> src -> root
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            potential_path = os.path.join(project_root, "icon", icon_name)
            if os.path.exists(potential_path):
                icon_path = potential_path
        
        if icon_path:
            self.page.window_icon = icon_path

    def setup_ui(self):
        """Constrói e organiza os elementos da interface gráfica."""
        # Header
        self.header = ft.Text("NetDiag Tool", size=30, weight=ft.FontWeight.BOLD, color="#42A5F5")
        
        # Interface Selection
        self.dd_interface = ft.Dropdown(
            label="Selecione a Interface de Rede",
            width=600,
            on_change=self.on_interface_change,
        )
        self.btn_refresh = ft.IconButton(icon="refresh", on_click=self.refresh_interfaces, tooltip="Atualizar Interfaces")
        
        # Main Action Button
        self.btn_start = ft.ElevatedButton(
            text="INICIAR DIAGNÓSTICO COMPLETO",
            icon="play_arrow",
            style=ft.ButtonStyle(
                color="#FFFFFF",
                bgcolor="#43A047",
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=20,
            ),
            width=600,
            on_click=self.start_diagnostic,
            disabled=True
        )

        # Progress Indicator
        self.progress_bar = ft.ProgressBar(width=600, color="#2196F3", visible=False)
        self.status_text = ft.Text("", italic=True)

        # Results Container (Cards)
        self.results_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        # Footer
        self.footer = ft.Column(
            [
                ft.Text("Desenvolvido por:", size=12, weight=ft.FontWeight.BOLD, color="#757575"),
                ft.Text("Felipe Ribeiro", size=12, color="#757575"),
                ft.Text("Ramal: 8001-2524", size=12, color="#757575"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=2
        )

        # Layout Final
        self.page.add(
            ft.Column(
                controls=[
                    ft.Row([self.header], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=20, color="transparent"),
                    ft.Row([self.dd_interface, self.btn_refresh], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([self.btn_start], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=10, color="transparent"),
                    ft.Row([self.progress_bar], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Row([self.status_text], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Divider(height=20, color="#424242"),
                    self.results_column,
                    ft.Divider(height=10, color="transparent"),
                    self.footer,
                    ft.Divider(height=5, color="transparent"),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                expand=True,
            )
        )

    def load_interfaces(self):
        """Carrega a lista de interfaces de rede disponíveis no dropdown."""
        interfaces = self.interface_info.get_interfaces()
        options = []
        default_val = None
        
        # Tentar priorizar Ethernet
        for name in interfaces:
            friendly_name = name
            display = name
            options.append(ft.dropdown.Option(key=name, text=display))
            if "ethernet" in friendly_name.lower() and not default_val:
                default_val = name

        self.dd_interface.options = options
        if options:
            self.dd_interface.value = default_val if default_val else options[0].key
            self.selected_interface = self.dd_interface.value
            self.btn_start.disabled = False
        else:
            self.btn_start.disabled = True
        
        self.page.update()

    def refresh_interfaces(self, e):
        """Callback para o botão de atualização de interfaces."""
        self.load_interfaces()

    def on_interface_change(self, e):
        """Callback para mudança de seleção no dropdown."""
        self.selected_interface = self.dd_interface.value
        self.btn_start.disabled = False
        self.page.update()

    def create_info_card(self, title, data, icon="info"):
        """Cria um componente visual de cartão para exibir resultados."""
        content_controls = []
        for label, value in data.items():
             content_controls.append(
                ft.Row([
                    ft.Text(f"{label}:", weight=ft.FontWeight.BOLD, width=150),
                    ft.Text(str(value), selectable=True, font_family="Consolas")
                ])
            )
            
        return ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.ListTile(
                            leading=ft.Icon(icon),
                            title=ft.Text(title, weight=ft.FontWeight.BOLD),
                        ),
                        ft.Container(
                            content=ft.Column(content_controls, spacing=5),
                            padding=ft.padding.only(left=20, bottom=20, right=20)
                        )
                    ]
                ),
                width=600,
                padding=10,
            )
        )

    def start_diagnostic(self, e):
        """Inicia o processo de diagnóstico em uma thread separada."""
        if self.is_running: return
        self.is_running = True
        self.btn_start.disabled = True
        self.btn_start.text = "RODANDO DIAGNÓSTICO..."
        self.btn_start.style.bgcolor = "#616161"
        self.dd_interface.disabled = True
        self.btn_refresh.disabled = True
        self.results_column.controls.clear()
        self.progress_bar.visible = True
        self.page.update()

        threading.Thread(target=self.run_tests_logic, daemon=True).start()

    def run_tests_logic(self) -> None:
        """
        Lógica principal de execução dos testes de rede (Executado em Thread Separada).
        
        Fluxo:
        1. Coleta informações da interface selecionada.
        2. Realiza testes de conectividade (Ping Gateway e Internet).
        3. Realiza descoberta de camada 2 (LLDP/CDP) via Scapy.
        """
        try:
            # 1. Informações da Interface
            self.update_status("Obtendo informações da interface...")
            if_info = self.interface_info.get_interface_details(self.selected_interface)
            self.add_result_card("Informações da Interface", {
                "Nome": if_info.get("name", "--"),
                "IP Address": if_info.get("ip", "--"),
                "MAC Address": if_info.get("mac", "--"),
                "Subnet Mask": if_info.get("mask", "--"),
                "Status": "Ativo" if if_info.get("ip") and if_info.get("ip") != "N/A" else "Sem IP"
            }, "network_check")

            # 1.1 Informações Wi-Fi (se disponível)
            wifi_info = self.interface_info.get_wifi_info()
            if wifi_info.get("ssid") and wifi_info.get("ssid") != "N/A":
                self.add_result_card("Informações Wi-Fi", {
                    "SSID": wifi_info.get("ssid", "--"),
                    "BSSID (MAC AP)": wifi_info.get("bssid", "--"),
                    "Autenticação": wifi_info.get("auth", "--"),
                    "Sinal": wifi_info.get("signal", "--"),
                }, "wifi")

            # 2. Conectividade (Ping)
            self.update_status("Verificando conectividade (Ping)...")
            
            gateway = if_info.get("gateway")
            gw_res = {"status": "N/A", "latency": "--"}
            if gateway and gateway != "N/A":
                 gw_res = self.connectivity.ping_host(gateway)

            gateway_mac = self.interface_info.get_gateway_mac(gateway)
            
            inet_res = self.connectivity.ping_host("8.8.8.8")
            
            self.add_result_card("Conectividade", {
                "Gateway Ping": gw_res.get("status", "N/A"),
                "Internet (8.8.8.8)": inet_res.get("status", "Falha"),
                "Latência Gateway": gw_res.get("latency", "--"),
                "Latência Internet": inet_res.get("latency", "--"),
                "MAC do Gateway (Roteador/AP)": gateway_mac or "N/A",
            }, "public")

            # 3. Descoberta LLDP/CDP (Pode demorar)
            self.update_status("Escutando pacotes LLDP/CDP (Isso pode levar até 60s)...")
            
            # Iniciar descoberta
            mac = if_info.get("mac")
            disc_res = self.discovery.start_discovery(self.selected_interface, mac_address=mac)
            
            self.add_result_card("Detalhes do Switch (LLDP/CDP)", {
                "Switch Name": disc_res.get("switch_name", "--"),
                "Switch IP": disc_res.get("switch_ip", "--"),
                "Port ID": disc_res.get("port_id", "--"),
                "VLAN": disc_res.get("vlan", "--"),
                "Protocolo": disc_res.get("protocol", "--"),
            }, "hub")

        except Exception as e:
            self.update_status(f"Erro Crítico durante os testes: {str(e)}")
        finally:
            self.is_running = False
            self.update_status("Diagnóstico Concluído!")
            self.finish_ui_update()

    def update_status(self, text: str) -> None:
        """
        Atualiza o texto de status na interface gráfica.

        Args:
            text (str): A mensagem a ser exibida para o usuário.
        """
        self.status_text.value = text
        self.page.update()

    def add_result_card(self, title: str, data: dict, icon: str) -> None:
        """
        Adiciona um cartão de resultado à lista de resultados na interface.

        Args:
            title (str): O título do cartão.
            data (dict): Dicionário contendo os pares chave-valor a serem exibidos.
            icon (str): O nome do ícone (Material Icon) a ser exibido.
        """
        card = self.create_info_card(title, data, icon)
        self.results_column.controls.append(card)
        self.page.update()

    def finish_ui_update(self) -> None:
        """
        Restaura o estado da interface do usuário após a conclusão dos testes.
        Reabilita botões e oculta a barra de progresso.
        """
        self.progress_bar.visible = False
        self.btn_start.disabled = False
        self.btn_start.text = "INICIAR DIAGNÓSTICO COMPLETO"
        self.btn_start.style.bgcolor = "#43A047"
        self.dd_interface.disabled = False
        self.btn_refresh.disabled = False
        self.page.update()

def main(page: ft.Page):
    app = NetDiagApp(page)

if __name__ == "__main__":
    ft.app(target=main)
