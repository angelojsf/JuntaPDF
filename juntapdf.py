import atexit
import concurrent.futures
import glob
import logging
import os
import re
import shutil
import subprocess
import sys
import json
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import webbrowser
print("Executável usado:", sys.executable)


try:
    import psutil
    PSUtil_AVAILABLE = True
except ImportError:
    PSUtil_AVAILABLE = False
    logging.warning("psutil não disponível - algumas métricas estarão limitadas")


pdf_metadata_cache = {}
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('juntapdf.log', encoding='utf-8')
    ]
)

# =============================================================================
# VARIÁVEIS GLOBAIS DE DEPENDÊNCIAS - DEFINIR PRIMEIRO
# =============================================================================
PDF_LIBS_AVAILABLE = False
PIKEPDF_AVAILABLE = False  
DND_AVAILABLE = False
PDFA_AVAILABLE = False
GHOSTSCRIPT_PATH = None
ICC_PROFILE_PATH = None
_atexit_cleanup_registered = False
temp_files_global = []
temp_files_lock = threading.Lock()

# =============================================================================
# CONFIGURAÇÃO DE LOGGING PROFISSIONAL COM SEGURANÇA
# =============================================================================
class SecureLogger:
    def __init__(self):
        self.sensitive_patterns = [
            r'password[=:]\s*\S+',
            r'user[=:]\s*\S+',
            r'[\w\.-]+@[\w\.-]+\.\w+',  # emails
            r'senha[=:]\s*\S+',
            r'pwd[=:]\s*\S+'
        ]
    
    def sanitize_log(self, message):
        """Remove informações sensíveis dos logs"""
        if not isinstance(message, str):
            message = str(message)
        for pattern in self.sensitive_patterns:
            message = re.sub(pattern, '[REDACTED]', message, flags=re.IGNORECASE)
        return message

secure_logger = SecureLogger()

def limpar_logs_antigos(dias=30):
    """Remove logs com mais de X dias - Compliance institucional"""
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
    """Configura rotação automática de logs para evitar arquivos muito grandes"""
    try:
        log_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Logs")
        if not os.path.exists(log_dir):
            return
            
        for log_file in glob.glob(os.path.join(log_dir, "juntapdf_*.log")):
            try:
                # Rotaciona se maior que 10MB (mais conservador)
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
    """Configura sistema de logging profissional para troubleshooting"""
    # 🔥 NOVO: Rotação de logs antes de criar novo
    setup_log_rotation()
    
    log_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Logs")
    os.makedirs(log_dir, exist_ok=True)
    
    # 🔥 NOVO: Limpeza de logs antigos (compliance institucional)
    limpar_logs_antigos(30)  # Mantém apenas logs dos últimos 30 dias
    
    log_file = os.path.join(log_dir, f"juntapdf_{time.strftime('%Y%m%d')}.log")
    
    # Handler personalizado para sanitização
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
    logging.info(f"Política de retenção: 30 dias")
    logging.info(f"Rotacionamento: 10MB")

setup_logging()

def setup_recovery_indicator():
    recovered = attempt_auto_recovery()
    if recovered:
        recovery_frame = ttk.Frame(root)
        recovery_frame.pack(side="top", fill="x", padx=10, pady=5)
        
        ttk.Button(
            recovery_frame, 
            text="🔄 Recovery Disponível - Clique aqui",
            command=show_recovery_dashboard,
            style="Accent.TButton"
        ).pack(fill="x")

def show_first_run_disclaimer():
    """Mostra aviso na primeira execução"""
    config_file = os.path.join(tempfile.gettempdir(), "juntapdf_aceite.flag")
    
    if not os.path.exists(config_file):
        response = messagebox.askyesno(
            "Termo de Uso - JuntaPDF",
            "Esta ferramenta processa PDFs localmente.\n\n"
            "• Não envia dados para internet\n"
            "• Usuário é responsável pelo conteúdo processado\n"
            "• Logs são armazenados localmente\n\n"
            "Aceita os termos de uso?",
            icon='question'
        )
        
        if response:
            open(config_file, 'w').write(f"Aceito em: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            sys.exit(0)

# =============================================================================
# CONSTANTES DE SEGURANÇA E LIMITES
# =============================================================================
MAX_CONCURRENT_OPERATIONS = 1
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
MAX_TOTAL_PAGES = 10000
MAX_FILES_PER_OPERATION = 100

# =============================================================================
# EXCEÇÕES PERSONALIZADAS
# =============================================================================
class SecurityError(Exception):
    """Erro de segurança"""
    pass

class PDFCorruptionError(Exception):
    """PDF corrompido ou inválido"""
    pass

class SystemOverloadError(Exception):
    """Sistema sobrecarregado"""
    pass

class PDFProcessingError(Exception):
    """Erro geral de processamento PDF"""
    pass

# =============================================================================
# MONITORAMENTO DE PERFORMANCE E SEGURANÇA
# =============================================================================
class PerformanceMonitor:
    def __init__(self):
        self.operation_times = []
        self.memory_usage = []
    
    def check_system_health(self):
        """Verifica se o sistema está saudável"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                raise SystemOverloadError("Sistema com memória insuficiente")
            
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 80:
                raise SystemOverloadError("CPU sobrecarregada")
        except ImportError:
            # psutil não disponível, continuar sem monitoramento
            pass

performance_monitor = PerformanceMonitor()

# =============================================================================
# SISTEMA DE RECUPERAÇÃO DE FALHAS
# =============================================================================
def create_operation_checkpoint(operation_type, files_processed, current_step, temp_files):
    """Salva estado atual da operação para recovery"""
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
        # Restringir permissões do arquivo
        if hasattr(os, 'chmod'):
            os.chmod(checkpoint_file, 0o600)
        logging.info(f"Checkpoint criado: {checkpoint_file}")
    except Exception as e:
        logging.warning(f"Erro ao criar checkpoint: {e}")

def cleanup_checkpoint():
    """Remove checkpoint após operação bem-sucedida"""
    checkpoint_file = os.path.join(tempfile.gettempdir(), f"juntapdf_checkpoint_{os.getpid()}.json")
    try:
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            logging.info("Checkpoint removido")
    except Exception as e:
        logging.warning(f"Erro ao remover checkpoint: {e}")

# =============================================================================
# 🚨 CORREÇÃO 1: EXECUÇÃO SEGURA CENTRALIZADA - ELIMINA TODOS shell=True
# =============================================================================

def attempt_auto_recovery():
    """Tenta recuperação automática de operações interrompidas"""
    checkpoint_pattern = os.path.join(tempfile.gettempdir(), "juntapdf_checkpoint_*.json")
    checkpoints = glob.glob(checkpoint_pattern)
    
    recovered_operations = []
    
    for checkpoint_file in checkpoints:
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                checkpoint = json.load(f)
            
            # Verificar se é recente (menos de 1 hora) e válido
            is_recent = time.time() - checkpoint.get('timestamp', 0) < 3600
            has_valid_data = checkpoint.get('files_processed') and checkpoint.get('operation_type')
            
            if is_recent and has_valid_data:
                recovered_operations.append({
                    'file': checkpoint_file,
                    'data': checkpoint,
                    'age_minutes': int((time.time() - checkpoint['timestamp']) / 60)
                })
                
        except Exception as e:
            logging.warning(f"Erro ao processar checkpoint {checkpoint_file}: {e}")
            # Remove checkpoint corrompido
            try:
                os.remove(checkpoint_file)
            except:
                pass
    
    return recovered_operations

def offer_recovery_on_startup():
    """Oferece recovery na inicialização do programa"""
    try:
        recovered = attempt_auto_recovery()
        if not recovered:
            return
            
        for recovery in recovered:
            operation_type = recovery['data'].get('operation_type', 'Desconhecida')
            file_count = len(recovery['data'].get('files_processed', []))
            age = recovery['age_minutes']
            
            response = messagebox.askyesno(
                "Recuperação Disponível",
                f"Foi detectada uma operação interrompida:\n\n"
                f"• Tipo: {operation_type}\n"
                f"• Arquivos: {file_count}\n" 
                f"• Interrompida há: {age} minutos\n\n"
                f"Deseja visualizar detalhes para possível recuperação?",
                icon='warning'
            )
            
            if response:
                show_recovery_details(recovery)
                
    except Exception as e:
        logging.error(f"Erro no sistema de recovery: {e}")

def show_recovery_details(recovery):
    """Mostra detalhes da operação para recovery"""
    details_window = tk.Toplevel(root)
    details_window.title("Detalhes da Recuperação")
    details_window.geometry("500x400")
    
    frame = ttk.Frame(details_window, padding="10")
    frame.pack(fill="both", expand=True)
    
    # Informações da operação
    data = recovery['data']
    ttk.Label(frame, text="Detalhes da Operação Interrompida", 
             font=("Segoe UI", 11, "bold")).pack(pady=(0, 10))
    
    info_text = f"""Tipo: {data.get('operation_type', 'N/A')}
Arquivos processados: {len(data.get('files_processed', []))}
Etapa: {data.get('current_step', 'N/A')}
Idade: {recovery['age_minutes']} minutos

Arquivos envolvidos:
"""
    
    for i, file_path in enumerate(data.get('files_processed', [])[:10]):  # Mostra até 10 arquivos
        info_text += f"  {i+1}. {os.path.basename(file_path)}\n"
    
    if len(data.get('files_processed', [])) > 10:
        info_text += f"  ... e mais {len(data.get('files_processed', [])) - 10} arquivos\n"
    
    text_widget = tk.Text(frame, wrap="word", height=15, width=60)
    text_widget.pack(fill="both", expand=True, pady=5)
    text_widget.insert("1.0", info_text)
    text_widget.config(state="disabled")
    
    # Botões de ação
    button_frame = ttk.Frame(frame)
    button_frame.pack(fill="x", pady=10)
    
    def cleanup_recovery():
        try:
            os.remove(recovery['file'])
            details_window.destroy()
            show_toast("Checkpoint de recovery removido")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao remover checkpoint: {e}")
    
    ttk.Button(button_frame, text="Limpar Recovery", 
              command=cleanup_recovery).pack(side="left", padx=5)
    ttk.Button(button_frame, text="Fechar", 
              command=details_window.destroy).pack(side="right", padx=5)


def process_large_file_in_chunks(file_path, operation_callback, chunk_size=5*1024*1024):
    """
    Processa arquivos grandes em chunks para economizar memória
    operation_callback: função que processa cada chunk (deve retornar dados processados)
    """
    temp_files = []
    try:
        file_size = os.path.getsize(file_path)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        logging.info(f"Processando arquivo grande em chunks: {os.path.basename(file_path)} "
                    f"({file_size/1024/1024:.1f}MB, {total_chunks} chunks)")
        
        with open(file_path, 'rb') as f:
            for chunk_num in range(total_chunks):
                if cancel_operation:
                    raise PDFProcessingError("Operação cancelada pelo usuário")
                
                # Ler chunk
                chunk_data = f.read(chunk_size)
                if not chunk_data:
                    break
                
                # Processar chunk usando a callback fornecida
                processed_chunk = operation_callback(chunk_data, chunk_num, total_chunks)
                
                # Salvar chunk processado em arquivo temporário
                temp_file = os.path.join(tempfile.gettempdir(), 
                                       f"chunk_{chunk_num}_{os.getpid()}_{int(time.time())}.tmp")
                with open(temp_file, 'wb') as temp_f:
                    temp_f.write(processed_chunk)
                
                temp_files.append(temp_file)
                add_temp_file(temp_file)
                
                # Atualizar progresso
                progress = (chunk_num + 1) / total_chunks * 100
                show_status(f"Processando chunk {chunk_num + 1}/{total_chunks} ({progress:.1f}%)", "info")
                root.update_idletasks()
        
        return temp_files
        
    except Exception as e:
        # Limpeza em caso de erro
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
                remove_temp_file(temp_file)
            except:
                pass
        raise PDFProcessingError(f"Erro no processamento por chunks: {e}")

def exec_segura(cmd, timeout=300, descricao="", progress_widget=None):
    """
    Execução centralizada e segura de comandos - ELIMINA shell=True
    """
    # 🔒 CONVERSÃO OBRIGATÓRIA: string → lista
    if isinstance(cmd, str):
        import shlex
        cmd = shlex.split(cmd)  # Divide string em lista segura
    
    logging.info(f"Executando {descricao}: {' '.join(cmd)}")
    
    try:
        # Configurar progresso se fornecido
        if progress_widget and hasattr(progress_widget, 'config'):
            progress_widget.config(mode="indeterminate")
            progress_widget.start(10)
        
        # 🚨 CRÍTICO: shell=False SEMPRE
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True, 
            timeout=timeout,
            shell=False,  # 🔒 IMPEDE SHELL INJECTION
            encoding='utf-8',
            errors='ignore'
        )
        
        # Parar progresso
        if progress_widget and hasattr(progress_widget, 'stop'):
            progress_widget.stop()
            if hasattr(progress_widget, 'config'):
                progress_widget.config(mode="determinate")
        
        return result
        
    except subprocess.TimeoutExpired:
        logging.error(f"Timeout em {descricao}")
        if progress_widget and hasattr(progress_widget, 'stop'):
            progress_widget.stop()
        kill_ghostscript_processes()
        raise
    except Exception as e:
        logging.error(f"Erro em {descricao}: {e}")
        if progress_widget and hasattr(progress_widget, 'stop'):
            progress_widget.stop()
        raise

# =============================================================================
# VALIDAÇÕES DE SEGURANÇA FORTALECIDAS
# =============================================================================
def validate_file_security(file_path):
    """Validação completa de segurança do arquivo - VERSÃO CORRIGIDA"""
    # Verificar se arquivo existe
    if not os.path.exists(file_path):
        raise SecurityError("Arquivo não existe")
    
    # Tamanho máximo
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise SecurityError(f"Arquivo muito grande ({file_size/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024}MB)")
    
    # 🔥 CORREÇÃO CRÍTICA: Validação de nome de arquivo MAIS PERMISSIVA
    # Permite caracteres comuns como (), $, -, _ mas ainda bloqueia injeção
    filename = os.path.basename(file_path)
    
    # 🔒 Caracteres realmente perigosos (mantém segurança essencial)
    dangerous_patterns = [
        '..',  # Path traversal
        '|',   # Pipe injection
        '&',   # Command injection  
        ';',   # Command termination
        '`',   # Command substitution
        '\0',  # Null byte
        '\r',  # Carriage return
        '\n'   # New line
    ]
    
    if any(pattern in file_path for pattern in dangerous_patterns):
        raise SecurityError("Nome de arquivo contém caracteres perigosos")
    
    # 🔥 NOVO: Verificação de path traversal mais específica e robusta
    try:
        # Normaliza o caminho e verifica se há tentativa de escape do diretório
        absolute_path = os.path.abspath(file_path)
        normalized_path = os.path.normpath(file_path)
        
        # Verifica se após normalização ainda contém '..'
        if '..' in normalized_path or normalized_path != os.path.normpath(absolute_path):
            raise SecurityError("Tentativa de path traversal detectada")
            
    except Exception as e:
        raise SecurityError(f"Erro ao validar caminho do arquivo: {e}")
    
    # Verificar se é PDF pela assinatura
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                raise SecurityError("Arquivo não é um PDF válido (assinatura inválida)")
            
            # 🔒 VERIFICAR JAVASCRIPT EMBUTIDO
            f.seek(0)
            first_chunk = f.read(4096)
            if b'/JavaScript' in first_chunk:
                raise SecurityError("Arquivo PDF contém JavaScript incorporado - potencial risco de segurança")
                
    except Exception as e:
        raise SecurityError(f"Erro ao verificar arquivo: {e}")

# =============================================================================
# SISTEMA DE FALLBACK E RESILIÊNCIA
# =============================================================================
def resilient_pdf_operation(operation, fallback_operation, max_retries=3):
    """Executa operação com fallback automático"""
    for attempt in range(max_retries):
        try:
            performance_monitor.check_system_health()
            return operation()
        except (PDFProcessingError, SystemOverloadError) as e:
            if attempt == max_retries - 1:
                logging.warning(f"Falha na operação principal após {max_retries} tentativas, usando fallback: {e}")
                return fallback_operation()
            logging.info(f"Tentativa {attempt + 1} falhou, retentando: {e}")
            time.sleep(1)  # Backoff simples
        except Exception as e:
            logging.error(f"Erro inesperado: {e}")
            raise

# =============================================================================
# DETECÇÃO DE DEPENDÊNCIAS CRÍTICAS
# =============================================================================
def check_dependencies():
    """Valida ambiente antes de iniciar GUI"""
    issues = []
    
    # Crítico
    if not PDF_LIBS_AVAILABLE:
        issues.append("❌ PyPDF2 - FUNCIONALIDADES PRINCIPAIS DESABILITADAS")
    
    # Importante mas não crítico  
    if not GHOSTSCRIPT_PATH:
        issues.append("⚠️ Ghostscript - PDF/A e compressão desabilitados")
    
    if not PIKEPDF_AVAILABLE:
        issues.append("⚠️ pikepdf - Algumas otimizações limitadas")
    
    if issues:
        messagebox.showwarning(
            "Verificação de Ambiente",
            f"Recursos limitados:\n\n{chr(10).join(issues)}\n\n"
            f"Soluções:\n"
            f"• PyPDF2/pikepdf: Execute 'install.bat'\n"  
            f"• Ghostscript: Baixe em https://ghostscript.com"
        )

# =============================================================================
# NOVO: SISTEMA DE VERIFICAÇÃO DE AMBIENTE DETALHADO
# =============================================================================
def get_environment_report():
    """Gera relatório completo do ambiente"""
    report = []
    report.append("=" * 60)
    report.append("RELATÓRIO DE AMBIENTE - JUNTAPDF")
    report.append("=" * 60)
    report.append(f"Data/Hora: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Python: {sys.version}")
    report.append(f"Plataforma: {sys.platform}")
    report.append("")
    
    # Dependências principais
    report.append("DEPENDÊNCIAS PRINCIPAIS:")
    report.append(f"  PyPDF2: {'✓ DISPONÍVEL' if PDF_LIBS_AVAILABLE else '✗ NÃO ENCONTRADO'}")
    report.append(f"  pikepdf: {'✓ DISPONÍVEL' if PIKEPDF_AVAILABLE else '✗ NÃO ENCONTRADO'}")
    report.append(f"  tkinterdnd2: {'✓ DISPONÍVEL' if DND_AVAILABLE else '✗ NÃO ENCONTRADO'}")
    report.append("")
    
    # Ghostscript
    report.append("GHOSTSCRIPT:")
    if GHOSTSCRIPT_PATH:
        report.append(f"  Executável: {GHOSTSCRIPT_PATH}")
        report.append(f"  Versão: {get_ghostscript_version()}")
    else:
        report.append("  ✗ NÃO ENCONTRADO")
    report.append("")
    
    # Perfil ICC
    report.append("PERFIL ICC:")
    if ICC_PROFILE_PATH:
        report.append(f"  Arquivo: {ICC_PROFILE_PATH}")
        report.append(f"  Existe: {'✓ SIM' if os.path.exists(ICC_PROFILE_PATH) else '✗ NÃO'}")
    else:
        report.append("  ✗ NÃO ENCONTRADO")
    report.append("")
    
    # PDF/A
    report.append("PDF/A:")
    report.append(f"  Disponível: {'✓ SIM' if PDFA_AVAILABLE else '✗ NÃO'}")
    report.append("")
    
    # Diretórios
    report.append("DIRETÓRIOS:")
    report.append(f"  Temp: {tempfile.gettempdir()}")
    report.append(f"  Logs: {os.path.join(tempfile.gettempdir(), 'JuntaPDF_Logs')}")
    report.append("")
    
    # Limites
    report.append("LIMITES CONFIGURADOS:")
    report.append(f"  Máx. arquivos: {MAX_FILES_PER_OPERATION}")
    report.append(f"  Máx. páginas: {MAX_TOTAL_PAGES}")
    report.append(f"  Máx. tamanho: {MAX_FILE_SIZE/1024/1024} MB")
    report.append("")
    
    # Status geral
    status = "✅ AMBIENTE ADEQUADO" if PDF_LIBS_AVAILABLE and GHOSTSCRIPT_PATH else "⚠️ AMBIENTE COM LIMITAÇÕES"
    report.append(f"STATUS: {status}")
    
    return "\n".join(report)

def get_ghostscript_version():
    """Obtém versão do Ghostscript"""
    if not GHOSTSCRIPT_PATH:
        return "N/A"
    
    try:
        result = exec_segura([GHOSTSCRIPT_PATH, "--version"], 
                           timeout=10, descricao="Ghostscript version")
        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return "Erro ao obter versão"
    except Exception as e:
        return f"Erro: {e}"

def show_environment_check():
    """Mostra diálogo detalhado de verificação de ambiente"""
    report = get_environment_report()
    
    # Criar janela de diálogo
    dialog = tk.Toplevel()
    dialog.title("Verificação de Ambiente - JuntaPDF")
    dialog.geometry("700x600")
    dialog.resizable(True, True)
    dialog.transient(root)
    dialog.grab_set()
    
    # Frame principal
    main_frame = ttk.Frame(dialog, padding="10")
    main_frame.pack(fill="both", expand=True)
    
    # Título
    title_label = ttk.Label(main_frame, text="Relatório de Ambiente", 
                           font=("Segoe UI", 12, "bold"))
    title_label.pack(pady=(0, 10))
    
    # Área de texto com scroll
    text_frame = ttk.Frame(main_frame)
    text_frame.pack(fill="both", expand=True, pady=5)
    
    text_widget = tk.Text(text_frame, wrap="word", width=80, height=25,
                         font=("Consolas", 9), bg="#f8f8f8")
    scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    
    # Inserir relatório
    text_widget.insert("1.0", report)
    text_widget.config(state="disabled")  # Somente leitura
    
    # Frame de botões
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x", pady=10)
    
    def copy_report():
        """Copia relatório para área de transferência"""
        dialog.clipboard_clear()
        dialog.clipboard_append(report)
        show_toast("Relatório copiado para área de transferência!")
    
    def save_report():
        """Salva relatório em arquivo"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
            title="Salvar Relatório de Ambiente",
            initialfile=f"juntapdf_ambiente_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                show_toast(f"Relatório salvo em: {filename}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar relatório:\n{e}")
    
    def open_ghostscript_download():
        """Abre página de download do Ghostscript"""
        webbrowser.open("https://www.ghostscript.com/download/gsdnld.html")
    
    # Botões
    ttk.Button(button_frame, text="📋 Copiar Relatório", 
              command=copy_report).pack(side="left", padx=5)
    ttk.Button(button_frame, text="💾 Salvar em Arquivo", 
              command=save_report).pack(side="left", padx=5)
    
    if not GHOSTSCRIPT_PATH:
        ttk.Button(button_frame, text="🌐 Baixar Ghostscript", 
                  command=open_ghostscript_download).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Fechar", 
              command=dialog.destroy).pack(side="right", padx=5)
    
    # Focar na diálogo
    dialog.focus_set()

def show_performance_dashboard():
    """Mostra métricas de performance do sistema"""
    dialog = tk.Toplevel(root)
    dialog.title("Dashboard de Performance - JuntaPDF")
    dialog.geometry("500x400")
    dialog.resizable(False, False)
    dialog.transient(root)
    dialog.grab_set()

    # Frame principal
    main_frame = ttk.Frame(dialog, padding="15")
    main_frame.pack(fill="both", expand=True)

    # Título
    title_label = ttk.Label(
        main_frame, 
        text="📊 Dashboard de Performance", 
        font=("Segoe UI", 12, "bold")
    )
    title_label.pack(pady=(0, 15))

    # Frame das métricas
    metrics_frame = ttk.LabelFrame(main_frame, text="Métricas do Sistema", padding="10")
    metrics_frame.pack(fill="both", expand=True, pady=5)
    
    if not PSUtil_AVAILABLE:
        warning_frame = ttk.Frame(metrics_frame)
        warning_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Label(
            warning_frame, 
            text="⚠️ Métricas limitadas - instale 'pip install psutil' para monitoramento completo",
            foreground="orange",
            font=("Segoe UI", 8, "bold"),
            justify="center"
        ).pack()

    # Coletar métricas MELHORADAS
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
        "📁 Arquivos em Cache": f"{len(pdf_metadata_cache)}",
        "🧵 Threads Ativas": f"{thread_count}",
        "💾 Memória Utilizada": f"{memory_mb:.1f} MB" if isinstance(memory_mb, float) else memory_mb,
        "⚡ CPU em Uso": f"{cpu_percent}%" if isinstance(cpu_percent, float) else cpu_percent,
        "📊 Arquivos Temporários": f"{len(temp_files_global)}",
        "🔄 Operações Canceladas": "0",  # Poderia implementar contador
        "✅ PDFs Válidos": f"{sum(1 for f in pdf_metadata_cache if 'Erro' not in f)}",
        "❌ PDFs com Erro": f"{sum(1 for f in pdf_metadata_cache if 'Erro' in f)}"
    }

    # Exibir métricas em grid
    for i, (k, v) in enumerate(metrics.items()):
        ttk.Label(metrics_frame, text=k, font=("Segoe UI", 9, "bold")).grid(
            row=i, column=0, sticky="w", padx=5, pady=3
        )
        ttk.Label(metrics_frame, text=str(v), font=("Consolas", 9)).grid(
            row=i, column=1, sticky="w", padx=10, pady=3
        )

    # Botões de ação
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill="x", pady=15)

    def clear_cache():
        """Limpa o cache de metadados"""
        pdf_metadata_cache.clear()
        show_toast("Cache limpo!")
        dialog.destroy()
        show_performance_dashboard()  # Recarrega

    def cleanup_temp_files_manual():
        """Limpeza manual de arquivos temporários"""
        cleanup_temp_files()
        show_toast("Arquivos temporários limpos!")
        dialog.destroy()
        show_performance_dashboard()

    ttk.Button(button_frame, text="🔄 Atualizar", 
              command=lambda: dialog.destroy() or show_performance_dashboard()).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="🧹 Limpar Cache", 
              command=clear_cache).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="🗑️ Limpar Temporários", 
              command=cleanup_temp_files_manual).pack(side="left", padx=5)
    
    ttk.Button(button_frame, text="Fechar", 
              command=dialog.destroy).pack(side="right", padx=5)

    # Focar na diálogo
    dialog.focus_set()
    
# Handler de exceções global
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    error_msg = f"Erro não tratado:\n\nTipo: {exc_type.__name__}\nMensagem: {str(exc_value)}"
    logging.error(f"Exceção não tratada: {exc_type.__name__}: {exc_value}", exc_info=True)
    
    print(error_msg)
    try:
        tk.messagebox.showerror("Erro", error_msg)
    except:
        pass

sys.excepthook = handle_exception

# =============================================================================
# THREAD POOL SEGURO
# =============================================================================
thread_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_CONCURRENT_OPERATIONS,
    thread_name_prefix="JuntaPDF"
)

def submit_thread_task(func, *args, **kwargs):
    """Submete tarefa para execução com limites de recursos"""
    performance_monitor.check_system_health()
    return thread_executor.submit(func, *args, **kwargs)

# =============================================================================
# INICIALIZAÇÃO DE BIBLIOTECAS
# =============================================================================

# Verificação do tkinterdnd2
DND_AVAILABLE = False
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
    logging.info("tkinterdnd2 disponível")
except ImportError:
    DND_AVAILABLE = False
    logging.warning("tkinterdnd2 não disponível - arrastar/soltar desabilitado")

# Tenta importar PyPDF2
try:
    from PyPDF2 import PdfMerger, PdfReader, PdfWriter
    PDF_LIBS_AVAILABLE = True
    logging.info("PyPDF2 disponível")
except ImportError as e:
    PDF_LIBS_AVAILABLE = False  
    logging.error(f"PyPDF2 não disponível: {e}")
    messagebox.showerror("Erro", "PyPDF2 é necessário para o funcionamento do programa!\n\nExecute o instalador 'install.bat' primeiro.")
    sys.exit(1)

# Tenta importar pikepdf
try:
    import pikepdf
    PIKEPDF_AVAILABLE = True
    logging.info("pikepdf disponível")
except ImportError:
    PIKEPDF_AVAILABLE = False
    logging.warning("pikepdf não disponível - algumas funcionalidades estarão limitadas")

# Criar janela principal
try:
    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
        logging.info("Janela criada com suporte a Drag & Drop")
    else:
        root = tk.Tk()
        logging.info("Janela criada sem suporte a Drag & Drop")
except Exception as e:
    logging.error(f"Erro ao criar janela: {e}")
    root = tk.Tk()
    DND_AVAILABLE = False

# =============================================================================
# VARIÁVEIS GLOBAIS
# =============================================================================

# Flag global para cancelamento
cancel_operation = False

# --- VARIÁVEIS PARA ESTATÍSTICAS ---
total_files_merge_var = tk.StringVar(value="Arquivos: 0")
total_pages_merge_var = tk.StringVar(value="Páginas: 0") 
total_size_merge_var = tk.StringVar(value="Tamanho: 0 MB")

total_files_split_var = tk.StringVar(value="Arquivos: 0")
total_pages_split_var = tk.StringVar(value="Páginas: 0") 
total_size_split_var = tk.StringVar(value="Tamanho: 0 MB")

# 🔒 CORREÇÃO 2: LOCK PARA TEMP FILES
temp_files_global = []
temp_files_lock = threading.Lock()

def add_temp_file(file_path):
    """Adiciona arquivo temporário com lock - VERSÃO CORRIGIDA"""
    with temp_files_lock:
        if file_path not in temp_files_global:
            temp_files_global.append(file_path)
            logging.debug(f"Arquivo temporário registrado: {file_path}")

def remove_temp_file(file_path):
    """Remove arquivo temporário com lock - VERSÃO CORRIGIDA"""
    with temp_files_lock:
        if file_path in temp_files_global:
            temp_files_global.remove(file_path)
            logging.debug(f"Arquivo temporário removido: {file_path}")

# Variáveis para os badges
merge_badge_var = tk.StringVar(value="")
split_badge_var = tk.StringVar(value="")

# Variáveis de controle
split_all_var = tk.BooleanVar(value=False)
protect_var = tk.BooleanVar(value=False)
pdfa_var = tk.BooleanVar(value=False)
pdfa_var_split = tk.BooleanVar(value=False)
compress_var = tk.BooleanVar(value=False)
meta_var = tk.BooleanVar(value=False)

# Variáveis para os novos modos de divisão
split_mode_var = tk.StringVar(value="extract")  # "extract", "all", "interval", "parts"
split_interval_var = tk.StringVar(value="5")
split_parts_var = tk.StringVar(value="3")

# Variável de status global - DEFINIDA ANTES DE QUALQUER USO
status_var = tk.StringVar()

# Variável para nível de compressão
compress_level = tk.StringVar(value="Otimização Automática")

def safe_temp_file(prefix="temp", suffix=".pdf"):
    """Cria arquivo temporário seguro"""
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
    
def estimate_final_size(files, options):
    """Estima tamanho final do arquivo"""
    total_size = 0
    for f in files:
        if os.path.exists(f):
            total_size += os.path.getsize(f)
    
    if options.get('compress'):
        # Estimativa conservadora de compressão
        reduction_factor = 0.7  # 30% de redução
        total_size *= reduction_factor
    
    return max(total_size, 1024)  # Mínimo 1KB
# =============================================================================
# 🚨 CORREÇÃO CRÍTICA 1: CLEANUP ROBUSTO COM REGISTRO ÚNICO
# =============================================================================
def cleanup_temp_files():
    """Limpa arquivos temporários ao fechar o programa e encerra o executor com timeout seguro."""
    logging.info("Iniciando limpeza de arquivos temporários")
    
    # Remove arquivos temporários rastreados
    with temp_files_lock:
        files_to_clean = list(temp_files_global)
        
    for temp_file in files_to_clean:
        try:
            if os.path.exists(temp_file):
                os.remove(temp_file)
                logging.debug(f"Arquivo temporário removido: {temp_file}")
        except Exception as e:
            logging.warning(f"Erro ao limpar {temp_file}: {e}")

    # Limpar checkpoint
    try:
        cleanup_checkpoint()
    except Exception as e:
        logging.warning(f"Erro ao limpar checkpoint: {e}")

    # Parar thread executor com fallback caso a versão do Python não aceite timeout
    try:
        thread_executor.shutdown(wait=True, timeout=5)
    except TypeError:
        # Algumas versões não suportam timeout no shutdown; tenta sem timeout
        try:
            thread_executor.shutdown(wait=True)
        except Exception as e:
            logging.warning(f"Falha ao encerrar thread_executor: {e}")
    except Exception as e:
        logging.warning(f"Erro ao encerrar thread_executor: {e}")

# Registrar a limpeza automática UMA ÚNICA VEZ
if not _atexit_cleanup_registered:
    atexit.register(cleanup_temp_files)
    _atexit_cleanup_registered = True
    logging.info("Cleanup registrado no atexit")

# =============================================================================
# 🚨 CORREÇÃO CRÍTICA 2: GERENCIAMENTO SEGURO DE WIDGETS
# =============================================================================
def widget_exists(widget):
    """Verifica se um widget existe e é válido"""
    try:
        return widget is not None and hasattr(widget, "winfo_exists") and widget.winfo_exists()
    except Exception:
        return False

def safe_widget_config(widget, **kwargs):
    """Configura um widget apenas se ele existir e for válido."""
    try:
        if widget is None:
            return False
        # winfo_exists pode levantar em alguns cenários; proteger com try
        if hasattr(widget, "winfo_exists") and widget.winfo_exists():
            try:
                widget.config(**kwargs)
                return True
            except tk.TclError:
                return False
    except Exception:
        return False
    return False

# =============================================================================
# 🚨 CORREÇÃO 2: GERENCIAMENTO DE PROCESSOS GHOSTSCRIPT ROBUSTO (I18N)
# =============================================================================
def kill_ghostscript_processes():
    """Mata processos Ghostscript de forma robusta (multilíngue)"""
    try:
        killed = 0
        
        # Windows
        if sys.platform == "win32":
            # ✅ ROBUSTO: taskkill retorna 0 se matou algo, 128 se não encontrou
            result1 = exec_segura(["taskkill", "/f", "/im", "gswin64c.exe"], 
                                timeout=10, descricao="Kill gswin64c")
            result2 = exec_segura(["taskkill", "/f", "/im", "gswin32c.exe"], 
                                timeout=10, descricao="Kill gswin32c")
            
            # ✅ CORRETO: returncode == 0 significa SUCESSO (qualquer idioma)
            if result1.returncode == 0 or result2.returncode == 0:
                killed = 1
                logging.info("Processos Ghostscript finalizados no Windows")
            else:
                logging.info("Nenhum processo Ghostscript encontrado para finalizar")
                
        # Linux/Mac
        else:
            result = exec_segura(["pkill", "-f", "gs"], 
                               timeout=10, descricao="Kill gs processes")
            
            # ✅ pkill retorna 0 se matou processos, 1 se não encontrou
            if result.returncode == 0:
                killed = 1
                logging.info("Processos Ghostscript finalizados no Linux/Mac")
            else:
                logging.info("Nenhum processo Ghostscript encontrado para finalizar")
                
        return killed
        
    except Exception as e:
        logging.error(f"Erro ao finalizar processos Ghostscript: {e}")
        return 0

# -----------------------
# GHOSTSCRIPT E ICC - DETECÇÃO AUTOMÁTICA
# -----------------------
def encontrar_ghostscript():
    """Localiza o executável do Ghostscript no sistema."""
    logging.info("Procurando Ghostscript no sistema...")
    # Tenta encontrar no PATH
    for cmd in ("gswin64c", "gswin32c", "gs"):
        caminho = shutil.which(cmd)
        if caminho:
            logging.info(f"Ghostscript encontrado no PATH: {caminho}")
            return caminho

    # Procura em pastas comuns do Windows
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
            logging.info(f"Ghostscript encontrado em: {versoes[0]}")
            return versoes[0]

    logging.warning("Ghostscript não encontrado no sistema")
    return None

def encontrar_perfil_icc(gs_exec):
    """
    Encontra o perfil ICC sRGB que vem com o Ghostscript.
    Busca automaticamente baseado na localização do executável.
    """
    if not gs_exec:
        return None
    
    # Deriva o diretório base do Ghostscript
    gs_dir = os.path.dirname(os.path.dirname(gs_exec))  # sobe 2 níveis de /bin/
    
    # Locais possíveis do perfil ICC
    possible_paths = [
        os.path.join(gs_dir, "iccprofiles", "srgb.icc"),
        os.path.join(gs_dir, "iccprofiles", "default_rgb.icc"),
        os.path.join(gs_dir, "lib", "srgb.icc"),
        os.path.join(gs_dir, "Resource", "ColorSpace", "sRGB.icc"),
    ]
    
    # Verifica se algum existe
    for icc_path in possible_paths:
        if os.path.exists(icc_path):
            logging.info(f"Perfil ICC encontrado: {icc_path}")
            return icc_path
    
    # Busca recursiva na pasta do Ghostscript (última tentativa)
    try:
        for root, dirs, files in os.walk(gs_dir):
            for file in files:
                if file.lower() in ("srgb.icc", "default_rgb.icc"):
                    found_path = os.path.join(root, file)
                    logging.info(f"Perfil ICC encontrado (busca recursiva): {found_path}")
                    return found_path
    except Exception as e:
        logging.warning(f"Erro na busca recursiva por ICC: {e}")
    
    logging.warning("Perfil ICC não encontrado")
    return None

def validate_file_security(file_path):
    """
    Valida segurança do arquivo antes do processamento
    CORREÇÃO: Esta função estava FALTANDO no código original
    """
    # Verificar se arquivo existe
    if not os.path.exists(file_path):
        raise SecurityError(f"Arquivo não existe: {file_path}")
    
    # Verificar tamanho máximo
    file_size = os.path.getsize(file_path)
    if file_size > MAX_FILE_SIZE:
        raise SecurityError(f"Arquivo muito grande: {file_size/1024/1024:.1f}MB > {MAX_FILE_SIZE/1024/1024:.1f}MB")
    
    # Verificar se é PDF pela assinatura
    try:
        with open(file_path, 'rb') as f:
            header = f.read(4)
            if header != b'%PDF':
                raise SecurityError("Arquivo não é um PDF válido")
    except Exception as e:
        raise SecurityError(f"Erro ao validar arquivo: {e}")
    
    return True
    
class ThreadManager:
    """Gerencia threads de forma segura - CORREÇÃO: Esta classe estava FALTANDO"""
    def __init__(self):
        self.executor = None
        self.lock = threading.RLock()
        
    def submit_task(self, task_function):
        """Submete tarefa para execução em thread"""
        with self.lock:
            if self.executor is None:
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
            return self.executor.submit(task_function)
    
    def shutdown(self):
        """Finaliza executor de threads"""
        with self.lock:
            if self.executor is not None:
                self.executor.shutdown(wait=False)
                self.executor = None

# Instância global do gerenciador de threads
thread_manager = ThreadManager()

def submit_thread_task(task_function):
    """Submete tarefa para thread de forma segura"""
    return thread_manager.submit_task(task_function)

def validate_output_pdf(file_path):
    """Valida se o PDF de saída é válido e legível"""
    try:
        # Verificar se arquivo existe e tem tamanho razoável
        if not os.path.exists(file_path):
            return False, "Arquivo de saída não existe"
        
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            return False, "Arquivo de saída está vazio"
        
        if file_size < 100:  # PDF mínimo tem pelo menos 100 bytes
            return False, "Arquivo de saída é muito pequeno para ser um PDF válido"
        
        with open(file_path, 'rb') as f:
            # Verificar assinatura PDF
            header = f.read(4)
            if header != b'%PDF':
                return False, "Arquivo de saída não é um PDF válido (assinatura incorreta)"
            
            # Verificar se é legível
            try:
                f.seek(0)
                reader = PdfReader(f)
                
                if len(reader.pages) == 0:
                    return False, "PDF de saída não contém páginas"
                
                # Tentar acessar metadados básicos (não crítico se falhar)
                try:
                    _ = reader.metadata
                except:
                    logging.debug("Metadados do PDF não acessíveis (pode ser normal)")
                
                # Verificar algumas páginas para garantir que são acessíveis
                pages_to_check = min(3, len(reader.pages))
                for i in range(pages_to_check):
                    try:
                        _ = reader.pages[i].extract_text()
                    except:
                        # Não crítico se não conseguir extrair texto
                        pass
                        
            except Exception as e:
                return False, f"PDF de saída corrompido ou ilegível: {str(e)}"
        
        return True, f"PDF válido ({len(reader.pages)} páginas, {file_size/1024/1024:.2f} MB)"
        
    except Exception as e:
        return False, f"Erro na validação: {str(e)}"
# Detecta Ghostscript e ICC na inicialização
GHOSTSCRIPT_PATH = encontrar_ghostscript()
ICC_PROFILE_PATH = encontrar_perfil_icc(GHOSTSCRIPT_PATH) if GHOSTSCRIPT_PATH else None
PDFA_AVAILABLE = bool(GHOSTSCRIPT_PATH and ICC_PROFILE_PATH)

def comprimir_com_ghostscript(input_path, output_path, nivel="Otimização Automática"):
    """
    Compressão REAL de PDF usando Ghostscript com diferentes níveis
    """
    if not GHOSTSCRIPT_PATH:
        raise PDFProcessingError("Ghostscript não disponível para compressão")
    
    # Mapeamento de níveis de compressão
    niveis = {
        "Qualidade Máxima": "/printer",      # Balanço ideal qualidade/tamanho
        "Qualidade Equilibrada": "/ebook",      # Boa qualidade, menor tamanho  
        "Tamanho Mínimo": "/screen"           # Tamanho mínimo, qualidade reduzida
    }
    
    comando = [
        GHOSTSCRIPT_PATH,
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS={niveis.get(nivel, '/printer')}",
        "-dCompatibilityLevel=1.4",
        "-dNOPAUSE", "-dQUIET", "-dBATCH",
        "-dDetectDuplicateImages=true",
        "-dCompressFonts=true",
        "-dCompressPages=true",
        f"-sOutputFile={output_path}", 
        input_path
    ]
    
    logging.info(f"Iniciando compressão: {os.path.basename(input_path)} -> {nivel}")
    resultado = exec_segura(comando, timeout=120, descricao="Compressão Ghostscript")
    
    if resultado.returncode != 0:
        error_msg = resultado.stderr or "Erro desconhecido"
        logging.error(f"Falha na compressão Ghostscript: {error_msg}")
        raise PDFProcessingError(f"Falha na compressão: {error_msg}")
    
    # Verificar se arquivo de saída foi criado
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise PDFProcessingError("Arquivo comprimido não foi gerado ou está vazio")
    
    tamanho_original = os.path.getsize(input_path) / 1024 / 1024
    tamanho_comprimido = os.path.getsize(output_path) / 1024 / 1024
    reducao = ((tamanho_original - tamanho_comprimido) / tamanho_original) * 100
    
    logging.info(f"Compressão concluída: {tamanho_original:.1f}MB -> {tamanho_comprimido:.1f}MB (-{reducao:.1f}%)")
    
    return reducao

if PDFA_AVAILABLE:
    logging.info("PDF/A disponível: Ghostscript e ICC encontrados")
else:
    logging.warning("PDF/A indisponível: Ghostscript ou ICC não encontrados")

# =============================================================================
# FUNÇÕES AUXILIARES DA INTERFACE
# =============================================================================

# -----------------------
# ToolTip / Toast helper
# -----------------------
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
    """Mostra toast apenas se não houver messagebox ativo"""
    try:
        # Verifica se há algum messagebox ativo
        for widget in root.winfo_children():
            if isinstance(widget, tk.Toplevel) and any(isinstance(child, tk.Message) for child in widget.winfo_children()):
                logging.debug("Messagebox detectado - suprimindo toast")
                return
        
        toast = tk.Toplevel(root)
        toast.overrideredirect(True)
        toast.configure(bg="#333333")
        toast.attributes("-topmost", True)
        label = tk.Label(toast, text=message, fg="white", bg="#333333", font=("Segoe UI", 10))
        label.pack(ipadx=10, ipady=5)
        x = root.winfo_rootx() + 20
        y = root.winfo_rooty() + root.winfo_height() - 50
        toast.geometry(f"+{x}+{y}")
        toast.after(duration, toast.destroy)
        logging.debug(f"Toast exibido: {message}")
    except Exception as e:
        logging.warning(f"Erro ao exibir toast: {e}")

def abrir_pasta_output(folder):
    """Abre a pasta de saída no explorador de arquivos"""
    try:
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":  # macOS
            subprocess.call(["open", folder])
        else:  # Linux
            subprocess.call(["xdg-open", folder])
        logging.info(f"Pasta aberta: {folder}")
    except Exception as e:
        logging.error(f"Erro ao abrir pasta: {e}")
        show_toast("Erro ao abrir pasta de saída")

def debounce(wait):
    """Decorator para debounce de funções (evita múltiplas execuções rápidas)"""
    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                fn(*args, **kwargs)
            if hasattr(debounced, '_timer'):
                debounced._timer.cancel()
            debounced._timer = threading.Timer(wait, call_it)
            debounced._timer.start()
        return debounced
    return decorator

# Aplicar debounce a funções pesadas
def process_in_batches(file_list, batch_size=10):
    """Processa muitos arquivos em lotes para evitar sobrecarga"""
    for i in range(0, len(file_list), batch_size):
        batch = file_list[i:i + batch_size]
        yield batch
        # Pequena pausa entre lotes
        time.sleep(0.5)
        if cancel_operation:
            break
@debounce(0.3)
def update_stats_debounced(listbox, files_var, pages_var, size_var):
    update_stats(listbox, files_var, pages_var, size_var)

# -----------------------
# Validação de PDFs SEGURA
# -----------------------
def safe_pdf_reader(file_path):
    """Wrapper seguro para ler PDFs potencialmente corrompidos"""
    try:
        validate_file_security(file_path)
        
        with open(file_path, 'rb') as f:
            # Verificar assinatura PDF novamente
            if f.read(4) != b'%PDF':
                raise PDFCorruptionError("Arquivo não é um PDF válido")
            
        reader = PdfReader(file_path)
        # Tentar acessar propriedades críticas
        _ = len(reader.pages)
        _ = reader.metadata
        
        return reader
    except Exception as e:
        logging.error(f"PDF corrompido ou inválido: {file_path} - {e}")
        raise PDFCorruptionError(f"PDF corrompido ou inválido: {os.path.basename(file_path)}")

def validate_pdf(path):
    """Valida se o PDF é legível e não está corrompido."""
    try:
        # Validação de segurança primeiro
        validate_file_security(path)
        
        # Agora valida o conteúdo do PDF
        reader = safe_pdf_reader(path)
        _ = len(reader.pages)
        return True, None
    except (SecurityError, PDFCorruptionError) as e:
        logging.warning(f"PDF inválido ou inseguro: {path} - {e}")
        return False, str(e)
    except Exception as e:
        logging.warning(f"PDF inválido: {path} - {e}")
        return False, str(e)

# -----------------------
# Função para atualizar estatísticas
# -----------------------
def update_stats(listbox, files_var, pages_var, size_var):
    """Atualiza estatísticas baseadas nos arquivos da listbox"""
    files = list(listbox.get(0, tk.END))
    total_pages = 0
    total_size_bytes = 0
    
    # Limite de arquivos para prevenir sobrecarga
    if len(files) > MAX_FILES_PER_OPERATION:
        files = files[:MAX_FILES_PER_OPERATION]
        logging.warning(f"Limite de {MAX_FILES_PER_OPERATION} arquivos excedido")
    
    for f in files:
        try:
            reader = safe_pdf_reader(f)
            total_pages += len(reader.pages)
            total_size_bytes += os.path.getsize(f)
            
            # Verificar limite total de páginas
            if total_pages > MAX_TOTAL_PAGES:
                raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")
                
        except Exception as e:
            logging.warning(f"Erro ao ler {f} para estatísticas: {e}")
    
    # Atualizar variáveis
    files_var.set(f"Arquivos: {len(files)}")
    pages_var.set(f"Páginas: {total_pages}")
    
    # Converter tamanho para MB/KB
    if total_size_bytes > 1024 * 1024:  # Mais de 1MB
        size_mb = total_size_bytes / (1024 * 1024)
        size_var.set(f"Tamanho: {size_mb:.1f} MB")
    else:
        size_kb = total_size_bytes / 1024
        size_var.set(f"Tamanho: {size_kb:.1f} KB")

def get_pdf_info(path):
    """Retorna string com informações básicas do PDF para tooltip."""
    
    # 🔥 VERIFICAR CACHE PRIMEIRO
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
        
        return (
            f"{os.path.basename(path)}\n"
            f"Páginas: {num_pages}\n"
            f"Título: {title}\n"
            f"Autor: {author}\n"
            f"Tamanho: {size_kb} KB{encryption_note}"
        )
    except Exception as e:
        return f"{os.path.basename(path)}\n[Erro ao ler PDF: {e}]"

def attach_dynamic_tooltips(listbox):
    """Tooltips dinâmicos: troca imediatamente ao mudar de item."""
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

# -----------------------
# Drag & Drop para reordenar
# -----------------------
def setup_drag_reorder(listbox):
    """Configura arrastar e soltar para reordenar itens."""
    drag_data = {"index": None, "item": None}
    
    def on_drag_start(event):
        index = listbox.nearest(event.y)
        if index >= 0 and index < listbox.size():
            drag_data["index"] = index
            drag_data["item"] = listbox.get(index)
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)
    
    def on_drag_motion(event):
        current_index = listbox.nearest(event.y)
        if current_index >= 0 and current_index < listbox.size():
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(current_index)
    
    def on_drop(event):
        if drag_data["item"] is None:
            return
        
        drop_index = listbox.nearest(event.y)
        if drop_index >= 0 and drop_index < listbox.size():
            listbox.delete(drag_data["index"])
            listbox.insert(drop_index, drag_data["item"])
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(drop_index)
            status_var.set("Item reordenado.")
        
        drag_data["index"] = None
        drag_data["item"] = None
    
    listbox.bind("<Button-1>", on_drag_start)
    listbox.bind("<B1-Motion>", on_drag_motion)
    listbox.bind("<ButtonRelease-1>", on_drop)

# -----------------------
# Movimento estável
# -----------------------
def move_up(listbox, event=None):
    """Move todos os itens selecionados uma posição para cima."""
    listbox.focus_set()
    sel = list(listbox.curselection())
    if not sel:
        return
    for i, idx in enumerate(sel):
        if idx == 0:
            continue
        text = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx - 1, text)
        sel[i] = idx - 1
    listbox.selection_clear(0, tk.END)
    for idx in sel:
        listbox.selection_set(idx)
    status_var.set("Ordem alterada.")

def move_down(listbox, event=None):
    """Move todos os itens selecionados uma posição para baixo."""
    listbox.focus_set()
    sel = list(listbox.curselection())
    if not sel:
        return
    size = listbox.size()
    for i in range(len(sel) - 1, -1, -1):
        idx = sel[i]
        if idx == size - 1:
            continue
        text = listbox.get(idx)
        listbox.delete(idx)
        listbox.insert(idx + 1, text)
        sel[i] = idx + 1
    listbox.selection_clear(0, tk.END)
    for idx in sel:
        listbox.selection_set(idx)
    status_var.set("Ordem alterada.")

# -----------------------
# 🚨 CORREÇÃO: MENU DE CONTEXTO COM BOTÃO DIREITO
# -----------------------
def setup_context_menu(listbox, files_var, pages_var, size_var):
    """Configura menu de contexto com botão direito para a listbox"""
    context_menu = tk.Menu(listbox, tearoff=0)
    
    def show_context_menu(event):
        # Seleciona o item sob o cursor
        index = listbox.nearest(event.y)
        if 0 <= index < listbox.size():
            listbox.selection_clear(0, tk.END)
            listbox.selection_set(index)
            listbox.activate(index)
        
        # Mostra o menu no local do clique
        try:
            context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            context_menu.grab_release()
    
    def remove_selected_context():
        remove_selected(listbox, files_var, pages_var, size_var)
    
    def open_selected_context():
        selection = listbox.curselection()
        if selection:
            file_path = listbox.get(selection[0])
            open_pdf(listbox, tk.Event())
    
    def show_file_info():
        selection = listbox.curselection()
        if selection:
            file_path = listbox.get(selection[0])
            info = get_pdf_info(file_path)
            messagebox.showinfo("Informações do PDF", info)
    
    def clear_all_context():
        clear_list(listbox, files_var, pages_var, size_var)
    
    # Adiciona itens ao menu
    context_menu.add_command(label="Abrir PDF", command=open_selected_context)
    context_menu.add_command(label="Informações", command=show_file_info)
    context_menu.add_separator()
    context_menu.add_command(label="Remover Selecionado(s)", command=remove_selected_context)
    context_menu.add_command(label="Limpar Lista", command=clear_all_context)
    
    # Vincula o menu de contexto ao botão direito
    listbox.bind("<Button-3>", show_context_menu)  # Button-3 = botão direito
    
    return context_menu

# -----------------------
# Funções comuns
# -----------------------
def add_files(listbox, files_var, pages_var, size_var, event=None):
    files = filedialog.askopenfilenames(filetypes=[("Arquivos PDF", "*.pdf")])
    added = 0
    invalid = []
    
    # Verificar limite de arquivos
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
        update_stats_debounced(listbox, files_var, pages_var, size_var)
    
    # CORREÇÃO: Atualizar estado dos botões após adicionar arquivos
    enable_submit_on_conditions()

def remove_selected(listbox, files_var, pages_var, size_var, event=None):
    """🔒 CORREÇÃO 5: MULTI-SELECÇÃO FUNCIONAL - AGORA CORRIGIDA"""
    selected = list(listbox.curselection())
    if not selected:
        return
    
    # 🔥 CORREÇÃO CRÍTICA: Ordena em ordem DECRESCENTE para evitar problemas de índice
    selected.sort(reverse=True)
    
    removed_files = []
    for i in selected:
        removed_file = listbox.get(i)
        listbox.delete(i)
        removed_files.append(os.path.basename(removed_file))
        logging.info(f"Arquivo removido: {os.path.basename(removed_file)}")
    
    status_var.set(f"{len(removed_files)} arquivo(s) removido(s).")
    show_toast(f"{len(removed_files)} arquivo(s) removido(s).")
    update_stats_debounced(listbox, files_var, pages_var, size_var)
    
    # CORREÇÃO: Atualizar estado dos botões após remover arquivos
    enable_submit_on_conditions()

def clear_list(listbox, files_var, pages_var, size_var, event=None):
    if listbox.size() == 0:
        return
    listbox.delete(0, tk.END)
    status_var.set("Lista limpa.")
    show_toast("Lista limpa.")
    update_stats_debounced(listbox, files_var, pages_var, size_var)
    
    # CORREÇÃO: Atualizar estado dos botões após limpar lista
    enable_submit_on_conditions()

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
    update_stats_debounced(listbox, files_var, pages_var, size_var)
    
    # CORREÇÃO: Atualizar estado dos botões após ordenar
    enable_submit_on_conditions()

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
        if counter > 1000:  # Limite de segurança
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

# -----------------------
# Parse intervalos de páginas SEGURO
# -----------------------
def parse_page_ranges(ranges_str, max_pages):
    """Converte "1-3,5,10-15" em [1,2,3,5,10,11,12,13,14,15] COM VALIDAÇÃO"""
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
                
                # VALIDAÇÃO CRÍTICA: prevenir números negativos e fora do range
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
                # VALIDAÇÃO CRÍTICA
                if page_num < 1:
                    raise ValueError("Números de página devem ser positivos")
                if page_num > max_pages:
                    raise ValueError(f"Números de página devem ser <= {max_pages}")
                pages.add(page_num)

        # Remover duplicatas e ordenar
        pages = sorted(list(pages))
        
        # Verificar limite de páginas
        if len(pages) > MAX_TOTAL_PAGES:
            raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")
            
        return pages
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("Formato inválido. Use: 1-5, 10, 20-30")
        else:
            raise

# -----------------------
# UI State Management - AGORA COM SEGURANÇA
# -----------------------
def set_ui_state(enabled):
    """Habilita ou desabilita elementos da UI durante processamento - COM VERIFICAÇÕES SEGURAS"""
    state = "normal" if enabled else "disabled"
    
    # Usar safe_widget_config para todos os widgets
    safe_widget_config(btn_merge, state=state)
    safe_widget_config(btn_split, state=state)
    
    # Verificar frames de botões
    if 'btn_frame_merge' in globals():
        for widget in btn_frame_merge.winfo_children():
            if isinstance(widget, ttk.Button):
                safe_widget_config(widget, state=state)
    
    if 'btn_frame_split' in globals():
        for widget in btn_frame_split.winfo_children():
            if isinstance(widget, ttk.Button):
                safe_widget_config(widget, state=state)
    
    # Esconde botões de cancelamento se existirem
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
    else:
        safe_widget_config(root, cursor="watch")

def validate_pdfa_protection_compatibility():
    """
    Valida e ajusta automaticamente o conflito entre PDF/A e proteção por senha.
    Regra: PDF/A e proteção por senha são MUTUAMENTE EXCLUSIVOS.
    """
    protect_on = protect_var.get()
    pdfa_on = pdfa_var.get()
    
    # Se ambos estão ativos, resolva o conflito
    if protect_on and pdfa_on:
        # Prioridade: mantém a última opção que o usuário ativou
        # Se o usuário acabou de marcar proteção, desliga PDF/A
        # Se o usuário acabou de marcar PDF/A, desliga proteção
        
        # Para simplificar: sempre desativa o PDF/A quando há conflito
        # (mais seguro para documentos institucionais)
        pdfa_var.set(False)
        
        # Mostra explicação educativa
        show_message_in_main_thread(
            "Incompatibilidade Detectada",
            "PDF/A e proteção por senha são incompatíveis.\n\n"
            "• PDF/A é um formato de arquivamento de longo prazo\n"
            "• Proteção por senha impede a verificação de conformidade\n\n"
            "Solução: Use apenas uma das opções por vez.\n"
            "Para documentos institucionais, recomendamos PDF/A.",
            "warning"
        )
        
        # Atualiza o texto informativo
        if widget_exists(pdfa_info_label):
            safe_widget_config(pdfa_info_label, 
                             text="PDF/A desativado - Conflito com proteção por senha",
                             foreground="orange")
    
    # Atualiza estados dos widgets
    update_protection_pdfa_states()

def update_protection_pdfa_states():
    """Atualiza estados dos widgets baseado nas seleções atuais"""
    protect_on = protect_var.get()
    pdfa_on = pdfa_var.get()
    
    # Campo de senha só fica habilitado se proteção estiver ATIVA e PDF/A INATIVO
    password_state = "normal" if protect_on and not pdfa_on else "disabled"
    safe_widget_config(password_entry, state=password_state)
    
    # Atualiza textos informativos
    if widget_exists(pdfa_info_label):
        if pdfa_on:
            safe_widget_config(pdfa_info_label, 
                             text="Formato PDF/A-2B recomendado para SEI (sem proteção por senha)",
                             foreground="darkgreen")
        elif protect_on:
            safe_widget_config(pdfa_info_label, 
                             text="PDF/A indisponível com proteção por senha ativa",
                             foreground="orange")
        else:
            safe_widget_config(pdfa_info_label, 
                             text="Formato PDF/A-2B recomendado para o Sistema Eletrônico de Informações (SEI)",
                             foreground="darkgreen")

# -----------------------
# VALIDAÇÃO DE SENHA
# -----------------------
def focus_password_entry(*_):
    """Foca automaticamente no campo de senha quando a proteção é ativada"""
    if protect_var.get():
        safe_widget_config(password_entry, state="normal")
        password_entry.focus_set()
        password_entry.select_range(0, tk.END)

def validate_page_ranges_on_type(event=None):
    """Validação em tempo real dos intervalos de páginas"""
    widget = event.widget if event else split_pages_entry
    text = widget.get()
    
    # Remove cores anteriores
    safe_widget_config(widget, foreground="black")
    
    if not text.strip():
        return True
        
    try:
        # Simula o parse para validação
        if split_all_var.get():
            return True
            
        # Validação básica - apenas verifica se é número ou intervalo
        for part in text.replace(" ", "").split(","):
            if part and "-" in part:
                start, end = part.split("-", 1)
                int(start)
                int(end)
            elif part:
                int(part)
                
        return True
    except ValueError:
        # Destaca em vermelho se inválido
        safe_widget_config(widget, foreground="red")
        return False

def auto_expand_page_ranges(text):
    """Expande automaticamente intervalos simples como '1-3' para '1,2,3'"""
    if "-" in text and "," not in text and len(text) < 10:
        try:
            start, end = text.split("-")
            start_i, end_i = int(start), int(end)
            if 1 <= start_i < end_i <= 100:  # Limite razoável
                expanded = ",".join(str(i) for i in range(start_i, end_i + 1))
                return expanded
        except ValueError:
            pass
    return text

def on_page_range_focusout(event):
    """Ao sair do campo, tenta expandir intervalos automaticamente"""
    if not split_all_var.get():
        current_text = split_pages_entry.get()
        expanded = auto_expand_page_ranges(current_text)
        if expanded != current_text:
            split_pages_entry.delete(0, tk.END)
            split_pages_entry.insert(0, expanded)
            show_toast("Intervalo expandido automaticamente", 1500)

def enable_submit_on_conditions():
    """Habilita/desabilita botões baseado em condições mínimas"""
    has_files_merge = merge_list.size() > 0
    has_files_split = split_list.size() > 0
    
    # Para merge: precisa ter arquivos
    safe_widget_config(btn_merge, state="normal" if has_files_merge else "disabled")
    
    # Para split: precisa ter arquivos E modo válido
    if has_files_split:
        mode = split_mode_var.get()
        
        # Validações por modo
        valid = False
        if mode == "extract":
            valid = bool(split_pages_entry.get().strip())
        elif mode == "all":
            valid = True
        elif mode == "interval":
            try:
                valid = int(split_interval_var.get()) > 0
            except:
                valid = False
        elif mode == "parts":
            try:
                valid = int(split_parts_var.get()) > 0
            except:
                valid = False
        
        safe_widget_config(btn_split, state="normal" if valid else "disabled")
    else:
        safe_widget_config(btn_split, state="disabled")

def setup_ux_enhancements():
    """Configura todas as melhorias de UX"""
    # Validação em tempo real para páginas
    split_pages_entry.bind("<KeyRelease>", validate_page_ranges_on_type)
    split_pages_entry.bind("<FocusOut>", on_page_range_focusout)
    
    # Atualização automática dos botões
    for widget in [merge_list, split_list]:
        widget.bind("<<ListboxSelect>>", lambda e: enable_submit_on_conditions())
    
    split_all_var.trace_add("write", lambda *_: enable_submit_on_conditions())
    split_pages_entry.bind("<KeyRelease>", lambda e: enable_submit_on_conditions())
    
    # Enter para submeter nos campos
    password_entry.bind("<Return>", lambda e: merge_pdfs())
    split_pages_entry.bind("<Return>", lambda e: split_or_extract_pdfs())
    
    # Tooltip persistente para o campo de páginas
    pages_tooltip = ToolTip(split_pages_entry, 
        "Exemplos:\n• 1-5 (páginas 1 a 5)\n• 1,3,5 (páginas 1, 3 e 5)\n• 1-3,7,10-15 (combina intervalos)")
    
    def show_pages_tooltip(event):
        pages_tooltip.schedule_show()
    
    def hide_pages_tooltip(event):
        pages_tooltip.hide()
    
    split_pages_entry.bind("<Enter>", show_pages_tooltip)
    split_pages_entry.bind("<Leave>", hide_pages_tooltip)

def add_file_count_badge(listbox, badge_var):
    """Adiciona contador de arquivos na aba"""
    def update_badge():
        count = listbox.size()
        badge_var.set(f" ({count})" if count > 0 else "")
    
    listbox.bind("<<ListboxSelect>>", lambda e: update_badge())
    return update_badge

def focus_compress_combo(*_):
    """Foca automaticamente no combo de compressão quando ativado"""
    if compress_var.get():
        safe_widget_config(compress_combo, state="normal")
        compress_combo.focus_set()

def validate_password_strength(password):
    """Valida força básica da senha"""
    if not password:
        return False, "Senha não pode estar vazia"
    
    if len(password) < 4:
        return False, "Senha muito curta (mínimo 4 caracteres)"
    
    return True, "Senha OK"

def show_status(message, type="info"):
    """Mostra status com cores diferentes - COM VERIFICAÇÃO DE SEGURANÇA"""
    try:
        colors = {
            "info": "blue",
            "success": "darkgreen", 
            "warning": "orange",
            "error": "red"
        }
        status_var.set(message)
        # Verifica se status_label já foi criado
        if 'status_label' in globals():
            safe_widget_config(status_label, foreground=colors.get(type, "blue"))
    except Exception as e:
        logging.debug(f"Erro ao atualizar status: {e}")


def check_dependencies():
    """Verificação simplificada de dependências - CORREÇÃO: Função faltando"""
    logging.info("✅ Dependências verificadas:")
    logging.info(f"   - PyPDF2: {PDF_LIBS_AVAILABLE}")
    logging.info(f"   - pikepdf: {PIKEPDF_AVAILABLE}")
    logging.info(f"   - Ghostscript: {bool(GHOSTSCRIPT_PATH)}")
    logging.info(f"   - PDF/A: {PDFA_AVAILABLE}")
    logging.info(f"   - Drag & Drop: {DND_AVAILABLE}")

def show_first_run_disclaimer():
    """Mostra aviso inicial se necessário - CORREÇÃO: Função faltando"""
    # Pode deixar vazio ou adicionar um aviso opcional
    pass

def offer_recovery_on_startup():
    """Oferece recuperação de operação anterior - CORREÇÃO: Função faltando"""
    # Pode deixar vazio - funcionalidade opcional
    pass

def create_operation_checkpoint(operation_type, files_processed, current_step, temp_files):
    """Cria checkpoint para recuperação - CORREÇÃO: Função faltando"""
    # Funcionalidade avançada - pode deixar como placeholder
    pass

def cleanup_checkpoint():
    """Limpa checkpoint - CORREÇÃO: Função faltando"""
    # Funcionalidade avançada - pode deixar como placeholder
    pass

def show_environment_check():
    """Mostra verificação de ambiente - CORREÇÃO: Função faltando"""
    try:
        info = f"""Verificação do Ambiente JuntaPDF:

PyPDF2: {'✅ Disponível' if PDF_LIBS_AVAILABLE else '❌ Não disponível'}
pikepdf: {'✅ Disponível' if PIKEPDF_AVAILABLE else '❌ Não disponível'}
Ghostscript: {'✅ ' + GHOSTSCRIPT_PATH if GHOSTSCRIPT_PATH else '❌ Não encontrado'}
PDF/A: {'✅ Disponível' if PDFA_AVAILABLE else '❌ Indisponível'}
Drag & Drop: {'✅ Disponível' if DND_AVAILABLE else '❌ Não disponível'}

Python: {sys.version}
Sistema: {sys.platform}"""
        
        messagebox.showinfo("Verificação de Ambiente", info)
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao verificar ambiente: {e}")
# =============================================================================
# 🚨 CORREÇÃO 4: MESSAGEBOX NA THREAD PRINCIPAL
# =============================================================================
def show_message_in_main_thread(title, message, type="info"):
    """Exibe messagebox de forma segura na thread principal"""
    def show():
        if type == "error":
            messagebox.showerror(title, message)
        elif type == "warning":
            messagebox.showwarning(title, message)
        else:
            messagebox.showinfo(title, message)
    
    root.after(0, show)

# =============================================================================
# FUNÇÕES PRINCIPAIS DE PROCESSAMENTO - COM SEGURANÇA
# =============================================================================

# 🚨 CORREÇÃO 3: CRIPTOGRAFIA COMPATÍVEL ENTRE VERSÕES PyPDF2
def aplicar_criptografia(writer, password):
    """
    Aplica criptografia COMPATÍVEL entre versões do PyPDF2
    CORREÇÃO CRÍTICA: Método que realmente funciona
    """
    if not password or len(password.strip()) == 0:
        raise ValueError("Senha não pode estar vazia")
    
    logging.info("Aplicando criptografia ao PDF...")
    
    try:
        # 🔥 VERIFICAÇÃO DE SEGURANÇA: Garante que há páginas antes de criptografar
        if not hasattr(writer, '_pages') or len(writer._pages) == 0:
            raise PDFProcessingError("Não é possível criptografar PDF sem páginas")
        
        # ESTRATÉGIA PRINCIPAL: Método moderno do PyPDF2 com parâmetros explícitos
        writer.encrypt(
            user_password=password,
            owner_password=password,
            use_128bit=True
        )
        logging.info("✅ Criptografia aplicada com sucesso (método padrão)")
        return True
        
    except Exception as e:
        logging.error(f"❌ Falha na criptografia (método 1): {e}")
        
        # ESTRATÉGIA ALTERNATIVA: Para versões específicas
        try:
            # Tentar método alternativo para versões mais antigas
            if hasattr(writer, '_encrypt'):
                writer._encrypt(password, password, use_128bit=True)
                logging.info("✅ Criptografia aplicada (método alternativo)")
                return True
            else:
                # Última tentativa: encrypt sem parâmetros
                writer.encrypt(password)
                logging.info("✅ Criptografia aplicada (método simples)")
                return True
                
        except Exception as e2:
            logging.error(f"❌ Falha total na criptografia: {e2}")
            raise PDFProcessingError(f"Falha na criptografia: {e2}")

# -----------------------
# Funções Juntar PDFs (com threading SEGURO)
# -----------------------
def merge_pdfs_thread():
    global cancel_operation
    cancel_operation = False

    files = merge_list.get(0, tk.END)
    if not files:
        show_message_in_main_thread("Erro", "Nenhum arquivo PDF selecionado.", "error")
        return

    # 🔥 LOG DE AUDITORIA - INÍCIO
    password = password_entry.get().strip()
    log_audit_event("merge_start", files, options={
        'pdfa': pdfa_var.get(),
        'protected': protect_var.get() and bool(password),
        'compress': compress_var.get(),
        'remove_metadata': meta_var.get(),
        'file_count': len(files)
    })
    
    # 🔥 VALIDAÇÃO CONFLITO PDF/A vs PROTEÇÃO
    if pdfa_var.get() and protect_var.get() and password:
        choice = messagebox.askyesno(
            "Conflito de Opções", 
            "PDF/A e proteção por senha são INCOMPATÍVEIS.\n\n"
            "• PDF/A: padrão de arquivamento (recomendado para documentos oficiais)\n"
            "• Proteção: segurança com senha\n\n"
            "Deseja priorizar o PDF/A e REMOVER a proteção?",
            icon='warning'
        )
        if choice:
            protect_var.set(False)
            password_entry.delete(0, tk.END)
            password = ""
            show_status("PDF/A selecionado - proteção desativada", "warning")
        else:
            pdfa_var.set(False)
            show_status("Proteção mantida - PDF/A desativado", "warning")

    # VALIDAÇÃO DE LIMITES
    if len(files) > MAX_FILES_PER_OPERATION:
        show_message_in_main_thread("Erro", f"Máximo de {MAX_FILES_PER_OPERATION} arquivos por operação.", "error")
        return

    folder = merge_output_entry.get() or os.path.dirname(files[0])
    
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        show_message_in_main_thread("Erro", f"Não foi possível criar diretório:\n{folder}\n\nErro: {e}", "error")
        return

    # Validação de senha
    password = password_entry.get().strip()
    if protect_var.get() and password:
        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            show_message_in_main_thread("Senha Fraca", f"{msg}\n\nDeseja continuar mesmo assim?", "warning")
    
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

    # CALCULAR PROGRESSO REAL
    total_steps = len(files) + 3
    current_step = 0
    
    progress_widget = None
    if 'progress_merge' in globals():
        progress_widget = progress_merge
        safe_widget_config(progress_widget, maximum=total_steps)
        safe_widget_config(progress_widget, value=current_step)

    temp_files_to_cleanup = []

    try:
        # CRIAR CHECKPOINT
        create_operation_checkpoint("merge", [], current_step, temp_files_to_cleanup)
        
        logging.info(f"Iniciando união de {len(files)} arquivos -> {output_path}")
        
        # FASE 1: Unir PDFs - COM BATCH PROCESSING
        merger = PdfMerger()
        
        # 🔥 PROCESSAMENTO EM LOTES
        for batch_num, batch in enumerate(process_in_batches(files, batch_size=5)):
            if cancel_operation:
                status_var.set("Operação cancelada.")
                logging.info("Operação cancelada pelo usuário")
                return
            
            show_status(f"Processando lote {batch_num + 1}...", "info")
            
            for idx, f in enumerate(batch):
                if cancel_operation:
                    return
                    
                # VALIDAÇÃO DE SEGURANÇA
                try:
                    validate_file_security(f)
                except SecurityError as e:
                    logging.error(f"Arquivo rejeitado: {f} - {e}")
                    show_message_in_main_thread("Erro de Segurança", f"Arquivo rejeitado:\n{os.path.basename(f)}\n\nMotivo: {e}", "error")
                    return
                
                merger.append(f)
                current_step += 1
                if progress_widget:
                    safe_widget_config(progress_widget, value=current_step)
                
                create_operation_checkpoint("merge", files[:idx+1], current_step, temp_files_to_cleanup)
                show_status(f"Unindo {idx + 1}/{len(files)}: {os.path.basename(f)}", "info")
                root.update_idletasks()

        # 🔥 ARQUIVO TEMPORÁRIO SEGURO
        temp_output = safe_temp_file(prefix="merge", suffix=".pdf")
        temp_files_to_cleanup.append(temp_output)
        
        with open(temp_output, "wb") as f_out:
            merger.write(f_out)
        merger.close()
        
        current_step += 1
        if progress_widget:
            safe_widget_config(progress_widget, value=current_step)
        show_status("Salvando arquivo unido...", "info")
        root.update_idletasks()
        
        current_temp = temp_output

        # FASE 2: Proteção e metadados
        if (not pdfa_var.get()) and protect_var.get() and password:
            current_step += 1
            if progress_widget:
                safe_widget_config(progress_widget, value=current_step)
            status_var.set("Aplicando proteção...")
            root.update_idletasks()
            
            try:
                reader = PdfReader(current_temp)
                writer = PdfWriter()
                
                for page in reader.pages:
                    writer.add_page(page)
                
                if protect_var.get() and password:
                    aplicar_criptografia(writer, password)
                
                if remove_meta:
                    writer.add_metadata({})
                elif reader.metadata:
                    writer.add_metadata(reader.metadata)
                
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

        # FASE 3: Compressão
        if compress_var.get() and GHOSTSCRIPT_PATH:
            try:
                current_step += 1
                if progress_widget:
                    safe_widget_config(progress_widget, value=current_step)
                
                show_status("Comprimindo PDF...", "info")
                root.update_idletasks()
                
                temp_comprimido = safe_temp_file(prefix="compressed", suffix=".pdf")
                temp_files_to_cleanup.append(temp_comprimido)
                
                nivel_compressao = compress_level.get()
                reducao = comprimir_com_ghostscript(current_temp, temp_comprimido, nivel_compressao)
                
                if os.path.exists(temp_comprimido) and os.path.getsize(temp_comprimido) > 0:
                    if current_temp in temp_files_to_cleanup:
                        temp_files_to_cleanup.remove(current_temp)
                    remove_temp_file(current_temp)
                    try:
                        os.remove(current_temp)
                    except:
                        pass
                    
                    current_temp = temp_comprimido
                    show_status(f"PDF comprimido: redução de {reducao:.1f}%", "success")
                else:
                    logging.warning("Arquivo comprimido inválido, mantendo original")
                    show_message_in_main_thread("Aviso", "Compressão falhou - mantendo PDF original", "warning")
                    
            except Exception as e:
                logging.warning(f"Falha na compressão: {e}")
                show_message_in_main_thread("Aviso", f"Compressão falhou: {e}\n\nContinuando com PDF não comprimido.", "warning")

        # CONCLUSÃO
        os.replace(current_temp, output_path)
        
        show_status("Validando integridade do PDF...", "info")
        root.update_idletasks()
        
        is_valid, validation_msg = validate_output_pdf(output_path)
        if not is_valid:
            logging.error(f"PDF de saída inválido: {validation_msg}")
            
            fallback_success = False
            if os.path.exists(current_temp):
                try:
                    logging.info("Tentando fallback para arquivo temporário original...")
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
                raise PDFProcessingError(f"Falha na validação do PDF de saída: {validation_msg}")
        
        # 🔥 LOG DE AUDITORIA - SUCESSO
        tamanho_final = os.path.getsize(output_path) / 1024 / 1024
        log_audit_event("merge_success", files, options={
            'output_path': output_path,
            'final_size_mb': round(tamanho_final, 2),
            'compression_applied': compress_var.get(),
            'pdfa_applied': pdfa_var.get(),
            'protection_applied': protect_var.get() and bool(password)
        })
        
        show_status(f"PDF criado e validado: {output_path} ({tamanho_final:.1f} MB)", "success")
        logging.info(f"PDF unido criado e validado: {output_path} ({tamanho_final:.1f} MB) - {validation_msg}")
        
        def show_success_dialog():
            result = messagebox.askyesno(
                "Sucesso", 
                f"PDF salvo em:\n{output_path}\nTamanho: {tamanho_final:.1f} MB\n\nDeseja abrir a pasta de saída?",
                icon='info'
            )
            if result:
                abrir_pasta_output(folder)
        
        root.after(0, show_success_dialog)

    except Exception as e:
        # 🔥 LOG DE AUDITORIA - ERRO
        log_audit_event("merge_error", files, options={
            'error': str(e),
            'error_type': type(e).__name__
        })
        
        logging.error(f"Falha ao unir PDFs: {e}")
        show_message_in_main_thread("Erro", f"Falha ao unir PDFs:\n{e}", "error")
        status_var.set("Erro ao unir arquivos.")
    finally:
        # LIMPEZA
        for temp_file in temp_files_to_cleanup:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    remove_temp_file(temp_file)
            except Exception as e:
                logging.warning(f"Erro ao limpar {temp_file}: {e}")
        
        cleanup_checkpoint()
        set_ui_state(True)
        if progress_widget:
            safe_widget_config(progress_widget, value=0)

def merge_pdfs(event=None):
    if merge_list.size() == 0:
        show_message_in_main_thread("Aviso", "Nenhum arquivo adicionado.", "warning")
        return
    
    # VERIFICAR LIMITES ANTES DE INICIAR
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
    logging.info("Cancelamento solicitado pelo usuário")
    
def log_audit_event(operation, files, user=None, options=None):
    """
    Registro de auditoria para compliance institucional
    operation: "merge_start", "merge_success", "merge_error", "split_start", etc.
    """
    try:
        audit_log = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'operation': operation,
            'files_count': len(files),
            'file_names': [os.path.basename(f) for f in files],  # Apenas nomes, não paths completos
            'options': options or {},
            'user': user or os.getlogin(),
            'session_id': f"{os.getpid()}_{int(time.time())}",
            'version': 'JuntaPDF 2.0'
        }
        
        # Salvar em arquivo separado de auditoria (não no log normal)
        audit_dir = os.path.join(tempfile.gettempdir(), "JuntaPDF_Audit")
        os.makedirs(audit_dir, exist_ok=True)
        
        audit_file = os.path.join(audit_dir, f"audit_{time.strftime('%Y%m')}.log")
        
        with open(audit_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(audit_log, ensure_ascii=False) + '\n')
            
        logging.debug(f"Evento de auditoria registrado: {operation}")
        
    except Exception as e:
        logging.warning(f"Erro ao registrar auditoria: {e}")
        # Não falhar a operação principal por causa do log de auditoria

# -----------------------
# Funções Dividir/Extrair PDFs (com threading SEGURO)
# -----------------------
def split_or_extract_pdfs_thread():
    global cancel_operation
    cancel_operation = False
    
    files = split_list.get(0, tk.END)
    if not files:
        show_message_in_main_thread("Erro", "Nenhum arquivo PDF selecionado.", "error")
        return

    # VALIDAÇÃO DE LIMITES
    if len(files) > MAX_FILES_PER_OPERATION:
        show_message_in_main_thread("Erro", f"Máximo de {MAX_FILES_PER_OPERATION} arquivos por operação.", "error")
        return

    folder = split_output_entry.get() or os.path.dirname(files[0])
    
    # 🔥 CORREÇÃO: CRIA DIRETÓRIO SE NÃO EXISTIR
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception as e:
        show_message_in_main_thread("Erro", f"Não foi possível criar diretório:\n{folder}\n\nErro: {e}", "error")
        return

    # DETECTAR MODO DE DIVISÃO
    split_mode = split_mode_var.get()
    
    # VALIDAÇÕES POR MODO
    if split_mode == "extract":
        page_ranges_input = split_pages_entry.get().strip()
        if not page_ranges_input:
            show_message_in_main_thread("Erro", "Especifique os intervalos de páginas.", "error")
            return
    
    elif split_mode == "interval":
        try:
            interval = int(split_interval_var.get())
            if interval < 1:
                raise ValueError
        except ValueError:
            show_message_in_main_thread("Erro", "Intervalo deve ser um número inteiro maior que 0.", "error")
            return
    
    elif split_mode == "parts":
        try:
            parts = int(split_parts_var.get())
            if parts < 1:
                raise ValueError
        except ValueError:
            show_message_in_main_thread("Erro", "Número de partes deve ser um inteiro maior que 0.", "error")
            return

    convert_pdfa = pdfa_var_split.get()

    try:
        # CALCULAR TOTAL DE ETAPAS
        total_pages_to_process = 0
        for f in files:
            try:
                total_pages_to_process += len(safe_pdf_reader(f).pages)
            except:
                pass

        # VERIFICAR LIMITE TOTAL
        if total_pages_to_process > MAX_TOTAL_PAGES:
            raise SystemOverloadError(f"Limite de {MAX_TOTAL_PAGES} páginas excedido")

        extra_steps = 2 if pdfa_var_split.get() and PDFA_AVAILABLE else 1
        total_steps = total_pages_to_process + extra_steps
        
        # Usar safe_widget_config para progressbar
        progress_widget = None
        if 'progress_split' in globals():
            progress_widget = progress_split
            safe_widget_config(progress_widget, maximum=max(1, total_steps))
            safe_widget_config(progress_widget, value=0)
        else:
            logging.warning("Progressbar split não disponível")

        current_step = 0

        logging.info(f"Iniciando divisão de {len(files)} arquivos (modo: {split_mode}) -> {folder}")

        for file_idx, f in enumerate(files):
            if cancel_operation:
                status_var.set("Operação cancelada.")
                logging.info("Operação cancelada pelo usuário")
                return
            
            # VALIDAÇÃO DE SEGURANÇA
            try:
                validate_file_security(f)
            except SecurityError as e:
                logging.error(f"Arquivo rejeitado por segurança: {f} - {e}")
                continue
            
            reader = safe_pdf_reader(f)
            total_pages_file = len(reader.pages)
            base_name = os.path.splitext(os.path.basename(f))[0]

            # ===== MODO 1: EXTRAIR PÁGINAS ESPECÍFICAS =====
            if split_mode == "extract":
                page_ranges_input = split_pages_entry.get().strip()
                pages_to_extract = parse_page_ranges(page_ranges_input, total_pages_file)
                
                writer = PdfWriter()
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

            # ===== MODO 2: DIVIDIR POR INTERVALO =====
            elif split_mode == "interval":
                interval = int(split_interval_var.get())
                part_num = 1
                
                for start_page in range(0, total_pages_file, interval):
                    if cancel_operation:
                        return
                    
                    writer = PdfWriter()
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
                    
                    show_status(f"Dividindo {file_idx+1}/{len(files)} - Parte {part_num} (páginas {start_page+1}-{end_page})", "info")
                    part_num += 1

            # ===== MODO 3: DIVIDIR EM X PARTES =====
            elif split_mode == "parts":
                num_parts = int(split_parts_var.get())
                pages_per_part = total_pages_file // num_parts
                remainder = total_pages_file % num_parts
                
                current_page = 0
                for part_num in range(1, num_parts + 1):
                    if cancel_operation:
                        return
                    
                    writer = PdfWriter()
                    
                    # Distribui páginas extras nas primeiras partes
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
                    
                    show_status(f"Dividindo {file_idx+1}/{len(files)} - Parte {part_num}/{num_parts}", "info")
                    current_page = end_page

            # ===== MODO 4: DIVIDIR TODAS AS PÁGINAS (AGORA EM ÚLTIMO) =====
            elif split_mode == "all":
                for i, page in enumerate(reader.pages):
                    if cancel_operation:
                        return
                    
                    writer = PdfWriter()
                    writer.add_page(page)
                    
                    output_name = f"{base_name}_pagina_{i+1:03d}_de_{total_pages_file:03d}.pdf"
                    output_path = generate_unique_filename(folder, output_name)
                    
                    with open(output_path, "wb") as f_out:
                        writer.write(f_out)

                    current_step += 1
                    if progress_widget:
                        safe_widget_config(progress_widget, value=current_step)
                    show_status(f"Processando {file_idx+1}/{len(files)} - Página {i+1}/{total_pages_file}", "info")
                    root.update_idletasks()

        # CONCLUSÃO
        if progress_widget:
            safe_widget_config(progress_widget, value=total_steps)
        show_status("Operação concluída!", "success")
        logging.info("Operação de divisão concluída com sucesso")
        show_message_in_main_thread("Sucesso", "Operação concluída!", "info")
        
    except (ValueError, SystemOverloadError) as e:
        logging.error(f"Erro na divisão: {e}")
        show_message_in_main_thread("Erro", str(e), "error")
    except Exception as e:
        logging.error(f"Falha ao processar PDFs: {e}")
        show_message_in_main_thread("Erro", f"Falha ao processar PDFs:\n{e}", "error")
        status_var.set("Erro ao processar arquivos.")
    finally:
        set_ui_state(True)
        if progress_widget:
            root.after(300, lambda: safe_widget_config(progress_widget, value=0))

def split_or_extract_pdfs(event=None):
    if split_list.size() == 0:
        show_message_in_main_thread("Aviso", "Nenhum arquivo adicionado.", "warning")
        return
    
    # VERIFICAR LIMITES ANTES DE INICIAR
    try:
        total_pages = 0
        for f in split_list.get(0, tk.END):
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
    if 'btn_cancel_split' in globals():
        try:
            btn_cancel_split.pack(pady=5)
        except tk.TclError:
            pass
    submit_thread_task(split_or_extract_pdfs_thread)

def cancel_split():
    global cancel_operation
    cancel_operation = True
    logging.info("Cancelamento solicitado pelo usuário")

# -----------------------
# Abrir PDF com duplo clique
# -----------------------
def open_pdf(listbox, event):
    selection = listbox.curselection()
    if not selection:
        return
    file_path = listbox.get(selection[0])
    try:
        # VALIDAÇÃO DE SEGURANÇA ANTES DE ABRIR
        validate_file_security(file_path)
        
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":  # macOS
            subprocess.call(["open", file_path])
        else:  # Linux
            subprocess.call(["xdg-open", file_path])
        logging.info(f"Arquivo aberto: {os.path.basename(file_path)}")
    except Exception as e:
        logging.error(f"Erro ao abrir arquivo: {e}")
        show_message_in_main_thread("Erro", f"Não foi possível abrir:\n{e}", "error")

# -----------------------
# Drag & Drop de arquivos externos
# -----------------------
def drop(event, listbox, files_var, pages_var, size_var):
    if not DND_AVAILABLE:
        return
        
    dropped = root.tk.splitlist(event.data)
    added = 0
    invalid = []
    
    # Verificar limite de arquivos
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
def on_closing():
    """Função para fechar o programa corretamente"""
    global cancel_operation
    cancel_operation = True
    cleanup_temp_files()
    root.quit()
    root.destroy()
# =============================================================================
# CONFIGURAÇÃO DA INTERFACE GRÁFICA
# =============================================================================
root.title("JuntaPDF")
root.geometry("900x780")
root.resizable(True, True)

# Define ícone (opcional)
try:
    root.iconbitmap("pdf_icon.ico")
except:
    pass

# =============================================================================
# NOVO: MENU PRINCIPAL
# =============================================================================
menubar = tk.Menu(root)

# Menu "Arquivo" - NOVO
arquivo_menu = tk.Menu(menubar, tearoff=0)

def get_current_tab_components():
    """Retorna os componentes da aba ativa atual"""
    current_tab = notebook.select()
    tabs = notebook.tabs()
    
    if current_tab == tabs[0]:  # Aba Juntar PDFs
        return merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var
    elif current_tab == tabs[1]:  # Aba Dividir PDFs  
        return split_list, total_files_split_var, total_pages_split_var, total_size_split_var
    return merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var  # fallback

def menu_adicionar_arquivos():
    """Adiciona arquivos na aba atual"""
    listbox, files_var, pages_var, size_var = get_current_tab_components()
    add_files(listbox, files_var, pages_var, size_var)

def menu_remover_selecionados():
    """Remove selecionados na aba atual"""
    listbox, files_var, pages_var, size_var = get_current_tab_components()
    remove_selected(listbox, files_var, pages_var, size_var)

def menu_limpar_lista():
    """Limpa lista na aba atual"""
    listbox, files_var, pages_var, size_var = get_current_tab_components()
    clear_list(listbox, files_var, pages_var, size_var)

# Adiciona itens ao menu Arquivo
arquivo_menu.add_command(
    label="Adicionar Arquivos (Ctrl+O)", 
    command=menu_adicionar_arquivos,
    accelerator="Ctrl+O"
)

arquivo_menu.add_command(
    label="Remover Selecionados (Del)", 
    command=menu_remover_selecionados,
    accelerator="Del"
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

# Menu "Sobre JuntaPDF" (já existente)
sobre_menu = tk.Menu(menubar, tearoff=0)

# Licenças & Créditos
def mostrar_licencas():
    janela_licencas = tk.Toplevel(root)
    janela_licencas.title("Licenças & Créditos - JuntaPDF")
    janela_licencas.geometry("600x500")
    
    # Frame com scrollbar
    frame = tk.Frame(janela_licencas)
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    text_widget = tk.Text(frame, wrap=tk.WORD, padx=10, pady=10, font=("Arial", 10))
    scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=text_widget.yview)
    text_widget.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    
    # Texto
    texto = """Este software foi desenvolvido integrando bibliotecas de código aberto, garantindo transparência e segurança para uso institucional e corporativo.

🛠 BIBLIOTECAS UTILIZADAS

• PyPDF2 – Licença BSD-3-Clause
• PNeFOP – Licença Mozilla Public License 2.0
• Ghostscript – Licença AGPLv3*
• tkinterdnd2, psutil – Licenças MIT/BSD

*Uso do Ghostscript: permitido internamente. Em redistribuições, é necessário incluir o aviso de licença da Artifex Software ou utilizar uma instalação separada do Ghostscript.

📄 DIREITOS AUTORAIS

O código do JuntaPDF é de autoria independente e não deriva diretamente das bibliotecas utilizadas. Esta ferramenta combina e automatiza funcionalidades sem alterar os componentes originais, respeitando integralmente suas licenças.

🔒 OBSERVAÇÃO IMPORTANTE

O JuntaPDF processa arquivos localmente. NENHUM DADO É ENVIADO PARA A INTERNET. A responsabilidade pelo conteúdo dos arquivos processados é inteiramente do usuário.

Desenvolvido por Angelo Filho"""
    
    text_widget.insert(tk.END, texto)
    
    # Aplicar negrito
    text_widget.tag_configure("bold", font=("Arial", 10, "bold"))
    text_widget.tag_add("bold", "3.0", "3.20")   # BIBLIOTECAS UTILIZADAS
    text_widget.tag_add("bold", "11.0", "11.16") # DIREITOS AUTORAIS
    text_widget.tag_add("bold", "16.0", "16.21") # OBSERVAÇÃO IMPORTANTE
    text_widget.tag_add("bold", "18.0", "18.35") # NENHUM DADO É ENVIADO...
    
    text_widget.config(state=tk.DISABLED)

# PRIMEIRO: Licenças & Créditos
sobre_menu.add_command(
    label="Licenças & Créditos", 
    command=mostrar_licencas
)

# SEGUNDO: Verificar Ambiente
sobre_menu.add_command(label="Verificar Ambiente", command=show_environment_check)

# TERCEIRO: Dashboard de Performance
sobre_menu.add_command(label="Dashboard de Performance", command=show_performance_dashboard)

menubar.add_cascade(label="Sobre o JuntaPDF", menu=sobre_menu)

root.config(menu=menubar)

# Barra de status
status_label = ttk.Label(root, textvariable=status_var, foreground="blue")
status_label.pack(side="bottom", pady=5)

# Status inicial com detecção de recursos
status_parts = ["Pronto"]
if DND_AVAILABLE:
    status_parts.append("Drag & Drop ✓")
if PDFA_AVAILABLE:
    status_parts.append("PDF/A ✓")
else:
    status_parts.append("PDF/A ✗ (Ghostscript não detectado)")

status_var.set(" | ".join(status_parts))

notebook = ttk.Notebook(root)
notebook.pack(fill="both", expand=True, padx=10, pady=5)

# -----------------------
# Aba Juntar PDFs - REDESENHADA
# -----------------------
merge_frame = ttk.Frame(notebook)
notebook.add(merge_frame, text="Juntar PDFs")

# Frame de arquivos
frame_files_merge = ttk.LabelFrame(merge_frame, text="Arquivos PDF (arraste para reordenar)")
frame_files_merge.pack(fill="both", expand=True, padx=10, pady=5)

# Estatísticas
stats_frame_merge = ttk.Frame(frame_files_merge)
stats_frame_merge.pack(fill="x", padx=5, pady=5)
ttk.Label(stats_frame_merge, textvariable=total_files_merge_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
ttk.Label(stats_frame_merge, textvariable=total_pages_merge_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10) 
ttk.Label(stats_frame_merge, textvariable=total_size_merge_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

# Listbox
merge_list_frame = ttk.Frame(frame_files_merge)
merge_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
merge_list = tk.Listbox(merge_list_frame, selectmode=tk.EXTENDED, width=85, height=12, exportselection=False)
merge_list.pack(side=tk.LEFT, fill="both", expand=True)

if DND_AVAILABLE:
    merge_list.drop_target_register(DND_FILES)
    merge_list.dnd_bind('<<Drop>>', lambda e: drop(e, merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var))

merge_list.bind("<Double-1>", lambda e: open_pdf(merge_list, e))
attach_dynamic_tooltips(merge_list)
setup_drag_reorder(merge_list)
# 🚨 CORREÇÃO: Menu de contexto adicionado
setup_context_menu(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)

merge_list.bind("<Shift-Up>", lambda e: (move_up(merge_list), "break")[1])
merge_list.bind("<Shift-Down>", lambda e: (move_down(merge_list), "break")[1])

scroll_merge = ttk.Scrollbar(merge_list_frame, orient="vertical", command=merge_list.yview)
scroll_merge.pack(side=tk.RIGHT, fill="y")
merge_list.config(yscrollcommand=scroll_merge.set)

# BOTÕES DE CONTROLE - REORGANIZADOS
btn_frame_merge = ttk.Frame(merge_frame)
btn_frame_merge.pack(fill="x", padx=10, pady=8)

# Linha 1: Gerenciamento de Arquivos
ttk.Label(btn_frame_merge, text="Gerenciar Arquivos:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=(0,5), pady=2, sticky="w")
ttk.Button(btn_frame_merge, text="Adicionar (Ctrl+O)", 
          command=lambda: add_files(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).grid(row=0, column=1, padx=2, pady=2)
ttk.Button(btn_frame_merge, text="Remover (Del)", 
          command=lambda: remove_selected(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).grid(row=0, column=2, padx=2, pady=2)
ttk.Button(btn_frame_merge, text="Limpar (Ctrl+L)", 
          command=lambda: clear_list(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var)).grid(row=0, column=3, padx=2, pady=2)

# Linha 2: Organização
ttk.Label(btn_frame_merge, text="Organizar:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, padx=(0,5), pady=2, sticky="w")
ttk.Button(btn_frame_merge, text="Mover ↑ (Shift+↑)", command=lambda: move_up(merge_list), width=16).grid(row=1, column=1, padx=2, pady=2)
ttk.Button(btn_frame_merge, text="Mover ↓ (Shift+↓)", command=lambda: move_down(merge_list), width=16).grid(row=1, column=2, padx=2, pady=2)
ttk.Button(btn_frame_merge, text="Ordem alfabética (Ctrl+S)", 
          command=lambda: sort_az(merge_list, total_files_merge_var, total_pages_merge_var, total_size_merge_var), width=24).grid(row=1, column=3, padx=2, pady=2)

# DESTINO DO ARQUIVO - MAIS COMPACTO
frame_output_merge = ttk.LabelFrame(merge_frame, text="Configurações de Saída")
frame_output_merge.pack(fill="x", padx=10, pady=5)

# Pasta de saída
ttk.Label(frame_output_merge, text="Nome do arquivo final:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
merge_filename_entry = ttk.Entry(frame_output_merge, width=40)
merge_filename_entry.insert(0, "Deixe vazio para nome automático")
merge_filename_entry.config(foreground="gray")
merge_filename_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")

# Pasta de saída (SEGUNDO)
ttk.Label(frame_output_merge, text="Pasta de saída:").grid(row=1, column=0, padx=5, pady=3, sticky="w")
merge_output_entry = ttk.Entry(frame_output_merge, width=40)
merge_output_entry.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
ttk.Button(frame_output_merge, text="Selecionar Pasta", 
          command=lambda: choose_output_folder(merge_output_entry)).grid(row=1, column=2, padx=5, pady=3)

# Preview (TERCEIRO)
filename_preview_var = tk.StringVar()
filename_preview_label = ttk.Label(frame_output_merge, textvariable=filename_preview_var, 
                                  foreground="blue", font=("Segoe UI", 8))
filename_preview_label.grid(row=2, column=0, columnspan=3, padx=10, pady=2, sticky="w")

frame_output_merge.columnconfigure(1, weight=1)

# OPÇÕES DE PROCESSAMENTO - REORGANIZADAS
frame_opts_merge = ttk.LabelFrame(merge_frame, text="Opções de Processamento")
frame_opts_merge.pack(fill="x", padx=10, pady=5)

# Linha 1: PDF/A com texto explicativo
pdfa_var.set(PDFA_AVAILABLE)
pdfa_check = ttk.Checkbutton(frame_opts_merge, text="Converter para PDF/A-2B", variable=pdfa_var)
pdfa_check.grid(row=0, column=0, sticky="w", padx=10, pady=3)

# TEXTO EXPLICATIVO DO PDF/A (como você gostava)
pdfa_info_label = ttk.Label(
    frame_opts_merge,
    text="Formato PDF/A-2B recomendado para o Sistema Eletrônico de Informações (SEI) do Governo Federal",
    foreground="darkgreen",
    font=("Segoe UI", 8)
)
pdfa_info_label.grid(row=0, column=1, columnspan=2, padx=10, pady=3, sticky="w")

# Linha 2: Senha
protect_check = ttk.Checkbutton(frame_opts_merge, text="Proteger com senha", variable=protect_var)
protect_check.grid(row=1, column=0, sticky="w", padx=10, pady=3)

password_entry = ttk.Entry(frame_opts_merge, width=20, show="*")
password_entry.grid(row=1, column=1, padx=5, pady=3, sticky="w")
password_entry.config(state="disabled")

# Linha 3: Compressão e Metadados
compress_check = ttk.Checkbutton(frame_opts_merge, text="Comprimir PDF:", variable=compress_var)
compress_check.grid(row=2, column=0, sticky="w", padx=10, pady=3)

compress_combo = ttk.Combobox(
    frame_opts_merge, 
    textvariable=compress_level,
    values=["Qualidade Máxima", "Qualidade Equilibrada", "Tamanho Mínimo"],
    state="readonly",
    width=25
)
compress_combo.grid(row=2, column=1, padx=5, pady=3, sticky="w")
compress_combo.set("Qualidade Máxima")
compress_combo.config(state="disabled")

meta_check = ttk.Checkbutton(frame_opts_merge, text="Remover metadados", variable=meta_var)
meta_check.grid(row=2, column=2, sticky="w", padx=20, pady=3)

# Info PDF/A se não disponível
if not PDFA_AVAILABLE:
    pdfa_check.config(state="disabled")
    pdfa_info_label.config(text="Instale Ghostscript para habilitar PDF/A", foreground="red")

# BOTÃO PRINCIPAL - MAIOR DESTAQUE
action_frame_merge = ttk.Frame(merge_frame)
action_frame_merge.pack(fill="x", padx=10, pady=10)

btn_merge = ttk.Button(
    action_frame_merge, 
    text="Juntar PDFs (Ctrl+R)", 
    command=merge_pdfs
)
btn_merge.pack(pady=5)

# Progresso
progress_merge = ttk.Progressbar(merge_frame, orient="horizontal", length=520, mode="determinate")
progress_merge.pack(pady=5)

# Botão cancelar
btn_cancel_merge = ttk.Button(merge_frame, text="Cancelar Operação", command=cancel_merge)

# -----------------------
# Aba Dividir/Extrair PDFs - REDESENHADA
# -----------------------
split_frame = ttk.Frame(notebook)
notebook.add(split_frame, text="Dividir PDFs")

# Frame de arquivos
frame_files_split = ttk.LabelFrame(split_frame, text="Arquivos PDF (arraste para reordenar)")
frame_files_split.pack(fill="both", expand=True, padx=10, pady=5)

# Estatísticas
stats_frame_split = ttk.Frame(frame_files_split)
stats_frame_split.pack(fill="x", padx=5, pady=5)
ttk.Label(stats_frame_split, textvariable=total_files_split_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
ttk.Label(stats_frame_split, textvariable=total_pages_split_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)
ttk.Label(stats_frame_split, textvariable=total_size_split_var, font=("Segoe UI", 9, "bold")).pack(side="left", padx=10)

# Listbox
split_list_frame = ttk.Frame(frame_files_split)
split_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
split_list = tk.Listbox(split_list_frame, selectmode=tk.EXTENDED, width=85, height=12, exportselection=False)
split_list.pack(side=tk.LEFT, fill="both", expand=True)

if DND_AVAILABLE:
    split_list.drop_target_register(DND_FILES)
    split_list.dnd_bind('<<Drop>>', lambda e: drop(e, split_list, total_files_split_var, total_pages_split_var, total_size_split_var))

split_list.bind("<Double-1>", lambda e: open_pdf(split_list, e))
attach_dynamic_tooltips(split_list)
setup_drag_reorder(split_list)
# 🚨 CORREÇÃO: Menu de contexto adicionado
setup_context_menu(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)

split_list.bind("<Shift-Up>", lambda e: (move_up(split_list), "break")[1])
split_list.bind("<Shift-Down>", lambda e: (move_down(split_list), "break")[1])

scroll_split = ttk.Scrollbar(split_list_frame, orient="vertical", command=split_list.yview)
scroll_split.pack(side=tk.RIGHT, fill="y")
split_list.config(yscrollcommand=scroll_split.set)

# BOTÕES DE CONTROLE
btn_frame_split = ttk.Frame(split_frame)
btn_frame_split.pack(fill="x", padx=10, pady=8)

# Linha 1: Gerenciamento
ttk.Label(btn_frame_split, text="Gerenciar Arquivos:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=(0,5), pady=2, sticky="w")
ttk.Button(btn_frame_split, text="Adicionar (Ctrl+O)", 
          command=lambda: add_files(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).grid(row=0, column=1, padx=2, pady=2)
ttk.Button(btn_frame_split, text="Remover (Del)", 
          command=lambda: remove_selected(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).grid(row=0, column=2, padx=2, pady=2)
ttk.Button(btn_frame_split, text="Limpar (Ctrl+L)", 
          command=lambda: clear_list(split_list, total_files_split_var, total_pages_split_var, total_size_split_var)).grid(row=0, column=3, padx=2, pady=2)

# =============================================================================
# NOVA SEÇÃO: OPÇÕES DE DIVISÃO AVANÇADAS (COM ORDEM CORRIGIDA)
# =============================================================================

# Frame principal de opções
frame_split_opts = ttk.LabelFrame(split_frame, text="Configurações de Divisão")
frame_split_opts.pack(fill="x", padx=10, pady=5)

# ----- MODO 1: EXTRAIR PÁGINAS ESPECÍFICAS -----
extract_radio = ttk.Radiobutton(
    frame_split_opts,
    text="Extrair páginas específicas:",
    variable=split_mode_var,
    value="extract"
)
extract_radio.grid(row=0, column=0, padx=10, pady=5, sticky="w")

split_pages_entry = ttk.Entry(frame_split_opts, width=40)
split_pages_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
split_pages_entry.insert(0, "1-5, 10, 20-30")

info_label = ttk.Label(
    frame_split_opts,
    text="Exemplos: 1-5 (páginas 1 a 5) • 1,3,5 (páginas 1, 3 e 5) • 1-3,7,10-15 (combina intervalos)",
    foreground="gray",
    font=("Segoe UI", 8)
)
info_label.grid(row=1, column=1, padx=10, pady=(0, 5), sticky="w")

# ----- MODO 2: DIVIDIR POR INTERVALO -----
interval_radio = ttk.Radiobutton(
    frame_split_opts,
    text="Dividir em intervalos de:",
    variable=split_mode_var,
    value="interval"
)
interval_radio.grid(row=2, column=0, padx=10, pady=5, sticky="w")

interval_frame = ttk.Frame(frame_split_opts)
interval_frame.grid(row=2, column=1, padx=5, pady=5, sticky="w")

split_interval_entry = ttk.Entry(interval_frame, textvariable=split_interval_var, width=8)
split_interval_entry.pack(side="left", padx=(0, 5))

ttk.Label(interval_frame, text="páginas por arquivo (ex: 5 → 5+5+5+3 = 18 páginas)", 
          foreground="gray", font=("Segoe UI", 8)).pack(side="left")

# ----- MODO 3: DIVIDIR EM X PARTES -----
parts_radio = ttk.Radiobutton(
    frame_split_opts,
    text="Dividir em:",
    variable=split_mode_var,
    value="parts"
)
parts_radio.grid(row=3, column=0, padx=10, pady=5, sticky="w")

parts_frame = ttk.Frame(frame_split_opts)
parts_frame.grid(row=3, column=1, padx=5, pady=5, sticky="w")

split_parts_entry = ttk.Entry(parts_frame, textvariable=split_parts_var, width=8)
split_parts_entry.pack(side="left", padx=(0, 5))

ttk.Label(parts_frame, text="partes iguais (ex: 18 páginas ÷ 3 partes = 6 páginas/parte)", 
          foreground="gray", font=("Segoe UI", 8)).pack(side="left")

# ----- MODO 4: DIVIDIR TODAS AS PÁGINAS (AGORA EM ÚLTIMO LUGAR) -----
all_radio = ttk.Radiobutton(
    frame_split_opts,
    text="Dividir TODAS as páginas em arquivos separados (1 página por arquivo)",
    variable=split_mode_var,
    value="all"
)
all_radio.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

# Configurar estados iniciais dos campos
def update_split_fields_state(*args):
    """Habilita/desabilita campos baseado no modo selecionado"""
    mode = split_mode_var.get()
    
    # Todos começam desabilitados
    split_pages_entry.config(state="disabled")
    split_interval_entry.config(state="disabled")
    split_parts_entry.config(state="disabled")
    
    # Habilita apenas o campo do modo selecionado
    if mode == "extract":
        split_pages_entry.config(state="normal")
    elif mode == "interval":
        split_interval_entry.config(state="normal")
    elif mode == "parts":
        split_parts_entry.config(state="normal")

# Conectar mudança de modo
split_mode_var.trace_add("write", update_split_fields_state)

# Aplicar estado inicial
update_split_fields_state()

# DESTINO E OPÇÕES
frame_output_split = ttk.LabelFrame(split_frame, text="Configurações de Saída")
frame_output_split.pack(fill="x", padx=10, pady=5)

# Pasta de saída
ttk.Label(frame_output_split, text="Pasta de saída:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
split_output_entry = ttk.Entry(frame_output_split, width=40)
split_output_entry.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
ttk.Button(frame_output_split, text="Selecionar Pasta", 
          command=lambda: choose_output_folder(split_output_entry)).grid(row=0, column=2, padx=5, pady=3)

# PDF/A option
pdfa_var_split.set(PDFA_AVAILABLE)
pdfa_check_split = ttk.Checkbutton(frame_output_split, text="Converter para PDF/A-2B", variable=pdfa_var_split)
pdfa_check_split.grid(row=1, column=0, columnspan=2, sticky="w", padx=10, pady=3)
pdfa_info_split = ttk.Label(
    frame_output_split,
    text="Formato recomendado para documentos eletrônicos no SEI/Governo Federal",
    foreground="darkgreen", 
    font=("Segoe UI", 8)
)
pdfa_info_split.grid(row=1, column=2, padx=10, pady=3, sticky="w")

if not PDFA_AVAILABLE:
    pdfa_check_split.config(state="disabled")
    pdfa_info_split.config(text="Instale Ghostscript para habilitar", foreground="red")

frame_output_split.columnconfigure(1, weight=1)

# BOTÃO PRINCIPAL
action_frame_split = ttk.Frame(split_frame)
action_frame_split.pack(fill="x", padx=10, pady=10)

btn_split = ttk.Button(
    action_frame_split, 
    text="Dividir/Extrair PDFs", 
    command=split_or_extract_pdfs
)
btn_split.pack(pady=5)

# Progresso
progress_split = ttk.Progressbar(split_frame, orient="horizontal", length=520, mode="determinate")
progress_split.pack(pady=5)

# Botão cancelar
btn_cancel_split = ttk.Button(split_frame, text="Cancelar Operação", command=cancel_split)

# -----------------------
# Atalhos globais
# -----------------------
def get_active_listbox():
    current_tab = notebook.select()
    tabs = notebook.tabs()
    if current_tab == tabs[0]:
        return merge_list
    elif current_tab == tabs[1]:
        return split_list
    return merge_list

root.bind_all("<Control-o>", lambda e: add_files(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-O>", lambda e: add_files(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Delete>", lambda e: remove_selected(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-l>", lambda e: clear_list(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-L>", lambda e: clear_list(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-s>", lambda e: sort_az(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-S>", lambda e: sort_az(get_active_listbox(), total_files_merge_var, total_pages_merge_var, total_size_merge_var))
root.bind_all("<Control-r>", lambda e: merge_pdfs())
root.bind_all("<Control-R>", lambda e: merge_pdfs())
root.bind_all("<Escape>", lambda e: root.quit())

# -----------------------
# Inicialização final
# -----------------------
root.protocol("WM_DELETE_WINDOW", on_closing)

# Configurar estados iniciais
def on_protect_toggle(*_):
    """Chamado quando proteção é alternada"""
    validate_pdfa_protection_compatibility()
    focus_password_entry()

def on_pdfa_toggle(*_):
    """Chamado quando PDF/A é alternado"""
    validate_pdfa_protection_compatibility()

# Conectar eventos
protect_var.trace_add("write", lambda *_: on_protect_toggle())
pdfa_var.trace_add("write", lambda *_: on_pdfa_toggle())

def on_compress_toggle(*_):
    safe_widget_config(compress_combo, state="normal" if compress_var.get() else "disabled")
compress_var.trace_add("write", lambda *_: (on_compress_toggle(), focus_compress_combo()))

# Funções para placeholder do nome
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

# Função para atualizar preview do nome
def update_filename_preview():
    files = merge_list.get(0, tk.END)
    if not files:
        filename_preview_var.set("Nenhum arquivo selecionado")
        return
    
    # 🔥 ADICIONAR ESTIMAÇÃO DE TAMANHO
    estimated_size = estimate_final_size(files, {
        'compress': compress_var.get(),
        'compress_level': compress_level.get()
    })
    
    preview_name = get_default_output_name("merge", files, {...})
    preview_text = f"Nome: {preview_name} | Tamanho estimado: {estimated_size/1024/1024:.1f}MB"
    filename_preview_var.set(preview_text)

# Conectar eventos para atualizar preview
merge_list.bind("<<ListboxSelect>>", lambda e: update_filename_preview())
compress_var.trace_add("write", lambda *_: update_filename_preview())
pdfa_var.trace_add("write", lambda *_: update_filename_preview())
protect_var.trace_add("write", lambda *_: update_filename_preview())

# Atualizar preview inicial
root.after(500, update_filename_preview)

# =============================================================================
# CONFIGURAÇÃO DAS MELHORIAS DE UX
# =============================================================================

setup_ux_enhancements()

# Configurar badges nas abas
update_merge_badge = add_file_count_badge(merge_list, merge_badge_var)
update_split_badge = add_file_count_badge(split_list, split_badge_var)

# Atualizar badges inicialmente
update_merge_badge()
update_split_badge()

# Atualizar textos das abas com badges
def update_tab_titles():
    notebook.tab(0, text=f"Juntar PDFs{merge_badge_var.get()}")
    notebook.tab(1, text=f"Dividir PDFs{split_badge_var.get()}")

merge_badge_var.trace_add("write", lambda *_: update_tab_titles())
split_badge_var.trace_add("write", lambda *_: update_tab_titles())

# Atualizar estado inicial dos botões
root.after(500, enable_submit_on_conditions)

# Aplicar validação inicial de compatibilidade
root.after(600, lambda: update_protection_pdfa_states())

# Foco inicial
root.after(100, lambda: merge_list.focus_set())

# Agora sim pode verificar dependências
check_dependencies()
show_first_run_disclaimer()

# 🔥 NOVO: Verificação final de sanidade
def verificar_sanidade_inicial():
    """Verifica se todas as variáveis críticas foram inicializadas corretamente"""
    variaveis_criticas = [
        ('PDF_LIBS_AVAILABLE', PDF_LIBS_AVAILABLE),
        ('GHOSTSCRIPT_PATH', GHOSTSCRIPT_PATH), 
        ('PIKEPDF_AVAILABLE', PIKEPDF_AVAILABLE),
        ('DND_AVAILABLE', DND_AVAILABLE),
        ('PDFA_AVAILABLE', PDFA_AVAILABLE)
    ]
    
    for nome, valor in variaveis_criticas:
        logging.info(f"Status {nome}: {valor}")
    
    # Verifica se não há variáveis "fantasma" concatenadas
    variaveis_globais = list(globals().keys())
    variaveis_suspeitas = [v for v in variaveis_globais if 'AVAILABLE' in v and 'GHOSTSCRIPT' in v]
    
    if variaveis_suspeitas:
        logging.warning(f"Variáveis suspeitas detectadas: {variaveis_suspeitas}")
        # Remove variáveis concatenadas acidentais
        for var_suspeita in variaveis_suspeitas:
            if var_suspeita in globals():
                del globals()[var_suspeita]
                logging.info(f"Variável suspeita removida: {var_suspeita}")

# Chamar verificação de sanidade
verificar_sanidade_inicial()

# Inicia a aplicação
if __name__ == "__main__":
    try:
        # Verificação final antes de iniciar
        if not PDF_LIBS_AVAILABLE:
            messagebox.showerror("Erro Crítico", "PyPDF2 não está disponível. O programa não pode funcionar.")
            sys.exit(1)
            
        logging.info("✅ JuntaPDF inicializado com sucesso!")
        logging.info("🚀 Iniciando interface gráfica...")
        
        # Opcional: oferta de recuperação (pode comentar se não quiser)
        root.after(1000, offer_recovery_on_startup)
        
        root.mainloop()
        
    except Exception as e:
        logging.critical(f"❌ Erro fatal: {e}")
        messagebox.showerror("Erro Fatal", f"Ocorreu um erro inesperado:\n{e}")
    finally:
        # Limpeza final garantida
        logging.info("🧹 Finalizando JuntaPDF...")
        cleanup_temp_files()