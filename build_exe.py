import PyInstaller.__main__
import os
import shutil

def run_build():
    """
    Script de automação para build do executável NetDiag Tool usando PyInstaller.
    Configurado para incluir binários do Flet e dependências do Scapy para execução offline.
    """
    
    # 1. Limpeza de builds anteriores
    print(">>> Limpando diretórios de build antigos...")
    if os.path.exists("build"):
        shutil.rmtree("build")
    if os.path.exists("dist"):
        shutil.rmtree("dist")

    print(">>> Iniciando processo de build do NetDiag Tool v3.0 (Flet Edition)...")

    # 2. Configuração de Caminhos
    base_dir = os.path.abspath(os.path.dirname(__file__))
    icon_dir = os.path.join(base_dir, "icon")
    icon_path = None

    # 3. Busca de Ícone
    if os.path.exists(icon_dir):
        print(f">>> Procurando ícones em: {icon_dir}")
        for file in os.listdir(icon_dir):
            if file.lower().endswith(".ico"):
                icon_path = os.path.join(icon_dir, file)
                print(f">>> Ícone encontrado e selecionado: {icon_path}")
                break
    else:
        print(f">>> Diretório de ícones não encontrado: {icon_dir}")

    # 4. Definição dos Argumentos do PyInstaller
    pyinstaller_args = [
        'main.py',                       # Script principal de entrada
        '--name=NetDiagTool',            # Nome do executável final
        '--onefile',                     # Empacotar tudo em um único arquivo .exe
        '--noconsole',                   # Não exibir janela de console (modo GUI)
        '--clean',                       # Limpar cache do PyInstaller
        '--noupx',                       # Desativar compressão UPX (Reduz alertas de antivírus)
        '--version-file=version_info.txt', # Adicionar metadados de versão (Ajuda na reputação)
        
        # Hooks para Imports Ocultos (Dependências dinâmicas)
        '--hidden-import=flet',
        '--hidden-import=flet_desktop',  # Essencial para execução offline do Flet
        '--hidden-import=scapy.layers.all',
        '--hidden-import=scapy.contrib.lldp',
        '--hidden-import=scapy.contrib.cdp',
        '--hidden-import=scapy.layers.l2',
        '--hidden-import=scapy.arch.windows',
        
        # Inclusão de Dados/Recursos
        '--add-data=src;src',            # Incluir código fonte (necessário para alguns imports relativos)
        '--add-data=icon;icon',          # Incluir pasta de ícones dentro do executável
        
        # Coleta de Binários e Dependências Complexas
        '--collect-all=flet',            # Coleta todos os arquivos do pacote Flet
        '--collect-all=flet_desktop',    # Coleta binários (flet.exe, dlls) para não precisar baixar da internet
    ]

    # Adicionar ícone se encontrado
    if icon_path:
        pyinstaller_args.append(f'--icon={icon_path}')
    else:
        print(">>> AVISO: Nenhum arquivo .ico foi encontrado. O executável terá o ícone padrão.")

    # 5. Execução do PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)

    # 6. Pós-Processamento (Opcional)
    # Copiar pasta de ícones para dist (para o usuário ter acesso externo se quiser customizar atalhos)
    if os.path.exists(icon_dir):
        dest_icon_dir = os.path.join("dist", "icon")
        # shutil.copytree(icon_dir, dest_icon_dir) # Comentado pois já está embutido no onefile
        # print(f"Pasta de ícones copiada para: {dest_icon_dir}")

    print("\n>>> Build Concluído com Sucesso!")
    print(f">>> Executável localizado em: {os.path.join(base_dir, 'dist', 'NetDiagTool.exe')}")

if __name__ == "__main__":
    run_build()
