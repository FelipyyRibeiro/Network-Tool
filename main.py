import sys
import os
import ctypes
import traceback
from datetime import datetime

# Configurar variáveis de ambiente para evitar problemas com Proxy em redes corporativas
# Isso é crucial para o Flet funcionar localmente sem tentar passar pelo proxy
os.environ["NO_PROXY"] = "localhost,127.0.0.1"

# Adiciona o diretório src ao caminho de busca 
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

import flet as ft
from src.gui.flet_app import main as flet_main

def is_admin() -> bool:
    """
    Verifica se a aplicação está rodando com privilégios de administrador.
    
    Returns:
        bool: True se for admin, False caso contrário.
    """
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def show_error_message(title: str, message: str) -> None:
    """
    Exibe uma caixa de mensagem de erro nativa do Windows.
    Útil para notificar o usuário quando a GUI não pode ser iniciada.
    
    Args:
        title (str): Título da janela de erro.
        message (str): Mensagem detalhada do erro.
    """
    try:
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x10) # 0x10 = MB_ICONERROR
    except Exception:
        pass

def log_error(e: Exception) -> None:
    """
    Registra erros fatais em um arquivo de log local.
    
    Args:
        e (Exception): A exceção capturada.
    """
    try:
        # Tenta salvar no diretório do executável ou no diretório atual
        base_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.getcwd()
        log_file = os.path.join(base_dir, "error_log.txt")
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.now()}] Erro fatal:\n")
            f.write(str(e))
            f.write("\n")
            traceback.print_exc(file=f)
    except Exception:
        pass

if __name__ == "__main__":
    # Verificação de Admin
    if not is_admin():
        # Apenas logamos ou ignoramos, pois a GUI vai abrir de qualquer jeito
        # O usuário já foi avisado na documentação/termos
        pass
    
    print("Iniciando Network Tool v3.0 (Flet Edition)...")
    
    try:
        # Tenta iniciar a aplicação Flet
        # O Flet precisa conectar em localhost:porta. Se houver proxy, pode falhar.
        # A variável NO_PROXY acima deve mitigar isso.
        ft.app(target=flet_main)
        
    except Exception as e:
        # Captura erros fatais (como falha de conexão do Flet ou Scapy)
        err_msg = f"Ocorreu um erro fatal ao iniciar a aplicação:\n{str(e)}\n\nConsulte o arquivo error_log.txt para mais detalhes."
        print(err_msg)
        
        # Logar em arquivo
        log_error(e)
        
        # Mostrar popup visual (importante para --noconsole)
        show_error_message("Erro Fatal - NetDiag Tool", err_msg)
        
        # Não usar input() aqui pois trava em --noconsole
        sys.exit(1)
