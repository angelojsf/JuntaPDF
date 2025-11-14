# JuntaPDF

[![Python](https://img.shields.io/badge/Python-3.7%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

**Professional tool for merging, splitting, and optimizing PDFs - 100% local and secure**

**Repository:** https://github.com/angelojsf/JuntaPDF

**Language:** [Português (BR)](README.md) | **English**

---

## Table of Contents

- [Overview](#overview)
- [Installation](#installation)
  - [Windows](#windows)
  - [Linux/macOS](#linuxmacos)
- [How to Use](#how-to-use)
  - [Merge PDFs](#merge-pdfs)
  - [Split PDFs](#split-pdfs)
- [Technical Features](#technical-features)
- [Enterprise Deployment](#enterprise-deployment)
- [Monitoring and Logs](#monitoring-and-logs)
- [FAQ](#faq)
- [Support](#support)
- [License](#license)

---

## Overview

JuntaPDF is a desktop tool for PDF document manipulation focused on security, compliance, and 100% local processing. Ideal for corporate environments, public institutions, and privacy-conscious users.

**Key Features:**
- Fully offline processing (zero data sent to the internet)
- PDF/A-2B standard compliance (ISO 19005-2)
- Intuitive drag-and-drop interface
- File integrity validation
- Automatic log sanitization system
- Password protection and intelligent compression

---

## Installation

### Windows

**1. Install Python 3.7 or higher**

Download from [python.org](https://www.python.org/downloads/) and during installation:
- Check the **"Add Python to PATH"** option
- Recommended: Check **"Install for all users"** (corporate environments)

**2. Clone the repository**

```bash
git clone https://github.com/angelojsf/JuntaPDF.git
cd JuntaPDF
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. (Optional) Install Ghostscript for PDF/A features**

Download the installer from [ghostscript.com/releases](https://ghostscript.com/releases/gsdnld.html) and install. Required only for PDF/A-2B format generation.

**5. Run the program**

```bash
python juntapdf.py
```

### Linux/macOS

```bash
# Clone the repository
git clone https://github.com/angelojsf/JuntaPDF.git
cd JuntaPDF

# Install dependencies
pip3 install -r requirements.txt

# (Optional) Install Ghostscript via package manager
# Ubuntu/Debian:
sudo apt-get install ghostscript

# macOS (Homebrew):
brew install ghostscript

# Run
python3 juntapdf.py
```

---

## How to Use

### Merge PDFs

1. **Add files:** Drag PDF files to the list area or click "Add PDFs"
2. **Reorder:** Select a file and use `Shift + ↑/↓` to change order
3. **Remove:** Select file(s) and press `Delete` or click "Remove Selected"
4. **Configure options:**
   - Choose compression level (Quality, Balanced, Size)
   - (Optional) Enable PDF/A-2B conversion
   - (Optional) Set password protection
5. **Process:** Click "MERGE PDFs" and choose destination folder

**Result:** File `merged_output.pdf` (or custom name) in the chosen folder.

### Split PDFs

1. **Add file:** Load a single PDF file
2. **Choose split mode:**
   - **Extract specific pages:** Enter ranges (e.g., `1-5, 10, 15-20`)
   - **Fixed interval:** Set number of pages per file (e.g., `5` = 5-page blocks)
   - **Equal parts:** Divide into X files of similar size
   - **All pages:** Generate one file per individual page
3. **Process:** Click "PROCESS PDFs" and choose destination folder

**Result:** Sequentially numbered files (e.g., `document_part_001.pdf`, `document_part_002.pdf`).

---

## Technical Features

| Feature | Technical Details | Benefit |
|---------|------------------|---------|
| **PDF/A-2B** | Conversion via Ghostscript with sRGB OutputIntent | ISO 19005-2 compliance for long-term archiving, compatible with government systems and electronic document management |
| **Compression** | 3 levels using `pikepdf` (object streams, JPEG/Flate filters) | Reduces size while maintaining visual quality. "Quality" mode preserves maximum resolution |
| **Password Protection** | AES-128 encryption, Owner/User password support | Local access control without dependency on external services |
| **Integrity Validation** | PDF structure checking (xref, trailer, objects) | Detects corrupted or potentially malicious PDFs before processing |
| **Drag & Drop Interface** | `tkinterdnd2` library with visual feedback | Reduces learning curve, streamlines workflow |
| **Sanitized Logs** | Automatic removal of sensitive information (absolute paths, usernames) | GDPR/privacy compliance, facilitates auditing without exposing personal data |
| **Performance Monitoring** | Integrated dashboard with CPU, memory, and disk metrics | Identifies bottlenecks in large batch processing |

### Operating Limits

- **Files per operation:** 100 files
- **Total pages:** 10,000 pages per operation
- **Maximum size per file:** 500 MB
- **Log retention:** 30 days (automatic cleanup)

---

## Enterprise Deployment

### Silent Installation

```bash
# Silent Python dependencies installation
pip install --no-input --quiet PyPDF2==3.0.1 pikepdf==8.10.2 tkinterdnd2==0.3.0 psutil>=5.8.0

# Ghostscript (Windows - command line)
# Download .exe from https://ghostscript.com/releases/gsdnld.html
# Execute with parameters:
gs-installer.exe /S /D=C:\Program Files\gs\gs10.02.1
```

### Environment Requirements

- **Python:** 3.7 or higher
- **Operating System:** Windows 10+, Ubuntu 20.04+, macOS 11+
- **RAM Memory:** Minimum 4 GB (recommended 8 GB for batch processing)
- **Disk Space:** 100 MB for installation + temporary space for processing (up to 2x PDF size)
- **Ghostscript:** Version 9.50+ (required only for PDF/A features)

### Network Configuration

**Does not require internet connection** during operation. All dependencies are installed locally.

### Audit and Compliance

- **Structured logs:** JSON with timestamp, operation, status, and duration
- **Location:** `%TEMP%\JuntaPDF_Logs\` (Windows) or `/tmp/JuntaPDF_Logs/` (Linux/macOS)
- **Sanitization:** File paths reduced to base names, user identifier removal
- **Format:** Compatible with SIEM tools (Splunk, ELK Stack)

**Log entry example:**

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

## Monitoring and Logs

### Performance Dashboard

Access via menu **"Tools" → "Performance Monitor"**:

- **CPU Usage:** Real-time graph per core
- **Memory:** Active consumption vs. available
- **Disk:** I/O speed and free space
- **History:** Last 50 operations with processing times

### Log Management

- **Retention:** Logs are kept for 30 days
- **Cleanup:** Automatic on program startup
- **Export:** "Export Logs" button in dashboard generates ZIP file

### Health Indicators

| Indicator | Normal Value | Recommended Action |
|-----------|--------------|-------------------|
| CPU > 90% for > 5 min | < 80% | Reduce batch size or close concurrent applications |
| Memory > 90% | < 75% | Process fewer files simultaneously |
| Disk I/O < 10 MB/s | > 50 MB/s | Check real-time antivirus or disk fragmentation |

---

## FAQ

### General Questions

**Q: Does the program need internet?**  
A: No. All processing is done locally. Internet is only required for initial installation of Python dependencies.

**Q: Are PDFs sent to any server?**  
A: No. No data leaves your computer. The code is auditable at [github.com/angelojsf/JuntaPDF](https://github.com/angelojsf/JuntaPDF).

**Q: Is it free for commercial use?**  
A: Yes. Licensed under BSD-3-Clause (see [LICENSE](LICENSE)).

### Compatibility

**Q: Does it work with government electronic document systems?**  
A: Yes. PDF/A-2B conversion ensures compatibility with systems requiring ISO 19005 standard.

**Q: What's the difference between PDF/A-1B and PDF/A-2B?**  
A: PDF/A-2B (used by JuntaPDF) supports JPEG2000 compression, transparency, and layers while maintaining archival compliance. PDF/A-1B is more restrictive. For most cases, PDF/A-2B is preferable.

**Q: Are digitally signed PDFs supported?**  
A: Partially. The tool can process signed PDFs, but digital signatures will be invalidated after modification (expected behavior for any PDF manipulation). To preserve signatures, do not process the document.

### Troubleshooting

**Q: "Ghostscript not found" error when enabling PDF/A**  
A: Install Ghostscript as per [Installation](#installation) section. On Windows, add `C:\Program Files\gs\gs10.XX.X\bin` to system PATH.

**Q: Program froze when processing large file**  
A: Files > 200 MB may cause slowdown. Solution:
1. Split the PDF into smaller parts first
2. Use "Size" compression level to reduce memory usage
3. Close other programs

**Q: Output PDF is corrupted/won't open**  
A: Possible causes:
- Input PDF was already corrupted (use repair tool like `pdftk`)
- Interruption during processing (don't close program until completion)
- Insufficient disk space (check destination partition)

**Q: How to report a bug?**  
A: Open an issue at [github.com/angelojsf/JuntaPDF/issues](https://github.com/angelojsf/JuntaPDF/issues) including:
- Operating system and Python version
- Log file (if available)
- Steps to reproduce the problem

---

## Support

- **Issues and Bugs:** [GitHub Issues](https://github.com/angelojsf/JuntaPDF/issues)
- **Technical Documentation:** This README and commented source code
- **Component Licenses:** [LICENSE](LICENSE) | [NOTICE](NOTICE)

---

## License

Copyright (c) 2025 Angelo José

This project is licensed under the [BSD 3-Clause License](LICENSE). See LICENSE file for complete details.

### Third-Party Components

- **PyPDF2** - BSD License
- **pikepdf** - MPL 2.0
- **tkinterdnd2** - MIT License
- **Ghostscript** - AGPL 3.0 (optional usage)

See [NOTICE](NOTICE) for complete information on dependency licenses.

---

**Developed with focus on privacy, security, and institutional compliance.**