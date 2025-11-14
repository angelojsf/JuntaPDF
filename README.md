# JuntaPDF

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

**Ferramenta profissional para unir, dividir e otimizar PDFs - 100% local e seguro**

**Repositório:** https://github.com/angelojsf/JuntaPDF

---

## Sumário

- [Visão Geral](#visão-geral)
- [Instalação](#instalação)
  - [Windows](#windows)
  - [Linux/macOS](#linuxmacos)
- [Como Usar](#como-usar)
  - [Unir PDFs](#unir-pdfs)
  - [Dividir PDFs](#dividir-pdfs)
- [Recursos Técnicos](#recursos-técnicos)
- [Deploy Corporativo](#deploy-corporativo)
- [Monitoramento e Logs](#monitoramento-e-logs)
- [FAQ](#faq)
- [Suporte](#suporte)
- [Licença](#licença)

---

## Visão Geral

JuntaPDF é uma ferramenta desktop para manipulação de documentos PDF com foco em segurança, conformidade e processamento 100% local. Ideal para ambientes corporativos, instituições públicas e usuários que priorizam privacidade.

**Características principais:**
- Processamento totalmente offline (zero dados enviados à internet)
- Compatível com padrão PDF/A-2B (ISO 19005-2)
- Interface drag-and-drop intuitiva
- Validação de integridade de arquivos
- Sistema de logs com sanitização automática
- Suporte a senhas e compressão inteligente

---

## Instalação

### Windows

**1. Instale o Python 3.7 ou superior**

Baixe em [python.org](https://www.python.org/downloads/) e durante a instalação:
- Marque a opção **"Add Python to PATH"**
- Recomendado: Marque **"Install for all users"** (ambientes corporativos)

**2. Clone o repositório**

```bash
git clone https://github.com/angelojsf/JuntaPDF.git
cd JuntaPDF
```

**3. Instale as dependências**

```bash
pip install -r requirements.txt
```

**4. (Opcional) Instale o Ghostscript para recursos PDF/A**

Baixe o instalador em [ghostscript.com/releases](https://ghostscript.com/releases/gsdnld.html) e instale. Necessário apenas para geração de PDFs em formato PDF/A-2B.

**5. Execute o programa**

```bash
python juntapdf.py
```

### Linux/macOS

```bash
# Clone o repositório
git clone https://github.com/angelojsf/JuntaPDF.git
cd JuntaPDF

# Instale dependências
pip3 install -r requirements.txt

# (Opcional) Instale Ghostscript via gerenciador de pacotes
# Ubuntu/Debian:
sudo apt-get install ghostscript

# macOS (Homebrew):
brew install ghostscript

# Execute
python3 juntapdf.py
```

---

## Como Usar

### Unir PDFs

1. **Adicionar arquivos:** Arraste arquivos PDF para a área de listagem ou clique em "Adicionar PDFs"
2. **Reordenar:** Selecione um arquivo e use `Shift + ↑/↓` para alterar a ordem
3. **Remover:** Selecione arquivo(s) e pressione `Delete` ou clique em "Remover Selecionados"
4. **Configurar opções:**
   - Escolha nível de compressão (Qualidade, Balanceado, Tamanho)
   - (Opcional) Ative conversão para PDF/A-2B
   - (Opcional) Defina senha de proteção
5. **Processar:** Clique em "UNIR PDFs" e escolha pasta de destino

**Resultado:** Arquivo `merged_output.pdf` (ou nome personalizado) na pasta escolhida.

### Dividir PDFs

1. **Adicionar arquivo:** Carregue um único arquivo PDF
2. **Escolher modo de divisão:**
   - **Extrair páginas específicas:** Digite intervalos (ex: `1-5, 10, 15-20`)
   - **Intervalo fixo:** Define número de páginas por arquivo (ex: `5` = blocos de 5 páginas)
   - **Partes iguais:** Divide em X arquivos de tamanho similar
   - **Todas as páginas:** Gera um arquivo para cada página individual
3. **Processar:** Clique em "PROCESSAR PDFs" e escolha pasta de destino

**Resultado:** Arquivos numerados sequencialmente (ex: `documento_parte_001.pdf`, `documento_parte_002.pdf`).

---

## Recursos Técnicos

| Recurso | Detalhes Técnicos | Benefício |
|---------|-------------------|-----------|
| **PDF/A-2B** | Conversão via Ghostscript com OutputIntent sRGB | Conformidade ISO 19005-2 para arquivamento de longo prazo, compatível com SEI e sistemas governamentais |
| **Compressão** | 3 níveis usando `pikepdf` (object streams, filtros JPEG/Flate) | Reduz tamanho mantendo qualidade visual. Modo "Qualidade" preserva resolução máxima |
| **Proteção por Senha** | Criptografia AES-128, suporte a senhas Owner/User | Controle de acesso local sem dependência de serviços externos |
| **Validação de Integridade** | Checagem de estrutura PDF (xref, trailer, objetos) | Detecta PDFs corrompidos ou potencialmente maliciosos antes do processamento |
| **Interface Drag & Drop** | Biblioteca `tkinterdnd2` com feedback visual | Reduz curva de aprendizado, agiliza fluxo de trabalho |
| **Logs Sanitizados** | Remoção automática de informações sensíveis (caminhos absolutos, nomes de usuário) | Conformidade com LGPD/GDPR, facilita auditoria sem expor dados pessoais |
| **Monitoramento de Performance** | Dashboard integrado com métricas de CPU, memória e disco | Identifica gargalos em processamento de lotes grandes |

### Limites Operacionais

- **Arquivos por operação:** 100 arquivos
- **Páginas totais:** 10.000 páginas por operação
- **Tamanho máximo por arquivo:** 500 MB
- **Retenção de logs:** 30 dias (limpeza automática)

---

## Deploy Corporativo

### Instalação Silenciosa

```bash
# Instalação de dependências Python sem interação
pip install --no-input --quiet PyPDF2==3.0.1 pikepdf==8.10.2 tkinterdnd2==0.3.0 psutil>=5.8.0

# Ghostscript (Windows - linha de comando)
# Baixar .exe em https://ghostscript.com/releases/gsdnld.html
# Executar com parâmetros:
gs-installer.exe /S /D=C:\Program Files\gs\gs10.02.1
```

### Requisitos de Ambiente

- **Python:** 3.7 ou superior
- **Sistema Operacional:** Windows 10+, Ubuntu 20.04+, macOS 11+
- **Memória RAM:** Mínimo 4 GB (recomendado 8 GB para processamento em lote)
- **Espaço em Disco:** 100 MB para instalação + espaço temporário para processamento (até 2x o tamanho dos PDFs)
- **Ghostscript:** Versão 9.50+ (necessário apenas para recursos PDF/A)

### Configuração de Rede

**Não requer conexão à internet** durante operação. Todas as dependências são instaladas localmente.

### Auditoria e Conformidade

- **Logs estruturados:** JSON com timestamp, operação, status e duração
- **Localização:** `%TEMP%\JuntaPDF_Logs\` (Windows) ou `/tmp/JuntaPDF_Logs/` (Linux/macOS)
- **Sanitização:** Caminhos de arquivo reduzidos a nomes base, remoção de identificadores de usuário
- **Formato:** Compatível com ferramentas SIEM (Splunk, ELK Stack)

**Exemplo de entrada de log:**

```json
{
  "timestamp": "2025-11-14T10:30:45.123Z",
  "operation": "merge",
  "files_count": 5,
  "total_pages": 127,
  "output_size_mb": 8.3,
  "compression_level": "balanced",
  "pdf_a_enabled": true,
  "duration_seconds": 12.4,
  "status": "success"
}
```

---

## Monitoramento e Logs

### Dashboard de Performance

Acesse via menu **"Ferramentas" → "Monitor de Performance"**:

- **Uso de CPU:** Gráfico em tempo real por núcleo
- **Memória:** Consumo ativo vs. disponível
- **Disco:** Velocidade de I/O e espaço livre
- **Histórico:** Últimas 50 operações com tempos de processamento

### Gestão de Logs

- **Retenção:** Logs são mantidos por 30 dias
- **Limpeza:** Automática na inicialização do programa
- **Exportação:** Botão "Exportar Logs" no dashboard gera arquivo ZIP

### Indicadores de Saúde

| Indicador | Valor Normal | Ação Recomendada |
|-----------|--------------|-------------------|
| CPU > 90% por > 5 min | < 80% | Reduzir tamanho de lote ou fechar aplicações concorrentes |
| Memória > 90% | < 75% | Processar menos arquivos simultaneamente |
| I/O Disco < 10 MB/s | > 50 MB/s | Verificar antivírus em tempo real ou fragmentação de disco |

---

## FAQ

### Questões Gerais

**P: O programa precisa de internet?**  
R: Não. Todo o processamento é feito localmente. Internet é necessária apenas para instalação inicial das dependências Python.

**P: Os PDFs são enviados para algum servidor?**  
R: Não. Nenhum dado sai do seu computador. O código é auditável em [github.com/angelojsf/JuntaPDF](https://github.com/angelojsf/JuntaPDF).

**P: É gratuito para uso comercial?**  
R: Sim. Licenciado sob BSD-3-Clause (veja [LICENSE](LICENSE)).

### Compatibilidade

**P: Funciona com SEI (Sistema Eletrônico de Informações)?**  
R: Sim. A conversão para PDF/A-2B garante compatibilidade com SEI e outros sistemas governamentais que exigem padrão ISO 19005.

**P: Qual a diferença entre PDF/A-1B e PDF/A-2B?**  
R: PDF/A-2B (usado pelo JuntaPDF) suporta compressão JPEG2000, transparência e camadas, mantendo conformidade para arquivamento. PDF/A-1B é mais restritivo. Para a maioria dos casos, PDF/A-2B é preferível.

**P: PDFs assinados digitalmente são suportados?**  
R: Parcialmente. A ferramenta pode processar PDFs assinados, mas as assinaturas digitais serão invalidadas após modificação (comportamento esperado de qualquer manipulação de PDF). Para preservar assinaturas, não processe o documento.

### Troubleshooting

**P: Erro "Ghostscript não encontrado" ao ativar PDF/A**  
R: Instale o Ghostscript conforme seção [Instalação](#instalação). No Windows, adicione `C:\Program Files\gs\gs10.XX.X\bin` ao PATH do sistema.

**P: Programa travou ao processar arquivo grande**  
R: Arquivos > 200 MB podem causar lentidão. Solução:
1. Divida o PDF em partes menores primeiro
2. Use nível de compressão "Tamanho" para reduzir uso de memória
3. Feche outros programas

**P: PDF de saída está corrompido/não abre**  
R: Possíveis causas:
- PDF de entrada já estava corrompido (use ferramenta de reparo como `pdftk`)
- Interrupção durante processamento (não feche o programa até conclusão)
- Espaço em disco insuficiente (verifique partição de destino)

**P: Como reportar um bug?**  
R: Abra uma issue em [github.com/angelojsf/JuntaPDF/issues](https://github.com/angelojsf/JuntaPDF/issues) incluindo:
- Sistema operacional e versão do Python
- Arquivo de log (se disponível)
- Passos para reproduzir o problema

---

## Suporte

- **Issues e Bugs:** [GitHub Issues](https://github.com/angelojsf/JuntaPDF/issues)
- **Documentação Técnica:** Este README e código-fonte comentado
- **Licenças de Componentes:** [LICENSE](LICENSE) | [NOTICE](NOTICE)

---

## Licença

Copyright (c) 2025 Angelo José

Este projeto é licenciado sob a [BSD 3-Clause License](LICENSE). Veja o arquivo LICENSE para detalhes completos.

### Componentes de Terceiros

- **PyPDF2** - BSD License
- **pikepdf** - MPL 2.0
- **tkinterdnd2** - MIT License
- **Ghostscript** - AGPL 3.0 (uso opcional)

Consulte [NOTICE](NOTICE) para informações completas sobre licenças de dependências.

---

**Desenvolvido com foco em privacidade, segurança e conformidade institucional.**