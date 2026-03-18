# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 빌드 설정 — 목표 크기 50MB 이하"""

import os

block_cipher = None

# 불필요한 패키지 최대한 제거
EXCLUDES = [
    # 데이터 과학
    'matplotlib', 'numpy', 'pandas', 'scipy', 'sklearn',
    # 이미지/영상
    'PIL', 'cv2', 'imageio',
    # ML/딥러닝
    'torch', 'tensorflow', 'keras',
    # GUI (tkinter 제외)
    'PyQt5', 'PyQt6', 'wx', 'PySide2', 'PySide6',
    # Jupyter/IPython
    'IPython', 'jupyter', 'notebook', 'nbformat',
    # 테스트
    'test', 'unittest', 'pytest', 'doctest',
    # 기타 불필요
    'xmlrpc', 'ftplib', 'imaplib', 'poplib', 'smtplib', 'telnetlib',
    'audioop', 'crypt', 'ossaudiodev', 'spwd', 'sunau',
    'distutils', 'lib2to3',
    # openai / anthropic 내부의 무거운 옵션
    'openai._legacy_response',
    'httpx._transports.asgi',
    'httpx._transports.wsgi',
]

a = Analysis(
    ['../main.py'],
    pathex=[os.path.abspath('..')],
    binaries=[],
    datas=[],
    hiddenimports=[
        # chardet
        'chardet',
        'chardet.universaldetector',
        # tkinter
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'tkinter.font',
        # 표준 라이브러리
        'base64', 'json', 'os', 're', 'math', 'threading',
        'socket', 'logging', 'datetime',
        # 네트워크
        'httpx',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ChatSummarizer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,        # 심볼 제거로 크기 절감
    upx=True,          # UPX 압축 (~20~30% 추가 절감)
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,     # 콘솔 창 없는 GUI 앱
    icon=None,
    version=None,
)
