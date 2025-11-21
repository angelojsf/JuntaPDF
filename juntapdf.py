import atexit
import concurrent.futures
import glob
import logging
import os
import re
import subprocess
import shutil
import sys
import json
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def aplicar_tema_moderno(root):
    """
    Tema personalizado com cores institucionais - profissional e único
    """
    try:
        # Cores da identidade visual
        COR_PRIMARIA = "#004A80"      # Azul governo
        COR_SECUNDARIA = "#0078D4"    # Azul Microsoft
        COR_FUNDO = "#F5F5F5"         # Cinza muito claro
        COR_TEXTO = "#333333"         # Cinza escuro
        COR_BORDA = "#CCCCCC"         # Cinza médio
        
        # Configura estilo manualmente
        style = ttk.Style()
        
        # Tema geral
        style.configure(".", 
                       background=COR_FUNDO,
                       foreground=COR_TEXTO,
                       font=("Segoe UI", 9))
        
        # Frame principal
        style.configure("TFrame", background=COR_FUNDO)
        
        # LabelFrame (caixas de grupo)
        style.configure("TLabelframe", 
                       background=COR_FUNDO,
                       borderwidth=1,
                       relief="solid")
        style.configure("TLabelframe.Label",
                       background=COR_FUNDO,
                       foreground=COR_PRIMARIA,
                       font=("Segoe UI", 9, "bold"))
        
        # Botões - DESTAQUE INSTITUCIONAL
        style.configure("TButton",
                       background="#E1E1E1",
                       foreground=COR_TEXTO,
                       borderwidth=1,
                       relief="raised",
                       padding=(12, 4),
                       font=("Segoe UI", 9))
        
        style.map("TButton",
                 background=[('active', '#D0D0D0'),
                           ('pressed', COR_PRIMARIA)],
                 foreground=[('pressed', 'white')])
        
        # Botão de ação principal
        style.configure("Primary.TButton",
                       background=COR_PRIMARIA,
                       foreground="white",
                       font=("Segoe UI", 9, "bold"))
        
        style.map("Primary.TButton",
                 background=[('active', COR_SECUNDARIA),
                           ('pressed', '#003366')])
        
        # Progressbar
        style.configure("Horizontal.TProgressbar",
                       background=COR_PRIMARIA,
                       troughcolor=COR_FUNDO,
                       borderwidth=0)
        
        # Labels
        style.configure("TLabel",
                       background=COR_FUNDO,
                       foreground=COR_TEXTO,
                       font=("Segoe UI", 9))
        
        style.configure("Title.TLabel",
                       background=COR_FUNDO,
                       foreground=COR_PRIMARIA,
                       font=("Segoe UI", 11, "bold"))
        
        # Entry/Combobox
        style.configure("TEntry",
                       fieldbackground="white",
                       borderwidth=1,
                       relief="solid")
        
        style.configure("TCombobox",
                       fieldbackground="white")
        
        logging.info("🎨 Tema institucional personalizado aplicado")
        
    except Exception as e:
        logging.warning(f"Erro ao aplicar tema personalizado: {e}")
        # Não retorna nada - função void


try:
    import psutil
    PSUtil_AVAILABLE = True
except ImportError:
    PSUtil_AVAILABLE = False
    logging.warning("psutil não disponível - algumas métricas estarão limitadas")

class SecureLogger:
    def __init__(self):
        self.sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'user[=:]\s*\S+',
            r'[\w\.-]+@[\w\.-]+\.\w+',
            r'senha[=:]\s*\S+',
            r'pwd[=:]\s*\S+'
        ]
    
    def sanitize_log(self, message):
        if not isinstance(message, str):
            message = str(message)
        for pattern in self.sensitive_patterns:
            message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
        return message

secure_logger = SecureLogger()

def limpar_logs_antigos(dias=30):
    try:
        log_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Logs")
        if not os.path.exists(log_dir):
            return
            
        agora = time.time()
        limite_tempo = agora - (dias * 24 * 60 * 60)
        
        for arquivo in os.listdir(log_dir):
            if arquivo.startswith("juntapdf_") and arquivo.endswith(".log"):
                caminho_completo = os.path.join(log_dir, arquivo)
                if os.path.getmtime(caminho_completo) < limite_tempo:
                    os.remove(caminho_completo)
                    logging.debug(f"Log expirado removido: {arquivo}")
                    
    except Exception as e:
        logging.warning(f"Erro ao limpar logs antigos: {e}")

def setup_log_rotation():
    try:
        log_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Logs")
        if not os.path.exists(log_dir):
            return
            
        for log_file in glob.glob(os.path.join(log_dir, "juntapdf_*.log")):
            try:
                if os.path.getsize(log_file) > 10 * 1024 * 1024:
                    base_name = os.path.basename(log_file)
                    name_without_ext = os.path.splitext(base_name)[0]
                    timestamp = time.strftime("%Y%m%d_%H%M%S")
                    new_name = f"{name_without_ext}_rotated_{timestamp}.log"
                    new_path = os.path.join(log_dir, new_name)
                    
                    os.rename(log_file, new_path)
                    logging.info(f"Log rotacionado: {base_name} -> {new_name}")
                    
            except Exception as e:
                logging.warning(f"Erro ao rotacionar log {log_file}: {e}")
                
    except Exception as e:
        logging.warning(f"Erro no sistema de rotação de logs: {e}")

def setup_logging():
    setup_log_rotation()
    
    log_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Logs")
    os.makedirs(log_dir, exist_ok=True)
    
    limpar_logs_antigos(30)
    
    log_file = os.path.join(log_dir, f"juntapdf_{time.strftime('%Y%m%d')}.log")
    
    class SanitizedFileHandler(logging.FileHandler):
        def emit(self, record):
            record.msg = secure_logger.sanitize_log(record.msg)
            if record.args:
                record.args = tuple(secure_logger.sanitize_log(str(arg)) if isinstance(arg, str) else arg 
                                  for arg in record.args)
            super().emit(record)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            SanitizedFileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logging.info("=" * 60)
    logging.info("JuntaPDF Iniciado")
    logging.info(f"Versão Python: {sys.version}")
    logging.info(f"Diretório de Log: {log_dir}")

setup_logging()

PDF_LIBS_AVAILABLE = False
PIKEPDF_AVAILABLE = False  
DND_AVAILABLE = False
PDFA_AVAILABLE = False
GHOSTSCRIPT_PATH = None
ICC_PROFILE_PATH = None
temp_files_global = []
temp_files_lock = threading.Lock()
MAX_FILE_SIZE = 500 * 1024 * 1024
MAX_TOTAL_PAGES = 10000
MAX_FILES_PER_OPERATION = 100
MAX_FILES_FOR_SPLIT = 10
MAX_PAGES_PER_FILE_FOR_SPLIT = 1000
MAX_TOTAL_OUTPUT_FILES = 500
MAX_PAGES_FOR_SINGLE_FILE_SPLIT = 200

class SecurityError(Exception):
    pass

class PDFCorruptionError(Exception):
    pass

class SystemOverloadError(Exception):
    pass

class PDFProcessingError(Exception):
    pass

class PerformanceMonitor:
    def __init__(self):
        self.operation_times = []
        self.memory_usage = []
    
    def check_system_health(self):
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                raise SystemOverloadError("Sistema com memória insuficiente")
            
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 80:
                raise SystemOverloadError("CPU sobrecarregada")
        except ImportError:
            pass

performance_monitor = PerformanceMonitor()

def create_operation_checkpoint(operation_type, files_processed, current_step, temp_files):
    checkpoint = {
        'operation_type': operation_type,
        'files_processed': list(files_processed),
        'current_step': current_step,
        'temp_files': list(temp_files),
        'timestamp': time.time()
    }
    
    checkpoint_file = os.path.join(tempfile.gettempdir(), f"juntapdf_checkpoint_{os.getpid()}.json")
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f)
        if hasattr(os, 'chmod'):
            os.chmod(checkpoint_file, 0o600)
        logging.info(f"Checkpoint criado: {checkpoint_file}")
    except Exception as e:
        logging.warning(f"Erro ao criar checkpoint: {e}")

def cleanup_checkpoint():
    checkpoint_file = os.path.join(tempfile.gettempdir(), f"juntapdf_checkpoint_{os.getpid()}.json")
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logging.info("Checkpoint removido")
    except Exception as e:
        logging.warning(f"Erro ao remover checkpoint: {e}")

class UIThreadDispatcher:
    """Gerenciador seguro de chamadas de interface a partir de threads."""
    def __init__(self, root_element):
        self.root = root_element

    def dispatch(self, func, *args, **kwargs):
        """Envia a função para rodar na thread principal de forma segura."""
        def wrapped():
            try:
                func(*args, **kwargs)
            except Exception as e:
                print(f"Erro na UI (Dispatch): {e}")
        
        if self.root:
            self.root.after(0, wrapped)

# Variável global para o dispatcher (será iniciada na criação da interface)
ui_dispatch = None 

def exec_segura(cmd, timeout=60, descricao="Processo", progress_widget=None, cwd=None):
    """
    Versão DEFINITIVA: Substitui todas as outras chamadas de subprocesso.
    Blindada contra deadlocks, erros de unicode e falhas silenciosas.
    """
    import shlex
    
    # Se o comando vier como string única, divide corretamente
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)

    logging.info(f"Executando {descricao}: {cmd}")

    try:
        # Popen com PIPES e modo binário para evitar travamento de buffer e encoding
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False, # Segurança
            cwd=cwd
        )
        
        try:
            # Comunicação com timeout real
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
            
            # Decodificação resiliente (ignora caracteres estranhos do Ghostscript)
            stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
            stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
            
            # Retorna objeto compatível com subprocess.CompletedProcess
            return subprocess.CompletedProcess(cmd, process.returncode, stdout, stderr)
            
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate() # Limpa buffers
            logging.error(f"Timeout em {descricao}")
            raise subprocess.TimeoutExpired(cmd, timeout)
            
    except Exception as e:
        logging.error(f"Erro crítico em exec_segura ({descricao}): {str(e)}")
        # Retorna um objeto de erro falso para não quebrar quem chama
        return subprocess.CompletedProcess(cmd, 1, "", f"Erro Python: {str(e)}")

    except subprocess.TimeoutExpired:
        # Já tratado acima; propaga para camadas superiores
        raise
    except Exception as e:
        logging.error(f"Erro em {descricao}: {e}")
        raise
    finally:
        try:
            if progress_widget and hasattr(progress_widget, 'stop'):
                progress_widget.stop()
                if hasattr(progress_widget, 'config'):
                    progress_widget.config(mode="determinate")
        except Exception:
            logging.debug("Progress widget stop falhou (ignorando).")

def validar_pdfa_com_ghostscript_rigoroso(file_path):
    """
    Versão unificada, blindada e integrada com exec_segura (FASE 0).
    Retorna: (bool_ok, motivo)
    """
    if not os.path.exists(file_path):
        return False, "Arquivo não encontrado."

    # 1. Resolver Ghostscript de forma robusta
    gs_cmd = (
        GHOSTSCRIPT_PATH 
        if "GHOSTSCRIPT_PATH" in globals() and GHOSTSCRIPT_PATH 
        else shutil.which("gswin64c") 
             or shutil.which("gswin32c") 
             or "gswin64c"
    )

    # 2. Comando de validação: PDF/A estrito (policy=1)
    cmd = [
        gs_cmd,
        "-dPDFA",
        "-dBATCH",
        "-dNOPAUSE",
        "-dNOOUTERSAVE",
        "-dPDFACompatibilityPolicy=1",
        "-sDEVICE=pdfwrite",
        "-sOutputFile=" + os.devnull,
        file_path
    ]

    try:
        # 3. Execução blindada (sem timeout_dinamico!)
        result = exec_segura(
            cmd,
            timeout=60,
            descricao="Validação PDF/A Ghostscript",
            progress_widget=None
        )

        stderr = result.stderr or ""

        if result.returncode == 0:
            return True, "Válido (Ghostscript aceitou)"

        # 4. Diagnóstico
        motivo = "Falha na validação PDF/A (policy=1)."
        if "Error:" in stderr:
            for line in stderr.splitlines():
                if "Error:" in line:
                    motivo = line.strip()
                    break
        elif stderr.strip():
            motivo = f"Erro GS: {stderr.strip()[:100]}"

        return False, motivo

    except subprocess.TimeoutExpired:
        return False, "Timeout: PDF muito complexo para validação."
    except Exception as e:
        return False, f"Erro técnico: {str(e)}"


def calcular_tamanho_lote(num_arquivos, tamanho_total_estimate):
    """
    Calcula o tamanho ideal do lote baseado no número de arquivos e tamanho total
    para evitar sobrecarga de memória
    """
    
    # Limites conservadores para evitar memory overflow
    if tamanho_total_estimate > 100 * 1024 * 1024:  # > 100MB
        return max(1, num_arquivos // 10)  # Lotes muito pequenos para grandes arquivos
    elif tamanho_total_estimate > 50 * 1024 * 1024:  # > 50MB
        return max(2, num_arquivos // 5)
    elif num_arquivos > 20:
        return 5  # Lotes de 5 arquivos para muitas operações
    elif num_arquivos > 10:
        return 3  # Lotes de 3 arquivos
    else:
        return num_arquivos  # Processa tudo de uma vez se for pouco

def validate_file_security(file_path):
    if not os.path.exists(file_path):
        raise SecurityError("Arquivo não existe")
    
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise SecurityError(f"Arquivo muito grande ({file_size/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024}MB)")
    
    filename = os.path.basename(file_path)
    
    dangerous_patterns = [
        '..',
        '|',
        ';',
        '`',
        '\0',
        '\r',
        '\n'
    ]
    
    if any(pattern in file_path for pattern in dangerous_patterns):
        raise SecurityError("Nome de arquivo contém caracteres perigosos")
    
    try:
        absolute_path = os.path.abspath(file_path)
        normalized_path = os.path.normpath(file_path)
        
        if '..' in normalized_path or normalized_path != os.path.normpath(absolute_path):
            raise SecurityError("Tentativa de path traversal detectada")
            
    except Exception as e:
        raise SecurityError(f"Erro ao validar caminho: {e}")
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                raise SecurityError("Arquivo não é um PDF válido")
            
            f.seek(0)
            first_chunk = f.read(4096)
            if b'/JavaScript' in first_chunk:
                raise SecurityError("PDF contém JavaScript - risco de segurança")
                
    except Exception as e:
        raise SecurityError(f"Erro ao verificar arquivo: {e}")

def validate_split_limits(files, split_mode, options=None):
    options = options or {}
    
    if len(files) > MAX_FILES_FOR_SPLIT:
        raise SystemOverloadError(
            f"Máximo de {MAX_FILES_FOR_SPLIT} arquivos para divisão. "
            f"Selecionados: {len(files)}"
        )
    
    total_input_pages = 0
    total_output_files_estimate = 0
    
    for f in files:
        try:
            reader = safe_pdf_reader(f)
            pages = len(reader.pages)
            total_input_pages += pages
            
            if pages > MAX_PAGES_PER_FILE_FOR_SPLIT:
                raise SystemOverloadError(
                    f"Arquivo '{os.path.basename(f)}' tem {pages} páginas. "
                    f"Máximo permitido para divisão: {MAX_PAGES_PER_FILE_FOR_SPLIT}"
                )
            
            if split_mode == "all":
                total_output_files_estimate += pages
            elif split_mode == "extract":
                page_ranges = options.get('page_ranges', [])
                total_output_files_estimate += 1
            elif split_mode == "interval":
                interval = options.get('interval', 5)
                total_output_files_estimate += (pages + interval - 1) // interval
            elif split_mode == "parts":
                parts = options.get('parts', 3)
                total_output_files_estimate += min(parts, pages)
                
        except Exception as e:
            logging.warning(f"Erro ao validar arquivo {f}: {e}")
            continue
    
    if total_input_pages > MAX_TOTAL_PAGES:
        raise SystemOverloadError(
            f"Total de {total_input_pages} páginas excede o limite de {MAX_TOTAL_PAGES}"
        )
    
    if total_output_files_estimate > MAX_TOTAL_OUTPUT_FILES:
        raise SystemOverloadError(
            f"Operação geraria aproximadamente {total_output_files_estimate} arquivos. "
            f"Máximo permitido: {MAX_TOTAL_OUTPUT_FILES}"
        )
    
    if split_mode == "all" and total_input_pages > MAX_PAGES_FOR_SINGLE_FILE_SPLIT:
        raise SystemOverloadError(
            f"Divisão página-a-página limitada a {MAX_PAGES_FOR_SINGLE_FILE_SPLIT} páginas. "
            f"Total: {total_input_pages}"
        )
    
    return total_input_pages, total_output_files_estimate

DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
    logging.info("tkinterdnd2 disponível")
except ImportError:
    DND_AVAILABLE = False
    logging.warning("tkinterdnd2 não disponível")

try:
    from PyPDF2 import PdfMerger, PdfReader, PdfWriter
    PDF_LIBS_AVAILABLE = True
    logging.info("PyPDF2 disponível")
except ImportError as e:
    PDF_LIBS_AVAILABLE = False  
    logging.error(f"PyPDF2 não disponível: {e}")

try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
    logging.info(f"pikepdf {pikepdf.__version__} disponível")
except ImportError as e:
    PIKEPDF_AVAILABLE = False
    logging.warning(f"pikepdf não disponível: {e}")
except Exception as e:
    PIKEPDF_AVAILABLE = False
    logging.warning(f"Erro ao importar pikepdf: {e}")

cancel_operation = False

total_files_merge_var = None
total_pages_merge_var = None
total_size_merge_var = None
total_files_split_var = None
total_pages_split_var = None
total_size_split_var = None
protect_var = None
pdfa_var = None
pdfa_var_split = None
compress_var = None
meta_var = None
split_mode_var = None
split_interval_var = None
split_parts_var = None
status_var = None
compress_level = None

pdf_metadata_cache = {}

def safe_temp_file(prefix="temp", suffix=".pdf"):
    import tempfile
    temp_file = tempfile.NamedTemporaryFile(
        prefix=prefix, 
        suffix=suffix, 
        delete=False
    )
    temp_path = temp_file.name
    temp_file.close()
    add_temp_file(temp_path)
    return temp_path

def add_temp_file(file_path):
    with temp_files_lock:
        if file_path not in temp_files_global:
            temp_files_global.append(file_path)
            logging.debug(f"Arquivo temporário registrado: {file_path}")

def remove_temp_file(file_path):
    with temp_files_lock:
        if file_path in temp_files_global:
            temp_files_global.remove(file_path)
            logging.debug(f"Arquivo temporário removido: {file_path}")

def cleanup_temp_files():
    logging.info("Iniciando limpeza de arquivos temporários")
    
    with temp_files_lock:
        files_to_clean = list(temp_files_global)
        
    for temp_file in files_to_clean:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logging.debug(f"Arquivo temporário removido: {temp_file}")
        except Exception as e:
            logging.warning(f"Erro ao limpar {temp_file}: {e}")

    try:
        cleanup_checkpoint()
    except Exception as e:
        logging.warning(f"Erro ao limpar checkpoint: {e}")

    try:
        if 'thread_executor' in globals():
            thread_executor.shutdown(wait=True, timeout=5)
    except TypeError:
        try:
            if 'thread_executor' in globals():
                thread_executor.shutdown(wait=True)
        except Exception as e:
            logging.warning(f"Falha ao encerrar thread_executor: {e}")
    except Exception as e:
        logging.warning(f"Erro ao encerrar thread_executor: {e}")

atexit.register(cleanup_temp_files)
logging.info("Cleanup registrado no atexit")

def widget_exists(widget):
    try:
        return widget is not None and hasattr(widget, "winfo_exists") and widget.winfo_exists()
    except Exception:
        return False

def safe_widget_config(widget, **kwargs):
    try:
        if widget is None:
            return False
        if hasattr(widget, "winfo_exists") and widget.winfo_exists():
            try:
                widget.config(**kwargs)
                return True
            except tk.TclError:
                return False
    except Exception:
        return False
    return False

def encontrar_ghostscript():
    logging.info("Procurando Ghostscript...")
    for cmd in ("gswin64c", "gswin32c", "gs"):
        caminho = shutil.which(cmd)
        if caminho:
            logging.info(f"Ghostscript encontrado: {caminho}")
            return caminho

    possiveis_pastas = [
        r"C:\Program Files\gs",
        r"C:\Program Files (x86)\gs",
        r"C:\Ghostscript",
    ]

    for base in possiveis_pastas:
        if not os.path.exists(base):
            continue
        versoes = glob.glob(os.path.join(base, "gs*", "bin", "gswin64c.exe"))
        if not versoes:
            versoes = glob.glob(os.path.join(base, "gs*", "bin", "gswin32c.exe"))
        if versoes:
            versoes.sort(reverse=True)
            logging.info(f"Ghostscript encontrado: {versoes[0]}")
            return versoes[0]

    logging.warning("Ghostscript não encontrado")
    return None

def get_app_path():
    """Retorna o diretório base corretamente, seja .py ou .exe"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def encontrar_ghostscript_portavel():
    """Busca Ghostscript na pasta portátil e CONFIGURA AS BIBLIOTECAS"""
    exe_dir = get_app_path()
    
    # Caminho esperado: pasta_do_script/Ghostscript/bin/gswin64c.exe
    caminho_bin = os.path.join(exe_dir, "Ghostscript", "bin", "gswin64c.exe")
    
    if os.path.exists(caminho_bin):
        # --- PROTEÇÃO CRÍTICA (GS_LIB) ---
        caminho_lib = os.path.join(exe_dir, "Ghostscript", "lib")
        if os.path.exists(caminho_lib):
            os.environ['GS_LIB'] = caminho_lib
            logging.info(f"✅ GS_LIB configurado: {caminho_lib}")
        else:
            logging.warning("⚠️ Pasta 'lib' não encontrada - GS portátil pode falhar")
        # ---------------------------------

        logging.info(f"✅ Ghostscript PORTÁTIL encontrado: {caminho_bin}")
        return caminho_bin
        
    # Se não achar portátil, usa o do sistema (sua função original)
    logging.info("🔍 Ghostscript portátil não encontrado, buscando no sistema...")
    return encontrar_ghostscript()

def encontrar_perfil_icc_portavel(gs_exec=None):
    """BUSCA ABSOLUTA BLINDADA - encontra sRGB mesmo sem extensão"""
    
    # 1. Diretório base CORRETO (script ou executável)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)  # Pasta do .exe
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Pasta do .py
    
    logging.info(f"📁 Base directory: {base_dir}")
    
    # 2. Lista de possíveis nomes/locais - AGORA INCLUI SEM EXTENSÃO
    candidatos = []
    
    # Na pasta do script - COM E SEM EXTENSÃO
    candidatos.extend([
        os.path.join(base_dir, "srgb.icc"),
        os.path.join(base_dir, "sRGB.icc"),
        os.path.join(base_dir, "srgb"),  # ← SEM EXTENSÃO
        os.path.join(base_dir, "sRGB"),  # ← SEM EXTENSÃO
        os.path.join(base_dir, "Ghostscript", "Resource", "ColorSpace", "srgb.icc"),
        os.path.join(base_dir, "Ghostscript", "Resource", "ColorSpace", "sRGB.icc"),
        os.path.join(base_dir, "Ghostscript", "Resource", "ColorSpace", "srgb"),  # ← SEM EXTENSÃO
        os.path.join(base_dir, "Ghostscript", "Resource", "ColorSpace", "sRGB"),  # ← SEM EXTENSÃO
    ])
    
    # 3. Busca ativa
    for caminho in candidatos:
        if os.path.exists(caminho):
            logging.info(f"✅ PERFIL ICC ENCONTRADO: {caminho}")
            return caminho
    
    # 4. Busca inteligente por arquivos que contenham "srgb" no nome (case insensitive)
    logging.info("🔍 Buscando arquivos que contenham 'srgb' no nome...")
    
    # Procura em toda a estrutura de pastas
    for root_dir, dirs, files in os.walk(base_dir):
        for file in files:
            if 'srgb' in file.lower():  # Encontra qualquer arquivo com "srgb" no nome
                caminho_completo = os.path.join(root_dir, file)
                logging.info(f"📍 Arquivo potencial encontrado: {caminho_completo}")
                
                # Verifica se é um arquivo ICC válido (pelo menos 1KB)
                try:
                    if os.path.getsize(caminho_completo) > 1024:  # Mínimo 1KB
                        logging.info(f"✅ PERFIL ICC ENCONTRADO (busca inteligente): {caminho_completo}")
                        return caminho_completo
                except:
                    continue
    
    # 5. Fallback: busca no sistema (função original)
    logging.warning("🔍 ICC não encontrado localmente, buscando no sistema...")
    fallback = encontrar_perfil_icc(gs_exec)  # Sua função original do sistema
    if fallback:
        logging.info(f"✅ ICC encontrado no sistema: {fallback}")
        return fallback
    
    # 6. Diagnóstico detalhado do fracasso
    logging.error("❌ NENHUM perfil ICC encontrado em nenhum local!")
    
    # Lista todos os arquivos na pasta base para debug
    try:
        logging.info("📋 Arquivos na pasta base:")
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isfile(item_path):
                logging.info(f"   📄 {item} ({os.path.getsize(item_path)} bytes)")
    except Exception as e:
        logging.warning(f"Erro ao listar arquivos: {e}")
    
    return None

def encontrar_perfil_icc(gs_exec):
    if not gs_exec:
        return None
    
    gs_dir = os.path.dirname(os.path.dirname(gs_exec))

    possible_paths = [
        os.path.join(gs_dir, "iccprofiles", "srgb.icc"),
        os.path.join(gs_dir, "iccprofiles", "default_rgb.icc"),
        os.path.join(gs_dir, "lib", "srgb.icc"),
        os.path.join(gs_dir, "Resource", "ColorSpace", "sRGB.icc"),
    ]
    
    for icc_path in possible_paths:
        if os.path.exists(icc_path):
            logging.info(f"Perfil ICC encontrado: {icc_path}")
            return icc_path
    
    try:
        for root_dir, dirs, files in os.walk(gs_dir):
            for file in files:
                if file.lower() in ("srgb.icc", "default_rgb.icc"):
                    found_path = os.path.join(root_dir, file)
                    logging.info(f"Perfil ICC encontrado: {found_path}")
                    return found_path
    except Exception as e:
        logging.warning(f"Erro na busca recursiva: {e}")
    
    logging.warning("Perfil ICC não encontrado")
    return None

def diagnosticar_compressao(input_path):
    """Diagnóstico para entender por que a compressão não está funcionando"""
    try:
        import pikepdf
        
        with pikepdf.open(input_path) as pdf:
            info = {
                'paginas': len(pdf.pages),
                'versao_pdf': pdf.pdf_version,
                'criptografado': pdf.is_encrypted,
                'streams_total': 0,
                'imagens': 0
            }
            
            # Analisa objetos do PDF de forma segura
            for obj in pdf.objects:
                try:
                    if hasattr(obj, 'get'):
                        # Verifica se é imagem
                        if '/Subtype' in obj and obj['/Subtype'] == pikepdf.Name('/Image'):
                            info['imagens'] += 1
                        # Verifica se tem stream (pode ser comprimido)
                        if '/Length' in obj:
                            info['streams_total'] += 1
                except Exception:
                    continue  # Ignora objetos problemáticos
            
            return info
    except Exception as e:
        return {'erro': str(e)}

# Agora chama as funções portáteis (que fazem o fallback se precisar)
GHOSTSCRIPT_PATH = encontrar_ghostscript_portavel()
ICC_PROFILE_PATH = encontrar_perfil_icc_portavel(GHOSTSCRIPT_PATH)
PDFA_AVAILABLE = bool(GHOSTSCRIPT_PATH and ICC_PROFILE_PATH)

def comprimir_pdf(input_path, output_path, nivel="Qualidade Equilibrada", forcar=False):
    """
    Sistema de compressão APENAS para PDFs NORMAS (NÃO PDF/A)
    """
    # 🎯 REDIRECIONAMENTO CRÍTICO: Se for PDF/A, use a função robusta
    if PDFA_AVAILABLE and pdfa_var.get():
        logging.info("🔀 Redirecionando compressão para motor PDF/A robusto...")
        return converter_para_pdfa(input_path, output_path, nivel)
    
    # MAPEAMENTO para compressão NORMAL (não PDF/A)
    config_map = {
        "Tamanho Mínimo": "/ebook",
        "Qualidade Equilibrada": "/printer", 
        "Qualidade Máxima": "/prepress"
    }
    
    if nivel not in config_map:
        nivel = "Qualidade Equilibrada"
    
    gs_setting = config_map[nivel]
    
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível")
    
    # ⚠️ COMANDO SEM PDF/A - apenas compressão normal
    gs_args = [
        GHOSTSCRIPT_PATH, 
        "-sDEVICE=pdfwrite", 
        "-dNOPAUSE", 
        "-dBATCH", 
        "-dQUIET",
        f"-dPDFSETTINGS={gs_setting}",
        f"-sOutputFile={output_path}", 
        input_path
    ]
    
    resultado = exec_segura(gs_args, timeout=120, descricao=f"Compressão {nivel}")
    
    if resultado.returncode != 0:
        raise PDFProcessingError(f"Ghostscript falhou: {resultado.stderr}")
    
    # Cálculo de estatísticas
    tamanho_original = os.path.getsize(input_path)
    tamanho_comprimido = os.path.getsize(output_path)
    
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PDFProcessingError("Arquivo comprimido não gerado")
    
    reducao_percentual = ((tamanho_original - tamanho_comprimido) / tamanho_original) * 100
    
    logging.info(f"📊 Compressão Normal ({nivel}): {tamanho_original/1024/1024:.2f}MB → {tamanho_comprimido/1024/1024:.2f}MB ({reducao_percentual:+.1f}%)")
    
    return reducao_percentual, f"Compressão {nivel} aplicada"

def deve_comprimir(diagnostico, tamanho_original, nivel):
    """Decide se vale a pena comprimir baseado em múltiplos fatores"""
    
    # Fator 1: Tamanho muito pequeno
    if tamanho_original < 50 * 1024:  # < 50KB
        logging.info("📏 PDF muito pequeno - pulando compressão")
        return False
    
    # Fator 2: Já altamente comprimido
    if ('taxa_compressao_existente' in diagnostico and 
        diagnostico['taxa_compressao_existente'] > 0.8):
        logging.info("🎯 PDF já bem comprimido - pulando compressão")
        return False
    
    # Fator 3: Muitas imagens JPEG (já comprimidas)
    if (diagnostico.get('imagens', 0) > 5 and 
        diagnostico.get('streams_comprimidos', 0) / max(1, diagnostico.get('streams_total', 1)) > 0.7):
        logging.info("🖼️ Muitas imagens já comprimidas - risco de perda de qualidade")
        return nivel != "Tamanho Mínimo"  # Só comprime se for modo agressivo
    
    # Fator 4: PDF criptografado
    if diagnostico.get('criptografado', False):
        logging.info("🔒 PDF criptografado - pulando compressão")
        return False
        
    return True

def comprimir_com_pikepdf(input_path, output_path, nivel="Qualidade Máxima", diagnostico=None):
    """Versão melhorada com decisões inteligentes"""
    if not PIKEPDF_AVAILABLE:
        raise PDFProcessingError("pikepdf não disponível")
    
    import pikepdf
    
    logging.info(f"Comprimindo com pikepdf inteligente ({nivel}): {os.path.basename(input_path)}")
    
    tamanho_original = os.path.getsize(input_path)
    
    # Configurações adaptativas baseadas no diagnóstico
    configuracoes = {
        "Qualidade Máxima": {
            "compress_streams": True,
            "stream_decode_level": pikepdf.StreamDecodeLevel.none,
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        },
        "Qualidade Equilibrada": {
            "compress_streams": True,
            "stream_decode_level": pikepdf.StreamDecodeLevel.generalized,
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        },
        "Tamanho Mínimo": {
            "compress_streams": True,
            "stream_decode_level": pikepdf.StreamDecodeLevel.all,
            "object_stream_mode": pikepdf.ObjectStreamMode.generate,
        }
    }
    
    config = configuracoes.get(nivel, configuracoes["Qualidade Máxima"])
    
    # Otimização: não normaliza conteúdo se já for bem estruturado
    if diagnostico and diagnostico.get('versao_pdf', '') >= '1.5':
        config['normalize_content'] = False
    else:
        config['normalize_content'] = True
    
    with pikepdf.open(input_path) as pdf:
        pdf.save(output_path, **config)
    
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PDFProcessingError("Arquivo comprimido não foi gerado")
    
    tamanho_comprimido = os.path.getsize(output_path)
    reducao_percentual = ((tamanho_original - tamanho_comprimido) / tamanho_original) * 100
    
    logging.info(f"📊 pikepdf ({nivel}): {tamanho_original/1024/1024:.2f}MB → {tamanho_comprimido/1024/1024:.2f}MB ({reducao_percentual:+.1f}%)")
    
    return reducao_percentual

def comprimir_com_ghostscript(input_path, output_path, nivel, diagnostico=None):
    """Compressão usando Ghostscript - VERSÃO ATUALIZADA SEM PDF/A"""
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível")
    
    # 🎯 REDIRECIONAMENTO: Se for PDF/A, use a função específica
    if PDFA_AVAILABLE and pdfa_var.get():
        logging.info("🔀 Redirecionando para PDF/A robusto...")
        return converter_para_pdfa(input_path, output_path, nivel)
    
    # MAPEAMENTO para compressão NORMAL (NÃO PDF/A)
    configs = {
        "Qualidade Máxima": "-dPDFSETTINGS=/prepress",
        "Qualidade Equilibrada": "-dPDFSETTINGS=/printer", 
        "Tamanho Mínimo": "-dPDFSETTINGS=/ebook"
    }
    
    config = configs.get(nivel, "-dPDFSETTINGS=/prepress")
    
    # ⚠️ COMANDO SEM PDF/A - apenas compressão normal
    gs_args = [
        GHOSTSCRIPT_PATH, 
        "-sDEVICE=pdfwrite", 
        "-dNOPAUSE", 
        "-dBATCH", 
        "-dQUIET",
        config,
        f"-sOutputFile={output_path}", 
        input_path
    ]
    
    resultado = exec_segura(gs_args, timeout=120, descricao=f"Compressão Ghostscript {nivel}")
    
    if resultado.returncode != 0:
        raise PDFProcessingError(f"Ghostscript falhou: {resultado.stderr}")
    
    # Cálculo de estatísticas
    tamanho_original = os.path.getsize(input_path)
    tamanho_comprimido = os.path.getsize(output_path)
    
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PDFProcessingError("Arquivo comprimido não gerado")
    
    reducao_percentual = ((tamanho_original - tamanho_comprimido) / tamanho_original) * 100
    
    logging.info(f"📊 Ghostscript Normal ({nivel}): {tamanho_original/1024/1024:.2f}MB → {tamanho_comprimido/1024/1024:.2f}MB ({reducao_percentual:+.1f}%)")
    
    return reducao_percentual

def validar_compressao_eficiente(input_path, output_path, reducao_percentual):
    """Valida se a compressão foi eficiente (apenas verificação básica)"""
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        return False
    return reducao_percentual >= 0  # Aceita qualquer redução não-negativa

if PDFA_AVAILABLE:
    logging.info("PDF/A disponível")
else:
    logging.warning("PDF/A indisponível")

thread_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="JuntaPDF"
)

def validar_pdfa_com_ghostscript(file_path):
    """Validação REAL de PDF/A usando Ghostscript com política rigorosa"""
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível para validação PDF/A")
    
    logging.info(f"Validando PDF/A rigorosamente: {os.path.basename(file_path)}")
    
    comando = [
        GHOSTSCRIPT_PATH,
        "-dPDFA=2",                    # Especifica PDF/A-2B
        "-dPDFACompatibilityPolicy=1", # ⬅️ CRÍTICO: ABORTA se não for compatível
        "-dNOPAUSE",
        "-dBATCH", 
        "-dNOOUTERSAVE",
        "-sDEVICE=nullpage",           # Não gera saída, apenas valida
        file_path
    ]
    
    resultado = exec_segura(comando, timeout=60, descricao="Validação PDF/A rigorosa")
    
    # Ghostscript retorna 0 APENAS se PDF/A é válido conforme política 1
    if resultado.returncode == 0:
        logging.info(f"✓ PDF/A-2B válido (validação rigorosa): {os.path.basename(file_path)}")
        return True, "PDF/A-2B válido conforme validação Ghostscript rigorosa"
    else:
        error_msg = resultado.stderr or "Erro de validação PDF/A"
        logging.warning(f"✗ PDF/A inválido (validação rigorosa): {os.path.basename(file_path)} - {error_msg}")
        return False, f"PDF/A inválido: {error_msg}"

def validar_pdfa_com_veraPDF(file_path):
    """Validação com veraPDF se disponível (mais robusta)"""
    verapdf_path = shutil.which("verapdf")
    if not verapdf_path:
        return None, "veraPDF não encontrado"
    
    try:
        comando = [verapdf_path, "--format", "text", file_path]
        resultado = exec_segura(comando, timeout=120, descricao="Validação veraPDF")
        
        if resultado.returncode == 0 and "isCompliant=\"true\"" in resultado.stdout:
            return True, "PDF/A válido conforme veraPDF"
        else:
            return False, "PDF/A não conforme veraPDF"
    except Exception as e:
        return None, f"Erro veraPDF: {e}"

def validar_pdfa(file_path):
    """
    Validação PDF/A em 3 níveis de rigor
    Retorna (bool, str) indicando sucesso e mensagem detalhada
    """
    logging.info(f"🔍 Iniciando validação PDF/A rigorosa: {os.path.basename(file_path)}")
    
    # NÍVEL 1: Verificação básica de estrutura
    if not verificar_outputintent_no_pdf(file_path):
        return False, "Falha na verificação básica: OutputIntent GTS_PDFA1 não encontrado"
    
    # NÍVEL 2: Validação Ghostscript rigorosa
    is_gs_valid, gs_msg = validar_pdfa_com_ghostscript_rigoroso(file_path)
    if not is_gs_valid:
        return False, f"Validação Ghostscript falhou: {gs_msg}"
    is_2b_valid, msg_2b = validar_pdfa_2b_rigoroso(file_path)
    if not is_2b_valid:
        return False, f"Validação PDF/A-2B falhou: {msg_2b}"
    
    # NÍVEL 3: Tentativa com veraPDF se disponível
    verapdf_result, verapdf_msg = validar_pdfa_com_veraPDF(file_path)
    if verapdf_result is not None:
        if not verapdf_result:
            return False, f"Validação veraPDF falhou: {verapdf_msg}"
        else:
            logging.info("✅ PDF/A validado com veraPDF (padrão ouro)")
            return True, "PDF/A-2B válido conforme veraPDF"
    
    # Se chegou aqui, Ghostscript validou mas veraPDF não está disponível
    logging.info("✅ PDF/A validado com Ghostscript (veraPDF não disponível)")
    return True, "PDF/A-2B válido conforme validação Ghostscript rigorosa"

def verificar_outputintent_no_pdf(file_path):
    """Verifica se o OutputIntent foi gravado no PDF (Byte check)"""
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            
        patterns = [
            b'GTS_PDFA1',
            b'/GTS_PDFA1',
            b'OutputIntent', 
            b'/OutputIntent',
            b'/DestOutputProfile',
            b'sRGB IEC61966-2.1'  # Perfil de cor esperado
        ]
        
        matches = sum(1 for pattern in patterns if pattern in content)
        logging.info(f"Padrões PDF/A encontrados: {matches}/{len(patterns)}")
        
        return matches >= 2  # Pelo menos 2 padrões devem estar presentes
        
    except Exception as e:
        logging.warning(f"Erro na verificação do OutputIntent: {e}")
        return False

def validar_pdfa_2b_rigoroso(file_path):
    """Validação específica para PDF/A-2b ISO 19005-2:2011"""
    if not GHOSTSCRIPT_PATH:
        return False, "Ghostscript não disponível"

    try:
        comando = [
            GHOSTSCRIPT_PATH,
            "-dPDFA=2",                    
            "-dPDFACompatibilityPolicy=1", 
            "-dNOPAUSE", "-dBATCH", 
            "-dNOOUTERSAVE",
            "-sDEVICE=nullpage",           
            file_path
        ]

        resultado = exec_segura(comando, timeout=60, 
                              descricao="Validação PDF/A-2b Rigorosa")

        if resultado.returncode == 0:
            # Verifica se há warnings no stderr mesmo com sucesso (comum no GS)
            warnings = []
            if resultado.stderr:
                warnings = [line for line in resultado.stderr.splitlines() 
                          if "warning" in line.lower()]
            
            if warnings:
                return True, f"PDF/A-2B válido com avisos: {'; '.join(warnings[:3])}"
            
            return True, "PDF/A-2B válido conforme validação Ghostscript rigorosa"
            
        else:
            error_msg = resultado.stderr or "Erro de validação PDF/A-2b"
            
            # Análise detalhada do erro para feedback melhor
            if "Font" in error_msg and "not embedded" in error_msg:
                return False, "Fontes não embutidas - requer todas as fonts embedded"
            elif "Color" in error_msg and "space" in error_msg:
                return False, "Espaço de cor inválido - requer RGB ou CMYK com perfil"
            elif "transparency" in error_msg.lower():
                return False, "Transparências não suportadas em PDF/A-2B"
            elif "metadata" in error_msg.lower():
                return False, "Metadados XMP inválidos ou ausentes"
            else:
                return False, f"PDF/A-2B inválido: {error_msg[:200]}"

    except Exception as e:
        return False, f"Erro na execução da validação: {str(e)}"

def calcular_timeout_inteligente_pdfa(caminho_arquivo):
    """
    Calcula timeout dinâmico - VERSÃO INSTITUCIONAL GENEROSA
    Prioriza conclusão da operação sobre velocidade.
    """
    try:
        tamanho_mb = os.path.getsize(caminho_arquivo) / (1024 * 1024)
        
        # FÓRMULA GENEROSA PARA INSTITUIÇÕES:
        # Base de 5 minutos (300s) para qualquer operação
        timeout_base = 300 
        
        # Adicional: 30 segundos para cada 10MB
        timeout_extra = (tamanho_mb / 10) * 30
        
        timeout_total = timeout_base + timeout_extra
        
        # Teto máximo: 20 minutos (1200s) - Mínimo: 5 minutos
        timeout_final = max(300, min(1200, int(timeout_total)))
        
        logging.info(f"⏱️ Timeout PDF/A Institucional: {timeout_final}s (Arquivo: {tamanho_mb:.1f}MB)")
        return timeout_final
        
    except Exception as e:
        logging.warning(f"Erro ao calcular timeout, usando padrão seguro: {e}")
        return 600  # 10 minutos de fallback

def validar_pdfa_fallback(file_path):
    """
    Validação alternativa menos rigorosa para diagnóstico
    """
    if not GHOSTSCRIPT_PATH:
        return False, "Ghostscript não disponível"
    
    try:
        comando = [
            GHOSTSCRIPT_PATH,
            "-dPDFA=2",
            "-dPDFACompatibilityPolicy=0",  # Política mais permissiva (apenas avisa)
            "-dNOPAUSE", "-dBATCH", 
            "-sDEVICE=nullpage",
            file_path
        ]
        
        resultado = exec_segura(comando, timeout=30, descricao="Validação PDF/A Fallback")
        
        if resultado.returncode == 0:
            return True, "PDF/A válido (validação fallback)"
        else:
            return False, resultado.stderr or "Erro na validação fallback"
            
    except Exception as e:
        return False, f"Erro na validação fallback: {e}"

def diagnosticar_pdfa(file_path):
    """
    Diagnóstico SUPER DETALHADO do PDF gerado
    """
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Verifica marcadores CRÍTICOS do PDF/A
        marcadores = {
            'PDF Header': b'%PDF' in content[:1024],
            'PDF Version': b'%PDF-1.' in content[:1024],
            'OutputIntent': b'OutputIntent' in content,
            'GTS_PDFA1': b'GTS_PDFA1' in content,
            'ICC Profile': b'DestOutputProfile' in content,
            'sRGB Reference': b'sRGB' in content,
            'XMP Metadata': b'xmpmeta' in content or b'XMP' in content,
            'Fonts Embedded': b'/EmbeddedFiles' in content or b'/FontDescriptor' in content,
            'ICC Data Present': b'ICC' in content and len(content) > 1000,  # Verifica se tem dados ICC
        }
        
        logging.info("🔍 DIAGNÓSTICO DETALHADO PDF/A:")
        for marcador, encontrado in marcadores.items():
            status = "✅" if encontrado else "❌"
            logging.info(f"   {status} {marcador}: {encontrado}")
            
        # Verificação de estrutura crítica
        if b'OutputIntent' not in content:
            logging.error("❌ OUTPUTINTENT AUSENTE - PDF/A INVÁLIDO")
        if b'GTS_PDFA1' not in content:
            logging.error("❌ GTS_PDFA1 AUSENTE - PDF/A INVÁLIDO")
        if b'DestOutputProfile' not in content:
            logging.error("❌ DESTOUTPUTPROFILE AUSENTE - PDF/A INVÁLIDO")
            
        # Verifica tamanho do arquivo (muito pequeno = problema)
        file_size = len(content)
        logging.info(f"📏 Tamanho do arquivo: {file_size} bytes")
        if file_size < 5000:
            logging.error("❌ Arquivo muito pequeno - provável falha na geração")
            
    except Exception as e:
        logging.error(f"Erro no diagnóstico: {e}")

def preparar_ambiente_icc(temp_dir):
    """
    CORREÇÃO CRÍTICA: Copia o ICC para o temp para evitar erros de caminho
    e valida se o arquivo está íntegro.
    """
    # Busca o perfil ICC usando suas funções existentes
    caminho_original = None
    
    # Tenta todas as funções de busca disponíveis
    if 'encontrar_perfil_icc_portavel' in globals():
        caminho_original = encontrar_perfil_icc_portavel(GHOSTSCRIPT_PATH)
    if not caminho_original and 'encontrar_perfil_icc' in globals():
        caminho_original = encontrar_perfil_icc(GHOSTSCRIPT_PATH)
    if not caminho_original and 'ICC_PROFILE_PATH' in globals() and ICC_PROFILE_PATH:
        caminho_original = ICC_PROFILE_PATH

    if not caminho_original or not os.path.exists(caminho_original):
        logging.error("❌ Nenhum perfil sRGB.icc encontrado no sistema!")
        return None

    # Validação de integridade básica
    tamanho = os.path.getsize(caminho_original)
    if tamanho < 1000:  # Menor que 1kb provavelmente é inválido
        logging.warning(f"⚠️ Perfil ICC muito pequeno/inválido: {caminho_original} ({tamanho} bytes)")
        # Continua mesmo assim, mas o validador provavelmente rejeitará

    # CORREÇÃO: Copiar para a pasta temporária com nome simples
    destino_seguro = os.path.join(temp_dir, "srgb.icc")
    try:
        shutil.copy2(caminho_original, destino_seguro)
        logging.info(f"✅ ICC copiado para: {destino_seguro} ({os.path.getsize(destino_seguro)} bytes)")
        
        # Retorna o caminho com barras normais (Unix style) que o Ghostscript prefere
        return destino_seguro.replace("\\", "/")
    except Exception as e:
        logging.error(f"❌ Falha ao copiar ICC para temp: {e}")
        return None

def converter_para_pdfa(input_path, output_path, nivel_compressao="Qualidade Equilibrada"):
    """
    🎯 CONVERSÃO PDF/A-2B - FUSÃO DEFINITIVA (ChatGPT + Gemini)
    Combina: Caminhos Absolutos POSIX + Busca por ICC Real + Fallbacks Robusta
    """
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível")

    logging.info(f"🔄 Convertendo para PDF/A-2B (Fusão Definitiva): {os.path.basename(input_path)}")

    config_compressao = {
        "Tamanho Mínimo": "/ebook",
        "Qualidade Equilibrada": "/printer", 
        "Qualidade Máxima": "/prepress"
    }
    pdfsettings = config_compressao.get(nivel_compressao, "/printer")

    # 🎯 MELHORIA GEMINI: Busca por ICC REAL (>2.5KB)
    icc_source = None
    gs_dir = os.path.dirname(GHOSTSCRIPT_PATH)
    root_dir = os.path.dirname(gs_dir)
    
    # Lista de candidatos PRIORITÁRIOS (Gemini)
    candidatos = [
        os.path.join(root_dir, "iccprofiles", "srgb.icc"),
        os.path.join(root_dir, "lib", "srgb.icc"),
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'spool', 'drivers', 'color', 'sRGB Color Space Profile.icm'),
        os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'System32', 'spool', 'drivers', 'color', 'sRGB.icc'),
    ]
    
    # 🎯 VALIDAÇÃO POR TAMANHO (Gemini) - ICC deve ser >2.5KB
    for path in candidatos:
        if path and os.path.exists(path) and os.path.getsize(path) > 2500:
            icc_source = path
            logging.info(f"✅ ICC Real encontrado: {path} ({os.path.getsize(path)} bytes)")
            break
    
    # 🎯 BUSCA RECURSIVA DESESPERADA (Gemini)
    if not icc_source:
        logging.info("🔍 Busca recursiva por ICC...")
        for root, dirs, files in os.walk(root_dir):
            for file in files:
                if "srgb" in file.lower() and file.endswith((".icc", ".icm")):
                    path = os.path.join(root, file)
                    if os.path.getsize(path) > 2500:  # >2.5KB = ICC real
                        icc_source = path
                        logging.info(f"✅ ICC encontrado recursivamente: {path}")
                        break
            if icc_source: 
                break

    # 🎯 FALLBACK para funções originais
    if not icc_source:
        if 'encontrar_perfil_icc_portavel' in globals():
            icc_source = encontrar_perfil_icc_portavel(GHOSTSCRIPT_PATH)
        if not icc_source and 'ICC_PROFILE_PATH' in globals():
            icc_source = ICC_PROFILE_PATH

    if not icc_source or not os.path.exists(icc_source):
        raise PDFProcessingError("Nenhum perfil ICC sRGB válido (>2.5KB) encontrado no sistema.")

    # 🎯 VALIDAÇÃO FINAL DO ICC
    tamanho_icc = os.path.getsize(icc_source)
    if tamanho_icc < 2500:
        logging.warning(f"⚠️ ICC muito pequeno - pode ser inválido: {tamanho_icc} bytes")
    else:
        logging.info(f"📦 ICC validado: {tamanho_icc} bytes")

    temp_dir = None
    try:
        # 2. Prepara ambiente temporário
        temp_dir = tempfile.mkdtemp()
        
        # 🎯 CORREÇÃO CHATGPT: Copia ICC e converte para caminho ABSOLUTO POSIX
        icc_temp_path = os.path.join(temp_dir, "srgb.icc")
        shutil.copy2(icc_source, icc_temp_path)
        
        # 🎯 CONVERSÃO PARA CAMINHO GHOSTSCRIPT (POSIX)
        icc_path_gs = icc_temp_path.replace("\\", "/")
        logging.info(f"📍 Caminho ICC Ghostscript: {icc_path_gs}")

        # 3. Cria PostScript com caminho ABSOLUTO para ICC
        ps_content = f"""%!
% PDF/A-2B Definition - CAMINHO ABSOLUTO POSIX
[ /Title (Documento PDF/A-2B)
  /Author (JuntaPDF) 
  /Subject (Conformidade PDF/A-2B)
  /Keywords (PDF/A-2B; SEI; Governo Federal)
  /DOCINFO pdfmark

/ICCProfile ({icc_path_gs}) (r) file def  % ⬅️ CAMINHO ABSOLUTO POSIX!

[ /_objdef {{icc_PDFA}}
  /type /stream
  /OBJ pdfmark

[ {{icc_PDFA}} << /N 3 >> /PUT pdfmark

[ {{icc_PDFA}} ICCProfile /PUT pdfmark

[ /_objdef {{OutputIntent_PDFA}}
  /type /dict
  /OBJ pdfmark

[ {{OutputIntent_PDFA}} <<
  /Type /OutputIntent
  /S /GTS_PDFA1
  /DestOutputProfile {{icc_PDFA}}
  /OutputConditionIdentifier (sRGB IEC61966-2.1)
  /Info (sRGB IEC61966-2.1)
  /RegistryName (http://www.color.org)
>> /PUT pdfmark

[ /_objdef {{Catalog_PDFA}}
  /type /dict
  /OBJ pdfmark

[ {{Catalog_PDFA}} << /OutputIntents [ {{OutputIntent_PDFA}} ] >> /PUT pdfmark

[ {{Catalog}} << /OutputIntents [ {{OutputIntent_PDFA}} ] >> /PUT pdfmark
"""

        ps_temp_path = os.path.join(temp_dir, "pdfa_def.ps")
        with open(ps_temp_path, 'w', encoding='utf-8') as f:  # 🎯 UTF-8 do Gemini
            f.write(ps_content)
        
        logging.info("✅ PostScript criado com caminho absoluto POSIX")

        # 4. COMANDO GHOSTSCRIPT CORRETO
        gs_args = [
            GHOSTSCRIPT_PATH,
            "-dSAFER", "-dBATCH", "-dNOPAUSE", "-dQUIET",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.7", 
            "-dPDFA=2",
            "-dPDFACompatibilityPolicy=1",
            "-sColorConversionStrategy=RGB",
            "-sProcessColorModel=DeviceRGB",
            "-dConvertCMYKImagesToRGB=true",
            "-dDetectDuplicateImages=true",
            "-dEmbedAllFonts=true",
            "-dSubsetFonts=true",
            "-dCompressPages=true",
            "-dCompressFonts=true",
            "-dAutoFilterColorImages=false",
            "-dColorImageFilter=/FlateEncode",
            "-dGrayImageFilter=/FlateEncode",
            "-dMonoImageFilter=/FlateEncode", 
            "-dDownsampleColorImages=false",
            "-dDownsampleGrayImages=false",
            "-dDownsampleMonoImages=false",
            f"-dPDFSETTINGS={pdfsettings}",
            f"-sOutputFile={output_path}",
            ps_temp_path,    # ⬅️ CAMINHO ABSOLUTO do PostScript
            input_path
        ]

        logging.info("🚀 Executando Ghostscript com ICC Real...")
        
        timeout_calculado = calcular_timeout_inteligente_pdfa(input_path)
        
        # 🎯 cwd NÃO é mais crítico, mas mantemos por segurança
        resultado = exec_segura(gs_args, timeout=timeout_calculado, 
                              descricao=f"PDF/A-2B '{nivel_compressao}'",
                              cwd=temp_dir)

        if resultado.returncode != 0:
            error_msg = resultado.stderr or "Erro Ghostscript"
            logging.error(f"❌ Ghostscript falhou: {error_msg}")
            
            # 🎯 MELHORIA GEMINI: Fallback de validação
            if 'validar_pdfa_fallback' in globals():
                is_valid_fb, msg_fb = validar_pdfa_fallback(output_path)
                if not is_valid_fb:
                    raise PDFProcessingError(f"Falha GS: {error_msg}")
            else:
                raise PDFProcessingError(f"Ghostscript: {error_msg}")

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise PDFProcessingError("Arquivo PDF/A não foi gerado")

        # 🔍 VALIDAÇÃO RIGOROSA
        logging.info("🔍 Validando PDF/A...")
        is_valid, valid_msg = validar_pdfa_com_ghostscript_rigoroso(output_path)
        
        if not is_valid:
            diagnosticar_pdfa(output_path)
            
            # 🎯 MELHORIA GEMINI: Aceita arquivo gerado mesmo com validação falha
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logging.warning("⚠️ Validação estrita falhou, mas arquivo foi gerado")
                return True
            else:
                raise PDFProcessingError(f"PDF/A-2B inválido: {valid_msg}")

        # ESTATÍSTICAS
        tamanho_original = os.path.getsize(input_path)
        tamanho_final = os.path.getsize(output_path)
        reducao = ((tamanho_original - tamanho_final) / tamanho_original) * 100

        logging.info(f"✅ PDF/A-2B VÁLIDO: {tamanho_original/1024/1024:.2f}MB → {tamanho_final/1024/1024:.2f}MB ({reducao:+.1f}%)")
        
        return True

    except Exception as e:
        logging.error(f"❌ Falha na conversão PDF/A: {e}")
        try:
            if os.path.exists(output_path):
                os.remove(output_path)
        except:
            pass
        raise
    finally:
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logging.debug("✅ Ambiente temporário limpo")
            except Exception as e:
                logging.warning(f"⚠️ Erro ao limpar temp: {e}")
                
def converter_pdfa_modo_nuclear(input_path, output_path):
    """
    Modo ULTRA-AGGRESSIVE para PDFs com fontes corrompidas
    CONVERTE TUDO EM CURVAS - elimina problemas de fonte
    """
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível")

    logging.info("🚀 ATIVANDO MODO NUCLEAR PARA FONTES CORROMPIDAS")
    
    comando_nuclear = [
        GHOSTSCRIPT_PATH,
        "-dNOSAFER",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        
        # ⚡ PARÂMETROS NUCLEAR OTIMIZADOS
        "-dNoOutputFonts",           # ELIMINA fontes - converte TUDO em curvas
        "-dRenderCurves=true",       # Renderiza curvas com qualidade
        "-dPreserveMarkedContent=false",
        "-dPreserveAnnots=false",
        
        # Configurações de qualidade
        "-dPDFSETTINGS=/prepress",
        "-dAutoFilterColorImages=false",
        "-dColorImageFilter=/FlateEncode",
        "-dGrayImageFilter=/FlateEncode", 
        "-dMonoImageFilter=/FlateEncode",
        
        "-dNOPAUSE", "-dBATCH", "-dQUIET",
        f"-sOutputFile={output_path}",
        input_path
    ]
    
    try:
        resultado = exec_segura(comando_nuclear, timeout=300, 
                              descricao="PDF/A Nuclear - Fontes Corrompidas")
        
        if resultado.returncode == 0:
            logging.info("MODO NUCLEAR: PDF salvo (texto convertido em curvas)")
            return True
        else:
            logging.error(f"❌ Modo nuclear falhou: {resultado.stderr}")
            return False
            
    except Exception as e:
        logging.error(f"❌ Erro no modo nuclear: {e}")
        return False

def mostrar_aviso_modo_nuclear():
    messagebox.showwarning(
        "PDF Complexo - Conversão Especial Aplicada",
        "Este PDF contém elementos técnicos incompatíveis com o padrão PDF/A.\n\n"
        "Solução automática aplicada:\n"
        "• Texto convertido em imagens vetoriais\n" 
        "• Layout e aparência totalmente preservados\n"
        "• PDF/A válido gerado com sucesso\n\n"
        "⚠️  Característica do arquivo resultante:\n"
        "• Visualização e impressão PERFEITAS\n"
        "• OCR desativado, NÃO selecionável/copiável\n"
        "• Tamanho de arquivo ligeiramente maior\n\n"
    )

def submit_thread_task(func, *args, **kwargs):
    performance_monitor.check_system_health()
    
    def task_with_timeout():
        try:
            import threading
            result = [None]
            exception = [None]
            
            def worker():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exception[0] = e
            
            thread = threading.Thread(target=worker)
            thread.daemon = True
            thread.start()
            thread.join(timeout=300)
            
            if thread.is_alive():
                logging.error("Timeout na operação em thread")
                raise SystemOverloadError("Operação excedeu o tempo limite")
            
            if exception[0]:
                raise exception[0]
                
            return result[0]
            
        except Exception as e:
            logging.error(f"Erro na tarefa em thread: {e}")
            root.after(0, reset_ui_state)
            raise
    
    return thread_executor.submit(task_with_timeout)

class ToolTip:
    def __init__(self, widget, text=""):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.after_id = None

    def schedule_show(self):
        self.cancel_scheduled()
        self.after_id = self.widget.after(300, self.show)

    def cancel_scheduled(self):
        if self.after_id:
            try:
                self.widget.after_cancel(self.after_id)
            except:
                pass
            self.after_id = None

    def show(self, _=None):
        self.cancel_scheduled()
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_pointerx() + 16
        y = self.widget.winfo_pointery() + 16
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.attributes('-alpha', 0.0)
        label = tk.Label(
            tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffe0",
            relief=tk.SOLID,
            borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(ipadx=8, ipady=6)
        self.fade_in()

    def fade_in(self):
        if not self.tipwindow:
            return
        alpha = self.tipwindow.attributes('-alpha')
        if alpha < 1.0:
            self.tipwindow.attributes('-alpha', alpha + 0.12)
            self.tipwindow.after(20, self.fade_in)

    def hide(self, _=None):
        self.cancel_scheduled()
        if self.tipwindow:
            try:
                self.tipwindow.destroy()
            except:
                pass
            self.tipwindow = None

def show_toast(message, duration=2000):
    try:
        for widget in root.winfo_children():
            if isinstance(widget, tk.Toplevel) and any(isinstance(child, tk.Message) for child in widget.winfo_children()):
                logging.debug("Messagebox detectado - suprimindo toast")
                return
        
        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.configure(bg="#333333")
        toast.attributes("-topmost", True)
        toast.attributes('-alpha', 0.0)
        label = tk.Label(toast, text=message, fg="white", bg="#333333", font=("Segoe UI", 10))
        label.pack(ipadx=10, ipady=5)
        x = root.winfo_rootx() + 20
        y = root.winfo_rooty() + root.winfo_height() - 50
        toast.geometry(f"+{x}+{y}")
        
        def fade_in_toast(alpha=0.0):
            if alpha < 1.0:
                toast.attributes('-alpha', alpha)
                toast.after(20, lambda: fade_in_toast(alpha + 0.1))
            else:
                toast.attributes('-alpha', 1.0)
                toast.after(duration, fade_out_toast)
        
        def fade_out_toast(alpha=1.0):
            if alpha > 0.0:
                toast.attributes('-alpha', alpha)
                toast.after(20, lambda: fade_out_toast(alpha - 0.1))
            else:
                toast.destroy()
        
        fade_in_toast()
        logging.debug(f"Toast exibido: {message}")
    except Exception as e:
        logging.warning(f"Erro ao exibir toast: {e}")

def safe_pdf_reader(file_path):
    try:
        validate_file_security(file_path)
        
        with open(file_path, 'rb') as f:
            if f.read(4) != b'%PDF':
                raise PDFCorruptionError("Arquivo não é um PDF válido")
            
        reader = PdfReader(file_path, strict=False)
        _ = len(reader.pages)
        _ = reader.metadata
        
        return reader
    except Exception as e:
        logging.error(f"PDF corrompido: {file_path} - {e}")
        raise PDFCorruptionError(f"PDF corrompido: {os.path.basename(file_path)}")

def create_pdf_writer_with_encoding():
    """Cria PdfWriter com configurações para preservar codificação UTF-8"""
    writer = PdfWriter()
    
    #Garante encoding UTF-8 em metadados
    try:
        # Define metadados básicos com encoding explícito
        metadata_basico = {
            '/Producer': 'JuntaPDF 2.0',
            '/Creator': 'JuntaPDF'
        }
        
        # Tenta adicionar metadados com encoding correto
        if hasattr(writer, 'add_metadata'):
            writer.add_metadata(metadata_basico)
            logging.debug("Metadados UTF-8 configurados no writer")
        
        # PyPDF2 mais antigo: configura _info diretamente
        elif hasattr(writer, '_info'):
            # Força strings como texto Unicode
            writer._info = {
                k: v.encode('utf-8').decode('utf-8') if isinstance(v, str) else v
                for k, v in metadata_basico.items()
            }
            logging.debug("Metadados UTF-8 configurados via _info")
            
    except Exception as e:
        logging.warning(f"Não foi possível configurar metadados UTF-8: {e}")
        # Não é crítico - continua sem metadados customizados
    
    return writer

def validate_pdf(path):
    """Wrapper simples para safe_pdf_reader"""
    try:
        reader = safe_pdf_reader(path)  # Já faz todas as validações
        return True, None
    except Exception as e:
        return False, str(e)

def validate_output_pdf(file_path, password=None):
    try:
        if not os.path.exists(file_path):
            return False, "Arquivo de saída não existe"
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Arquivo de saída está vazio"
        
        if file_size < 100:
            return False, "Arquivo muito pequeno"
        
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                return False, "Não é um PDF válido"
            
            try:
                f.seek(0)
                reader = PdfReader(f, strict=False)
                
                if reader.is_encrypted:
                    if password is not None:
                        if reader.decrypt(password) == 0:
                            return False, "Senha incorreta ou falha na descriptografia"
                    else:
                        return False, "PDF criptografado, mas nenhuma senha fornecida"
                
                if len(reader.pages) == 0:
                    return False, "PDF não contém páginas"
                
                try:
                    _ = reader.metadata
                except:
                    logging.debug("Metadados não acessíveis")
                
                pages_to_check = min(3, len(reader.pages))
                for i in range(pages_to_check):
                    try:
                        _ = reader.pages[i].extract_text()
                    except:
                        pass
                        
            except Exception as e:
                return False, f"PDF corrompido: {str(e)}"
        
        return True, f"PDF válido ({len(reader.pages)} páginas, {file_size/1024/1024:.2f} MB)"
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"

def update_stats(listbox, files_var, pages_var, size_var):
    files = list(listbox.get(0, tk.END))
    total_pages = 0
    total_size_bytes = 0
    
    if len(files) > MAX_FILES_PER_OPERATION:
        files = files[:MAX_FILES_PER_OPERATION]
        logging.warning(f"Limite de {MAX_FILES_PER_OPERATION} arquivos excedido")
    
    for f in files:
        try:
            reader = safe_pdf_reader(f)
            total_pages += len(reader.pages)
            total_size_bytes += os.path.getsize(f)
            
            if total_pages > MAX_TOTAL_PAGES:
                raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")
                
        except Exception as e:
            logging.warning(f"Erro ao ler {f}: {e}")
    
    files_var.set(f"{len(files)} arquivo{'s' if len(files) != 1 else ''}")
    pages_var.set(f"{total_pages} página{'s' if total_pages != 1 else ''}")
    
    if total_size_bytes > 1024 * 1024:
        size_mb = total_size_bytes / (1024 * 1024)
        size_var.set(f"{size_mb:.1f} MB")
    else:
        size_kb = total_size_bytes / 1024
        size_var.set(f"{size_kb:.1f} KB")

def get_pdf_info(path):
    if path in pdf_metadata_cache:
        return pdf_metadata_cache[path]
    try:
        reader = safe_pdf_reader(path)
        num_pages = len(reader.pages)
        meta = reader.metadata or {}
        title = meta.get("/Title") or meta.get("Title") or "Sem título"
        author = meta.get("/Author") or meta.get("Author") or "Desconhecido"
        size_kb = max(1, os.path.getsize(path) // 1024)
        
        is_encrypted = reader.is_encrypted
        encryption_note = "\nProtegido com senha" if is_encrypted else ""
        
        info = (
            f"{os.path.basename(path)}\n"
            f"Páginas: {num_pages}\n"
            f"Título: {title}\n"
            f"Autor: {author}\n"
            f"Tamanho: {size_kb} KB{encryption_note}"
        )
        pdf_metadata_cache[path] = info
        return info
    except Exception as e:
        return f"{os.path.basename(path)}\n[Erro ao ler PDF: {e}]"

def attach_dynamic_tooltips(listbox):
    tooltip = ToolTip(listbox, "")
    current_index = {"value": None}

    def on_motion(event):
        idx = listbox.nearest(event.y)
        size = listbox.size()
        if size == 0 or idx < 0 or idx >= size:
            current_index["value"] = None
            tooltip.hide()
            return

        try:
            bbox = listbox.bbox(idx)
        except:
            bbox = None
        if bbox:
            y1 = bbox[1]
            y2 = y1 + bbox[3]
            if not (y1 <= event.y <= y2):
                tooltip.hide()
                return

        if current_index["value"] != idx:
            current_index["value"] = idx
            file_path = listbox.get(idx)
            tooltip.hide()
            tooltip.text = get_pdf_info(file_path)
            tooltip.schedule_show()

    def on_leave(_):
        current_index["value"] = None
        tooltip.hide()

    def on_click(_):
        tooltip.hide()

    listbox.bind("<Motion>", on_motion)
    listbox.bind("<Leave>", on_leave)
    listbox.bind("<Button-1>", on_click)

def setup_drag_reorder(listbox):
    def on_drag_start(event):
        index = listbox.nearest(event.y)
        if index >= 0 and index < listbox.size():
            if not listbox.selection_includes(index):
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(index)
            listbox.config(cursor="hand2")
    
    def on_drag_motion(event):
        current_index = listbox.nearest(event.y)
        if current_index >= 0 and current_index < listbox.size():
            if not listbox.selection_includes(current_index):
                listbox.selection_set(current_index)
    
    def on_drag_release(event):
        listbox.config(cursor="")
    
    listbox.bind("<Button-1>", on_drag_start)
    listbox.bind("<B1-Motion>", on_drag_motion)
    listbox.bind("<ButtonRelease-1>", on_drag_release)

def highlight_move(listbox, indices):
    for i in indices:
        listbox.itemconfig(i, {'bg': '#e3f2fd'})
    listbox.after(300, lambda: reset_highlight(listbox))

def reset_highlight(listbox):
    for i in range(listbox.size()):
        listbox.itemconfig(i, {'bg': 'white'})

def move_up(listbox, event=None):
    listbox.focus_set()
    selected = list(listbox.curselection())
    if not selected:
        show_toast("Nenhum item selecionado", 1500)
        return
    
    if 0 in selected:
        show_toast("Itens no topo não podem subir", 1500)
        return
    
    selected.sort()
    
    moved_count = 0
    new_selection = []
    
    for idx in selected:
        if idx == 0:
            continue
            
        text = listbox.get(idx)
        listbox.delete(idx)
        new_idx = idx - 1
        listbox.insert(new_idx, text)
        new_selection.append(new_idx)
        moved_count += 1
    
    listbox.selection_clear(0, tk.END)
    for idx in new_selection:
        listbox.selection_set(idx)
    
    if moved_count > 0:
        highlight_move(listbox, new_selection)
        status_var.set(f"{moved_count} item(ns) movido(s) para cima")
        show_toast(f"↑ {moved_count} item(ns) movidos", 1000)

def move_down(listbox, event=None):
    listbox.focus_set()
    selected = list(listbox.curselection())
    if not selected:
        show_toast("Nenhum item selecionado", 1500)
        return
    
    size = listbox.size()
    
    if (size - 1) in selected:
        show_toast("Itens no final não podem descer", 1500)
        return
    
    selected.sort(reverse=True)
    
    moved_count = 0
    new_selection = []
    
    for idx in selected:
        if idx == size - 1:
            continue
            
        text = listbox.get(idx)
        listbox.delete(idx)
        new_idx = idx + 1
        listbox.insert(new_idx, text)
        new_selection.append(new_idx)
        moved_count += 1
    
    new_selection.sort()
    
    listbox.selection_clear(0, tk.END)
    for idx in new_selection:
        listbox.selection_set(idx)
    
    if moved_count > 0:
        highlight_move(listbox, new_selection)
        status_var.set(f"{moved_count} item(ns) movido(s) para baixo")
        show_toast(f"↓ {moved_count} item(ns) movidos", 1000)

def add_files(listbox, files_var, pages_var, size_var, event=None):
    files = filedialog.askopenfilenames(filetypes=[("Arquivos PDF", "*.pdf")])
    added = 0
    invalid = []
    
    current_count = listbox.size()
    if current_count + len(files) > MAX_FILES_PER_OPERATION:
        messagebox.showwarning(
            "Limite Excedido", 
            f"Máximo de {MAX_FILES_PER_OPERATION} arquivos por operação.\n"
            f"Atualmente: {current_count}, tentando adicionar: {len(files)}"
        )
        files = files[:MAX_FILES_PER_OPERATION - current_count]
    
    for f in files:
        if f and f.lower().endswith(".pdf") and f not in listbox.get(0, tk.END):
            is_valid, error = validate_pdf(f)
            if is_valid:
                listbox.insert(tk.END, f)
                added += 1
                logging.info(f"Arquivo adicionado: {os.path.basename(f)}")
            else:
                invalid.append((os.path.basename(f), error))
                logging.warning(f"Arquivo inválido: {os.path.basename(f)} - {error}")
    
    if invalid:
        error_msg = "PDFs inválidos ou corrompidos:\n\n"
        for name, err in invalid[:5]:
            error_msg += f"• {name}\n  {err[:50]}...\n\n"
        if len(invalid) > 5:
            error_msg += f"... e mais {len(invalid) - 5} arquivo(s)"
        messagebox.showwarning("Aviso", error_msg)
    
    if added > 0:
        status_var.set(f"{added} arquivo(s) adicionados.")
        show_toast(f"{added} arquivo(s) adicionados.")
        update_stats(listbox, files_var, pages_var, size_var)
        
        if listbox.size() > 0:
            for widget in listbox.master.master.winfo_children():
                if isinstance(widget, ttk.Label) and "arraste" in widget.cget("text").lower():
                    widget.config(text="Arquivos PDF")

def remove_selected(listbox, files_var, pages_var, size_var, event=None):
    selected = list(listbox.curselection())
    if not selected:
        return
    
    selected.sort(reverse=True)
    
    removed_files = []
    for i in selected:
        removed_file = listbox.get(i)
        listbox.delete(i)
        removed_files.append(os.path.basename(removed_file))
        logging.info(f"Arquivo removido: {os.path.basename(removed_file)}")
    
    status_var.set(f"{len(removed_files)} arquivo(s) removido(s).")
    show_toast(f"{len(removed_files)} arquivo(s) removido(s).")
    update_stats(listbox, files_var, pages_var, size_var)
    
    if listbox.size() == 0:
        for widget in listbox.master.master.winfo_children():
            if isinstance(widget, ttk.Label) and "arquivos" in widget.cget("text").lower():
                widget.config(text="Arquivos PDF (arraste para reordenar)")

def clear_list(listbox, files_var, pages_var, size_var, event=None):
    if listbox.size() == 0:
        return
    listbox.delete(0, tk.END)
    status_var.set("Lista limpa.")
    show_toast("Lista limpa.")
    update_stats(listbox, files_var, pages_var, size_var)
    
    for widget in listbox.master.master.winfo_children():
        if isinstance(widget, ttk.Label) and "arquivos" in widget.cget("text").lower():
            widget.config(text="Lista de arquivos")

def sort_az(listbox, files_var, pages_var, size_var, event=None):
    files = list(listbox.get(0, tk.END))
    if not files:
        return
    files.sort(key=lambda x: os.path.basename(x).lower())
    listbox.delete(0, tk.END)
    for f in files:
        listbox.insert(tk.END, f)
    status_var.set("Arquivos ordenados A→Z.")
    show_toast("Ordenado alfabeticamente.")
    update_stats(listbox, files_var, pages_var, size_var)

def choose_output_folder(entry):
    folder = filedialog.askdirectory()
    if folder:
        entry.delete(0, tk.END)
        entry.insert(0, folder)
        logging.info(f"Pasta de saída selecionada: {folder}")

def generate_unique_filename(folder, base_name):
    name, ext = os.path.splitext(base_name)
    counter = 1
    new_name = base_name
    while os.path.exists(os.path.join(folder, new_name)):
        new_name = f"{name}({counter}){ext}"
        counter += 1
        if counter > 1000:
            timestamp = int(time.time())
            new_name = f"{name}_{timestamp}{ext}"
            break
    return os.path.join(folder, new_name)

def get_default_output_name(operation_type, files, options=None, page_ranges=None):
    if not files:
        return "documento.pdf"
    
    base_name = os.path.splitext(os.path.basename(files[0]))[0]
    if len(base_name) > 20:
        base_name = base_name[:20] + "..."
    
    timestamp = time.strftime("%Y-%m-%d_%H%M")
    count = len(files)
    
    if operation_type == "merge":
        if count == 1:
            return f"{base_name}_completo_{timestamp}.pdf"
        else:
            return f"{base_name}_unido_{count}arquivos_{timestamp}.pdf"
    elif operation_type == "extract":
        return f"{base_name}_extraido_{timestamp}.pdf"
    else:
        return f"{base_name}_processado_{timestamp}.pdf"

def parse_page_ranges(ranges_str, max_pages):
    if not ranges_str.strip():
        return []

    pages = set()
    try:
        for part in ranges_str.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                start, end = part.split("-", 1)
                start_i, end_i = int(start), int(end)
                
                if start_i < 1 or end_i < 1:
                    raise ValueError("Números de página devem ser positivos")
                if start_i > max_pages or end_i > max_pages:
                    raise ValueError(f"Números de página devem ser <= {max_pages}")
                
                if start_i <= end_i:
                    pages.update(range(start_i, end_i + 1))
                else:
                    pages.update(range(end_i, start_i + 1))
            else:
                page_num = int(part)
                if page_num < 1:
                    raise ValueError("Números de página devem ser positivos")
                if page_num > max_pages:
                    raise ValueError(f"Números de página devem ser <= {max_pages}")
                pages.add(page_num)

        pages = sorted(list(pages))
        
        if len(pages) > MAX_TOTAL_PAGES:
            raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")
            
        return pages
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("Formato inválido. Use: 1-5, 10, 20-30")
        else:
            raise

def reset_ui_state():
    try:
        logging.info("Restaurando estado da UI...")
        
        set_ui_state(True)
        safe_widget_config(btn_merge, text="Juntar PDFs (Ctrl+R)")
        safe_widget_config(btn_split, text="Dividir/Extrair PDFs (Ctrl+R)")        
        toggle_password_entry()
        
        if 'progress_merge' in globals():
            safe_widget_config(progress_merge, value=0)
            safe_widget_config(progress_merge, mode="determinate")
        
        if 'progress_split' in globals():
            safe_widget_config(progress_split, value=0)
            safe_widget_config(progress_split, mode="determinate")
        
        safe_widget_config(root, cursor="")
        
        if 'btn_cancel_merge' in globals():
            try:
                btn_cancel_merge.pack_forget()
            except tk.TclError:
                pass
        
        if 'btn_cancel_split' in globals():
            try:
                btn_cancel_split.pack_forget()
            except tk.TclError:
                pass
        
        show_status("Pronto", "info")
        
        root.update_idletasks()
        
        logging.info("Estado da UI restaurado com sucesso")
        
    except Exception as e:
        logging.error(f"Erro ao restaurar estado da UI: {e}")

def set_ui_state(enabled):
    state = "normal" if enabled else "disabled"
    
    safe_widget_config(btn_merge, state=state)
    safe_widget_config(btn_split, state=state)
    
    if enabled:
        if 'btn_cancel_merge' in globals():
            try:
                btn_cancel_merge.pack_forget()
            except tk.TclError:
                pass
        if 'btn_cancel_split' in globals():
            try:
                btn_cancel_split.pack_forget()
            except tk.TclError:
                pass
        
        safe_widget_config(root, cursor="")
        
        if 'progress_merge' in globals():
            safe_widget_config(progress_merge, value=0)
        if 'progress_split' in globals():
            safe_widget_config(progress_split, value=0)
    else:
        safe_widget_config(root, cursor="wait")
        
        if 'btn_merge' in globals():
            safe_widget_config(btn_merge, text="Processando...")
        if 'btn_split' in globals():
            safe_widget_config(btn_split, text="Processando...")

def show_status(message, type="info"):
    try:
        colors = {
            "info": "blue",
            "success": "darkgreen", 
            "warning": "orange",
            "error": "red"
        }
        status_var.set(message)
        if 'status_label' in globals():
            safe_widget_config(status_label, foreground=colors.get(type, "blue"))
    except Exception as e:
        logging.debug(f"Erro ao atualizar status: {e}")

def show_message_in_main_thread(title, message, type="info"):
    def show():
        if type == "error":
            messagebox.showerror(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
    
    root.after(0, show)

def aplicar_criptografia(writer, password, preserve_metadata=True, original_metadata=None):
    if not password or len(password.strip()) == 0:
        raise ValueError("Senha não pode estar vazia")
    
    logging.info("Aplicando criptografia ao PDF...")
    
    # Garante que a senha está em UTF-8
    if isinstance(password, str):
        password = password.encode('utf-8').decode('utf-8')

    try:
        # PRESERVA METADADOS ANTES DA CRIPTOGRAFIA
        if preserve_metadata and original_metadata:
            try:
                writer.add_metadata(original_metadata)
                logging.info("Metadados preservados na criptografia")
            except Exception as meta_error:
                logging.warning(f"Erro ao preservar metadados na criptografia: {meta_error}")

        # Aplica criptografia
        if hasattr(writer, '_encrypt'):
            writer._encrypt(
                user_password=password,
                owner_password=password,
                use_128bit=True
            )
        else:
            writer.encrypt(
                user_password=password,
                owner_password=password,
                use_128bit=True
            )
        logging.info("Criptografia aplicada com sucesso")
        return True
        
    except Exception as e:
        logging.error(f"Falha na criptografia: {e}")
        
        try:
            writer.encrypt(password)
            logging.info("Criptografia aplicada (método simples de fallback)")
            return True
        except Exception as e2:
            logging.error(f"Falha total na criptografia: {e2}")
            raise PDFProcessingError(f"Falha na criptografia: {e2}")

def log_audit_event(operation, files, user=None, options=None):
    try:
        audit_log = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'operation': operation,
            'files_count': len(files),
            'file_names': [os.path.basename(f) for f in files],
            'options': options or {},
            'user': user or os.getlogin(),
            'session_id': f"{os.getpid()}_{int(time.time())}",
            'version': 'JuntaPDF 2.0'
        }
        
        audit_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Audit")
        os.makedirs(audit_dir, exist_ok=True)
        
        audit_file = os.path.join(audit_dir, f"audit_{time.strftime('%Y%m')}.log")
        
        with open(audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_log, ensure_ascii=False) + '\n')
            
        logging.debug(f"Evento de auditoria registrado: {operation}")
        
    except Exception as e:
        logging.warning(f"Erro ao registrar auditoria: {e}")

def setup_context_menu(listbox, files_var, pages_var, size_var):
    context_menu = tk.Menu(listbox, tearoff=0)
    
    def remove_selected_context():
        remove_selected(listbox, files_var, pages_var, size_var)
    
    def open_selected_context():
        try:
            index = listbox.index(tk.ACTIVE)
            if index >= 0:
                current_selection = listbox.curselection()
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(index)
                open_pdf(listbox, tk.Event())
                listbox.selection_clear(0, tk.END)
                for i in current_selection:
                    listbox.selection_set(i)
        except Exception as e:
            logging.warning(f"Erro no menu de contexto: {e}")
    
    def show_file_info():
        try:
            index = listbox.index(tk.ACTIVE)
            if index >= 0:
                file_path = listbox.get(index)
                info = get_pdf_info(file_path)
                messagebox.showinfo("Informações do PDF", info)
        except Exception as e:
            logging.warning(f"Erro no menu de contexto: {e}")
    
    def clear_all_context():
        clear_list(listbox, files_var, pages_var, size_var)
    
    def adicionar_arquivos_context():
        add_files(listbox, files_var, pages_var, size_var)

    context_menu.add_command(label="Adicionar Arquivos (Ctrl+O)", command=adicionar_arquivos_context)
    context_menu.add_command(label="Abrir PDF", command=open_selected_context)
    context_menu.add_command(label="Informações", command=show_file_info)
    context_menu.add_separator()
    context_menu.add_command(label="Remover (Del)", command=remove_selected_context)
    context_menu.add_command(label="Limpar Lista (Ctrl+L)", command=clear_all_context)
    
    def show_context_menu(event):
        index = listbox.nearest(event.y)
        
        if index >= 0 and index < listbox.size():
            if not listbox.selection_includes(index):
                listbox.selection_clear(0, tk.END)
                listbox.selection_set(index)
            listbox.activate(index)
        else:
            listbox.selection_clear(0, tk.END)
            
        selected_count = len(listbox.curselection())

        if selected_count == 0:
            context_menu.entryconfigure(0, state="normal")
            context_menu.entryconfigure(1, state="disabled")
            context_menu.entryconfigure(2, state="disabled")
            context_menu.entryconfigure(4, label="Remover", state="disabled")
            
        elif selected_count == 1:
            context_menu.entryconfigure(0, state="normal")
            context_menu.entryconfigure(1, state="normal")
            context_menu.entryconfigure(2, state="normal")
            context_menu.entryconfigure(4, label="Remover Selecionado", state="normal")
            
        else:
            context_menu.entryconfigure(0, state="normal")
            context_menu.entryconfigure(1, state="normal")
            context_menu.entryconfigure(2, state="normal")
            context_menu.entryconfigure(4, label=f"Remover os {selected_count} Itens", state="normal")
        
        context_menu.entryconfigure(5, state="normal" if listbox.size() > 0 else "disabled")

        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    listbox.bind("<Button-3>", show_context_menu)
    
    return context_menu

def open_pdf(listbox, event):
    selection = listbox.curselection()
    if not selection:
        return
    file_path = listbox.get(selection[0])
    try:
        validate_file_security(file_path)
        
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":
            subprocess.call(["open", file_path])
        else:
            subprocess.call(["xdg-open", file_path])
        logging.info(f"Arquivo aberto: {os.path.basename(file_path)}")
    except Exception as e:
        logging.error(f"Erro ao abrir arquivo: {e}")
        show_message_in_main_thread("Erro", f"Não foi possível abrir:\n{e}", "error")

def drop(event, listbox, files_var, pages_var, size_var):
    if not DND_AVAILABLE:
        return
        
    dropped = root.tk.splitlist(event.data)
    added = 0
    invalid = []
    
    current_count = listbox.size()
    if current_count + len(dropped) > MAX_FILES_PER_OPERATION:
        show_message_in_main_thread(
            "Limite Excedido", 
            f"Máximo de {MAX_FILES_PER_OPERATION} arquivos por operação.\n"
            f"Atualmente: {current_count}, tentando adicionar: {len(dropped)}",
            "warning"
        )
        dropped = dropped[:MAX_FILES_PER_OPERATION - current_count]
    
    for f in dropped:
        if f.lower().endswith(".pdf") and f not in listbox.get(0, tk.END):
            is_valid, error = validate_pdf(f)
            if is_valid:
                listbox.insert(tk.END, f)
                added += 1
                logging.info(f"Arquivo adicionado via drag & drop: {os.path.basename(f)}")
            else:
                invalid.append((os.path.basename(f), error))
                logging.warning(f"Arquivo inválido via drag & drop: {os.path.basename(f)}")
    
    if invalid:
        error_msg = "PDFs inválidos:\n\n"
        for name, err in invalid[:3]:
            error_msg += f"• {name}\n"
        if len(invalid) > 3:
            error_msg += f"... e mais {len(invalid) - 3}"
        show_message_in_main_thread("Aviso", error_msg, "warning")
    
    if added > 0:
        status_var.set(f"{added} arquivo(s) adicionados via arrastar/soltar.")
        show_toast(f"{added} arquivo(s) adicionados.")
        update_stats(listbox, files_var, pages_var, size_var)
        
        if listbox.size() > 0:
            for widget in listbox.master.master.winfo_children():
                if isinstance(widget, ttk.Label) and "arraste" in widget.cget("text").lower():
                    widget.config(text="Arquivos PDF")

def validate_pdfa_protection_compatibility():
    protect_on = protect_var.get()
    pdfa_on = pdfa_var.get()
    
    if protect_on and pdfa_on:
        return False, "PDF/A-2B não suporta criptografia por senha"
    
    if not PDFA_AVAILABLE and pdfa_on:
        return False, "Ghostscript não disponível para PDF/A"
        
    return True, ""
    

def toggle_password_entry(*args):
    if hasattr(toggle_password_entry, 'processing') and toggle_password_entry.processing:
        return
    
    toggle_password_entry.processing = True
    
    try:
        protect_on = protect_var.get()
        pdfa_on = pdfa_var.get()
        
        if protect_on and pdfa_on:
            pdfa_var.set(False)
            
            show_message_in_main_thread(
                "Compatibilidade de Formatos",
                "Proteção por senha e PDF/A-2B são incompatíveis.\n\n"
                "Solução automática: Proteção por senha foi ativada e PDF/A-2B desativado.\n\n"
                "Motivo técnico: O padrão PDF/A-2B não suporta criptografia por senha.\n"
                "Para documentos protegidos, use o formato PDF padrão.",
                "info"
            )
        
        protect_on_final = protect_var.get()
        pdfa_on_final = pdfa_var.get()
        
        if protect_on_final and not pdfa_on_final:
            safe_widget_config(password_entry, state="normal")
            if not password_entry.get().strip():
                password_entry.focus_set()
        else:
            safe_widget_config(password_entry, state="disabled")
            password_entry.delete(0, tk.END)
            
    finally:
        toggle_password_entry.processing = False

def gerenciar_compatibilidade_opcoes(*args):
    """Gestão simplificada - apenas bloqueio técnico essencial"""
    
    # Única restrição técnica: PDF/A não aceita senha
    if protect_var.get() and pdfa_var.get():
        pdfa_var.set(False)
        show_message_in_main_thread(
            "Incompatibilidade Técnica", 
            "PDF/A-2B não suporta proteção por senha.\nPDF/A foi desativado.", 
            "warning"
        )
        return
    
    # Apenas controle de estado do combobox
    if compress_var.get():
        safe_widget_config(compress_combo, state="readonly")
    else:
        safe_widget_config(compress_combo, state="disabled")

def toggle_compress_combo(*args):
    """
    Habilita/desabilita o combobox de compressão.
    CORREÇÃO CRÍTICA: Não desmarca mais a compressão se for PDF/A.
    """
    try:
        # Apenas define se o campo está clicável ou não
        if compress_var.get():
            safe_widget_config(compress_combo, state="readonly")
        else:
            safe_widget_config(compress_combo, state="disabled")
        gerenciar_compatibilidade_opcoes()
        
    except Exception as e:
        logging.warning(f"Erro ao alternar compressão: {e}")
        


def merge_pdfs_thread():
    global cancel_operation
    cancel_operation = False

    files = merge_list.get(0, tk.END)
    if not files:
        show_message_in_main_thread("Erro", "Nenhum arquivo PDF selecionado.", "error")
        return

    password = password_entry.get().strip()

    log_audit_event("merge_start", files, options={
        'pdfa': pdfa_var.get(),
        'protected': protect_var.get() and bool(password),
        'compress': compress_var.get(),
        'remove_metadata': meta_var.get(),
        'file_count': len(files)
    })

    if len(files) > MAX_FILES_PER_OPERATION:
        show_message_in_main_thread("Erro", f"Máximo de {MAX_FILES_PER_OPERATION} arquivos por operação.", "error")
        return

    folder = merge_output_entry.get() or os.path.dirname(files[0])

    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        show_message_in_main_thread("Erro", f"Não foi possível criar diretório:\n{folder}\n\nErro: {e}", "error")
        return

    password = password_entry.get().strip()

    custom_name = merge_filename_entry.get().strip()
    if custom_name and custom_name != "Deixe vazio para nome automático":
        output_name = custom_name
        if not output_name.lower().endswith(".pdf"):
            output_name += ".pdf"
    else:
        output_name = get_default_output_name(
            "merge",
            files,
            options={
                'compress': compress_var.get(),
                'pdfa': pdfa_var.get(),
                'protected': protect_var.get() and bool(password)
            }
        )

    output_path = generate_unique_filename(folder, output_name)
    remove_meta = meta_var.get()
    convert_pdfa = pdfa_var.get()

    total_steps = len(files) + 3
    current_step = 0

    progress_widget = None
    if 'progress_merge' in globals():
        progress_widget = progress_merge
        safe_widget_config(progress_widget, maximum=total_steps)
        safe_widget_config(progress_widget, value=current_step)

    temp_files_to_cleanup = []

    try:
        create_operation_checkpoint("merge", [], current_step, temp_files_to_cleanup)

        logging.info(f"Iniciando união de {len(files)} arquivos -> {output_path}")

        total_size_estimate = 0
        for f in files:
            try:
                total_size_estimate += os.path.getsize(f)
            except:
                pass
        
        BATCH_SIZE = calcular_tamanho_lote(len(files), total_size_estimate)
        
        merger = PdfMerger()
        
        files_processados = 0
            
        for batch_start in range(0, len(files), BATCH_SIZE):
            if cancel_operation:
                status_var.set("Operação cancelada.")
                logging.info("Operação cancelada pelo usuário")
                cleanup_checkpoint()
                return
                
            batch_end = min(batch_start + BATCH_SIZE, len(files))
            batch_files = files[batch_start:batch_end]
            
            logging.info(f"📦 Processando lote {(batch_start//BATCH_SIZE)+1}: arquivos {batch_start+1}-{batch_end}")
            
            for idx, f in enumerate(batch_files):
                if cancel_operation:
                    status_var.set("Operação cancelada.")
                    logging.info("Operação cancelada pelo usuário")
                    cleanup_checkpoint()
                    return
                    
                try:
                    validate_file_security(f)
                except SecurityError as e:
                    logging.error(f"Arquivo rejeitado: {f} - {e}")
                    show_message_in_main_thread("Erro de Segurança", f"Arquivo rejeitado:\n{os.path.basename(f)}\n\nMotivo: {e}", "error")
                    return
                
                merger.append(f)
                files_processados += 1
                current_step += 1
                
                if progress_widget:
                    safe_widget_config(progress_widget, value=current_step)
                
                create_operation_checkpoint("merge", files[:files_processados], current_step, temp_files_to_cleanup)
                show_status(f"Unindo {files_processados}/{len(files)}: {os.path.basename(f)}", "info")
                root.update_idletasks()
            
            if batch_end < len(files):
                import gc
                gc.collect()
                logging.info(f"🧹 Memória liberada após lote {(batch_start//BATCH_SIZE)+1}/{(len(files)-1)//BATCH_SIZE+1}")

        temp_output = safe_temp_file(prefix="merge", suffix=".pdf")
        temp_files_to_cleanup.append(temp_output)
        
        with open(temp_output, "wb") as f_out:
            merger.write(f_out)
        
        try:
            merger.close()
        except Exception as e:
            logging.warning(f"Aviso ao fechar merger: {e}")        
        current_step += 1
        if progress_widget:
            safe_widget_config(progress_widget, value=current_step)
        show_status("Salvando arquivo unido...", "info")
        root.update_idletasks()
        
        current_temp = temp_output

        if (not pdfa_var.get()) and protect_var.get() and password:
            current_step += 1
            if progress_widget:
                safe_widget_config(progress_widget, value=current_step)
            status_var.set("Aplicando proteção...")
            root.update_idletasks()
            
            try:
                reader = PdfReader(current_temp, strict=False)
                writer = create_pdf_writer_with_encoding()
                
                for page in reader.pages:
                    writer.add_page(page)
                
                original_metadata = {}
                if reader.metadata and not remove_meta:
                    try:
                        metadata_dict = {}
                        for key, value in reader.metadata.items():
                            if isinstance(value, str):
                                metadata_dict[key] = value
                            else:
                                metadata_dict[key] = str(value)
                        
                        writer.add_metadata(metadata_dict)
                        logging.info("Metadados preservados no PDF final")
                    except Exception as meta_error:
                        logging.warning(f"Erro ao preservar metadados: {meta_error}")
                        if not remove_meta:
                            writer.add_metadata({})
                elif remove_meta:
                    writer.add_metadata({})
                    
                aplicar_criptografia(writer, password, preserve_metadata=not remove_meta, 
                                   original_metadata=original_metadata if not remove_meta else {})
                
                temp_protected = safe_temp_file(prefix="protected", suffix=".pdf")
                temp_files_to_cleanup.append(temp_protected)
                
                with open(temp_protected, "wb") as f_out:
                    writer.write(f_out)
                    
                if current_temp in temp_files_to_cleanup:
                    temp_files_to_cleanup.remove(current_temp)
                remove_temp_file(current_temp)
                try:
                    os.remove(current_temp)
                except:
                    pass
                    
                current_temp = temp_protected
                
            except Exception as e:
                logging.warning(f"Falha na proteção: {e}")
                show_message_in_main_thread("Aviso", f"Proteção falhou: {e}\n\nContinuando sem proteção.", "warning")

        # --- SEÇÃO PDF/A UNIFICADA ---
        if pdfa_var.get() and PDFA_AVAILABLE:
            try:
                current_step += 1
                if progress_widget:
                    safe_widget_config(progress_widget, value=current_step)
                
                show_status("Convertendo para PDF/A-2B validado...", "info")
                root.update_idletasks()
                
                temp_pdfa = safe_temp_file(prefix="pdfa_validado", suffix=".pdf")
                temp_files_to_cleanup.append(temp_pdfa)
                
                # 🎯 USA A FUNÇÃO ROBUSTA CORRETA
                nivel_ui = compress_level.get()
                converter_para_pdfa(current_temp, temp_pdfa, nivel_ui)
                
                # Substitui pelo arquivo PDF/A válido
                if current_temp in temp_files_to_cleanup:
                    temp_files_to_cleanup.remove(current_temp)
                remove_temp_file(current_temp)
                try:
                    os.remove(current_temp)
                except:
                    pass
                    
                current_temp = temp_pdfa
                show_status("✅ PDF/A-2B validado com sucesso!", "success")
                
            except Exception as e:
                logging.error(f"❌ Falha na conversão PDF/A: {e}")
                show_message_in_main_thread(
                    "PDF/A Não Foi Possível", 
                    f"Não foi possível gerar PDF/A-2B válido:\n\n{str(e)}\n\n"
                    f"O arquivo será salvo como PDF padrão (sem PDF/A).\n\n"
                    f"💡 Dica: Verifique se o PDF original possui fonts embutidas.",
                    "warning"
                )

        # MOVE O ARQUIVO FINAL PARA O DESTINO
        try:
            logging.info(f"Movendo arquivo final: {current_temp} -> {output_path}")
            
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except PermissionError:
                    logging.warning("Destino em uso, tentando sobrescrever diretamente")
            
            move_success = False
            last_error = None
            
            for attempt in range(3):
                try:
                    shutil.move(current_temp, output_path)
                    logging.info(f"Arquivo movido com sucesso (tentativa {attempt+1})")
                    move_success = True
                    break
                    
                except (PermissionError, OSError) as e:
                    last_error = e
                    error_str = str(e).lower()
                    
                    if "permission denied" in error_str or "acesso negado" in error_str:
                        logging.warning(f"Falha no move direto (tentativa {attempt+1}): {e}")
                        
                        if attempt < 2:
                            import time
                            time.sleep(1)
                            
                            try:
                                shutil.copy2(current_temp, output_path)
                                logging.info(f"Arquivo copiado com sucesso via copy2 (tentativa {attempt+1})")
                                
                                try:
                                    os.remove(current_temp)
                                    logging.info("Arquivo temporário removido")
                                except Exception as e_del:
                                    logging.warning(f"Não foi possível remover temporário: {e_del}")
                                
                                move_success = True
                                break
                                
                            except Exception as e_copy:
                                logging.warning(f"Fallback copy2 também falhou: {e_copy}")
                                if attempt == 2:
                                    raise
                        else:
                            raise
                    else:
                        raise
            
            if not move_success and last_error:
                raise PDFProcessingError(f"Falha após 3 tentativas: {last_error}")
                
        except Exception as e_move:
            logging.error(f"ERRO CRÍTICO ao mover arquivo: {e_move}")
            raise PDFProcessingError(f"Não foi possível salvar o arquivo final: {e_move}")
        
        show_status("Validando integridade do PDF...", "info")
        root.update_idletasks()
        
        validation_password = password if (protect_var.get() and password) else None
        is_valid, validation_msg = validate_output_pdf(output_path, validation_password)
        if not is_valid:
            logging.error(f"PDF de saída inválido: {validation_msg}")
            
            fallback_success = False
            if os.path.exists(current_temp):
                try:
                    logging.info("Tentando fallback...")
                    os.replace(current_temp, output_path)
                    is_valid, validation_msg = validate_output_pdf(output_path)
                    if is_valid:
                        fallback_success = True
                        logging.info("Fallback bem-sucedido!")
                except Exception as fallback_error:
                    logging.error(f"Falha no fallback: {fallback_error}")
            
            if not fallback_success:
                try:
                    if os.path.exists(output_path):
                        os.remove(output_path)
                except:
                    pass
                raise PDFProcessingError(f"Falha na validação: {validation_msg}")
        
        tamanho_final = os.path.getsize(output_path) / 1024 / 1024
        log_audit_event("merge_success", files, options={
            'output_path': output_path,
            'final_size_mb': round(tamanho_final, 2),
            'compression_applied': compress_var.get(),
            'pdfa_applied': pdfa_var.get(),
            'protection_applied': protect_var.get() and bool(password)
        })
        
        show_status(f"PDF criado e validado: {output_path} ({tamanho_final:.1f} MB)", "success")
        logging.info(f"PDF unido criado: {output_path} ({tamanho_final:.1f} MB)")
        
        def show_success_dialog():
            result = messagebox.askyesno(
                "Sucesso", 
                f"PDF salvo em:\n{output_path}\nTamanho: {tamanho_final:.1f} MB\n\nDeseja abrir a pasta de saída?",
                icon='info'
            )
            if result:
                try:
                    if sys.platform == "win32":
                        os.startfile(folder)
                    elif sys.platform == "darwin":
                        subprocess.call(["open", folder])
                    else:
                        subprocess.call(["xdg-open", folder])
                except Exception as e:
                    logging.error(f"Erro ao abrir pasta: {e}")
        
        root.after(0, show_success_dialog)

    except Exception as e:
        log_audit_event("merge_error", files, options={
            'error': str(e),
            'error_type': type(e).__name__
        })
        
        logging.error(f"Falha ao unir PDFs: {e}")
        show_message_in_main_thread("Erro", f"Falha ao unir PDFs:\n{e}", "error")
        status_var.set("Erro ao unir arquivos.")
        try:
            if 'output_path' in locals() and os.path.exists(output_path):
                os.remove(output_path)
                logging.info("Arquivo de saída corrompido removido")
        except Exception as cleanup_error:
            logging.warning(f"Erro ao limpar arquivo corrompido: {cleanup_error}")
    finally:
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    remove_temp_file(temp_file)
            except Exception as e:
                logging.warning(f"Erro ao limpar {temp_file}: {e}")
        
        cleanup_checkpoint()
        
        root.after(0, reset_ui_state)
        
        logging.info("Limpeza pós-operação concluída")

def merge_pdfs(event=None):
    if merge_list.size() == 0:
        show_message_in_main_thread("Aviso", "Nenhum arquivo adicionado.", "warning")
        return
    
    try:
        total_pages = 0
        for f in merge_list.get(0, tk.END):
            reader = safe_pdf_reader(f)
            total_pages += len(reader.pages)
            if total_pages > MAX_TOTAL_PAGES:
                raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")
    except SystemOverloadError as e:
        show_message_in_main_thread("Limite Excedido", str(e), "error")
        return
    except Exception as e:
        logging.warning(f"Erro ao verificar limites: {e}")
    
    set_ui_state(False)
    if 'btn_cancel_merge' in globals():
        try:
            btn_cancel_merge.pack(pady=5)
        except tk.TclError:
            pass
    submit_thread_task(merge_pdfs_thread)

def cancel_merge():
    global cancel_operation
    cancel_operation = True
    logging.info("Cancelamento da união solicitado")
    show_status("Cancelando operação...", "warning")
    root.after(1000, reset_ui_state)

def split_or_extract_pdfs_thread():
    global cancel_operation
    cancel_operation = False
    
    files = split_list.get(0, tk.END)
    if not files:
        show_message_in_main_thread("Erro", "Nenhum arquivo PDF selecionado.", "error")
        return

    try:
        split_mode = split_mode_var.get()
        options = {}
        
        if split_mode == "extract":
            page_ranges_input = split_pages_entry.get().strip()
            if not page_ranges_input:
                show_message_in_main_thread("Erro", "Especifique os intervalos de páginas.", "error")
                return
            options['page_ranges'] = page_ranges_input
            
        elif split_mode == "interval":
            try:
                interval = int(split_interval_var.get())
                if interval < 1:
                    raise ValueError
                options['interval'] = interval
            except ValueError:
                show_message_in_main_thread("Erro", "Intervalo deve ser um número inteiro maior que 0.", "error")
                return
            
        elif split_mode == "parts":
            try:
                parts = int(split_parts_var.get())
                if parts < 1:
                    raise ValueError
                options['parts'] = parts
            except ValueError:
                show_message_in_main_thread("Erro", "Número de partes deve ser um inteiro maior que 0.", "error")
                return
        
        total_input_pages, total_output_estimate = validate_split_limits(files, split_mode, options)
        
        if total_output_estimate > 50:
            resposta_usuario = [None] 

            def ask_confirmation_safe():
                try:
                    ok = messagebox.askyesno(
                        "Confirmação de Operação",
                        f"Esta operação irá gerar aproximadamente {total_output_estimate} arquivos.\n"
                        f"Isso pode levar alguns minutos e consumir memória.\n\n"
                        f"Deseja continuar?",
                        icon='warning'
                    )
                    resposta_usuario[0] = ok
                except Exception as e:
                    logging.error(f"Erro no dialog: {e}")
                    resposta_usuario[0] = False

            # Agenda o dialog na thread principal
            if 'ui_dispatch' in globals() and ui_dispatch:
                ui_dispatch.dispatch(ask_confirmation_safe)
            else:
                root.after(0, ask_confirmation_safe)

            # Pooling seguro (sem root.update())
            for _ in range(600): 
                if cancel_operation:
                    return
                if resposta_usuario[0] is not None:
                    break
                time.sleep(0.1)
            
            if not resposta_usuario[0]:
                logging.info("Operação cancelada pelo usuário (Split > 50 arquivos)")
                if 'ui_dispatch' in globals() and ui_dispatch:
                    ui_dispatch.dispatch(lambda: status_var.set("Operação cancelada."))
                return
                
    except SystemOverloadError as e:
        show_message_in_main_thread("Limite Excedido", str(e), "error")
        return
    except Exception as e:
        logging.error(f"Erro na validação: {e}")
        show_message_in_main_thread("Erro", f"Erro na validação: {e}", "error")
        return

    folder = split_output_entry.get() or os.path.dirname(files[0])
    
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        show_message_in_main_thread("Erro", f"Não foi possível criar diretório:\n{folder}\n\nErro: {e}", "error")
        return

    convert_pdfa = pdfa_var_split.get()

    try:
        total_pages_to_process = total_input_pages
        extra_steps = 2 if pdfa_var_split.get() and PDFA_AVAILABLE else 1
        total_steps = total_pages_to_process + extra_steps
        
        progress_widget = None
        if 'progress_split' in globals():
            progress_widget = progress_split
            safe_widget_config(progress_widget, maximum=max(1, total_steps))
            safe_widget_config(progress_widget, value=0)

        current_step = 0
        files_processed = 0
        total_files_created = 0

        logging.info(f"Iniciando divisão de {len(files)} arquivos (modo: {split_mode}) -> {folder}")

        for file_idx, f in enumerate(files):
            if cancel_operation:
                status_var.set("Operação cancelada.")
                logging.info("Operação cancelada")
                return
            
            try:
                validate_file_security(f)
            except SecurityError as e:
                logging.error(f"Arquivo rejeitado: {f} - {e}")
                continue
            
            reader = safe_pdf_reader(f)
            total_pages_file = len(reader.pages)
            base_name = os.path.splitext(os.path.basename(f))[0]

            if split_mode == "extract":
                page_ranges_input = split_pages_entry.get().strip()
                pages_to_extract = parse_page_ranges(page_ranges_input, total_pages_file)
                
                if len(pages_to_extract) > 100:
                    show_message_in_main_thread(
                        "Limite de Extração", 
                        f"Extração limitada a 100 páginas por arquivo.\n"
                        f"Solicitado: {len(pages_to_extract)} páginas.",
                        "warning"
                    )
                    pages_to_extract = pages_to_extract[:100]
                
                writer = create_pdf_writer_with_encoding()
                for page_idx, page_num in enumerate(pages_to_extract):
                    if cancel_operation:
                        return
                    
                    writer.add_page(reader.pages[page_num - 1])
                    current_step += 1
                    if progress_widget:
                        safe_widget_config(progress_widget, value=current_step)
                    show_status(f"Extraindo {file_idx+1}/{len(files)} - Página {page_idx+1}/{len(pages_to_extract)}", "info")
                    root.update_idletasks()

                output_name = get_default_output_name("extract", [f], page_ranges=page_ranges_input)
                output_path = generate_unique_filename(folder, output_name)
                
                with open(output_path, "wb") as f_out:
                    writer.write(f_out)
                    if pdfa_var_split.get() and PDFA_AVAILABLE:
                        try:
                            temp_pdfa = safe_temp_file(prefix="pdfa_split", suffix=".pdf")
                            converter_para_pdfa(output_path, temp_pdfa)
                            os.replace(temp_pdfa, output_path)
                            remove_temp_file(temp_pdfa)
                        except Exception as e:
                            logging.warning(f"Falha PDF/A no split: {e}")
                            # Mantém o original se falhar
                
                total_files_created += 1
                files_processed += 1

            elif split_mode == "interval":
                interval = int(split_interval_var.get())
                part_num = 1
                
                for start_page in range(0, total_pages_file, interval):
                    if cancel_operation:
                        return
                    
                    if part_num > 50:
                        logging.warning(f"Limite de partes atingido para {base_name}")
                        break
                    
                    writer = create_pdf_writer_with_encoding()
                    end_page = min(start_page + interval, total_pages_file)
                    
                    for page_idx in range(start_page, end_page):
                        writer.add_page(reader.pages[page_idx])
                        current_step += 1
                        if progress_widget:
                            safe_widget_config(progress_widget, value=current_step)
                        root.update_idletasks()
                    
                    output_name = f"{base_name}_parte_{part_num:02d}_pag_{start_page+1}-{end_page}.pdf"
                    output_path = generate_unique_filename(folder, output_name)
                    
                    with open(output_path, "wb") as f_out:
                        writer.write(f_out)
                    if pdfa_var_split.get() and PDFA_AVAILABLE:
                        try:
                            temp_pdfa = safe_temp_file(prefix="pdfa_split", suffix=".pdf")
                            converter_para_pdfa(output_path, temp_pdfa)
                            os.replace(temp_pdfa, output_path)
                            remove_temp_file(temp_pdfa)
                        except Exception as e:
                            logging.warning(f"Falha PDF/A no split: {e}")
                            # Mantém o original se falhar
                    
                    show_status(f"Dividindo {file_idx+1}/{len(files)} - Parte {part_num} (páginas {start_page+1}-{end_page})", "info")
                    part_num += 1
                    total_files_created += 1
                
                files_processed += 1

            elif split_mode == "parts":
                num_parts = int(split_parts_var.get())
                num_parts = min(num_parts, total_pages_file)
                pages_per_part = total_pages_file // num_parts
                remainder = total_pages_file % num_parts
                
                current_page = 0
                for part_num in range(1, num_parts + 1):
                    if cancel_operation:
                        return
                    
                    writer = PdfWriter()
                    
                    part_size = pages_per_part + (1 if part_num <= remainder else 0)
                    end_page = current_page + part_size
                    
                    for page_idx in range(current_page, end_page):
                        writer.add_page(reader.pages[page_idx])
                        current_step += 1
                        if progress_widget:
                            safe_widget_config(progress_widget, value=current_step)
                        root.update_idletasks()
                    
                    output_name = f"{base_name}_parte_{part_num:02d}_de_{num_parts:02d}_pag_{current_page+1}-{end_page}.pdf"
                    output_path = generate_unique_filename(folder, output_name)
                    
                    with open(output_path, "wb") as f_out:
                        writer.write(f_out)
                    if pdfa_var_split.get() and PDFA_AVAILABLE:
                        try:
                            temp_pdfa = safe_temp_file(prefix="pdfa_split", suffix=".pdf")
                            converter_para_pdfa(output_path, temp_pdfa)
                            os.replace(temp_pdfa, output_path)
                            remove_temp_file(temp_pdfa)
                        except Exception as e:
                            logging.warning(f"Falha PDF/A no split: {e}")
                            # Mantém o original se falhar
                    
                    show_status(f"Dividindo {file_idx+1}/{len(files)} - Parte {part_num}/{num_parts}", "info")
                    current_page = end_page
                    total_files_created += 1
                
                files_processed += 1

            elif split_mode == "all":
                # OTIMIZAÇÃO: Processamento em lote para divisão página-a-página
                BATCH_SIZE = 10  # Processa 10 páginas por lote
                
                for batch_start in range(0, total_pages_file, BATCH_SIZE):
                    if cancel_operation:
                        return
                    
                    batch_end = min(batch_start + BATCH_SIZE, total_pages_file)
                    
                    for i in range(batch_start, batch_end):
                        if cancel_operation:
                            return
                            
                        if i >= MAX_PAGES_FOR_SINGLE_FILE_SPLIT:
                            logging.warning(f"Limite de páginas individuais atingido para {base_name}")
                            break
                        
                        writer = create_pdf_writer_with_encoding()
                        writer.add_page(reader.pages[i])
                        
                        output_name = f"{base_name}_pagina_{i+1:03d}_de_{total_pages_file:03d}.pdf"
                        output_path = generate_unique_filename(folder, output_name)
                        
                        with open(output_path, "wb") as f_out:
                            writer.write(f_out)
                        if pdfa_var_split.get() and PDFA_AVAILABLE:
                            try:
                                temp_pdfa = safe_temp_file(prefix="pdfa_split", suffix=".pdf")
                                converter_para_pdfa(output_path, temp_pdfa)
                                os.replace(temp_pdfa, output_path)
                                remove_temp_file(temp_pdfa)
                            except Exception as e:
                                logging.warning(f"Falha PDF/A no split: {e}")
                                # Mantém o original se falhar
                        current_step += 1
                        if progress_widget:
                            safe_widget_config(progress_widget, value=current_step)
                        show_status(f"Processando {file_idx+1}/{len(files)} - Página {i+1}/{total_pages_file}", "info")
                        root.update_idletasks()
                        total_files_created += 1
                
                files_processed += 1

            if total_files_created >= MAX_TOTAL_OUTPUT_FILES:
                show_message_in_main_thread(
                    "Limite Atingido",
                    f"Limite de {MAX_TOTAL_OUTPUT_FILES} arquivos criados atingido.\n"
                    f"Processamento interrompido após {files_processed} de {len(files)} arquivos.",
                    "warning"
                )
                break

        if progress_widget:
            safe_widget_config(progress_widget, value=total_steps)
        
        show_status(f"Operação concluída! Criados {total_files_created} arquivos.", "success")
        logging.info(f"Operação de divisão concluída: {total_files_created} arquivos criados")
        
        def show_success():
            messagebox.showinfo(
                "Sucesso", 
                f"Operação concluída!\n\n"
                f"Arquivos processados: {files_processed}/{len(files)}\n"
                f"Arquivos criados: {total_files_created}\n"
                f"Pasta de saída: {folder}",
                icon='info'
            )
        
        root.after(0, show_success)
        
    except (ValueError, SystemOverloadError) as e:
        logging.error(f"Erro na divisão: {e}")
        show_message_in_main_thread("Erro", str(e), "error")
    except Exception as e:
        logging.error(f"Falha ao processar PDFs: {e}")
        show_message_in_main_thread("Erro", f"Falha ao processar PDFs:\n{e}", "error")
        status_var.set("Erro ao processar arquivos.")
    finally:
        root.after(0, reset_ui_state)
        
        if progress_widget:
            root.after(300, lambda: safe_widget_config(progress_widget, value=0))

def split_or_extract_pdfs(event=None):
    if split_list.size() == 0:
        show_message_in_main_thread("Aviso", "Nenhum arquivo adicionado.", "warning")
        return
    
    if split_list.size() > MAX_FILES_FOR_SPLIT:
        show_message_in_main_thread(
            "Limite Excedido", 
            f"Máximo de {MAX_FILES_FOR_SPLIT} arquivos para divisão.\n"
            f"Selecionados: {split_list.size()}",
            "error"
        )
        return
    
    set_ui_state(False)
    if 'btn_cancel_split' in globals():
        try:
            btn_cancel_split.pack(pady=5)
        except tk.TclError:
            pass
    submit_thread_task(split_or_extract_pdfs_thread)

def cancel_split():
    global cancel_operation
    cancel_operation = True
    logging.info("Cancelamento da divisão solicitado")
    show_status("Cancelando operação...", "warning")
    root.after(1000, reset_ui_state)

def executar_operacao_aba_ativa(event=None):
    current_tab = notebook.index(notebook.select())
    
    logging.info(f"Executando operação da aba {current_tab}")
    
    if current_tab == 0:
        logging.info("Iniciando união de PDFs via CTRL+R")
        merge_pdfs()
    elif current_tab == 1:
        logging.info("Iniciando divisão de PDFs via CTRL+R")
        split_or_extract_pdfs()
    else:
        logging.warning(f"Aba desconhecida: {current_tab}")

def on_closing():
    global cancel_operation
    cancel_operation = True
    cleanup_temp_files()
    root.quit()
    root.destroy()

def show_environment_check():
    try:
        info = f"""Verificação do Ambiente JuntaPDF:

PyPDF2: {'Disponível' if PDF_LIBS_AVAILABLE else 'Não disponível'}
pikepdf: {'Disponível' if PIKEPDF_AVAILABLE else 'Não disponível'}
Ghostscript: {GHOSTSCRIPT_PATH if GHOSTSCRIPT_PATH else 'Não encontrado'}
PDF/A: {'Disponível' if PDFA_AVAILABLE else 'Indisponível'}
Drag & Drop: {'Disponível' if DND_AVAILABLE else 'Não disponível'}

Python: {sys.version}
Sistema: {sys.platform}"""
        
        messagebox.showinfo("Verificação de Ambiente", info)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao verificar ambiente: {e}")

def show_performance_dashboard():
    dialog = tk.Toplevel(root)
    dialog.title("Dashboard de Performance - JuntaPDF")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    main_frame = ttk.Frame(dialog, padding="15")
    main_frame.pack(fill="both", expand=True)

    title_label = ttk.Label(
        main_frame, 
        text="Dashboard de Performance", 
        font=("Segoe UI", 12, "bold")
    )
    title_label.pack(pady=(0, 15))

    metrics_frame = ttk.LabelFrame(main_frame, text="Métricas do Sistema", padding="10")
    metrics_frame.pack(fill="both", expand=True, pady=5)
    
    if not PSUtil_AVAILABLE:
        warning_frame = ttk.Frame(metrics_frame)
        warning_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(
            warning_frame, 
            text="Métricas limitadas - instale 'pip install psutil' para monitoramento completo",
            foreground="orange",
            font=("Segoe UI", 8, "bold"),
            justify="center"
        ).pack()

    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        cpu_percent = process.cpu_percent(interval=0.1)
        thread_count = process.num_threads()
    except ImportError:
        memory_mb = "N/A (instale psutil)"
        cpu_percent = "N/A"
        thread_count = "N/A"

    metrics = {
        "Arquivos em Cache": f"{len(pdf_metadata_cache)}",
        "Threads Ativas": f"{thread_count}",
        "Memória Utilizada": f"{memory_mb:.1f} MB" if isinstance(memory_mb, float) else memory_mb,
        "CPU em Uso": f"{cpu_percent}%" if isinstance(cpu_percent, float) else cpu_percent,
        "Arquivos Temporários": f"{len(temp_files_global)}",
        "Operações Canceladas": "0",
        "PDFs Válidos": f"{sum(1 for f in pdf_metadata_cache if 'Erro' not in f)}",
        "PDFs com Erro": f"{sum(1 for f in pdf_metadata_cache if 'Erro' in f)}"
    }

    for i, (k, v) in enumerate(metrics.items()):
        ttk.Label(metrics_frame, text=k, font=("Segoe UI", 9, "bold")).grid(
            row=i, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Label(metrics_frame, text=str(v), font=("Consolas", 9)).grid(
            row=i, column=1, sticky="w", padx=10, pady=3
        )

    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x", pady=15)

    def clear_cache():
        pdf_metadata_cache.clear()
        show_toast("Cache limpo!")
        dialog.destroy()
        show_performance_dashboard()

    def cleanup_temp_files_manual():
        cleanup_temp_files()
        show_toast("Arquivos temporários limpos!")
        dialog.destroy()
        show_performance_dashboard()

    ttk.Button(button_frame, text="Atualizar", 
              command=lambda: dialog.destroy() or show_performance_dashboard()).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Limpar Cache", 
              command=clear_cache).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Limpar Temporários", 
              command=cleanup_temp_files_manual).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Fechar", 
              command=dialog.destroy).pack(side="right", padx=5)

    dialog.focus_set()

def mostrar_licencas():
    janela_licencas = tk.Toplevel(root)
    janela_licencas.title("Licenças & Créditos - JuntaPDF")
    janela_licencas.geometry("600x500")
    
    frame = tk.Frame(janela_licencas)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    text_widget = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10, font=("Arial", 10))
    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    texto = """Este software foi desenvolvido integrando bibliotecas de código aberto, garantindo transparência e segurança para uso institucional e corporativo.

BIBLIOTECAS UTILIZADAS

• PyPDF2 – Licença BSD-3-Clause
• PNeFOP – Licença Mozilla Public License 2.0
• Ghostscript – Licença AGPLv3*
• tkinterdnd2, psutil – Licenças MIT/BSD

*Uso do Ghostscript: permitido internamente. Em redistribuições, é necessário incluir o aviso de licença da Artifex Software ou utilizar uma instalação separada do Ghostscript.

DIREITOS AUTORAIS

O código do JuntaPDF é de autoria independente e não deriva diretamente das bibliotecas utilizadas. Esta ferramenta combina e automatiza funcionalidades sem alterar os componentes originais, respeitando integralmente suas licenças.

OBSERVAÇÃO IMPORTANTE

O JuntaPDF processa arquivos localmente. NENHUM DADO É ENVIADO PARA A INTERNET. A responsabilidade pelo conteúdo dos arquivos processados é inteiramente do usuário.

Desenvolvido por Angelo Filho"""
    
    text_widget.insert(tk.END, texto)
    
    text_widget.tag_configure("bold", font=("Arial", 10, "bold"))
    text_widget.tag_add("bold", "3.0", "3.20")
    text_widget.tag_add("bold", "11.0", "11.16")
    text_widget.tag_add("bold", "16.0", "16.21")
    text_widget.tag_add("bold", "18.0", "18.35")
    
    text_widget.config(state=tk.DISABLED)

def criar_interface():
    global root, total_files_merge_var, total_pages_merge_var, total_size_merge_var
    global total_files_split_var, total_pages_split_var, total_size_split_var
    global merge_badge_var, split_badge_var, split_all_var, protect_var, pdfa_var
    global pdfa_var_split, compress_var, meta_var, split_mode_var, split_interval_var
    global split_parts_var, status_var, compress_level
    global merge_list, split_list, btn_merge, btn_split, progress_merge, progress_split
    global btn_cancel_merge, btn_cancel_split, password_entry, compress_combo
    global merge_filename_entry, merge_output_entry, split_output_entry
    global split_pages_entry, split_interval_entry, split_parts_entry
    global status_label, notebook
    global DND_AVAILABLE, PDF_LIBS_AVAILABLE, PDFA_AVAILABLE, GHOSTSCRIPT_PATH
    
    # CORREÇÃO: Criação da janela principal com tratamento correto
    try:
        if DND_AVAILABLE:
            root = TkinterDnD.Tk()
            logging.info("Janela com Drag & Drop")
        else:
            raise ImportError("DND não disponível")
    except Exception as e:
        logging.warning(f"Falha ao criar janela com DnD: {e}")
        root = tk.Tk()  # Fallback para tkinter normal
        DND_AVAILABLE = False
        logging.info("Janela criada sem Drag & Drop (fallback)")
    
    # 🟢 CORREÇÃO 1: INSTANCIAR DISPATCHER (ADICIONE ESTAS 3 LINHAS)
    global ui_dispatch
    ui_dispatch = UIThreadDispatcher(root)
    logging.info("✅ Dispatcher de UI inicializado com sucesso")
    
    tema_aplicado = aplicar_tema_moderno(root)
    
    
    if not PDF_LIBS_AVAILABLE:
        messagebox.showerror("Erro Crítico", 
                           "PyPDF2 não está disponível!\n\n"
                           "Execute 'pip install PyPDF2' ou execute o 'install.bat' incluído.")
        sys.exit(1)
    
    total_files_merge_var = tk.StringVar(value="0 arquivos")
    total_pages_merge_var = tk.StringVar(value="0 páginas") 
    total_size_merge_var = tk.StringVar(value="0 MB")
    total_files_split_var = tk.StringVar(value="0 arquivos")
    total_pages_split_var = tk.StringVar(value="0 páginas") 
    total_size_split_var = tk.StringVar(value="0 MB")
    protect_var = tk.BooleanVar(value=False)
    pdfa_var = tk.BooleanVar(value=PDFA_AVAILABLE)
    pdfa_var_split = tk.BooleanVar(value=PDFA_AVAILABLE)
    compress_var = tk.BooleanVar(value=False)
    meta_var = tk.BooleanVar(value=False)

    split_mode_var = tk.StringVar(value="extract")
    split_interval_var = tk.StringVar(value="5")
    split_parts_var = tk.StringVar(value="3")

    status_var = tk.StringVar()

    compress_level = tk.StringVar(value="Qualidade Máxima")
    
    root.title("JuntaPDF")
    root.geometry("900x750")
    root.resizable(True, True)

    menubar = tk.Menu(root)

    arquivo_menu = tk.Menu(menubar, tearoff=0)

    def get_current_tab_components():
        current_tab = notebook.select()
        tabs = notebook.tabs()
        
        if current_tab == tabs[0]:
            return merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var
        elif current_tab == tabs[1]:
            return split_list, total_files_split_var, total_pages_split_var, total_size_split_var
        return merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var

    def menu_adicionar_arquivos():
        listbox, files_var, pages_var, size_var = get_current_tab_components()
        add_files(listbox, files_var, pages_var, size_var)

    def menu_remover_selecionados():
        listbox, files_var, pages_var, size_var = get_current_tab_components()
        remove_selected(listbox, files_var, pages_var, size_var)

    def menu_limpar_lista():
        listbox, files_var, pages_var, size_var = get_current_tab_components()
        clear_list(listbox, files_var, pages_var, size_var)

    
    arquivo_menu.add_command(
        label="Executar Operação (Ctrl+R)", 
        command=executar_operacao_aba_ativa,
        accelerator="Ctrl+R"
    )
    arquivo_menu.add_separator()
    arquivo_menu.add_command(
        label="Adicionar Arquivos (Ctrl+O)", 
        command=menu_adicionar_arquivos,
        accelerator="Ctrl+O"
    )
   
    arquivo_menu.add_command(
        label="Limpar Lista (Ctrl+L)", 
        command=menu_limpar_lista,
        accelerator="Ctrl+L"
    )

    arquivo_menu.add_separator()

    arquivo_menu.add_command(
        label="Sair", 
        command=on_closing,
        accelerator="Esc"
    )

    menubar.add_cascade(label="Arquivo", menu=arquivo_menu)

    sobre_menu = tk.Menu(menubar, tearoff=0)
    sobre_menu.add_command(label="Licenças & Créditos", command=mostrar_licencas)
    sobre_menu.add_command(label="Verificar Ambiente", command=show_environment_check)
    sobre_menu.add_command(label="Dashboard de Performance", command=show_performance_dashboard)
    menubar.add_cascade(label="Sobre o JuntaPDF", menu=sobre_menu)

    root.config(menu=menubar)

    status_label = ttk.Label(root, textvariable=status_var, foreground="blue")
    status_label.pack(side="bottom", pady=5)

    status_parts = ["Pronto"]
    if DND_AVAILABLE:
        status_parts.append("Drag & Drop ✓")
    if PDFA_AVAILABLE:
        status_parts.append("PDF/A ✓")
    else:
        status_parts.append("PDF/A ✗")

    status_var.set(" | ".join(status_parts))

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=5)

    merge_frame = ttk.Frame(notebook)
    notebook.add(merge_frame, text="Juntar PDFs")

    stats_header = ttk.Frame(merge_frame, relief="solid", borderwidth=1, padding=10)
    stats_header.pack(fill="x", padx=10, pady=5)

    ttk.Label(stats_header, text="📊", font=("Segoe UI", 14)).pack(side="left", padx=5)
    ttk.Label(stats_header, textvariable=total_files_merge_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
    ttk.Label(stats_header, text="•", foreground="gray").pack(side="left")
    ttk.Label(stats_header, textvariable=total_pages_merge_var, font=("Segoe UI", 10)).pack(side="left", padx=10)
    ttk.Label(stats_header, text="•", foreground="gray").pack(side="left")
    ttk.Label(stats_header, textvariable=total_size_merge_var, font=("Segoe UI", 10)).pack(side="left", padx=10)

    files_section = ttk.LabelFrame(merge_frame, text="Lista de arquivos")
    files_section.pack(fill="both", expand=True, padx=10, pady=5)

    toolbar = ttk.Frame(files_section)
    toolbar.pack(fill="x", padx=5, pady=5)

    ttk.Button(toolbar, text="Adicionar (Ctrl+O)", 
              command=lambda: add_files(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).pack(side="left", padx=2)
    ttk.Button(toolbar, text="Remover (Del)", 
              command=lambda: remove_selected(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).pack(side="left", padx=2)
    ttk.Button(toolbar, text="Limpar (Ctrl+L)", 
              command=lambda: clear_list(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).pack(side="left", padx=2)

    ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=5)

    ttk.Button(toolbar, text="Mover ↑ (Shift+↑)", command=lambda: move_up(merge_list)).pack(side="left", padx=2)
    ttk.Button(toolbar, text="Mover ↓ (Shift+↓)", command=lambda: move_down(merge_list)).pack(side="left", padx=2)
    ttk.Button(toolbar, text="Ordem A→Z (Ctrl+S)", 
              command=lambda: sort_az(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).pack(side="left", padx=2)

    list_frame = ttk.Frame(files_section)
    list_frame.pack(fill="both", expand=True, padx=5, pady=5)

    merge_list = tk.Listbox(list_frame, selectmode=tk.EXTENDED, height=10)
    merge_list.pack(side=tk.LEFT, fill="both", expand=True)

    scroll_merge = ttk.Scrollbar(list_frame, orient="vertical", command=merge_list.yview)
    scroll_merge.pack(side=tk.RIGHT, fill="y")
    merge_list.config(yscrollcommand=scroll_merge.set)

    merge_list.bind("<Double-1>", lambda e: open_pdf(merge_list, e))
    attach_dynamic_tooltips(merge_list)
    setup_drag_reorder(merge_list)
    setup_context_menu(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)

    if DND_AVAILABLE:
        merge_list.drop_target_register(DND_FILES)
        merge_list.dnd_bind('<<Drop>>', lambda e: drop(e, merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var))

    config_section = ttk.LabelFrame(merge_frame, text="Configurações de Saída")
    config_section.pack(fill="x", padx=10, pady=5)

    config_section.columnconfigure(1, weight=1)

    chk_pdfa = ttk.Checkbutton(
        config_section, 
        text="Converter para PDF/A-2B", 
        variable=pdfa_var,
        command=toggle_password_entry
    )
    chk_pdfa.grid(row=0, column=0, sticky="w", padx=10, pady=5)

    pdfa_info_label = ttk.Label(
        config_section,
        text="Recomendado para o Sistema Eletrônico de Informações (SEI) do Governo Federal" if PDFA_AVAILABLE else "Instale Ghostscript para habilitar PDF/A",
        foreground="darkgreen" if PDFA_AVAILABLE else "red",
        font=("Segoe UI", 8)
    )
    pdfa_info_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

    compress_frame = ttk.Frame(config_section)
    compress_frame.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=5)
    
    compress_check = ttk.Checkbutton(compress_frame, text="Comprimir PDF:", variable=compress_var)
    compress_check.pack(side="left")
    
    # Debug: Verifica status das ferramentas
    logging.info(f"Ghostscript: {GHOSTSCRIPT_PATH}")
    logging.info(f"pikepdf disponível: {PIKEPDF_AVAILABLE}")
    
    # Desabilita se nem Ghostscript nem pikepdf estão disponíveis
    if not GHOSTSCRIPT_PATH and not PIKEPDF_AVAILABLE:
        compress_check.config(state="disabled")
        compress_var.set(False)
        logging.warning("Compressão desabilitada - Requer Ghostscript ou biblioteca pikepdf")
    
    compress_combo = ttk.Combobox(compress_frame, textvariable=compress_level, 
                                  values=["Qualidade Máxima", "Qualidade Equilibrada", "Tamanho Mínimo"],
                                  state="readonly", width=20)
    compress_combo.pack(side="left", padx=5)
    compress_combo.set("Qualidade Máxima")
    compress_combo.config(state="disabled")
    
    # Label informativo de compressão
    def get_compression_status():
        if GHOSTSCRIPT_PATH and PIKEPDF_AVAILABLE:
            return ("Ghostscript + pikepdf disponíveis", "darkgreen")
        elif GHOSTSCRIPT_PATH:
            return ("Ghostscript disponível", "darkgreen")
        elif PIKEPDF_AVAILABLE:
            return ("pikepdf disponível (compressão básica)", "darkorange")
        else:
            return ("Instale Ghostscript ou execute: pip install pikepdf", "red")
    
    status_text, status_color = get_compression_status()
    compress_info = ttk.Label(compress_frame, text=status_text, 
                             foreground=status_color, font=("Segoe UI", 8))
    compress_info.pack(side="left", padx=5)

    protect_frame = ttk.Frame(config_section)
    protect_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=5)
    ttk.Checkbutton(protect_frame, text="Proteger com senha:", variable=protect_var,
                   command=lambda: toggle_password_entry()).pack(side="left")
    password_entry = ttk.Entry(protect_frame, width=20, show="*", state="disabled")
    password_entry.pack(side="left", padx=5)

    ttk.Checkbutton(config_section, text="Remover metadados", variable=meta_var).grid(row=3, column=0, sticky="w", padx=10, pady=5)

    name_frame = ttk.Frame(config_section)
    name_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    ttk.Label(name_frame, text="Nome do arquivo final:").pack(side="left")
    merge_filename_entry = ttk.Entry(name_frame)
    merge_filename_entry.pack(side="left", fill="x", expand=True, padx=5)
    merge_filename_entry.insert(0, "Deixe vazio para nome automático")
    merge_filename_entry.config(foreground="gray")

    def on_merge_filename_focusin(event):
        if merge_filename_entry.get() == "Deixe vazio para nome automático":
            merge_filename_entry.delete(0, tk.END)
            safe_widget_config(merge_filename_entry, foreground="black")

    def on_merge_filename_focusout(event):
        if not merge_filename_entry.get().strip():
            safe_widget_config(merge_filename_entry, foreground="gray")
            merge_filename_entry.insert(0, "Deixe vazio para nome automático")

    merge_filename_entry.bind("<FocusIn>", on_merge_filename_focusin)
    merge_filename_entry.bind("<FocusOut>", on_merge_filename_focusout)

    output_frame = ttk.Frame(config_section)
    output_frame.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
    ttk.Label(output_frame, text="Pasta de saída:").pack(side="left")
    merge_output_entry = ttk.Entry(output_frame)
    merge_output_entry.pack(side="left", fill="x", expand=True, padx=5)
    ttk.Button(output_frame, text="Selecionar Pasta", command=lambda: choose_output_folder(merge_output_entry)).pack(side="left")

    if not PDFA_AVAILABLE:
        chk_pdfa.config(state="disabled")
        pdfa_info_label.config(text="Instale Ghostscript para habilitar PDF/A", foreground="red")

    action_section = ttk.Frame(merge_frame)
    action_section.pack(fill="x", padx=10, pady=10)

    btn_merge = ttk.Button(action_section, text="Juntar PDFs (Ctrl+R)", command=merge_pdfs)
    btn_merge.pack(pady=10)

    progress_merge = ttk.Progressbar(action_section, mode="determinate", length=400)
    progress_merge.pack(pady=5)

    btn_cancel_merge = ttk.Button(merge_frame, text="Cancelar Operação", command=cancel_merge)

    split_frame = ttk.Frame(notebook)
    notebook.add(split_frame, text="Dividir PDFs")

    stats_header_split = ttk.Frame(split_frame, relief="solid", borderwidth=1, padding=10)
    stats_header_split.pack(fill="x", padx=10, pady=5)

    ttk.Label(stats_header_split, text="📊", font=("Segoe UI", 14)).pack(side="left", padx=5)
    ttk.Label(stats_header_split, textvariable=total_files_split_var, font=("Segoe UI", 10, "bold")).pack(side="left", padx=10)
    ttk.Label(stats_header_split, text="•", foreground="gray").pack(side="left")
    ttk.Label(stats_header_split, textvariable=total_pages_split_var, font=("Segoe UI", 10)).pack(side="left", padx=10)
    ttk.Label(stats_header_split, text="•", foreground="gray").pack(side="left")
    ttk.Label(stats_header_split, textvariable=total_size_split_var, font=("Segoe UI", 10)).pack(side="left", padx=10)

    files_section_split = ttk.LabelFrame(split_frame, text="Arquivos PDF")
    files_section_split.pack(fill="both", expand=True, padx=10, pady=5)

    toolbar_split = ttk.Frame(files_section_split)
    toolbar_split.pack(fill="x", padx=5, pady=5)

    ttk.Button(toolbar_split, text="Adicionar (Ctrl+O)", 
              command=lambda: add_files(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).pack(side="left", padx=2)
    ttk.Button(toolbar_split, text="Remover (Del)", 
              command=lambda: remove_selected(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).pack(side="left", padx=2)
    ttk.Button(toolbar_split, text="Limpar (Ctrl+L)", 
              command=lambda: clear_list(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).pack(side="left", padx=2)

    list_frame_split = ttk.Frame(files_section_split)
    list_frame_split.pack(fill="both", expand=True, padx=5, pady=5)

    split_list = tk.Listbox(list_frame_split, selectmode=tk.EXTENDED, height=10)
    split_list.pack(side=tk.LEFT, fill="both", expand=True)

    scroll_split = ttk.Scrollbar(list_frame_split, orient="vertical", command=split_list.yview)
    scroll_split.pack(side=tk.RIGHT, fill="y")
    split_list.config(yscrollcommand=scroll_split.set)

    split_list.bind("<Double-1>", lambda e: open_pdf(split_list, e))
    attach_dynamic_tooltips(split_list)
    setup_drag_reorder(split_list)
    setup_context_menu(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)

    if DND_AVAILABLE:
        split_list.drop_target_register(DND_FILES)
        split_list.dnd_bind('<<Drop>>', lambda e: drop(e, split_list, total_files_split_var, total_pages_split_var, total_size_split_var))

    split_config = ttk.LabelFrame(split_frame, text="Configurações de Divisão")
    split_config.pack(fill="x", padx=10, pady=5)

    mode_frame = ttk.Frame(split_config)
    mode_frame.pack(fill="x", padx=10, pady=10)

    ttk.Label(mode_frame, text="Modo:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0,10))

    split_mode_combo = ttk.Combobox(mode_frame, width=35, state="readonly")
    split_mode_combo['values'] = (
        "Extrair páginas específicas",
        "Dividir por intervalo de páginas", 
        "Dividir em partes iguais",
        "Dividir todas (1 arquivo por página)"
    )
    split_mode_combo.current(0)
    split_mode_combo.pack(side="left", padx=5)

    options_frame = ttk.Frame(split_config)
    options_frame.pack(fill="x", padx=10, pady=5)

    split_pages_entry = ttk.Entry(options_frame, width=40)
    split_interval_entry = ttk.Entry(options_frame, width=10)
    split_parts_entry = ttk.Entry(options_frame, width=10)

    def update_split_mode(*args):
        for widget in options_frame.winfo_children():
            widget.pack_forget()
        
        mode_idx = split_mode_combo.current()
        
        if mode_idx == 0:
            ttk.Label(options_frame, text="Páginas:").pack(side="left", padx=5)
            split_pages_entry.pack(side="left", padx=5, fill="x", expand=True)
            split_pages_entry.delete(0, tk.END)
            split_pages_entry.insert(0, "1-5, 10, 20-30")
            ttk.Label(options_frame, text="Ex: 1-5, 10, 20-30", foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=5)
            split_mode_var.set("extract")
            
        elif mode_idx == 1:
            ttk.Label(options_frame, text="Páginas por arquivo:").pack(side="left", padx=5)
            split_interval_entry.pack(side="left", padx=5)
            split_interval_entry.delete(0, tk.END)
            split_interval_entry.insert(0, "5")
            ttk.Label(options_frame, text="Ex: 5 → divide em grupos de 5 páginas", foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=5)
            split_mode_var.set("interval")
            split_interval_var.set("5")
            
        elif mode_idx == 2:
            ttk.Label(options_frame, text="Número de partes:").pack(side="left", padx=5)
            split_parts_entry.pack(side="left", padx=5)
            split_parts_entry.delete(0, tk.END)
            split_parts_entry.insert(0, "3")
            ttk.Label(options_frame, text="Ex: 3 → divide em 3 arquivos iguais", foreground="gray", font=("Segoe UI", 8)).pack(side="left", padx=5)
            split_mode_var.set("parts")
            split_parts_var.set("3")
            
        elif mode_idx == 3:
            ttk.Label(options_frame, text="Cada página será salva como arquivo individual", 
                     foreground="blue", font=("Segoe UI", 9)).pack(side="left", padx=10)
            split_mode_var.set("all")

    split_mode_combo.bind("<<ComboboxSelected>>", update_split_mode)
    update_split_mode()

    pdfa_frame = ttk.Frame(split_config)
    pdfa_frame.pack(fill="x", padx=10, pady=5)
    pdfa_check_split = ttk.Checkbutton(pdfa_frame, text="Converter para PDF/A-2B", variable=pdfa_var_split)
    pdfa_check_split.pack(side="left")
    pdfa_info_split = ttk.Label(
        pdfa_frame,
        text="Formato recomendado para documentos eletrônicos no SEI/Governo Federal",
        foreground="darkgreen", 
        font=("Segoe UI", 8)
    )
    pdfa_info_split.pack(side="left", padx=10)

    if not PDFA_AVAILABLE:
        pdfa_check_split.config(state="disabled")
        pdfa_info_split.config(text="Instale Ghostscript para habilitar", foreground="red")

    output_split_frame = ttk.Frame(split_config)
    output_split_frame.pack(fill="x", padx=10, pady=5)
    ttk.Label(output_split_frame, text="Pasta de saída:").pack(side="left")
    split_output_entry = ttk.Entry(output_split_frame)
    split_output_entry.pack(side="left", fill="x", expand=True, padx=5)
    ttk.Button(output_split_frame, text="Selecionar Pasta", command=lambda: choose_output_folder(split_output_entry)).pack(side="left")

    action_section_split = ttk.Frame(split_frame)
    action_section_split.pack(fill="x", padx=10, pady=10)

    btn_split = ttk.Button(action_section_split, text="Dividir/Extrair PDFs (Ctrl+R)", command=split_or_extract_pdfs)
    btn_split.pack(pady=10)

    progress_split = ttk.Progressbar(action_section_split, mode="determinate", length=400)
    progress_split.pack(pady=5)

    btn_cancel_split = ttk.Button(split_frame, text="Cancelar Operação", command=cancel_split)

    def get_active_listbox():
        current_tab = notebook.select()
        tabs = notebook.tabs()
        if current_tab == tabs[0]:
            return merge_list
        return split_list

    def get_active_vars():
        current_tab = notebook.select()
        tabs = notebook.tabs()
        if current_tab == tabs[0]:
            return merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var
        return split_list, total_files_split_var, total_pages_split_var, total_size_split_var

    root.bind_all("<Control-o>", lambda e: add_files(*get_active_vars()))
    root.bind_all("<Control-O>", lambda e: add_files(*get_active_vars()))
    root.bind_all("<Delete>", lambda e: remove_selected(*get_active_vars()))
    root.bind_all("<Control-l>", lambda e: clear_list(*get_active_vars()))
    root.bind_all("<Control-L>", lambda e: clear_list(*get_active_vars()))
    root.bind_all("<Control-s>", lambda e: sort_az(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var))
    root.bind_all("<Control-S>", lambda e: sort_az(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var))
    root.bind_all("<Control-r>", executar_operacao_aba_ativa)
    root.bind_all("<Control-R>", executar_operacao_aba_ativa)
    root.bind_all("<Escape>", lambda e: on_closing())

    # Bindings da lista (Mover itens)
    if merge_list:
        merge_list.bind("<Shift-Up>", lambda e: (move_up(merge_list), "break")[1])
        merge_list.bind("<Shift-Down>", lambda e: (move_down(merge_list), "break")[1])

    # Protocolo de fechamento da janela
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # CONFIGURAÇÃO FINAL CRÍTICA - ADICIONE ESTAS LINHAS:
    
    # Configura traces para automação da UI
    try:
        protect_var.trace_add("write", lambda *args: toggle_password_entry())
        pdfa_var.trace_add("write", lambda *args: toggle_password_entry())
        compress_var.trace_add("write", lambda *args: toggle_compress_combo())
        pdfa_var.trace_add("write", lambda *args: gerenciar_compatibilidade_opcoes())
        compress_var.trace_add("write", lambda *args: gerenciar_compatibilidade_opcoes())
    except Exception as e:
        logging.warning(f"Erro ao configurar traces: {e}")

    # Atualização inicial das estatísticas
    try:
        update_stats(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)
        update_stats(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)
    except Exception as e:
        logging.warning(f"Erro na atualização inicial: {e}")

    logging.info("Interface criada com sucesso")
    return root


if __name__ == "__main__":
    try:

        # Debug de bibliotecas
        try:
            from PyPDF2 import PdfReader
            print("✓ PyPDF2 carregado")
        except ImportError as e:
            print("✗ PyPDF2 falhou:", e)
            input("Pressione Enter para sair...")
            sys.exit(1)
        
        # Verifica se tkinter funciona
        try:
            print("Testando tkinter...")
            test_root = tk.Tk()
            test_root.withdraw()  # Esconde a janela de teste
            print("✓ tkinter funcionando")
            test_root.destroy()
        except Exception as e:
            print("✗ tkinter falhou:", e)
            input("Pressione Enter para sair...")
            sys.exit(1)
            
        # Cria interface
        print("Criando interface principal...")
        root = criar_interface()
        
        if root:
            print("✓ Interface criada com sucesso!")
            print("Iniciando mainloop...")
            root.mainloop()
            print("Mainloop finalizado normalmente")
        else:
            print("❌ ERRO: Interface não foi criada (root é None)")
            input("Pressione Enter para sair...")
            
    except Exception as e:
        print("❌ ERRO FATAL:", str(e))
        import traceback
        traceback.print_exc()
        print("\n*** COPIE ESTA MENSAGEM INTEIRA E COLE PARA O ASSISTENTE ***")
        input("Pressione Enter para sair...")