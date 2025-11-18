# JuntaPDF - Ferramenta de Gestão e Processamento Documental

**Versão:** 2.0 (Estável)
**Licença:** BSD 3-Clause
**Classificação:** Software de Utilidade Administrativa / Processamento Local

---

## Sumário

1. [Apresentação](#1-apresentação)
2. [Finalidade e Aplicação](#2-finalidade-e-aplicação)
3. [Requisitos de Sistema](#3-requisitos-de-sistema)
4. [Funcionalidades Detalhadas](#4-funcionalidades-detalhadas)
    * [Módulo de Unificação (Juntar)](#módulo-de-unificação-juntar)
    * [Módulo de Divisão e Extração](#módulo-de-divisão-e-extração)
    * [Protocolos de Segurança e Auditoria](#protocolos-de-segurança-e-auditoria)
5. [Instruções de Instalação e Execução](#5-instruções-de-instalação-e-execução)
6. [Suporte e Manutenção](#6-suporte-e-manutenção)
7. [Licença e Créditos](#7-licença-e-créditos)

---

## 1. Apresentação

O **JuntaPDF** é uma solução de software desenvolvida para atender às demandas de manipulação técnica de documentos digitais no formato PDF (*Portable Document Format*). O sistema foi projetado com foco estrito na segurança da informação, privacidade de dados e conformidade com normas de arquivamento digital e preservação de longo prazo.

Diferente de soluções baseadas em nuvem (*SaaS*), o JuntaPDF executa todo o processamento localmente na estação de trabalho. Isso garante que documentos sensíveis, autos de processos e dados pessoais não trafeguem por redes externas, mitigando riscos de vazamento e assegurando a soberania sobre o acervo documental.

## 2. Finalidade e Aplicação

Esta ferramenta destina-se a servidores, arquivistas, advogados e gestores que necessitam realizar operações de:

* **Unificação Documental (Juntar):** Consolidação de múltiplos arquivos dispersos em um único volume digital, mantendo a integridade lógica e a ordenação sequencial necessária para a instrução processual ou administrativa.
* **Segmentação (Dividir/Extrair):** Fragmentação de documentos volumosos ou extração de páginas específicas (peças processuais) para atendimento de diligências ou reorganização de fundos documentais.
* **Preservação Digital (PDF/A):** Conversão e validação de documentos para o padrão ISO 19005-2 (PDF/A-2b), garantindo a acessibilidade e a reprodutibilidade do documento a longo prazo.
* **Otimização de Acervo:** Compressão inteligente de arquivos para adequação aos limites de upload impostos por sistemas de peticionamento eletrônico e gestão pública (PJe, e-SAJ, SEI, etc.), sem comprometimento da legibilidade.

## 3. Requisitos de Sistema

Para a correta execução em ambiente de produção:

* **Sistema Operacional:** Windows 10/11, Linux ou macOS.
* **Runtime:** Python 3.8 ou superior.
* **Dependências de Terceiros:** Ghostscript (necessário apenas para os módulos de conversão PDF/A e compressão avançada).
* **Privilégios:** Não requer privilégios administrativos para execução (instalação em nível de usuário).

## 4. Funcionalidades Detalhadas

### Módulo de Unificação (Juntar)
Permite a agregação de múltiplos arquivos PDF em um único volume consolidado.
* **Ordenação:** Flexibilidade para ordenação manual ou alfabética antes da fusão.
* **Sanitização:** Remoção automática de metadados que não sejam pertinentes ao documento final (limpeza de rastros de edição).
* **Sigilo:** Possibilidade de aplicar criptografia (senha) no documento unificado.

### Módulo de Divisão e Extração
Oferece quatro modalidades de segmentação documental:
1.  **Extração Seletiva:** Retirada de páginas específicas (ex: páginas 1, 5-10, 20) para compor novo arquivo.
2.  **Intervalo Regular:** Divisão do documento em blocos de tamanho fixo (ex: volumes de 200 páginas).
3.  **Particionamento Equitativo:** Divisão do arquivo original em um número predeterminado de partes iguais.
4.  **Individualização:** Conversão de cada página do documento original em um arquivo independente.

### Protocolos de Segurança e Auditoria
* **Execução Offline:** O código não possui rotinas de telemetria, *analytics* ou comunicação externa.
* **Trilha de Auditoria (Logs):** O sistema mantém registro local das operações. Dados sensíveis (senhas, nomes de usuário e caminhos de rede pessoais) são ofuscados automaticamente nos registros através de expressões regulares.
* **Validação de Integridade:** Verificação automática de cabeçalhos e estruturas do PDF para prevenir a corrupção de arquivos durante o processamento.

## 5. Instruções de Instalação e Execução

### Procedimento Padrão

1.  Certifique-se de que o interpretador Python esteja devidamente instalado na estação de trabalho.
2.  Transfira o pacote de arquivos do sistema para um diretório local.
3.  Execute o *script* principal através do terminal ou do executável gerado:
    ```bash
    python juntapdf.py
    ```
4.  Para habilitar a funcionalidade de PDF/A, instale o Ghostscript e assegure-se de que o executável esteja mapeado nas variáveis de ambiente (PATH).

## 6. Suporte e Manutenção

Inconsistências na execução ou falhas na integridade dos arquivos gerados devem ser reportadas via abertura de chamado técnico (*Issue*) no repositório de controle de versão. Recomenda-se anexar o arquivo de log sanitizado (localizado no diretório temporário do sistema) para análise.

## 7. Licença e Créditos

**Copyright © 2025 Angelo Filho.**

Este software é distribuído sob a licença **BSD 3-Clause**.
O uso desta ferramenta em ambientes institucionais deve observar as políticas internas de segurança da informação e gestão documental vigentes na organização.