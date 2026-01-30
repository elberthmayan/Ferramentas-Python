import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yt_dlp
import threading
import os
import sys

class YoutubeDownloaderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Downloader Pro")
        self.root.geometry("700x580") # Aumentei um pouco a altura para caber o seletor
        self.root.resizable(False, False)
        
        # --- CONFIGURAÇÃO DE CORES (TEMA DARK/PREMIUM) ---
        self.cores = {
            'bg': '#1e1e1e',         # Fundo Cinza Escuro
            'fg': '#ffffff',         # Texto Branco
            'input_bg': '#333333',   # Fundo do Input
            'btn_bg': '#cc0000',     # Vermelho YouTube
            'btn_fg': '#ffffff',     # Texto Botão
            'btn_hover': '#ff3333',  # Vermelho mais claro
            'accent': '#00a8ff'      # Azul Cyan para detalhes
        }
        
        self.root.configure(bg=self.cores['bg'])

        # --- ESTILOS TTK ---
        style = ttk.Style()
        style.theme_use('clam')
        
        # Estilo da Barra de Progresso
        style.configure("TProgressbar", thickness=10, troughcolor=self.cores['input_bg'], background=self.cores['accent'])

        # --- INTERFACE ---
        
        # 1. Cabeçalho
        frame_header = tk.Frame(root, bg=self.cores['bg'])
        frame_header.pack(pady=30)
        
        lbl_titulo = tk.Label(frame_header, text="YOUTUBE DOWNLOADER", font=("Segoe UI", 24, "bold"), fg=self.cores['fg'], bg=self.cores['bg'])
        lbl_titulo.pack()
        
        lbl_subtitulo = tk.Label(frame_header, text="Baixe vídeos e músicas em alta qualidade", font=("Segoe UI", 10), fg="gray", bg=self.cores['bg'])
        lbl_subtitulo.pack()

        # 2. Área de Input
        frame_input = tk.Frame(root, bg=self.cores['bg'])
        frame_input.pack(pady=10)

        lbl_link = tk.Label(frame_input, text="Cole o link do vídeo:", font=("Segoe UI", 11), fg=self.cores['fg'], bg=self.cores['bg'])
        lbl_link.pack(anchor="w", padx=5)
        
        # Entry customizado (sem borda, fundo escuro)
        self.entry_link = tk.Entry(frame_input, width=60, font=("Segoe UI", 12), bg=self.cores['input_bg'], fg="white", insertbackground="white", relief="flat", bd=10)
        self.entry_link.pack(pady=5)

        # 3. Seletor de Diretório (NOVO)
        frame_dir = tk.Frame(root, bg=self.cores['bg'])
        frame_dir.pack(pady=5, padx=85, fill='x') # Alinhado visualmente com o input acima

        lbl_dir_title = tk.Label(frame_dir, text="Salvar em:", font=("Segoe UI", 10, "bold"), fg="gray", bg=self.cores['bg'])
        lbl_dir_title.pack(anchor="w")

        frame_path_btn = tk.Frame(frame_dir, bg=self.cores['bg'])
        frame_path_btn.pack(fill='x', pady=2)

        # Define diretório padrão
        default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads_YouTube")
        self.download_path = tk.StringVar(value=default_dir)

        # Campo que mostra o caminho
        self.entry_path = tk.Entry(frame_path_btn, textvariable=self.download_path, font=("Consolas", 9), 
                                   bg=self.cores['input_bg'], fg="#cccccc", relief="flat", bd=8, state='readonly')
        self.entry_path.pack(side="left", fill='x', expand=True, padx=(0, 10))

        # Botão para mudar pasta
        btn_change_dir = tk.Button(frame_path_btn, text="📂 Alterar", font=("Segoe UI", 9), 
                                   bg="#444444", fg="white", activebackground="#555555", activeforeground="white",
                                   relief="flat", cursor="hand2", command=self.escolher_diretorio)
        btn_change_dir.pack(side="right")

        # 4. Opções (Radio Buttons customizados para Dark Mode)
        self.formato_var = tk.StringVar(value="video")
        
        frame_opcoes = tk.Frame(root, bg=self.cores['bg'])
        frame_opcoes.pack(pady=15)
        
        # Usando tk.Radiobutton normal para poder pintar o fundo de preto (ttk é chato com cores)
        rb_config = {'bg': self.cores['bg'], 'fg': self.cores['fg'], 'font': ("Segoe UI", 11), 'selectcolor': '#1e1e1e', 'activebackground': self.cores['bg'], 'activeforeground': self.cores['accent']}
        
        rb_video = tk.Radiobutton(frame_opcoes, text="Vídeo (MP4 HD)", variable=self.formato_var, value="video", **rb_config)
        rb_video.pack(side="left", padx=20)
        
        rb_audio = tk.Radiobutton(frame_opcoes, text="Áudio (MP3)", variable=self.formato_var, value="audio", **rb_config)
        rb_audio.pack(side="left", padx=20)

        # 4. Botão Principal
        self.btn_download = tk.Button(root, text="INICIAR DOWNLOAD", font=("Segoe UI", 12, "bold"), 
                                      bg=self.cores['btn_bg'], fg=self.cores['btn_fg'], 
                                      activebackground=self.cores['btn_hover'], activeforeground='white',
                                      relief="flat", cursor="hand2", command=self.iniciar_download_thread)
        self.btn_download.pack(pady=25, ipadx=40, ipady=10)

        # 5. Barra de Progresso e Status
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=550, mode="determinate", style="TProgressbar")
        self.progress_bar.pack(pady=5)

        self.lbl_status = tk.Label(root, text="Pronto para baixar", font=("Segoe UI", 10), fg="gray", bg=self.cores['bg'])
        self.lbl_status.pack(pady=5)
        
        # (Rodapé removido pois agora temos o seletor de pasta visível)

    def escolher_diretorio(self):
        caminho_escolhido = filedialog.askdirectory()
        if caminho_escolhido:
            self.download_path.set(caminho_escolhido)

    def iniciar_download_thread(self):
        link = self.entry_link.get()
        if not link:
            messagebox.showwarning("Ops!", "Você esqueceu de colar o link!")
            return
        
        self.btn_download.config(state="disabled", text="CONECTANDO...", bg="#444444")
        self.lbl_status.config(text="Analisando link...", fg=self.cores['accent'])
        self.progress_bar['value'] = 0
        
        thread = threading.Thread(target=self.realizar_download, args=(link,))
        thread.start()

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            # Tenta pegar a porcentagem. As vezes vem com caracteres de controle ANSI, então limpamos
            p = d.get('_percent_str', '0%').replace('%','')
            try:
                self.root.after(0, lambda: self.progress_bar.configure(value=float(p)))
                self.root.after(0, lambda: self.lbl_status.config(text=f"Baixando: {d.get('_percent_str')} | Vel: {d.get('_speed_str')}"))
            except:
                pass
        elif d['status'] == 'finished':
            self.root.after(0, lambda: self.lbl_status.config(text="Processando arquivo (convertendo)...", fg="yellow"))
            self.root.after(0, lambda: self.progress_bar.configure(value=100))

    def realizar_download(self, link):
        tipo = self.formato_var.get()
        
        # Pega o caminho escolhido pelo usuário na interface
        pasta_destino = self.download_path.get()
        
        if not os.path.exists(pasta_destino):
            try:
                os.makedirs(pasta_destino)
            except:
                self.atualizar_status("Erro: Pasta inválida. Usando padrão.", "orange")
                pasta_destino = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Downloads_YouTube")
                os.makedirs(pasta_destino, exist_ok=True)

        ydl_opts = {
            'outtmpl': f'{pasta_destino}/%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True,
            'progress_hooks': [self.progress_hook], # Adicionamos o Hook para a barra de progresso
        }

        if tipo == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        else:
            ydl_opts['format'] = 'best'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([link])
            
            self.atualizar_status("DOWNLOAD CONCLUÍDO COM SUCESSO!", "#00ff00")
            messagebox.showinfo("Sucesso", f"Arquivo salvo em:\n{pasta_destino}")
            
        except Exception as e:
            # Tratamento de erro simplificado para brevidade, mas mantendo a lógica do FFmpeg
            erro_msg = str(e)
            if "ffprobe" in erro_msg or "ffmpeg" in erro_msg:
                 self.atualizar_status("Erro FFmpeg: Baixando formato original...", "orange")
                 try:
                    del ydl_opts['postprocessors']
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([link])
                    self.atualizar_status("Concluído (Sem conversão)", "#00ff00")
                    messagebox.showinfo("Aviso", "Baixado sem conversão MP3 (Falta FFmpeg).")
                 except:
                     self.atualizar_status("Falha no download.", "red")
            else:
                self.atualizar_status("Erro no download.", "red")
                messagebox.showerror("Erro", str(e))
        
        finally:
            self.root.after(0, self.resetar_interface)

    def atualizar_status(self, texto, cor):
        self.root.after(0, lambda: self.lbl_status.config(text=texto, fg=cor))

    def resetar_interface(self):
        self.btn_download.config(state="normal", text="INICIAR DOWNLOAD", bg=self.cores['btn_bg'])
        self.entry_link.delete(0, tk.END)

if __name__ == "__main__":
    root = tk.Tk()
    app = YoutubeDownloaderApp(root)
    root.mainloop()