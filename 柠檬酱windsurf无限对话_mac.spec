# -*- mode: python ; coding: utf-8 -*-
# macOS 版本打包配置
# 使用方法: pyinstaller 柠檬酱windsurf无限对话_mac.spec

import sys
import os

a = Analysis(
    ['ai_feedback_tool_blocking.py'],
    pathex=[],
    binaries=[],
    # macOS 使用正斜杠路径，sounds 目录包含音效文件
    datas=[
        ('frontend/dist', 'frontend/dist'),
        ('sounds', 'sounds'),
    ],
    hiddenimports=[
        'webview',
        'webview.platforms.cocoa',  # macOS WebKit 后端
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='柠檬酱windsurf无限对话',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# macOS .app 包（可选，双击启动）
app = BUNDLE(
    exe,
    name='柠檬酱windsurf无限对话.app',
    # 如果有 .icns 图标文件，取消注释下行
    # icon='icon.icns',
    bundle_identifier='com.lemonjam.windsurf-dialog',
    info_plist={
        'CFBundleName': '柠檬酱windsurf无限对话',
        'CFBundleDisplayName': '柠檬酱windsurf无限对话',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSHighResolutionCapable': True,
    },
)
