import customtkinter as ctk
import subprocess
import platform
import threading
from getmac import get_mac_address
import socket

class NetworkToolApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Network Tool - Monitoramento de Rede")
        self.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Configuração de Grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar   
        
        self.sidebar_frame = ctk.CTkFrame(self, width=140, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Network Tool", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        self.sidebar_button_1 = ctk.CTkButton(self.sidebar_frame, text="Dashboard", command=self.sidebar_button_event)
        self.sidebar_button_1.grid(row=1, column=0, padx=20, pady=10)
        
        self.appearance_mode_label = ctk.CTkLabel(self.sidebar_frame, text="Tema:", anchor="w")
        self.appearance_mode_label.grid(row=5, column=0, padx=20, pady=(10, 0))
        self.appearance_mode_optionemenu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Light", "Dark", "System"],
                                                                       command=self.change_appearance_mode_event)
        self.appearance_mode_optionemenu.grid(row=6, column=0, padx=20, pady=(10, 10))
        self.appearance_mode_optionemenu.set("Dark")

        # janela principal
        self.main_frame = ctk.CTkFrame(self, corner_radius=10)
        self.main_frame.grid(row=0, column=1, padx=(20, 20), pady=(20, 20), sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Input Area
        self.input_label = ctk.CTkLabel(self.main_frame, text="Endereço IP ou Hostname:", font=ctk.CTkFont(size=14))
        self.input_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        
        self.entry = ctk.CTkEntry(self.main_frame, placeholder_text="Ex: 8.8.8.8 ou google.com", width=400)
        self.entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.ping_button = ctk.CTkButton(self.button_frame, text="Executar Ping", command=self.start_ping_thread)
        self.ping_button.pack(side="left", padx=(0, 10))
        
        self.mac_button = ctk.CTkButton(self.button_frame, text="Obter MAC", command=self.start_mac_thread)
        self.mac_button.pack(side="left", padx=10)

        self.info_button = ctk.CTkButton(self.button_frame, text="Info Básica", command=self.start_info_thread)
        self.info_button.pack(side="left", padx=10)

        # Area
        self.output_label = ctk.CTkLabel(self.main_frame, text="Resultado:", font=ctk.CTkFont(size=14))
        self.output_label.grid(row=3, column=0, padx=20, pady=(20, 5), sticky="w")

        self.output_textbox = ctk.CTkTextbox(self.main_frame, width=600, height=300)
        self.output_textbox.grid(row=4, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.output_textbox.rowconfigure(4, weight=1)

    def siderbar_button_event(self):
        print("Botão da Sidebar pressionado")

    def sidebar_button_event(self):
        return self.siderbar_button_event()
    def aparecencia_modo_evento_mudar(self, novo_modo: str):
        ctk.set_appearance_mode(novo_modo)

    def change_appearance_mode_event(self, novo_modo: str):
        return self.aparecencia_modo_evento_mudar(novo_modo)
    def log_mensagem(self, mensagem):
        try:
            self.output_textbox.insert("end", mensagem + "\n")
            self.output_textbox.see("end")
        except Exception:
            print(mensagem)
    
    def limpa_log(self):
        try:
            self.output_textbox.delete("1.0", "end")
        except Exception:
            pass
    
    def start_ping_thread(self):
        target = self.entry.get()
        if not target:
            self.log_mensagem("Por favor, insira um endereço IP ou hostname valido.")
            return
        self.log_mensagem(f"Iniciando ping para {target}...")
        threading.Thread(target=self.executa_ping, args=(target,), daemon=True).start()
    
    def executa_ping(self, target):
        param = '-n' if platform.system().lower()=='windows' else '-c'
        comando = ['ping', param, '4', target]
        try:
            resultado = subprocess.Popen(comando, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, )
            for linha in resultado.stdout:
                self.log_mensagem(linha.strip())
        except subprocess.TimeoutExpired:
            self.log_mensagem("O ping expirou. O host pode estar inacessível.")
        except Exception as e:
            self.log_mensagem(f"Erro ao executar ping: {str(e)}")

    def start_mac_thread(self):
        target = self.entry.get()
        if not target:
            self.log_mensagem("Por favor, insira um endereço IP ou hostname valido.")
            return
        self.log_mensagem(f"Obtendo endereço MAC para {target}...")
        threading.Thread(target=self.obter_mac, args=(target,), daemon=True).start()

    def obter_mac(self, target):
        try:
            #testando resolução de hostname caso necessário
            ip = socket.gethostbyname(target)
            mac = get_mac_address(ip=target)
            if mac:
                self.log_mensagem(f"Endereço IP de {target}: {ip}")
                self.log_mensagem(f"Endereço MAC de {target}: {mac}")
            else:
                self.log_mensagem(f"Não foi possível obter o endereço MAC para {target}.")
                self.log_mensagem("Certifique-se de que o dispositivo está na mesma rede local.")
        except Exception as e:
            self.log_mensagem(f"Erro ao obter endereço MAC: {str(e)}")

    def start_info_thread(self):
        target = self.entry.get()
        if not target:
            self.log_mensagem("Por favor, insira um endereço IP ou hostname valido.")
            return
        self.log_mensagem(f"Obtendo informações básicas para {target}...")
        threading.Thread(target=self.obter_info_basica, args=(target,), daemon=True).start()

    def obter_info_basica(self, target):
        try:
            ip = socket.gethostbyname(target)
            self.log_mensagem(f"Hostname: {target}")
            self.log_mensagem(f"Endereço IP: {ip}")
            try:
                hostname_resolved = socket.gethostbyaddr(ip)[0]
                self.log_mensagem(f"Hostname Resolved: {hostname_resolved}")
            except socket.herror:
                self.log_mensagem("Hostname Resolved: Não disponível")
        except Exception as e:
            self.log_mensagem(f"Erro ao obter informações básicas: {str(e)}")
    
if __name__ == "__main__":
    app = NetworkToolApp()
    print("Iniciando a aplicação...")
    app.mainloop()
        

        
