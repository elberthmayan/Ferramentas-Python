import os
import shutil
import datetime
import threading
import hashlib
import time
import platform
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk

# --- CONFIGURAÇÃO DE EXTENSÕES ---
EXTENSOES_FOTO = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.heic', '.tif', '.tiff'}
EXTENSOES_VIDEO = {'.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.3gp', '.m4v', '.mts'}
EXTENSOES_TODAS = EXTENSOES_FOTO.union(EXTENSOES_VIDEO)

# --- CORES E ESTILO (TEMA PROFISSIONAL DARK) ---
COR_FUNDO = "#121212"       # Preto Profundo
COR_PAINEL = "#1E1E1E"      # Cinza Carbono
COR_DESTAQUE = "#007ACC"    # Azul Profissional (Microsoft Style)
COR_SUCESSO = "#28A745"     # Verde Sóbrio
COR_ALERTA = "#DC3545"      # Vermelho Alerta
COR_INFO = "#17A2B8"        # Ciano Informativo
COR_ROXO = "#6F42C1"        # Roxo para a nova função
COR_TEXTO = "#E0E0E0"       # Branco Gelo

FONTE_LOGO = ("Impact", 50)
FONTE_TITULO = ("Segoe UI", 24, "bold")
FONTE_MENU = ("Segoe UI", 12, "bold")
FONTE_DESC = ("Segoe UI", 9)

# --- FUNÇÕES UTILITÁRIAS ---

def obter_data_arquivo(caminho_arquivo):
    """Tenta descobrir o ano do arquivo (EXIF para fotos ou Data de Modificação)."""
    ext = os.path.splitext(caminho_arquivo)[1].lower()
    
    # Tenta EXIF apenas se for foto
    if ext in EXTENSOES_FOTO:
        try:
            img = Image.open(caminho_arquivo)
            exif_data = img._getexif()
            # 36867 é a tag para DateTimeOriginal
            if exif_data and 36867 in exif_data:
                data_str = exif_data[36867]
                ano = data_str.split(':')[0]
                if int(ano) > 1900: # Validação básica de ano
                    return ano
        except Exception:
            pass
    
    # Fallback: Data de modificação do arquivo (funciona p/ vídeos e fotos sem EXIF)
    try:
        timestamp = os.path.getmtime(caminho_arquivo)
        data_arquivo = datetime.datetime.fromtimestamp(timestamp)
        return str(data_arquivo.year)
    except:
        return "Indeterminado"

def calcular_hash_arquivo(caminho, block_size=65536):
    """Gera hash MD5 para comparar conteúdo."""
    hasher = hashlib.md5()
    try:
        with open(caminho, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
    except:
        return None

def gerar_html_galeria(diretorio_base):
    """Gera um arquivo HTML para visualização elegante das fotos."""
    titulo_galeria = "Galeria Multimídia"
    arquivo_saida = "Galeria_Arquivos.html"
    
    albuns = {}
    contador_imgs = 0
    
    for root, dirs, files in os.walk(diretorio_base):
        # Ignora pastas de sistema/lixo
        if "_LIXEIRA" in root or "_SUSPEITOS" in root or "_REVISAO_RAPIDA" in root: continue
        
        path_root = Path(root)
        imagens_na_pasta = []
        
        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext in EXTENSOES_FOTO: # Galeria foca em fotos para visualização web simples
                caminho_completo = path_root / file
                try:
                    caminho_relativo = os.path.relpath(caminho_completo, diretorio_base)
                    caminho_web = caminho_relativo.replace('\\', '/')
                    imagens_na_pasta.append(caminho_web)
                    contador_imgs += 1
                except: pass
        
        if imagens_na_pasta:
            nome_pasta = str(path_root.relative_to(diretorio_base)).replace('\\', ' > ')
            if nome_pasta == ".": nome_pasta = "Raiz"
            albuns[nome_pasta] = sorted(imagens_na_pasta)

    if contador_imgs == 0: return False

    # HTML Template Minimalista
    html = f"""<!DOCTYPE html>
    <html lang="pt-br">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{titulo_galeria}</title>
        <style>
            body {{ background: #1a1a1a; color: #eee; font-family: sans-serif; margin: 0; padding: 20px; }}
            h1 {{ text-align: center; font-weight: 300; }}
            h2 {{ color: #007acc; border-bottom: 1px solid #333; padding-bottom: 10px; margin-top: 40px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }}
            .card {{ aspect-ratio: 1; overflow: hidden; border-radius: 4px; background: #222; cursor: pointer; transition: 0.2s; }}
            .card:hover {{ transform: scale(1.02); box-shadow: 0 5px 15px rgba(0,0,0,0.5); }}
            img {{ width: 100%; height: 100%; object-fit: cover; display: block; }}
        </style>
    </head>
    <body>
        <h1>📂 {titulo_galeria}</h1>
        <p style="text-align:center; color:#888">{contador_imgs} fotos organizadas</p>
    """
    
    for album, fotos in albuns.items():
        html += f"<h2>{album}</h2><div class='grid'>"
        for foto in fotos:
            html += f"<div class='card' onclick=\"window.open('{foto}', '_blank')\"><img src='{foto}' loading='lazy'></div>"
        html += "</div>"
    
    html += "</body></html>"
    
    try:
        with open(os.path.join(diretorio_base, arquivo_saida), "w", encoding="utf-8") as f:
            f.write(html)
        return True
    except:
        return False

# --- CLASSE PRINCIPAL ---

class PendriveManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PENDRIVE MANAGER v5.0 - Smart Organizer")
        self.root.geometry("1200x850")
        self.root.configure(bg=COR_FUNDO)

        # Configuração de Estilo
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TProgressbar", thickness=8, troughcolor=COR_PAINEL, background=COR_DESTAQUE)

        # Estado Global
        self.pasta_alvo = ""
        self.total_analisado = 0
        self.lista_arquivos_global = []
        self.fila_limpeza = [] # Nova lista para limpeza
        
        # Variáveis de Operação
        self.processando = False
        self.total_movidos = 0
        self.total_erros = 0
        
        self.tela_boas_vindas()

    def limpar_tela(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    # =========================================================================
    # TELA 1: HOME
    # =========================================================================
    def tela_boas_vindas(self):
        self.limpar_tela()
        
        frame = tk.Frame(self.root, bg=COR_FUNDO)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="PENDRIVE", font=FONTE_LOGO, fg="white", bg=COR_FUNDO).pack()
        tk.Label(frame, text="MANAGER", font=FONTE_LOGO, fg=COR_DESTAQUE, bg=COR_FUNDO).pack(pady=(0, 10))

        tk.Label(frame, text="ORGANIZADOR INTELIGENTE", font=("Segoe UI", 12, "bold"), fg="#888", bg=COR_FUNDO).pack(pady=(0, 50))

        btn = tk.Button(frame, text="SELECIONAR DISPOSITIVO / PASTA", 
                        bg=COR_DESTAQUE, fg="white", font=FONTE_MENU, relief="flat",
                        padx=40, pady=20, cursor="hand2",
                        command=self.selecionar_pasta_inicial)
        btn.pack()

        tk.Label(self.root, text="v5.0 Enterprise • Video & Photo Support", fg="#333", bg=COR_FUNDO, font=("Consolas", 8)).pack(side=tk.BOTTOM, pady=10)

    def selecionar_pasta_inicial(self):
        pasta = filedialog.askdirectory()
        if pasta:
            self.pasta_alvo = pasta
            self.tela_loading_inicial()

    # =========================================================================
    # TELA 2: SCANNING
    # =========================================================================
    def tela_loading_inicial(self):
        self.limpar_tela()
        
        frame = tk.Frame(self.root, bg=COR_FUNDO)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(frame, text="ANALISANDO MÍDIA...", font=FONTE_TITULO, fg=COR_TEXTO, bg=COR_FUNDO).pack(pady=20)
        
        self.lbl_status_load = tk.Label(frame, text="Lendo estrutura de diretórios...", font=("Consolas", 11), fg=COR_DESTAQUE, bg=COR_FUNDO)
        self.lbl_status_load.pack(pady=10)

        self.progress_load = ttk.Progressbar(frame, orient="horizontal", length=500, mode="indeterminate", style="TProgressbar")
        self.progress_load.pack(pady=20)
        self.progress_load.start(10)

        threading.Thread(target=self.thread_scan_inicial).start()

    def thread_scan_inicial(self):
        arquivos = []
        try:
            for root, dirs, files in os.walk(self.pasta_alvo):
                for file in files:
                    # Agora verifica TODAS as extensões (Foto + Video)
                    if os.path.splitext(file)[1].lower() in EXTENSOES_TODAS:
                        arquivos.append(os.path.join(root, file))
                        if len(arquivos) % 100 == 0:
                            self.root.after(0, lambda t=len(arquivos): self.lbl_status_load.config(text=f"Indexando: {t} arquivos encontrados"))
        except: pass
        
        self.total_analisado = len(arquivos)
        time.sleep(0.8) # Pequeno delay para UX
        self.root.after(0, self.tela_dashboard)

    # =========================================================================
    # TELA 3: DASHBOARD
    # =========================================================================
    def tela_dashboard(self):
        self.limpar_tela()
        
        # Header
        header = tk.Frame(self.root, bg=COR_PAINEL, pady=20, padx=40)
        header.pack(fill=tk.X)
        
        tk.Label(header, text="PAINEL DE CONTROLE", font=("Segoe UI", 14, "bold"), fg=COR_DESTAQUE, bg=COR_PAINEL).pack(side=tk.LEFT)
        path_short = self.pasta_alvo if len(self.pasta_alvo) < 50 else "..." + self.pasta_alvo[-50:]
        tk.Label(header, text=path_short, font=("Consolas", 9), fg="#666", bg=COR_PAINEL).pack(side=tk.RIGHT)

        # Container Principal
        container = tk.Frame(self.root, bg=COR_FUNDO)
        container.pack(expand=True, fill=tk.BOTH, padx=60, pady=40)

        # Stats
        stats = tk.Frame(container, bg=COR_FUNDO)
        stats.pack(fill=tk.X, pady=(0, 40))
        
        tk.Label(stats, text=str(self.total_analisado), font=("Segoe UI", 48, "bold"), fg="white", bg=COR_FUNDO).pack(side=tk.LEFT)
        tk.Label(stats, text="MÍDIAS\nIDENTIFICADAS", font=("Segoe UI", 10, "bold"), fg="#555", bg=COR_FUNDO, justify=tk.LEFT).pack(side=tk.LEFT, padx=20)
        
        tk.Button(stats, text="TROCAR PASTA", bg="#333", fg="#ccc", relief="flat", font=("Segoe UI", 8), command=self.tela_boas_vindas).pack(side=tk.RIGHT)

        # GRID DE FUNÇÕES
        grid = tk.Frame(container, bg=COR_FUNDO)
        grid.pack(fill=tk.BOTH, expand=True)

        # Linha 1
        self.criar_card(grid, 0, 0, "ORGANIZAR PROFUNDO", "Pastas por Ano > Fotos/Videos", "📂", COR_SUCESSO, self.iniciar_organizacao)
        self.criar_card(grid, 0, 1, "FAXINA INTELIGENTE", "Identificar Bom Dia, Prints e Receitas", "🧹", COR_ROXO, self.iniciar_limpeza_lixo)
        self.criar_card(grid, 0, 2, "REMOVER DUPLICATAS", "Compara conteúdo e libera espaço", "♻️", "#E83E8C", self.iniciar_duplicatas)
        
        # Linha 2
        self.criar_card(grid, 1, 0, "GERENCIAR LIXEIRA", "Recuperar itens ou esvaziar tudo", "🗑️", COR_ALERTA, self.gerenciar_lixeira)
        self.criar_card(grid, 1, 1, "VERIFICAR CORROMPIDOS", "Detecta imagens quebradas", "🛡️", "#FFC107", self.iniciar_corrupcao)
        self.criar_card(grid, 1, 2, "CRIAR GALERIA VISUAL", "Gera um site offline para ver as fotos", "🌐", COR_INFO, self.iniciar_galeria)
        
        # Footer Log
        self.lbl_log = tk.Label(self.root, text="Aguardando ação do usuário...", bg=COR_FUNDO, fg="#444", font=("Consolas", 9))
        self.lbl_log.pack(side=tk.BOTTOM, pady=15)

    def criar_card(self, parent, row, col, titulo, desc, icone, cor, comando):
        frame = tk.Frame(parent, bg=COR_PAINEL, padx=20, pady=20)
        tk.Frame(frame, bg=cor, width=4).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        
        content = tk.Frame(frame, bg=COR_PAINEL)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        tk.Label(content, text=icone, font=("Segoe UI", 20), bg=COR_PAINEL, fg="white").pack(anchor="w")
        tk.Label(content, text=titulo, font=("Segoe UI", 11, "bold"), bg=COR_PAINEL, fg="white").pack(anchor="w", pady=(5,0))
        tk.Label(content, text=desc, font=("Segoe UI", 8), bg=COR_PAINEL, fg="#888", wraplength=180, justify="left").pack(anchor="w", pady=(5, 15))
        
        btn = tk.Button(content, text="INICIAR", bg=cor, fg="white", relief="flat", font=("Segoe UI", 8, "bold"), width=12, command=comando)
        btn.pack(anchor="w")
        
        frame.grid(row=row, column=col, sticky="nsew", padx=10, pady=10)
        parent.grid_columnconfigure(col, weight=1)

    # =========================================================================
    # FUNÇÕES LÓGICAS
    # =========================================================================

    def abrir_arquivo_externo(self, caminho):
        """Abre o arquivo no visualizador padrão do sistema (Windows/Linux/Mac)."""
        try:
            if platform.system() == 'Windows':
                os.startfile(caminho)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.call(('open', caminho))
            else:  # Linux
                subprocess.call(('xdg-open', caminho))
        except Exception as e:
            messagebox.showerror("Erro ao Abrir", f"Não foi possível abrir o arquivo:\n{e}")

    def mover_seguro(self, origem, destino_custom=None):
        if destino_custom:
            pasta_lixo = destino_custom
        else:
            pasta_lixo = os.path.join(self.pasta_alvo, "_LIXEIRA_SEGURA")
            
        if not os.path.exists(pasta_lixo): os.makedirs(pasta_lixo)
        
        nome = os.path.basename(origem)
        destino = os.path.join(pasta_lixo, nome)
        
        c = 1
        while os.path.exists(destino):
            n, e = os.path.splitext(nome)
            destino = os.path.join(pasta_lixo, f"{n}_copy{c}{e}")
            c += 1
            
        shutil.move(origem, destino)

    # --- 1. ORGANIZAR ---
    def iniciar_organizacao(self):
        aviso = "Isso irá organizar seus arquivos na estrutura:\n\n📁 ANO\n  └── 📁 Fotos\n  └── 📁 Videos\n\nDeseja continuar?"
        if not messagebox.askyesno("Organização Profunda", aviso): return
        self.mostrar_progresso("Organizando arquivos e vídeos...")
        threading.Thread(target=self.thread_organizacao).start()

    def thread_organizacao(self):
        movidos = 0
        erros = 0
        ignorar = ["_LIXEIRA_SEGURA", "_SUSPEITOS", "_REVISAO_RAPIDA"]
        
        arquivos = []
        # Coleta inicial
        for root, d, files in os.walk(self.pasta_alvo):
            if any(x in root for x in ignorar): continue
            for f in files:
                if os.path.splitext(f)[1].lower() in EXTENSOES_TODAS:
                    arquivos.append(os.path.join(root, f))
        
        total = len(arquivos)
        for i, path in enumerate(arquivos):
            self.update_progresso(i, total, f"Organizando: {os.path.basename(path)}")
            try:
                ano = obter_data_arquivo(path)
                if ano == "Indeterminado": continue
                
                # Definir Subpasta (Fotos ou Videos)
                ext = os.path.splitext(path)[1].lower()
                subpasta_tipo = "Outros"
                
                if ext in EXTENSOES_FOTO:
                    subpasta_tipo = "Fotos"
                elif ext in EXTENSOES_VIDEO:
                    subpasta_tipo = "Videos"
                
                # Cria a estrutura: PASTA_ALVO / ANO / TIPO
                dest_dir = os.path.join(self.pasta_alvo, ano, subpasta_tipo)
                
                # Se arquivo já está no lugar certo, pula
                pasta_atual = os.path.dirname(path)
                if os.path.abspath(pasta_atual) == os.path.abspath(dest_dir):
                    continue

                if not os.path.exists(dest_dir): os.makedirs(dest_dir)
                
                nome = os.path.basename(path)
                dest = os.path.join(dest_dir, nome)
                
                # Renomear se já existe para não sobrescrever
                c = 1
                while os.path.exists(dest):
                    n, e = os.path.splitext(nome)
                    dest = os.path.join(dest_dir, f"{n}_{c}{e}")
                    c += 1
                
                shutil.move(path, dest)
                movidos += 1
            except: erros += 1
            
        # Limpar pastas vazias
        for r, d, f in os.walk(self.pasta_alvo, topdown=False):
            for name in d:
                try: os.rmdir(os.path.join(r, name))
                except: pass
                
        self.fim_processo(f"Organização Completa!\n\n{movidos} arquivos movidos para pastas de Anos e Categorias.")

    # --- 2. NOVO: FAXINA INTELIGENTE (Detectar Lixo) ---
    def iniciar_limpeza_lixo(self):
        info = ("MODO FAXINA INTELIGENTE\n\n"
                "Vou procurar apenas arquivos com nomes explícitos (WhatsApp, Print, Screenshot, etc).\n\n"
                "Ao final, você poderá MOVER TUDO para uma pasta separada para revisar em lote.\n"
                "Deseja iniciar?")
        if not messagebox.askyesno("Faxina", info): return
        
        self.mostrar_progresso("Buscando arquivos 'suspeitos'...")
        threading.Thread(target=self.thread_scan_lixo).start()

    def thread_scan_lixo(self):
        self.fila_limpeza = []
        termos_suspeitos = ["whatsapp", "screenshot", "screen", "captura", "print", "telegram", "facebook", "instagram", "download", "received"]
        
        arquivos = []
        for r, d, f in os.walk(self.pasta_alvo):
            if "_LIXEIRA" in r: continue
            
            # Se a PASTA tem nome suspeito
            pasta_lower = r.lower()
            eh_pasta_suspeita = any(t in pasta_lower for t in termos_suspeitos)
            
            for file in f:
                nome_lower = file.lower()
                ext = os.path.splitext(file)[1].lower()
                
                if ext in EXTENSOES_FOTO:
                    # REMOVIDO: Critério de tamanho sozinho (era o que pegava suas fotos pessoais)
                    
                    # Critério 1: Nome do arquivo (mais seguro)
                    tem_nome_lixo = any(t in nome_lower for t in termos_suspeitos) or "wa0" in nome_lower
                    
                    # Só adiciona se o NOME for explicitamente lixo ou se estiver numa pasta CLARAMENTE de lixo (ex: WhatsApp Images)
                    # Para evitar falsos positivos, vamos focar mais no nome do arquivo nesta versão segura.
                    
                    if tem_nome_lixo:
                        arquivos.append(os.path.join(r, file))

        self.fila_limpeza = arquivos
        self.root.after(0, self.abrir_revisor_lixo)

    def abrir_revisor_lixo(self):
        self.tela_dashboard()
        if not self.fila_limpeza:
            messagebox.showinfo("Limpo", "Não encontrei arquivos com nomes suspeitos (WhatsApp/Print).")
            return
            
        self.idx_lixo = 0
        self.win = tk.Toplevel(self.root)
        self.win.title(f"Revisor de Faxina ({len(self.fila_limpeza)} itens)")
        self.win.geometry("900x750")
        self.win.configure(bg=COR_PAINEL)
        
        # Cabeçalho
        topo = tk.Frame(self.win, bg=COR_PAINEL, pady=10)
        topo.pack(fill=tk.X)
        tk.Label(topo, text="REVISÃO RÁPIDA: BOM DIA, PRINTS E MEMES", fg=COR_ROXO, bg=COR_PAINEL, font=("Segoe UI", 16, "bold")).pack()
        tk.Label(topo, text="Use os botões abaixo ou MOVA TUDO para uma pasta", fg="#aaa", bg=COR_PAINEL).pack()

        # Área da Imagem
        centro = tk.Frame(self.win, bg="black")
        centro.pack(expand=True, fill=tk.BOTH, padx=20, pady=10)
        
        self.lbl_lixo_img = tk.Label(centro, bg="black")
        self.lbl_lixo_img.pack(expand=True, fill=tk.BOTH)
        
        self.lbl_lixo_nome = tk.Label(self.win, text="...", fg="white", bg=COR_PAINEL, font=("Consolas", 10))
        self.lbl_lixo_nome.pack(pady=5)

        # Botões Gigantes
        botoes = tk.Frame(self.win, bg=COR_PAINEL, pady=20)
        botoes.pack(fill=tk.X)
        
        btn_lixo = tk.Button(botoes, text="🗑️ É LIXO (DELETAR)", bg=COR_ALERTA, fg="white", font=("Segoe UI", 11, "bold"), 
                             width=20, height=2, command=self.acao_jogar_lixo)
        btn_lixo.pack(side=tk.LEFT, padx=20, expand=True)
        
        # NOVO BOTÃO: MOVER TUDO
        btn_todos = tk.Button(botoes, text="📁 MOVER TUDO P/ PASTA\n(Agilizar Processo)", bg=COR_INFO, fg="white", font=("Segoe UI", 11, "bold"), 
                             width=25, height=2, command=self.acao_mover_tudo)
        btn_todos.pack(side=tk.LEFT, padx=20, expand=True)

        btn_manter = tk.Button(botoes, text="✅ É IMPORTANTE (MANTER)", bg=COR_SUCESSO, fg="white", font=("Segoe UI", 11, "bold"), 
                               width=25, height=2, command=self.acao_manter)
        btn_manter.pack(side=tk.RIGHT, padx=20, expand=True)
        
        # Atalhos de teclado
        self.win.bind("<Left>", lambda e: self.acao_jogar_lixo())  # Seta Esquerda = Lixo
        self.win.bind("<Right>", lambda e: self.acao_manter())     # Seta Direita = Manter

        self.carregar_img_lixo()

    def carregar_img_lixo(self):
        if self.idx_lixo >= len(self.fila_limpeza):
            self.win.destroy()
            messagebox.showinfo("Fim da Faxina", "Revisão concluída com sucesso!")
            return
            
        path = self.fila_limpeza[self.idx_lixo]
        self.lbl_lixo_nome.config(text=f"({self.idx_lixo + 1}/{len(self.fila_limpeza)}) {os.path.basename(path)}")
        
        try:
            img = Image.open(path)
            # Redimensionar para caber na tela mantendo proporção
            img.thumbnail((800, 500))
            self.tk_lixo = ImageTk.PhotoImage(img)
            self.lbl_lixo_img.config(image=self.tk_lixo)
        except:
            self.lbl_lixo_img.config(image="", text="Erro ao carregar imagem", fg="white")

    def acao_jogar_lixo(self):
        path = self.fila_limpeza[self.idx_lixo]
        try:
            self.mover_seguro(path) # Move para pasta segura padrao
        except: pass
        self.idx_lixo += 1
        self.carregar_img_lixo()

    def acao_manter(self):
        # Não faz nada, só pula
        self.idx_lixo += 1
        self.carregar_img_lixo()

    def acao_mover_tudo(self):
        msg = ("Deseja mover TODOS os arquivos restantes desta lista para a pasta '_REVISAO_RAPIDA'?\n\n"
               "Isso permite que você abra a pasta no Windows e delete os arquivos visualmente muito mais rápido.")
        if not messagebox.askyesno("Confirmar", msg): return
        
        pasta_destino = os.path.join(self.pasta_alvo, "_REVISAO_RAPIDA")
        if not os.path.exists(pasta_destino): os.makedirs(pasta_destino)
        
        restantes = self.fila_limpeza[self.idx_lixo:]
        count = 0
        
        self.win.destroy()
        self.mostrar_progresso("Movendo arquivos para revisão em lote...")
        
        for item in restantes:
            try:
                self.mover_seguro(item, destino_custom=pasta_destino)
                count += 1
            except: pass
            
        self.fim_processo(f"{count} arquivos movidos para '_REVISAO_RAPIDA'.\nAbra a pasta para deletar o que não quiser.")
        os.startfile(pasta_destino)

    # --- 3. CORROMPIDOS ---
    def iniciar_corrupcao(self):
        self.mostrar_progresso("Verificando integridade das imagens...")
        threading.Thread(target=self.thread_corrupcao).start()

    def thread_corrupcao(self):
        self.suspeitos = []
        arquivos = []
        for r, d, f in os.walk(self.pasta_alvo):
            if "_LIXEIRA" in r: continue
            for file in f:
                # Verifica APENAS fotos, pois PIL não valida vídeos
                if os.path.splitext(file)[1].lower() in EXTENSOES_FOTO:
                    arquivos.append(os.path.join(r, file))
        
        total = len(arquivos)
        for i, p in enumerate(arquivos):
            self.update_progresso(i, total, f"Testando: {os.path.basename(p)}")
            try:
                img = Image.open(p)
                img.verify() # Verifica estrutura do arquivo
            except Exception as e:
                self.suspeitos.append((p, str(e)))
        
        self.root.after(0, self.abrir_audit_corrupt)

    def abrir_audit_corrupt(self):
        self.tela_dashboard()
        if not self.suspeitos:
            messagebox.showinfo("Tudo Certo", "Nenhuma imagem corrompida encontrada.")
            return
            
        # Janela Audit
        self.idx_audit = 0
        self.win = tk.Toplevel(self.root)
        self.win.title("Auditoria de Integridade")
        self.win.geometry("800x600")
        self.win.configure(bg=COR_PAINEL)
        
        tk.Label(self.win, text="ARQUIVO CORROMPIDO DETECTADO", fg=COR_ALERTA, bg=COR_PAINEL, font=FONTE_MENU).pack(pady=10)
        self.lbl_nome = tk.Label(self.win, text="", fg="white", bg=COR_PAINEL)
        self.lbl_nome.pack()
        self.lbl_prev = tk.Label(self.win, bg="black")
        self.lbl_prev.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)
        
        frame = tk.Frame(self.win, bg=COR_PAINEL)
        frame.pack(fill=tk.X, pady=20)
        tk.Button(frame, text="MOVER P/ LIXEIRA", bg=COR_ALERTA, fg="white", command=self.lixo_corrupt).pack(side=tk.LEFT, padx=50)
        tk.Button(frame, text="MANTER ARQUIVO", bg=COR_SUCESSO, fg="white", command=self.prox_corrupt).pack(side=tk.RIGHT, padx=50)
        
        self.load_corrupt()

    def load_corrupt(self):
        if self.idx_audit >= len(self.suspeitos):
            self.win.destroy()
            return
        
        p, err = self.suspeitos[self.idx_audit]
        self.lbl_nome.config(text=f"{os.path.basename(p)}\nErro: {err}")
        try:
            # Tenta abrir novamente para ver se exibe algo, mesmo com erro
            img = Image.open(p)
            img.thumbnail((400, 400))
            self.tk_img = ImageTk.PhotoImage(img)
            self.lbl_prev.config(image=self.tk_img, text="")
        except:
            self.lbl_prev.config(image="", text="VISUALIZAÇÃO INDISPONÍVEL", fg="#555")

    def lixo_corrupt(self):
        try: self.mover_seguro(self.suspeitos[self.idx_audit][0])
        except: pass
        self.prox_corrupt()

    def prox_corrupt(self):
        self.idx_audit += 1
        self.load_corrupt()

    # --- 4. DUPLICATAS ---
    def iniciar_duplicatas(self):
        self.mostrar_progresso("Comparando assinaturas digitais (Hash)...")
        threading.Thread(target=self.thread_dup).start()

    def thread_dup(self):
        # 1. Size
        by_size = {}
        arquivos = []
        for r, d, f in os.walk(self.pasta_alvo):
            if "_LIXEIRA" in r: continue
            for file in f:
                if os.path.splitext(file)[1].lower() in EXTENSOES_TODAS:
                    path = os.path.join(r, file)
                    arquivos.append(path)
                    try:
                        sz = os.path.getsize(path)
                        if sz not in by_size: by_size[sz] = []
                        by_size[sz].append(path)
                    except: pass
        
        # 2. Hash
        candidatos = [l for l in by_size.values() if len(l) > 1]
        hashes = {}
        total = sum(len(l) for l in candidatos)
        done = 0
        
        for group in candidatos:
            for p in group:
                done += 1
                self.update_progresso(done, total, "Verificando conteúdo...")
                h = calcular_hash_arquivo(p)
                if h:
                    if h not in hashes: hashes[h] = []
                    hashes[h].append(p)
                    
        self.dups = [l for l in hashes.values() if len(l) > 1]
        self.root.after(0, self.abrir_audit_dup)

    def abrir_audit_dup(self):
        self.tela_dashboard()
        if not self.dups:
            messagebox.showinfo("Limpo", "Sem duplicatas encontradas.")
            return
            
        self.idx_dup = 0
        self.win = tk.Toplevel(self.root)
        self.win.title("Removedor de Duplicatas")
        self.win.geometry("900x600")
        self.win.configure(bg=COR_PAINEL)
        
        # UI Comparacao
        comp = tk.Frame(self.win, bg=COR_PAINEL)
        comp.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Esq
        f1 = tk.Frame(comp, bg=COR_SUCESSO, padx=2, pady=2)
        f1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tk.Label(f1, text="ORIGINAL (Manter)", bg=COR_SUCESSO, fg="white").pack(fill=tk.X)
        self.lbl_orig = tk.Label(f1, bg="black", cursor="hand2")
        self.lbl_orig.pack(fill=tk.BOTH, expand=True)
        self.lbl_orig.bind("<Button-1>", lambda e: self.abrir_arquivo_externo(self.path_orig.cget("text")))
        self.path_orig = tk.Label(f1, text="...", bg="#222", fg="#aaa", wraplength=300)
        self.path_orig.pack(fill=tk.X)
        
        # Dir
        f2 = tk.Frame(comp, bg=COR_ALERTA, padx=2, pady=2)
        f2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        tk.Label(f2, text="CÓPIA (Lixeira)", bg=COR_ALERTA, fg="white").pack(fill=tk.X)
        self.lbl_copy = tk.Label(f2, bg="black", cursor="hand2")
        self.lbl_copy.pack(fill=tk.BOTH, expand=True)
        self.lbl_copy.bind("<Button-1>", lambda e: self.abrir_arquivo_externo(self.path_copy.cget("text")))
        self.path_copy = tk.Label(f2, text="...", bg="#222", fg="#aaa", wraplength=300)
        self.path_copy.pack(fill=tk.X)
        
        btns = tk.Frame(self.win, bg=COR_PAINEL)
        btns.pack(fill=tk.X, pady=10)
        tk.Button(btns, text="MOVER CÓPIAS P/ LIXEIRA", bg=COR_ALERTA, fg="white", command=self.lixo_dup).pack(side=tk.LEFT, padx=50)
        tk.Button(btns, text="PULAR", bg="#555", fg="white", command=self.prox_dup).pack(side=tk.RIGHT, padx=50)
        
        self.load_dup()

    def load_dup(self):
        if self.idx_dup >= len(self.dups):
            self.win.destroy()
            return
            
        g = self.dups[self.idx_dup]
        self.path_orig.config(text=g[0])
        self.path_copy.config(text=g[1])
        
        # Tenta mostrar preview se for imagem, se for video avisa
        try:
            if os.path.splitext(g[0])[1].lower() in EXTENSOES_FOTO:
                img = Image.open(g[0])
                img.thumbnail((350, 350))
                self.tk_o = ImageTk.PhotoImage(img)
                self.lbl_orig.config(image=self.tk_o, text="", cursor="hand2")
            else:
                self.lbl_orig.config(image="", text="🎥 VÍDEO\n(CLIQUE PARA ASSISTIR)", fg="white", font=("Segoe UI", 12, "bold"), cursor="hand2")
        except: pass
        
        try:
            if os.path.splitext(g[1])[1].lower() in EXTENSOES_FOTO:
                img = Image.open(g[1])
                img.thumbnail((350, 350))
                self.tk_c = ImageTk.PhotoImage(img)
                self.lbl_copy.config(image=self.tk_c, text="", cursor="hand2")
            else:
                self.lbl_copy.config(image="", text="🎥 VÍDEO\n(CLIQUE PARA ASSISTIR)", fg="white", font=("Segoe UI", 12, "bold"), cursor="hand2")
        except: pass

    def lixo_dup(self):
        for p in self.dups[self.idx_dup][1:]:
            try: self.mover_seguro(p)
            except: pass
        self.prox_dup()
        
    def prox_dup(self):
        self.idx_dup += 1
        self.load_dup()

    # --- 5. LIXEIRA ---
    def gerenciar_lixeira(self):
        lixo = os.path.join(self.pasta_alvo, "_LIXEIRA_SEGURA")
        if not os.path.exists(lixo):
            messagebox.showinfo("Lixeira", "Lixeira vazia.")
            return
        os.startfile(lixo)

    # --- 6. GALERIA ---
    def iniciar_galeria(self):
        aviso = ("⚠️ ATENÇÃO: RECURSO PARA COMPUTADOR\n\n"
                 "Esta função cria um arquivo 'Galeria_Arquivos.html' para visualizar fotos.\n"
                 "Por limitações de navegadores, vídeos podem não aparecer na pré-visualização estática.\n\n"
                 "Deseja criar a galeria?")
        
        if not messagebox.askyesno("Confirmar Criação de Galeria", aviso):
            return

        self.mostrar_progresso("Gerando Galeria HTML...")
        threading.Thread(target=self.thread_galeria).start()
        
    def thread_galeria(self):
        sucesso = gerar_html_galeria(self.pasta_alvo)
        time.sleep(1) # Visual
        self.root.after(0, lambda: self.fim_processo("Galeria criada com sucesso!\nAbra o arquivo 'Galeria_Arquivos.html' na pasta."))

    # --- UX ---
    def mostrar_progresso(self, txt):
        self.limpar_tela()
        f = tk.Frame(self.root, bg=COR_FUNDO)
        f.place(relx=0.5, rely=0.5, anchor="center")
        tk.Label(f, text="PROCESSANDO", font=FONTE_TITULO, fg="white", bg=COR_FUNDO).pack(pady=20)
        self.lbl_prog = tk.Label(f, text=txt, fg=COR_DESTAQUE, bg=COR_FUNDO, font=("Consolas", 11))
        self.lbl_prog.pack()
        self.prog = ttk.Progressbar(f, length=400, mode='determinate')
        self.prog.pack(pady=20)

    def update_progresso(self, atual, total, txt):
        self.root.after(0, lambda: self._update_ui(atual, total, txt))

    def _update_ui(self, atual, total, txt):
        pct = (atual/total)*100 if total > 0 else 0
        self.prog['value'] = pct
        self.lbl_prog.config(text=f"{txt} ({int(pct)}%)")

    def fim_processo(self, msg):
        self.tela_dashboard()
        messagebox.showinfo("Concluído", msg)

if __name__ == "__main__":
    root = tk.Tk()
    app = PendriveManagerApp(root)
    root.mainloop()