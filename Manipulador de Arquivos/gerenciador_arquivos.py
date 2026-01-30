import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import threading
import sys
import subprocess
import importlib

# --- VERIFICAÇÃO INICIAL DE BIBLIOTECAS (Apenas para evitar erros de import no topo) ---
# O controle real agora é feito dinamicamente dentro do App
try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pypdf
    HAS_PYPDF = True
except ImportError:
    HAS_PYPDF = False

try:
    from moviepy.editor import VideoFileClip, AudioFileClip
    HAS_MOVIEPY = True
except ImportError:
    HAS_MOVIEPY = False

class ModernButton(tk.Frame):
    """Um botão personalizado que parece um cartão (Card)"""
    def __init__(self, parent, title, subtitle, icon, command, colors):
        super().__init__(parent, bg=colors["card"], cursor="hand2")
        self.command = command
        self.colors = colors
        
        # Layout do Botão/Card
        self.lbl_icon = tk.Label(self, text=icon, font=("Segoe UI", 32), bg=colors["card"], fg=colors["accent"])
        self.lbl_icon.pack(pady=(20, 10))
        
        self.lbl_title = tk.Label(self, text=title, font=("Segoe UI", 14, "bold"), bg=colors["card"], fg=colors["fg"])
        self.lbl_title.pack(pady=(0, 5))
        
        self.lbl_sub = tk.Label(self, text=subtitle, font=("Segoe UI", 9), bg=colors["card"], fg=colors["subtext"], wraplength=180)
        self.lbl_sub.pack(pady=(0, 20), padx=10)

        # Eventos de Hover (Mouse em cima)
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        
        # Propagar clique para os elementos internos
        for widget in [self.lbl_icon, self.lbl_title, self.lbl_sub]:
            widget.bind("<Enter>", self.on_enter)
            widget.bind("<Leave>", self.on_leave)
            widget.bind("<Button-1>", self.on_click)

    def on_enter(self, event):
        self.configure(bg=self.colors["card_hover"])
        for widget in self.winfo_children():
            widget.configure(bg=self.colors["card_hover"])

    def on_leave(self, event):
        self.configure(bg=self.colors["card"])
        for widget in self.winfo_children():
            widget.configure(bg=self.colors["card"])

    def on_click(self, event):
        if self.command:
            self.command()

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Canivete Suíço - Dashboard")
        self.geometry("900x650")
        
        # --- PALETA DE CORES (Tema Dark Moderno) ---
        self.colors = {
            "bg": "#121212",           # Fundo Janela (Preto fosco)
            "card": "#1E1E1E",         # Fundo dos Cards
            "card_hover": "#2D2D2D",   # Card quando passa o mouse
            "fg": "#E0E0E0",           # Texto Principal
            "subtext": "#A0A0A0",      # Texto Secundário
            "accent": "#BB86FC",       # Roxo Neon (Destaque)
            "success": "#03DAC6",      # Verde Água
            "error": "#CF6679",        # Vermelho Suave
            "input_bg": "#2C2C2C",     # Fundo de inputs
            "warning": "#FFB74D",      # Laranja
            "console": "#000000"       # Fundo Console Instalação
        }
        
        self.configure(bg=self.colors["bg"])
        
        # Estilos globais do TTK
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self.style.configure("TFrame", background=self.colors["bg"])
        self.style.configure("TLabel", background=self.colors["bg"], foreground=self.colors["fg"], font=("Segoe UI", 11))
        self.style.configure("Header.TLabel", font=("Segoe UI", 24, "bold"), foreground=self.colors["fg"])
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", 12), foreground=self.colors["subtext"])
        
        self.style.configure("Accent.TButton", background=self.colors["accent"], foreground="#000000", font=("Segoe UI", 10, "bold"), borderwidth=0)
        self.style.map("Accent.TButton", background=[("active", "#9965f4")])
        
        self.style.configure("TCombobox", fieldbackground=self.colors["input_bg"], background=self.colors["card"], foreground=self.colors["fg"], borderwidth=0)
        
        self.style.configure("Horizontal.TProgressbar", background=self.colors["accent"], troughcolor=self.colors["card"], bordercolor=self.colors["bg"])

        # Container Principal (Onde as telas vão alternar)
        self.container = tk.Frame(self, bg=self.colors["bg"])
        self.container.pack(fill="both", expand=True)

        # Inicia no Dashboard
        self.show_dashboard()

    # ================= GERENCIADOR DE DEPENDÊNCIAS =================
    def check_dependency(self, pip_name, import_name):
        """
        Verifica se 'import_name' pode ser importado. 
        Se não, oferece instalar 'pip_name'.
        Retorna True se estiver tudo ok, False se falhou/cancelou.
        """
        try:
            importlib.import_module(import_name)
            return True
        except ImportError:
            # Pergunta ao usuário
            resp = messagebox.askyesno(
                "Dependência Faltando",
                f"A ferramenta requer a biblioteca '{pip_name}'.\n\nDeseja que eu instale agora automaticamente?"
            )
            if resp:
                return self.install_dependency_ui(pip_name, import_name)
            return False

    def install_dependency_ui(self, pip_name, import_name):
        """Abre uma janela de instalação e roda o pip"""
        
        # Janela Modal
        install_win = tk.Toplevel(self)
        install_win.title(f"Instalando {pip_name}...")
        install_win.geometry("400x150")
        install_win.configure(bg=self.colors["card"])
        install_win.resizable(False, False)
        install_win.transient(self)
        install_win.grab_set() # Bloqueia a janela principal
        
        # UI da Instalação
        lbl_info = tk.Label(install_win, text=f"Baixando e instalando {pip_name}...", 
                          bg=self.colors["card"], fg=self.colors["fg"], font=("Segoe UI", 10))
        lbl_info.pack(pady=20)
        
        pbar = ttk.Progressbar(install_win, mode="indeterminate", length=300)
        pbar.pack(pady=10)
        pbar.start(15)

        # Variável para capturar resultado da thread
        result = {"success": False}

        def run_pip():
            try:
                # Chama pip install via subprocess
                subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])
                
                # Tenta importar dinamicamente para garantir que o Python reconheça
                importlib.invalidate_caches()
                importlib.import_module(import_name)
                
                # Atualiza flags globais para compatibilidade com código antigo
                if import_name == "PIL": global HAS_PIL; HAS_PIL = True
                if import_name == "pypdf": global HAS_PYPDF; HAS_PYPDF = True
                if import_name == "moviepy": 
                    global HAS_MOVIEPY; HAS_MOVIEPY = True
                    # Moviepy precisa de imports específicos às vezes, forçamos aqui
                    try:
                        from moviepy.editor import VideoFileClip
                    except:
                        pass

                result["success"] = True
            except Exception as e:
                print(e)
                result["success"] = False
            
            # Fecha janela na thread principal
            self.after(0, install_win.destroy)

        # Roda em thread para não travar a UI
        t = threading.Thread(target=run_pip)
        t.start()
        
        # Aguarda a janela fechar (o código principal pausa aqui por causa do wait_window)
        self.wait_window(install_win)
        
        if result["success"]:
            messagebox.showinfo("Sucesso", f"{pip_name} instalado! A ferramenta está pronta.")
            return True
        else:
            messagebox.showerror("Erro", f"Falha ao instalar {pip_name}.\nVerifique sua conexão.")
            return False

    # ================= LÓGICA DE UI E NAVEGAÇÃO =================

    def clear_container(self):
        """Limpa a tela atual para mostrar a próxima"""
        for widget in self.container.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_container()
        
        # Cabeçalho
        header_frame = tk.Frame(self.container, bg=self.colors["bg"])
        header_frame.pack(pady=(40, 30))
        
        tk.Label(header_frame, text="Painel de Controle", font=("Segoe UI", 28, "bold"), bg=self.colors["bg"], fg=self.colors["fg"]).pack()
        tk.Label(header_frame, text="Escolha uma ferramenta", font=("Segoe UI", 12), bg=self.colors["bg"], fg=self.colors["subtext"]).pack(pady=5)

        # Grid de Cartões
        grid_frame = tk.Frame(self.container, bg=self.colors["bg"])
        grid_frame.pack(expand=True)

        tools = [
            ("Conversor Multimídia", "Converta Vídeos (WebM -> MP4) e Imagens em um só lugar.", "🔄", self.show_converter_selection),
            ("Juntar PDFs", "Combine múltiplos documentos\nem um único arquivo PDF.", "📄", self.show_pdf_tool)
        ]

        for i, (title, sub, icon, cmd) in enumerate(tools):
            card = ModernButton(grid_frame, title, sub, icon, cmd, self.colors)
            card.grid(row=0, column=i, padx=20, pady=20, ipadx=20, ipady=15)

    def show_converter_selection(self):
        self.clear_container()
        self.create_tool_header("O que deseja converter?", back_cmd=self.show_dashboard)

        grid_frame = tk.Frame(self.container, bg=self.colors["bg"])
        grid_frame.pack(expand=True)

        options = [
            ("Imagens", "JPG, PNG, WebP, BMP.\nVisualização incluída.", "🖼️", self.show_image_tool),
            ("Vídeos", "WebM para MP4, AVI,\nMP3 e muito mais.", "🎬", self.show_video_tool)
        ]

        for i, (title, sub, icon, cmd) in enumerate(options):
            card = ModernButton(grid_frame, title, sub, icon, cmd, self.colors)
            card.grid(row=0, column=i, padx=20, pady=20, ipadx=10, ipady=10)

    def create_tool_header(self, title, back_cmd=None):
        if back_cmd is None:
            back_cmd = self.show_dashboard

        top_bar = tk.Frame(self.container, bg=self.colors["bg"])
        top_bar.pack(fill="x", padx=30, pady=20)
        
        btn_back = tk.Button(top_bar, text="⬅ Voltar", command=back_cmd, 
                           bg=self.colors["card"], fg=self.colors["fg"], 
                           font=("Segoe UI", 10, "bold"), bd=0, activebackground=self.colors["card_hover"], activeforeground=self.colors["fg"], cursor="hand2")
        btn_back.pack(side="left")
        
        tk.Label(top_bar, text=title, font=("Segoe UI", 18, "bold"), bg=self.colors["bg"], fg=self.colors["accent"]).pack(side="right")
        
        ttk.Separator(self.container, orient="horizontal").pack(fill="x", padx=30, pady=(0, 20))

    # ================= FERRAMENTA 1: IMAGENS =================
    def show_image_tool(self):
        self.clear_container()
        self.create_tool_header("Conversor de Imagens", back_cmd=self.show_converter_selection)
        
        main_content = tk.Frame(self.container, bg=self.colors["bg"])
        main_content.pack(fill="both", expand=True, padx=40, pady=10)

        # Lado Esquerdo: Preview
        left_panel = tk.Frame(main_content, bg=self.colors["card"], padx=20, pady=20)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 20))
        
        tk.Label(left_panel, text="Pré-visualização", font=("Segoe UI", 12, "bold"), bg=self.colors["card"], fg=self.colors["fg"]).pack(pady=(0,10))
        
        self.preview_canvas = tk.Canvas(left_panel, bg="#101010", height=300, highlightthickness=0)
        self.preview_canvas.pack(fill="both", expand=True)
        self.preview_canvas.create_text(150, 150, text="Nenhuma imagem", fill="gray", font=("Segoe UI", 10), tags="placeholder")

        # Lado Direito: Controles
        right_panel = tk.Frame(main_content, bg=self.colors["bg"])
        right_panel.pack(side="right", fill="y", ipadx=20)
        
        # 1. Input
        tk.Label(right_panel, text="1. Escolha o Arquivo", bg=self.colors["bg"], fg=self.colors["subtext"]).pack(anchor="w")
        ttk.Button(right_panel, text="📂 Selecionar Imagem", command=self.selecionar_imagem_preview, style="Accent.TButton").pack(fill="x", pady=(5, 10))
        self.lbl_img_path = tk.Label(right_panel, text="...", bg=self.colors["bg"], fg="gray", font=("Segoe UI", 8))
        self.lbl_img_path.pack(anchor="w", pady=(0, 20))

        # 2. Formato
        tk.Label(right_panel, text="2. Formato de Saída", bg=self.colors["bg"], fg=self.colors["subtext"]).pack(anchor="w")
        self.combo_img_fmt = ttk.Combobox(right_panel, values=["PNG", "JPG", "WEBP", "BMP", "ICO", "PDF"], state="readonly")
        self.combo_img_fmt.set("PNG")
        self.combo_img_fmt.pack(fill="x", pady=(5, 20))

        # 3. Ação
        self.btn_convert_img = ttk.Button(right_panel, text="🚀 Converter Agora", command=self.converter_imagem_acao, style="Accent.TButton")
        self.btn_convert_img.pack(fill="x", pady=(10, 5))
        
        self.status_img = tk.Label(right_panel, text="", bg=self.colors["bg"], fg=self.colors["fg"])
        self.status_img.pack(pady=10)
        self.prog_img = ttk.Progressbar(right_panel, orient="horizontal", mode="indeterminate")

        self.img_caminho_atual = None

    def selecionar_imagem_preview(self):
        # VERIFICAÇÃO DE DEPENDÊNCIA
        if not self.check_dependency("Pillow", "PIL"):
            return

        # Como a instalação é dinâmica, precisamos reimportar dentro do escopo local
        # caso tenha acabado de ser instalada
        from PIL import Image, ImageTk

        caminho = filedialog.askopenfilename(filetypes=[("Imagens", "*.jpg;*.jpeg;*.png;*.bmp;*.webp")])
        if not caminho: return

        self.img_caminho_atual = caminho
        self.lbl_img_path.config(text=os.path.basename(caminho))
        
        try:
            img = Image.open(caminho)
            base_width = 300
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            if h_size > 300:
                h_size = 300
                w_percent = (h_size / float(img.size[1]))
                base_width = int((float(img.size[0]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
            self.preview_img_tk = ImageTk.PhotoImage(img)
            self.preview_canvas.delete("all")
            cw, ch = int(self.preview_canvas.winfo_width() or 300), int(self.preview_canvas.winfo_height() or 300)
            self.preview_canvas.create_image(cw//2, ch//2, image=self.preview_img_tk, anchor="center")
        except Exception as e:
            self.status_img.config(text=f"Erro no preview: {str(e)}", fg=self.colors["error"])

    def converter_imagem_acao(self):
        if not self.img_caminho_atual: return
        # Dependencia já checada na seleção, mas por segurança:
        if not self.check_dependency("Pillow", "PIL"): return

        fmt = self.combo_img_fmt.get().lower()
        pasta = os.path.dirname(self.img_caminho_atual)
        nome = os.path.splitext(os.path.basename(self.img_caminho_atual))[0]
        saida = os.path.join(pasta, f"{nome}_convertido.{fmt}")

        self.run_task(self.status_img, self.prog_img, self.btn_convert_img, lambda: self._convert_img_logic(saida, fmt))

    def _convert_img_logic(self, saida, fmt):
        from PIL import Image # Import local
        img = Image.open(self.img_caminho_atual)
        if fmt in ["jpg", "jpeg", "bmp"] and img.mode in ("RGBA", "P"):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == 'RGBA':
                bg.paste(img, mask=img.split()[3])
                img = bg
            else:
                img = img.convert("RGB")
        img.save(saida)
        return f"Salvo como {fmt.upper()}!"

    # ================= FERRAMENTA 2: PDFS =================
    def show_pdf_tool(self):
        self.clear_container()
        self.create_tool_header("Unificador de PDFs", back_cmd=self.show_dashboard)
        
        content = tk.Frame(self.container, bg=self.colors["bg"])
        content.pack(expand=True)
        
        card = tk.Frame(content, bg=self.colors["card"], padx=40, pady=40)
        card.pack()
        
        tk.Label(card, text="Selecione múltiplos arquivos PDF", font=("Segoe UI", 14), bg=self.colors["card"], fg=self.colors["fg"]).pack(pady=10)
        tk.Label(card, text="Eles serão unidos na ordem de seleção.", bg=self.colors["card"], fg=self.colors["subtext"]).pack(pady=(0, 20))
        
        self.btn_pdf = ttk.Button(card, text="📂 Selecionar e Unir", command=self.juntar_pdfs, style="Accent.TButton")
        self.btn_pdf.pack(ipadx=20, ipady=10)
        
        self.status_pdf = tk.Label(card, text="", bg=self.colors["card"], fg=self.colors["fg"])
        self.status_pdf.pack(pady=20)
        self.prog_pdf = ttk.Progressbar(card, orient="horizontal", mode="indeterminate")

    def juntar_pdfs(self):
        # VERIFICAÇÃO DE DEPENDÊNCIA
        if not self.check_dependency("pypdf", "pypdf"):
            return
        
        import pypdf # Import local seguro

        arquivos = filedialog.askopenfilenames(filetypes=[("PDF", "*.pdf")])
        if len(arquivos) < 2:
            self.status_pdf.config(text="Selecione ao menos 2 arquivos.", fg="orange")
            return
            
        saida = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not saida: return

        def logic():
            merger = pypdf.PdfMerger()
            for pdf in arquivos:
                merger.append(pdf)
            merger.write(saida)
            merger.close()
            return "PDFs unidos com sucesso!"

        self.run_task(self.status_pdf, self.prog_pdf, self.btn_pdf, logic)

    # ================= FERRAMENTA 3: VÍDEO/ÁUDIO =================
    def show_video_tool(self):
        self.clear_container()
        self.create_tool_header("Conversor de Vídeo", back_cmd=self.show_converter_selection)
        
        content = tk.Frame(self.container, bg=self.colors["bg"])
        content.pack(fill="both", expand=True, padx=40)
        
        tk.Label(content, text="Converta arquivos de internet (WebM) e outros formatos.", bg=self.colors["bg"], fg=self.colors["subtext"]).pack(pady=(0, 20))

        center_panel = tk.Frame(content, bg=self.colors["bg"])
        center_panel.pack()

        tk.Label(center_panel, text="Ação Desejada:", bg=self.colors["bg"], fg=self.colors["fg"]).pack(anchor="w", pady=(0,5))
        self.combo_video_mode = ttk.Combobox(center_panel, 
            values=["WebM/MKV para MP4 (Padrão)", "Converter para AVI", "Extrair Áudio (MP3)", "Extrair Áudio (WAV)", "Converter para GIF"], 
            state="readonly", width=35)
        self.combo_video_mode.set("WebM/MKV para MP4 (Padrão)")
        self.combo_video_mode.pack(pady=(0, 20))

        self.btn_vid = ttk.Button(center_panel, text="🎬 Selecionar Arquivo", command=self.converter_video, style="Accent.TButton")
        self.btn_vid.pack(ipadx=10, ipady=5)
        
        self.status_vid = tk.Label(center_panel, text="", bg=self.colors["bg"], fg=self.colors["fg"])
        self.status_vid.pack(pady=20)
        self.prog_vid = ttk.Progressbar(center_panel, orient="horizontal", mode="indeterminate")

    def converter_video(self):
        # VERIFICAÇÃO DE DEPENDÊNCIA
        if not self.check_dependency("moviepy", "moviepy"):
            return
        
        from moviepy.editor import VideoFileClip # Import local

        mode = self.combo_video_mode.get()
        caminho = filedialog.askopenfilename(filetypes=[("Vídeo/Áudio", "*.mp4;*.mkv;*.avi;*.webm;*.flv;*.ogg;*.mov")])
        if not caminho: return

        target_ext = ".mp4"
        if "AVI" in mode: target_ext = ".avi"
        elif "MP3" in mode: target_ext = ".mp3"
        elif "WAV" in mode: target_ext = ".wav"
        elif "GIF" in mode: target_ext = ".gif"
        
        saida = filedialog.asksaveasfilename(defaultextension=target_ext, filetypes=[(f"Arquivo {target_ext}", f"*{target_ext}")])
        if not saida: return

        def logic():
            clip = VideoFileClip(caminho)
            try:
                if "Áudio" in mode:
                    if not clip.audio: return "Erro: Vídeo sem áudio!"
                    clip.audio.write_audiofile(saida, logger=None)
                elif "GIF" in mode:
                    clip.write_gif(saida, logger=None)
                else:
                    codec = "libx264" if target_ext == ".mp4" else "rawvideo"
                    clip.write_videofile(saida, codec=codec, audio_codec="aac", logger=None)
            finally:
                clip.close()
            return "Processo concluído!"

        self.run_task(self.status_vid, self.prog_vid, self.btn_vid, logic)

    # ================= UTILITÁRIOS GERAIS =================
    def run_task(self, label, progress, button, logic_func):
        """Gerencia threads e UI para tarefas longas"""
        label.config(text="Processando...", fg=self.colors["accent"])
        progress.pack(fill="x", pady=10)
        progress.start(10)
        if button: button.config(state="disabled")

        def thread_target():
            try:
                msg = logic_func()
                self.after(0, lambda: self.finish_task(label, progress, button, msg, self.colors["success"]))
            except Exception as e:
                self.after(0, lambda: self.finish_task(label, progress, button, f"Erro: {str(e)}", self.colors["error"]))

        threading.Thread(target=thread_target).start()

    def finish_task(self, label, progress, button, text, color):
        progress.stop()
        progress.pack_forget()
        label.config(text=text, fg=color)
        if button: button.config(state="normal")

if __name__ == "__main__":
    app = App()
    app.mainloop()