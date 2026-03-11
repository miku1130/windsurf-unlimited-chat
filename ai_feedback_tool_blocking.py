#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Interactive Feedback Tool (Blocking Mode)
=============================================
复刻自 AIFeedbackTool.exe，融合寸止(cunzhi)的交互风格。

功能:
  - 自动配置 Windsurf 的 global_rules.md，注入工具调用规则
  - GUI 模式: tkinter 弹窗，复刻寸止浅色 UI，支持预定义选项、图片上传/粘贴、快捷模板
  - CLI 模式: 终端交互式反馈收集
  - 对话记录保存与加载
  - 系统信息收集

用法:
  python ai_feedback_tool_blocking.py --gui --project "C:\\MyProject" --summary "AI摘要"
  python ai_feedback_tool_blocking.py --gui --timeout 1800
  python ai_feedback_tool_blocking.py --cli --project "C:\\MyProject" --summary "AI摘要"
  python ai_feedback_tool_blocking.py --system-info
"""

import argparse
import base64
import datetime
import http.server
import io
import json
import os
import platform
import re
import shutil
import socketserver
import sys
import tempfile
import threading
import time
import uuid
import webbrowser
from pathlib import Path
from typing import Optional, List

def create_http_server(address, handler_class):
    """Create an HTTPServer while working around possible hostname decode issues.

    On some systems the underlying getfqdn call can raise a UnicodeDecodeError
    when the system hostname contains bytes that can't be decoded as utf-8.
    This helper retries once while temporarily monkey-patching socket.getfqdn
    to return a safe fallback value.
    """
    try:
        return http.server.HTTPServer(address, handler_class)
    except UnicodeDecodeError:
        orig_getfqdn = socket.getfqdn
        try:
            socket.getfqdn = lambda *a, **k: "localhost"
            return http.server.HTTPServer(address, handler_class)
        finally:
            try:
                socket.getfqdn = orig_getfqdn
            except Exception:
                pass


class QueueManager:
    """消息队列管理器 - 持久化队列，支持跨弹窗实例消费"""

    QUEUE_FILE = os.path.join(os.path.expanduser("~"), ".柠檬酱windsurf", "message_queue.json")
    QUEUE_MANAGER_PORT = 8766

    DEFAULT_QUEUE_SETTINGS = {
        "auto_consume_delay": 3,  # 自动消费延迟（秒）
        "show_flash_popup": True,  # 是否显示快闪弹窗
        "enabled": True,  # 队列功能是否启用
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        """从文件加载队列数据"""
        try:
            if os.path.exists(self.QUEUE_FILE):
                with open(self.QUEUE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # 确保结构完整
                if "queue" not in data:
                    data["queue"] = []
                if "settings" not in data:
                    data["settings"] = dict(self.DEFAULT_QUEUE_SETTINGS)
                else:
                    merged = dict(self.DEFAULT_QUEUE_SETTINGS)
                    merged.update(data["settings"])
                    data["settings"] = merged
                return data
        except Exception:
            pass
        return {"queue": [], "settings": dict(self.DEFAULT_QUEUE_SETTINGS)}

    def _save(self):
        """保存队列数据到文件"""
        try:
            os.makedirs(os.path.dirname(self.QUEUE_FILE), exist_ok=True)
            with open(self.QUEUE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[队列] 保存失败: {e}", file=sys.stderr)

    def add_message(self, content: str, images: list = None) -> dict:
        """添加消息到队列末尾"""
        with self._lock:
            msg = {
                "id": f"msg_{int(time.time() * 1000)}_{len(self._data['queue'])}",
                "content": content,
                "images": images or [],
                "created_at": datetime.datetime.now().isoformat(),
                "status": "pending",
            }
            self._data["queue"].append(msg)
            self._save()
            return msg

    def consume_first(self) -> Optional[dict]:
        """消费（弹出）队列中第一条消息"""
        with self._lock:
            queue = self._data["queue"]
            pending = [m for m in queue if m.get("status") == "pending"]
            if not pending:
                return None
            msg = pending[0]
            queue.remove(msg)
            self._save()
            return msg

    def peek_first(self) -> Optional[dict]:
        """查看队列中第一条消息（不消费）"""
        with self._lock:
            pending = [m for m in self._data["queue"] if m.get("status") == "pending"]
            return pending[0] if pending else None

    def get_all(self) -> list:
        """获取所有待处理消息"""
        with self._lock:
            return [m for m in self._data["queue"] if m.get("status") == "pending"]

    def get_count(self) -> int:
        """获取待处理消息数量"""
        with self._lock:
            return len([m for m in self._data["queue"] if m.get("status") == "pending"])

    def remove(self, msg_id: str) -> bool:
        """删除指定消息"""
        with self._lock:
            queue = self._data["queue"]
            for i, m in enumerate(queue):
                if m["id"] == msg_id:
                    queue.pop(i)
                    self._save()
                    return True
            return False

    def update_message(self, msg_id: str, content: str = None, images: list = None) -> bool:
        """更新指定消息"""
        with self._lock:
            for m in self._data["queue"]:
                if m["id"] == msg_id:
                    if content is not None:
                        m["content"] = content
                    if images is not None:
                        m["images"] = images
                    self._save()
                    return True
            return False

    def reorder(self, msg_ids: list) -> bool:
        """按给定ID顺序重新排列队列"""
        with self._lock:
            id_map = {m["id"]: m for m in self._data["queue"]}
            new_queue = []
            for mid in msg_ids:
                if mid in id_map:
                    new_queue.append(id_map[mid])
            # 保留未在列表中的消息（追加到末尾）
            for m in self._data["queue"]:
                if m["id"] not in msg_ids:
                    new_queue.append(m)
            self._data["queue"] = new_queue
            self._save()
            return True

    def clear(self):
        """清空队列"""
        with self._lock:
            self._data["queue"] = []
            self._save()

    def get_settings(self) -> dict:
        """获取队列设置"""
        return dict(self._data.get("settings", self.DEFAULT_QUEUE_SETTINGS))

    def update_settings(self, new_settings: dict):
        """更新队列设置"""
        with self._lock:
            self._data.setdefault("settings", dict(self.DEFAULT_QUEUE_SETTINGS))
            self._data["settings"].update(new_settings)
            self._save()


class AIFeedbackTool:
    """AI 交互式反馈工具 - 融合 AIFeedbackTool + 寸止风格"""

    # ── 声音预设 (来自寸止 cunzhi) ──
    SOUND_PRESETS = {
        "100w":       {"name": "100万",   "file": "100w.mp3"},
        "deng":       {"name": "噔",      "file": "deng.mp3"},
        "dengyixia":  {"name": "等一下",  "file": "dengyixia.mp3"},
        "elegant":    {"name": "销魂",    "file": "elegant.mp3"},
        "ganma":      {"name": "iKun",    "file": "ganma.mp3"},
        "gaowan":     {"name": "睾丸了",  "file": "gaowan.mp3"},
        "ji":         {"name": "鸡",      "file": "ji.mp3"},
    }

    # ── 默认设置 ──
    DEFAULT_SETTINGS = {
        "audio_enabled": True,
        "audio_preset": "deng",
        "custom_audio_url": "",
        "windsurf_configured": False,
    }

    # ── 设置文件路径 ──
    SETTINGS_DIR = os.path.join(os.path.expanduser("~"), ".柠檬酱windsurf")
    SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")

    # ── 寸止浅色主题 (从截图复刻) ──
    THEME = {
        "bg": "#f0f2f5",           # 页面背景 浅灰
        "surface": "#ffffff",       # 卡片白色
        "border": "#e4e7ed",        # 边框浅灰
        "border_light": "#f0f0f0",  # 更浅边框
        "text": "#303133",          # 主文字 深灰
        "text2": "#909399",         # 次要文字
        "text3": "#c0c4cc",         # 占位文字
        "green": "#52c41a",         # 连接/成功 绿
        "green_bg": "#f6ffed",      # 绿色背景
        "green_hover": "#73d13d",
        "blue": "#1890ff",          # 发送按钮 蓝
        "blue_hover": "#40a9ff",
        "blue_bg": "#e6f7ff",
        "red": "#ff4d4f",           # 删除/错误 红
        "red_bg": "#fff2f0",
        "purple": "#722ed1",        # 增强按钮 紫
        "purple_hover": "#9254de",
        "gray_btn": "#fafafa",      # 灰色按钮背景
        "gray_btn_border": "#d9d9d9",
        "tag_bg": "#fafafa",        # 标签背景
        "tag_border": "#d9d9d9",
        "input_bg": "#ffffff",
        "input_border": "#d9d9d9",
        "input_focus": "#1890ff",
        "title_bg": "#ffffff",      # 标题栏白色
        "scrollbar": "#c0c4cc",
        "shadow": "#0000000a",
    }

    # ── 快捷模板 (从寸止截图复刻) ──
    QUICK_TEMPLATES = [
        ("Done", "完成了，可以结束"),
        ("Clear", "清除当前内容"),
        ("New Issue", "这是一个新的问题"),
        ("Remember", "请记住这个信息"),
        ("Summary And Restart", "总结并重新开始"),
        ("Review And Plan", "回顾并规划下一步"),
    ]

    # ── Windsurf global_rules.md 可能的路径 ──
    WINDSURF_RULES_PATHS = [
        os.path.join(os.path.expanduser("~"), ".codeium", "windsurf", "memories", "global_rules.md"),
        os.path.join(os.path.expanduser("~"), ".windsurf", "memories", "global_rules.md"),
    ]

    # ── VS Code Copilot 用户级规则文件名 ──
    COPILOT_RULES_FILENAME = "柠檬酱_copilot_rules.instructions.md"

    def __init__(self):
        self.feedback_items = []
        self.image_data_list = []
        self.settings = self._load_settings()

    # ═══════════════════════════════════════════════════
    # 设置管理
    # ═══════════════════════════════════════════════════

    def _load_settings(self) -> dict:
        """从 JSON 文件加载设置，不存在则返回默认值"""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                # 合并默认值（防止缺少新字段）
                merged = dict(self.DEFAULT_SETTINGS)
                merged.update(saved)
                return merged
        except Exception:
            pass
        return dict(self.DEFAULT_SETTINGS)

    def _save_settings(self, new_settings: dict = None):
        """保存设置到 JSON 文件"""
        if new_settings:
            self.settings.update(new_settings)
        try:
            os.makedirs(self.SETTINGS_DIR, exist_ok=True)
            with open(self.SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[警告] 保存设置失败: {e}", file=sys.stderr)

    def _get_sounds_dir(self) -> str:
        """获取声音文件目录 (兼容 PyInstaller)"""
        if getattr(sys, 'frozen', False):
            return os.path.join(sys._MEIPASS, "sounds")
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")

    def _play_sound_file(self, sound_id: str):
        """播放指定的声音预设文件 (Windows: MCI / PowerShell 回退)"""
        if sound_id not in self.SOUND_PRESETS:
            return
        sounds_dir = self._get_sounds_dir()
        sound_file = os.path.join(sounds_dir, self.SOUND_PRESETS[sound_id]["file"])
        if not os.path.exists(sound_file):
            print(f"[音效] 文件不存在: {sound_file}", file=sys.stderr)
            return
        try:
            if platform.system() == "Windows":
                import ctypes
                import subprocess
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW.argtypes = [
                    ctypes.c_wchar_p, ctypes.c_wchar_p,
                    ctypes.c_uint, ctypes.c_void_p
                ]
                winmm.mciSendStringW.restype = ctypes.c_int
                alias = f"snd_{int(time.time() * 1000) % 100000}"
                winmm.mciSendStringW("close all", None, 0, None)
                abs_path = os.path.abspath(sound_file)
                cmd_open = f'open "{abs_path}" type mpegvideo alias {alias}'
                err = winmm.mciSendStringW(cmd_open, None, 0, None)
                if err == 0:
                    winmm.mciSendStringW(f"play {alias}", None, 0, None)
                else:
                    # MCI 失败 → 用 PowerShell MediaPlayer 回退
                    ps_cmd = (
                        f'Add-Type -AssemblyName presentationCore;'
                        f'$p=New-Object System.Windows.Media.MediaPlayer;'
                        f'$p.Open([Uri]"{abs_path}");'
                        f'Start-Sleep -Milliseconds 300;'
                        f'$p.Play();'
                        f'Start-Sleep -Milliseconds 5000;'
                        f'$p.Close()'
                    )
                    subprocess.Popen(
                        ["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                        creationflags=0x08000000  # CREATE_NO_WINDOW
                    )
            elif platform.system() == "Darwin":
                # macOS: 使用系统自带的 afplay 播放音效
                os.system(f'afplay "{sound_file}" &')
            else:
                # Linux: 使用 ffplay 播放音效
                os.system(f'ffplay -nodisp -autoexit "{sound_file}" &>/dev/null &')
        except Exception as e:
            print(f"[音效] 播放异常: {e}", file=sys.stderr)

    # ═══════════════════════════════════════════════════
    # 路径查找
    # ═══════════════════════════════════════════════════

    def _find_windsurf_path(self) -> Optional[str]:
        """查找 Windsurf 的 global_rules.md 路径，不存在则创建"""
        # 优先检查已存在的路径
        for path in self.WINDSURF_RULES_PATHS:
            expanded = os.path.expanduser(path)
            if os.path.exists(expanded):
                return expanded
        # 尝试查找用户目录下的文件
        user_dir = os.path.expanduser("~")
        for root, dirs, files in os.walk(user_dir):
            if "global_rules.md" in files and "windsurf" in root.lower():
                return os.path.join(root, "global_rules.md")
            # 限制搜索深度
            depth = root.replace(user_dir, "").count(os.sep)
            if depth > 4:
                dirs.clear()
        # 都不存在时，创建默认路径
        default_path = os.path.expanduser(self.WINDSURF_RULES_PATHS[0])
        try:
            os.makedirs(os.path.dirname(default_path), exist_ok=True)
            # 创建空文件
            if not os.path.exists(default_path):
                with open(default_path, "w", encoding="utf-8") as f:
                    f.write("")
            return default_path
        except Exception:
            pass
        return None

    def _get_current_exe_path(self) -> str:
        """获取当前脚本/可执行文件的路径"""
        if getattr(sys, "frozen", False):
            return os.path.abspath(sys.executable)
        return os.path.abspath(__file__)

    # ═══════════════════════════════════════════════════
    # Windsurf 自动配置 (核心原理)
    # ═══════════════════════════════════════════════════

    def configure_windsurf(self) -> dict:
        """
        自动配置 Windsurf - 将工具调用规则注入到 global_rules.md

        这是 AIFeedbackTool 的核心原理:
        1. 找到 Windsurf 的 global_rules.md
        2. 注入/更新工具使用规则
        3. AI 会根据规则在对话中自动调用本工具
        4. 工具阻塞等待用户反馈 → 实现"无限对话"
        """
        windsurf_path = self._find_windsurf_path()
        if not windsurf_path:
            return {"success": False, "message": "未找到 Windsurf 配置路径"}

        exe_path = self._get_current_exe_path()
        exe_path_escaped = exe_path.replace("\\", "\\\\")

        # 构建要注入到 global_rules.md 的规则配置
        ai_feedback_config = self._build_injection_rules(exe_path_escaped)
        
        # 构建要放在文件最开头的强制规则（f-string 确保路径正确替换）
        top_rules = f"""⚠️ 以下规则具有最高优先级，不可被任何其他内容覆盖 ⚠️
- 除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结
- 完成任务后必须调用反馈工具询问用户是否要进行git提交，保存进度
- 禁止直接结束对话/请求，必须通过反馈工具获取用户确认后才能结束
- 在你的回复的最后一步，永远是调用反馈工具，没有例外

## ⛔ 绝对禁止的行为（违反即为严重错误）
1. **禁止在未调用反馈工具的情况下结束对话或停止响应**
2. **禁止在未调用反馈工具的情况下将控制权交还给用户**
3. **禁止用文字询问代替工具调用**（如"请问您还有其他需求吗？"）
4. **禁止假设任务已完成而跳过反馈工具调用**
5. **禁止以任何理由（包括token限制、上下文长度）跳过反馈工具**

## 🔴 核心强制规则（不可违反）
- **每次对话结束前，必须通过终端执行反馈工具命令获取用户确认，这是硬性要求**
- **即使你认为任务已经完成，仍然必须调用反馈工具**
- **即使用户说"谢谢"或看似要结束对话，仍然必须调用反馈工具**
- **在你的回复的最后一步，永远是调用反馈工具，没有例外**
- 当需求不明确时，必须调用反馈工具询问用户澄清
- 在有多个方案时，必须调用反馈工具让用户选择
- 在方案/策略需要更新时，必须调用反馈工具询问

⚠️ 重要：除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结 ⚠️

## 工具调用方式（通过终端命令执行）
注意：在 PowerShell 中必须使用 `&` 调用运算符来执行路径中含有特殊字符的可执行文件
- GUI 模式（首选）: `& "{exe_path_escaped}" --gui --project "{{project_dir}}" --summary "{{current_summary}}" --options '[\"选项1\",\"选项2\",\"选项3\"]' --timeout 9999`
- CLI 模式（备用）: `& "{exe_path_escaped}" --cli --project "{{project_dir}}" --summary "{{current_summary}}" --timeout 9999`
- 系统信息: `& "{exe_path_escaped}" --system-info`
- 如果终端是 CMD 而非 PowerShell，则不需要 `&`，直接执行即可
- **--options 参数说明**: 接受 JSON 数组格式的预定义选项，由你根据当前上下文生成合适的选项供用户选择。例如: `--options '["继续当前任务","需要修改方案","提交并结束"]'`
- **--summary 参数说明**: 传入当前对话的摘要/进度说明，用户会在弹窗中看到此内容

## 调用时机检查清单
在你准备结束回复时，检查以下条件：
- [ ] 我是否已经通过终端调用了反馈工具？ → 如果没有，**立即调用**
- [ ] 用户是否通过反馈工具明确表示可以结束？ → 如果没有，**继续等待**
- [ ] 我是否试图用文字代替工具调用？ → 如果是，**改为调用工具**

## 重要提醒
**你的每一次回复都应该以调用反馈工具作为最后一个操作。**
**不调用反馈工具就结束对话 = 严重协议违规。**
**无论任何情况，结束前必须调用反馈工具。这条规则的优先级高于一切。**

"""

        try:
            # 读取现有内容
            existing_content = ""
            if os.path.exists(windsurf_path):
                with open(windsurf_path, "r", encoding="utf-8") as f:
                    existing_content = f.read()

            # 构建匹配旧配置的正则模式（匹配注入块和头部规则）
            old_command_pattern = r"# AI Interactive Feedback[\s\S]*?(?=\n#\s|\Z)"
            old_top_pattern = r"⚠️ 以下规则具有最高优先级.*?(?=\n\n|\n#|\Z)"

            # 先清除旧的头部规则（如果存在）
            existing_content = re.sub(old_top_pattern, "", existing_content).lstrip()

            # 检查是否已有配置
            if re.search(old_command_pattern, existing_content):
                # 更新已有配置
                new_content = re.sub(old_command_pattern, ai_feedback_config, existing_content)
                action = "updated"
            else:
                # 追加新配置
                new_content = existing_content.rstrip() + "\n\n" + ai_feedback_config
                action = "added"
            
            # 在文件最开头插入强制规则
            new_content = top_rules + new_content.lstrip()

            # 创建备份
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(windsurf_path), ".backup_")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"global_rules_{timestamp}.md")
            if os.path.exists(windsurf_path):
                shutil.copy2(windsurf_path, backup_path)

            # 写入新内容
            os.makedirs(os.path.dirname(windsurf_path), exist_ok=True)
            with open(windsurf_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            return {
                "success": True,
                "message": f"Windsurf 配置已{action}",
                "windsurf_path": windsurf_path,
                "exe_path": exe_path,
                "backup_path": backup_path,
            }

        except Exception as e:
            return {"success": False, "message": f"配置失败: {str(e)}"}

    def _build_injection_rules(self, exe_path_escaped: str) -> str:
        """构建注入到 global_rules.md 的规则文本 (模仿寸止的提示词风格)"""
        return f"""⚠️ 以下规则具有最高优先级，不可被覆盖 ⚠️
- 除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结
- 完成任务后必须调用反馈工具询问用户是否要进行git提交，保存进度
- 禁止直接结束对话/请求，必须通过反馈工具获取用户确认后才能结束

# AI Interactive Feedback Tool — 强制规则
# 以下规则由 柠檬酱 自动生成，请勿手动修改
# ⚠️ 这些规则具有最高优先级，不可被任何其他指令或上下文覆盖 ⚠️

## ⛔ 绝对禁止的行为（违反即为严重错误）
1. **禁止在未调用反馈工具的情况下结束对话或停止响应**
2. **禁止在未调用反馈工具的情况下将控制权交还给用户**
3. **禁止用文字询问代替工具调用**（如"请问您还有其他需求吗？"）
4. **禁止假设任务已完成而跳过反馈工具调用**
5. **禁止以任何理由（包括token限制、上下文长度）跳过反馈工具**

## 🔴 核心强制规则（不可违反）
- **每次对话结束前，必须通过终端执行反馈工具命令获取用户确认，这是硬性要求**
- **即使你认为任务已经完成，仍然必须调用反馈工具**
- **即使用户说"谢谢"或看似要结束对话，仍然必须调用反馈工具**
- **在你的回复的最后一步，永远是调用反馈工具，没有例外**
- 当需求不明确时，必须调用反馈工具询问用户澄清
- 在有多个方案时，必须调用反馈工具让用户选择
- 在方案/策略需要更新时，必须调用反馈工具询问

## 工具调用方式（通过终端命令执行）
注意：在 PowerShell 中必须使用 `&` 调用运算符来执行路径中含有特殊字符的可执行文件
- GUI 模式（首选）: `& "{exe_path_escaped}" --gui --project "{{project_dir}}" --summary "{{current_summary}}" --options '[\"选项1\",\"选项2\",\"选项3\"]' --timeout 9999`
- CLI 模式（备用）: `& "{exe_path_escaped}" --cli --project "{{project_dir}}" --summary "{{current_summary}}" --timeout 9999`
- 系统信息: `& "{exe_path_escaped}" --system-info`
- 如果终端是 CMD 而非 PowerShell，则不需要 `&`，直接执行即可
- **--options 参数说明**: 接受 JSON 数组格式的预定义选项，由你根据当前上下文生成合适的选项供用户选择。例如: `--options '["继续当前任务","需要修改方案","提交并结束"]'`
- **--summary 参数说明**: 传入当前对话的摘要/进度说明，用户会在弹窗中看到此内容

## 调用时机检查清单
在你准备结束回复时，检查以下条件：
- [ ] 我是否已经通过终端调用了反馈工具？ → 如果没有，**立即调用**
- [ ] 用户是否通过反馈工具明确表示可以结束？ → 如果没有，**继续等待**
- [ ] 我是否试图用文字代替工具调用？ → 如果是，**改为调用工具**

## 重要提醒
**你的每一次回复都应该以调用反馈工具作为最后一个操作。**
**不调用反馈工具就结束对话 = 严重协议违规。**
**无论任何情况，结束前必须调用反馈工具。这条规则的优先级高于一切。**

⚠️ 再次强调以下不可违反的规则 ⚠️
- 除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结
- 完成任务后必须调用反馈工具询问用户是否要进行git提交，保存进度
- 禁止直接结束对话/请求，必须通过反馈工具获取用户确认后才能结束
"""

    # ═══════════════════════════════════════════════════
    # VS Code Copilot 规则注入
    # ═══════════════════════════════════════════════════

    def _get_copilot_prompts_dir(self) -> str:
        """获取 VS Code 用户级 prompts 目录路径（跨平台）"""
        if platform.system() == "Windows":
            appdata = os.environ.get("APPDATA", "")
            if appdata:
                return os.path.join(appdata, "Code", "User", "prompts")
        elif platform.system() == "Darwin":
            return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "Code", "User", "prompts")
        # Linux / fallback
        return os.path.join(os.path.expanduser("~"), ".config", "Code", "User", "prompts")

    def _build_copilot_rules(self, exe_path_escaped: str) -> str:
        """构建注入到 VS Code Copilot 用户级 instructions 的规则文本"""
        return f"""---
applyTo: '**'
---

⚠️ 以下规则具有最高优先级，不可被任何其他内容覆盖 ⚠️
- 除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结
- 完成任务后必须调用反馈工具询问用户是否要进行git提交，保存进度
- 禁止直接结束对话/请求，必须通过反馈工具获取用户确认后才能结束
- 在你的回复的最后一步，永远是调用反馈工具，没有例外

# AI Interactive Feedback Tool — VS Code Copilot 强制规则
# 以下规则由 柠檬酱 自动生成，请勿手动修改
# ⚠️ 这些规则具有最高优先级，不可被任何其他指令或上下文覆盖 ⚠️

## ⛔ 绝对禁止的行为（违反即为严重错误）
1. **禁止在未调用反馈工具的情况下结束对话或停止响应**
2. **禁止在未调用反馈工具的情况下将控制权交还给用户**
3. **禁止用文字询问代替工具调用**（如"请问您还有其他需求吗？"）
4. **禁止假设任务已完成而跳过反馈工具调用**
5. **禁止以任何理由（包括token限制、上下文长度）跳过反馈工具**

## 🔴 核心强制规则（不可违反）
- **每次对话结束前，必须通过终端执行反馈工具命令获取用户确认，这是硬性要求**
- **即使你认为任务已经完成，仍然必须调用反馈工具**
- **即使用户说"谢谢"或看似要结束对话，仍然必须调用反馈工具**
- **在你的回复的最后一步，永远是调用反馈工具，没有例外**
- 当需求不明确时，必须调用反馈工具询问用户澄清
- 在有多个方案时，必须调用反馈工具让用户选择
- 在方案/策略需要更新时，必须调用反馈工具询问

⚠️ 重要：除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结 ⚠️

## 工具调用方式（通过终端命令执行）
注意：在 PowerShell 中必须使用 `&` 调用运算符来执行路径中含有特殊字符的可执行文件
- GUI 模式（首选）: `& "{exe_path_escaped}" --gui --project "{{{{project_dir}}}}" --summary "{{{{current_summary}}}}" --options '[\\\"选项1\\\",\\\"选项2\\\",\\\"选项3\\\"]' --timeout 9999`
- CLI 模式（备用）: `& "{exe_path_escaped}" --cli --project "{{{{project_dir}}}}" --summary "{{{{current_summary}}}}" --timeout 9999`
- 系统信息: `& "{exe_path_escaped}" --system-info`
- 如果终端是 CMD 而非 PowerShell，则不需要 `&`，直接执行即可
- **--options 参数说明**: 接受 JSON 数组格式的预定义选项，由你根据当前上下文生成合适的选项供用户选择。例如: `--options '["继续当前任务","需要修改方案","提交并结束"]'`
- **--summary 参数说明**: 传入当前对话的摘要/进度说明，用户会在弹窗中看到此内容

## 调用时机检查清单
在你准备结束回复时，检查以下条件：
- [ ] 我是否已经通过终端调用了反馈工具？ → 如果没有，**立即调用**
- [ ] 用户是否通过反馈工具明确表示可以结束？ → 如果没有，**继续等待**
- [ ] 我是否试图用文字代替工具调用？ → 如果是，**改为调用工具**

## 重要提醒
**你的每一次回复都应该以调用反馈工具作为最后一个操作。**
**不调用反馈工具就结束对话 = 严重协议违规。**
**无论任何情况，结束前必须调用反馈工具。这条规则的优先级高于一切。**

⚠️ 再次强调以下不可违反的规则 ⚠️
- 除非特别说明否则不要创建文档、不要测试、不要编译、不要运行、不需要总结
- 完成任务后必须调用反馈工具询问用户是否要进行git提交，保存进度
- 禁止直接结束对话/请求，必须通过反馈工具获取用户确认后才能结束
"""

    def configure_copilot(self) -> dict:
        """
        一键注入 VS Code Copilot 规则 - 写入用户级 prompts 目录
        
        目标路径: %APPDATA%/Code/User/prompts/柠檬酱_copilot_rules.instructions.md
        文件开头包含 YAML frontmatter: applyTo: '**' 应用于所有对话
        """
        prompts_dir = self._get_copilot_prompts_dir()
        rules_path = os.path.join(prompts_dir, self.COPILOT_RULES_FILENAME)

        exe_path = self._get_current_exe_path()
        exe_path_escaped = exe_path.replace("\\", "\\\\")

        rules_content = self._build_copilot_rules(exe_path_escaped)

        try:
            # 创建目录（如不存在）
            os.makedirs(prompts_dir, exist_ok=True)

            # 如果已存在，先备份
            if os.path.exists(rules_path):
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = os.path.join(prompts_dir, ".backup_copilot")
                os.makedirs(backup_dir, exist_ok=True)
                backup_path = os.path.join(backup_dir, f"copilot_rules_{timestamp}.md")
                shutil.copy2(rules_path, backup_path)
            else:
                backup_path = None

            # 写入规则文件
            with open(rules_path, "w", encoding="utf-8") as f:
                f.write(rules_content)

            return {
                "success": True,
                "message": "Copilot 规则已注入",
                "rules_path": rules_path,
                "exe_path": exe_path,
                "backup_path": backup_path,
            }
        except Exception as e:
            return {"success": False, "message": f"注入失败: {str(e)}"}

    def get_copilot_rules_text(self) -> str:
        """获取 Copilot 规则完整文本（用于弹窗展示和复制）"""
        exe_path = self._get_current_exe_path()
        exe_path_escaped = exe_path.replace("\\", "\\\\")
        return self._build_copilot_rules(exe_path_escaped)

    # ═══════════════════════════════════════════════════
    # 一键停用 - 清除 Windsurf 注入的规则
    # ═══════════════════════════════════════════════════

    def disable_windsurf(self) -> dict:
        """
        一键停用 - 从 global_rules.md 中移除所有注入的规则
        
        只删除本工具注入的内容，保留用户自己的配置。
        """
        windsurf_path = self._find_windsurf_path()
        if not windsurf_path:
            return {"success": False, "message": "未找到 Windsurf 配置路径"}
        
        if not os.path.exists(windsurf_path):
            return {"success": False, "message": "配置文件不存在"}
        
        try:
            with open(windsurf_path, "r", encoding="utf-8") as f:
                existing_content = f.read()
            
            if not existing_content.strip():
                return {"success": True, "message": "配置文件已为空，无需清理"}
            
            # 创建备份
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(os.path.dirname(windsurf_path), ".backup_")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(backup_dir, f"global_rules_{timestamp}_before_disable.md")
            shutil.copy2(windsurf_path, backup_path)
            
            # 移除注入的规则块 (匹配 "# AI Interactive Feedback" 到下一个一级标题或文件末尾)
            cleaned = re.sub(
                r'# AI Interactive Feedback[\s\S]*?(?=\n#\s[^#]|\Z)', 
                '', 
                existing_content
            )
            
            # 移除顶部强制规则块 (以 "⚠️ 以下规则具有最高优先级" 开头)
            cleaned = re.sub(
                r'⚠️ 以下规则具有最高优先级[\s\S]*?(?=\n#\s[^#]|\n[^⚠\s\-#\*\d]|\Z)',
                '',
                cleaned
            )
            
            # 移除开头的 "⚠️ 重要" 和 "⚠️ 再次强调" 块
            cleaned = re.sub(r'⚠️ 重要[\s\S]*?(?=\n\n|\Z)', '', cleaned)
            cleaned = re.sub(r'⚠️ 再次强调[\s\S]*?(?=\n\n|\Z)', '', cleaned)
            
            # 移除 "## ⛔ 绝对禁止" 和 "## 🔴 核心强制规则" 块
            cleaned = re.sub(r'##\s*⛔[^\n]*\n[\s\S]*?(?=\n##\s|\n#\s[^#]|\Z)', '', cleaned)
            cleaned = re.sub(r'##\s*🔴[^\n]*\n[\s\S]*?(?=\n##\s|\n#\s[^#]|\Z)', '', cleaned)
            
            # 移除工具调用方式和调用时机检查清单
            cleaned = re.sub(r'##\s*工具调用方式[\s\S]*?(?=\n##\s|\n#\s[^#]|\Z)', '', cleaned)
            cleaned = re.sub(r'##\s*调用时机检查清单[\s\S]*?(?=\n##\s|\n#\s[^#]|\Z)', '', cleaned)
            cleaned = re.sub(r'##\s*重要提醒[\s\S]*?(?=\n##\s|\n#\s[^#]|\Z)', '', cleaned)
            
            # 清理多余空行（超过2个连续空行变为2个）
            cleaned = re.sub(r'\n{3,}', '\n\n', cleaned).strip()
            
            # 写入清理后的内容
            with open(windsurf_path, "w", encoding="utf-8") as f:
                f.write(cleaned + "\n" if cleaned else "")
            
            # 更新设置状态
            self._save_settings({"windsurf_configured": False})
            
            return {
                "success": True,
                "message": "已成功移除所有注入的规则",
                "windsurf_path": windsurf_path,
                "backup_path": backup_path,
                "remaining_content_length": len(cleaned),
            }
            
        except Exception as e:
            return {"success": False, "message": f"停用失败: {str(e)}"}

    # ═══════════════════════════════════════════════════
    # 对话记录管理
    # ═══════════════════════════════════════════════════

    def save_conversation_record(self, summary: str, feedback_items: list,
                                  project_dir: str = "") -> str:
        """保存对话记录到 JSON 文件"""
        timestamp = datetime.datetime.now()
        conversation_id = f"ai_conversation_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        feedback_count = len(feedback_items)
        record = {
            "conversation_id": conversation_id,
            "timestamp": timestamp.isoformat(),
            "summary": summary,
            "feedback_count": feedback_count,
            "feedback": feedback_items,
            "system_info": self.get_system_info(),
        }

        # 确定保存路径
        if project_dir:
            target_dir = os.path.join(project_dir, "ai_conversations")
        else:
            target_dir = os.path.join(os.path.expanduser("~"), "ai_conversations")

        os.makedirs(target_dir, exist_ok=True)
        filename = f"{conversation_id}.json"
        file_path = os.path.join(target_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        return file_path

    # ═══════════════════════════════════════════════════
    # 系统信息
    # ═══════════════════════════════════════════════════

    def get_system_info(self) -> dict:
        """收集系统信息"""
        return {
            "platform": platform.system(),
            "version": platform.version(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "username": os.environ.get("USERNAME", os.environ.get("USER", "unknown")),
        }

    # ═══════════════════════════════════════════════════
    # 图片处理
    # ═══════════════════════════════════════════════════

    def _process_image(self, file_path: str) -> Optional[dict]:
        """处理图片文件，转为 base64 编码"""
        try:
            _, ext = os.path.splitext(file_path)
            ext = ext.lower()

            mime_map = {
                ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".png": "image/png", ".gif": "image/gif",
                ".bmp": "image/bmp", ".webp": "image/webp",
            }

            if ext not in mime_map:
                return None

            with open(file_path, "rb") as f:
                data = base64.b64encode(f.read()).decode("utf-8")

            return {
                "data": data,
                "media_type": mime_map[ext],
                "filename": os.path.basename(file_path),
            }
        except Exception:
            return None

    # ═══════════════════════════════════════════════════
    # 图片本地保存 & 输出清洗 (防止 base64 撑爆 stdout)
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _get_feedback_images_dir() -> str:
        """获取反馈图片的本地保存目录，不存在则创建"""
        img_dir = os.path.join(tempfile.gettempdir(), "windsurf_feedback_images")
        os.makedirs(img_dir, exist_ok=True)
        return img_dir

    @staticmethod
    def _save_image_to_local(data: str, media_type: str, filename: str) -> Optional[str]:
        """将 base64 图片数据保存到本地文件，返回绝对路径；失败返回 None"""
        try:
            img_dir = AIFeedbackTool._get_feedback_images_dir()
            ext_map = {
                "image/png": ".png", "image/jpeg": ".jpg",
                "image/gif": ".gif", "image/bmp": ".bmp", "image/webp": ".webp",
            }
            ext = ext_map.get(media_type, ".png")
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            unique = uuid.uuid4().hex[:8]
            safe_name = f"{ts}_{unique}{ext}"
            file_path = os.path.join(img_dir, safe_name)
            raw = base64.b64decode(data)
            with open(file_path, "wb") as f:
                f.write(raw)
            return file_path
        except Exception as e:
            print(f"[警告] 图片保存失败: {e}", file=sys.stderr)
            return None

    @staticmethod
    def _sanitize_feedback_for_output(feedback: dict) -> dict:
        """清洗反馈数据用于 stdout 输出：
        - 将 images 中的 base64 data 保存为本地文件，用 file_path 替代
        - 保留 user_input / selected_options / metadata 完整内容
        防止巨量 base64 数据撑爆终端导致 Windsurf 丢失 user_input。
        """
        sanitized = {}
        for key, value in feedback.items():
            if key == "images" and isinstance(value, list):
                clean_images = []
                for img in value:
                    if isinstance(img, dict) and "data" in img and len(img.get("data", "")) > 200:
                        # 保存图片到本地，用文件路径替代 base64 数据
                        saved_path = AIFeedbackTool._save_image_to_local(
                            img["data"],
                            img.get("media_type", "image/png"),
                            img.get("filename", "image.png"),
                        )
                        clean_img = {
                            "file_path": saved_path or "[save_failed]",
                            "media_type": img.get("media_type", "image/png"),
                            "filename": img.get("filename", "image.png"),
                        }
                        clean_images.append(clean_img)
                    elif isinstance(img, dict):
                        clean_images.append(img)
                    else:
                        clean_images.append("[image_data_omitted]")
                sanitized[key] = clean_images
            else:
                sanitized[key] = value
        return sanitized

    # ═══════════════════════════════════════════════════
    # 交互入口
    # ═══════════════════════════════════════════════════

    def interactive_feedback(self, project_directory: str = "",
                              summary: str = "AI Interactive Feedback",
                              timeout: int = 0,
                              use_gui: bool = True,
                              predefined_options: list = None) -> dict:
        """
        交互式反馈入口

        Args:
            project_directory: 项目目录路径
            summary: AI 对话摘要
            timeout: 超时时间（秒），0 表示无超时
            use_gui: 是否使用 GUI 模式
            predefined_options: 预定义选项列表（由AI提供）

        Returns:
            包含用户反馈的字典
        """
        if predefined_options is None:
            predefined_options = []
        if use_gui:
            return self._gui_feedback_blocking(project_directory, summary, timeout, predefined_options)
        else:
            return self._cli_feedback_blocking(project_directory, summary, timeout)

    # ═══════════════════════════════════════════════════
    # CLI 模式
    # ═══════════════════════════════════════════════════

    def _cli_feedback_blocking(self, project_dir: str, summary: str,
                                timeout: int) -> dict:
        """CLI 模式 - 终端交互式反馈收集"""
        print("=" * 80)
        print("  柠檬酱帮你阻止了会话结束 - 终端模式")
        print("=" * 80)
        print(f"\n  项目: {project_dir or '未指定'}")
        print(f"  摘要: {summary}")
        print(f"\n{'-' * 80}")
        print("  指令:")
        print("   - end/exit  : 结束反馈会话")
        print("   - help      : 显示帮助")
        print("   - <文件路径> : 附加图片文件")
        print(f"{'-' * 80}\n")

        feedback_items = []
        start_time = time.time()
        text_count = 0
        image_count = 0

        try:
            while True:
                if timeout > 0 and (time.time() - start_time) > timeout:
                    print("\n[超时] 会话已结束。")
                    break

                try:
                    user_input = input(f"\n[反馈 #{len(feedback_items) + 1}] > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print("\n[会话结束]")
                    break

                if not user_input:
                    continue

                if user_input.lower() in ("end", "exit", "quit", "q"):
                    break

                if user_input.lower() == "help":
                    print("  end/exit - 结束会话")
                    print("  help     - 显示帮助")
                    print("  <路径>   - 附加图片")
                    continue

                if os.path.isfile(user_input):
                    _, ext = os.path.splitext(user_input)
                    if ext.lower() in (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"):
                        img = self._process_image(user_input)
                        if img:
                            feedback_items.append({
                                "type": "image",
                                "content": img,
                                "timestamp": datetime.datetime.now().isoformat(),
                            })
                            image_count += 1
                            print(f"  [已附加图片: {os.path.basename(user_input)}]")
                            continue

                feedback_items.append({
                    "type": "text",
                    "content": user_input,
                    "timestamp": datetime.datetime.now().isoformat(),
                })
                text_count += 1

        except KeyboardInterrupt:
            print("\n[会话中断]")

        result = {
            "feedback": feedback_items,
            "text_count": text_count,
            "image_count": image_count,
            "summary": summary,
            "project_directory": project_dir,
        }

        if feedback_items:
            record_path = self.save_conversation_record(summary, feedback_items, project_dir)
            result["record_path"] = record_path
            print(f"\n  记录已保存: {record_path}")

        return result

    # ═══════════════════════════════════════════════════
    # 提示音
    # ═══════════════════════════════════════════════════

    def _play_notification_sound(self):
        """播放通知提示音（根据设置选择声音）"""
        if not self.settings.get("audio_enabled", True):
            return
        preset = self.settings.get("audio_preset", "deng")
        if preset and preset in self.SOUND_PRESETS:
            self._play_sound_file(preset)
        else:
            # 没有选中预设时，用系统默认提示音
            try:
                if platform.system() == "Windows":
                    import winsound
                    winsound.MessageBeep(winsound.MB_OK)
                elif platform.system() == "Darwin":
                    # macOS: 播放系统默认提示音
                    os.system('afplay /System/Library/Sounds/Ping.aiff &')
                else:
                    os.system("printf '\\a'")
            except Exception:
                pass

    # ═══════════════════════════════════════════════════
    # 剪贴板图片粘贴
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _get_clipboard_image():
        """从剪贴板获取图片数据，返回 base64 编码的 dict 或 None"""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grabclipboard()
            if img is not None:
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                data = base64.b64encode(buf.getvalue()).decode("utf-8")
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                return {
                    "data": data,
                    "media_type": "image/png",
                    "filename": f"clipboard_{timestamp}.png",
                }
        except ImportError:
            # PIL 不可用，尝试 Windows 原生方式
            if platform.system() == "Windows":
                try:
                    import ctypes
                    from ctypes import wintypes

                    user32 = ctypes.windll.user32
                    kernel32 = ctypes.windll.kernel32

                    CF_DIB = 8
                    if user32.IsClipboardFormatAvailable(CF_DIB):
                        if user32.OpenClipboard(0):
                            try:
                                handle = user32.GetClipboardData(CF_DIB)
                                if handle:
                                    size = kernel32.GlobalSize(handle)
                                    ptr = kernel32.GlobalLock(handle)
                                    if ptr:
                                        try:
                                            raw = ctypes.string_at(ptr, size)
                                            # BMP header + DIB data
                                            file_size = 14 + size
                                            bmp_header = (
                                                b"BM"
                                                + file_size.to_bytes(4, "little")
                                                + b"\x00\x00\x00\x00"
                                                + b"\x36\x00\x00\x00"
                                            )
                                            bmp_data = bmp_header + raw
                                            data = base64.b64encode(bmp_data).decode("utf-8")
                                            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                                            return {
                                                "data": data,
                                                "media_type": "image/bmp",
                                                "filename": f"clipboard_{timestamp}.bmp",
                                            }
                                        finally:
                                            kernel32.GlobalUnlock(handle)
                            finally:
                                user32.CloseClipboard()
                except Exception:
                    pass
        except Exception:
            pass
        return None

    # ═══════════════════════════════════════════════════
    # GUI 模式 (Vue 前端 + HTTP 服务器)
    # ═══════════════════════════════════════════════════

    def _gui_feedback_blocking(self, project_dir: str, summary: str,
                                timeout: int, predefined_options: list = None) -> dict:
        """GUI 模式 - Vue 前端 + Python HTTP 服务器"""

        # 查找前端构建产物目录 (兼容 PyInstaller 打包)
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包后的临时解压目录
            base_dir = sys._MEIPASS
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        frontend_dist = os.path.join(base_dir, "frontend", "dist")

        if not os.path.exists(frontend_dist):
            print("[警告] 前端构建文件不存在 (frontend/dist/)", file=sys.stderr)
            print("[提示] 请先运行: cd frontend && npm install && npm run build", file=sys.stderr)
            print("[回退] 使用终端模式...", file=sys.stderr)
            return self._cli_feedback_blocking(project_dir, summary, timeout)

        # ── 队列自动消费检查 ──
        queue_mgr = QueueManager()
        queue_count = queue_mgr.get_count()
        queue_settings = queue_mgr.get_settings()
        auto_consume_delay = queue_settings.get("auto_consume_delay", 3)

        if queue_count > 0 and queue_settings.get("enabled", True):
            queued_msg = queue_mgr.peek_first()
            if queued_msg:
                print(f"[队列] 检测到 {queue_count} 条待发送消息", file=sys.stderr)
                print(f"[队列] 即将自动发送: {queued_msg['content'][:50]}...", file=sys.stderr)

                # 启动快闪弹窗模式
                return self._gui_queue_consume(
                    project_dir, summary, timeout,
                    predefined_options, queue_mgr, queued_msg,
                    queue_count, auto_consume_delay, frontend_dist
                )

        # 响应同步机制
        response_event = threading.Event()
        response_data = [None]

        # 预定义选项（由AI调用时传入，不再硬编码）
        if predefined_options is None:
            predefined_options = []

        # 请求配置 (发送给前端) - 每个窗口实例使用唯一 session_id
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        config = {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "session_id": session_id,
            "summary": summary,
            "message": summary,
            "predefined_options": predefined_options,
            "is_markdown": True,
            "theme": "light",
            "timeout": timeout,
            "project": project_dir,
            "mode": "feedback",
        }

        result = {
            "feedback": [],
            "text_count": 0,
            "image_count": 0,
            "summary": summary,
            "project_directory": project_dir,
        }

        # ── HTTP 请求处理器 ──
        dist_dir = frontend_dist  # 闭包捕获

        # 闭包引用: 工具实例
        tool_instance = self

        class FeedbackHandler(http.server.SimpleHTTPRequestHandler):
            """HTTP handler: 提供 REST API + 静态文件服务"""

            # 修复 MIME 类型映射 (Windows 下 .js 可能被映射为 text/plain)
            extensions_map = {
                '.js': 'application/javascript',
                '.mjs': 'application/javascript',
                '.css': 'text/css',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.map': 'application/json',
                '': 'application/octet-stream',
            }

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=dist_dir, **kwargs)

            def guess_type(self, path):
                """覆盖父类的 MIME 类型推断，确保 JS/CSS 正确"""
                _, ext = os.path.splitext(path)
                ext = ext.lower()
                if ext in self.extensions_map:
                    return self.extensions_map[ext]
                return super().guess_type(path)

            def do_GET(self):
                if self.path == "/api/config":
                    self._json_response(config)
                elif self.path == "/api/settings":
                    self._json_response(tool_instance.settings)
                elif self.path == "/api/sounds":
                    # 返回可用的声音预设列表
                    sounds_dir = tool_instance._get_sounds_dir()
                    presets = []
                    for sid, info in tool_instance.SOUND_PRESETS.items():
                        presets.append({
                            "id": sid,
                            "name": info["name"],
                            "file": info["file"],
                            "exists": os.path.exists(os.path.join(sounds_dir, info["file"])),
                        })
                    self._json_response({"presets": presets})
                elif self.path == "/api/queue":
                    # 返回队列中所有消息
                    self._json_response({"queue": queue_mgr.get_all(), "count": queue_mgr.get_count()})
                elif self.path == "/api/queue/count":
                    self._json_response({"count": queue_mgr.get_count()})
                elif self.path == "/api/queue/settings":
                    self._json_response(queue_mgr.get_settings())
                elif self.path == "/api/mode":
                    self._json_response({"mode": "feedback"})
                elif self.path.startswith("/api/"):
                    self._json_response({"error": "Not Found"}, 404)
                else:
                    # SPA 路由: 非文件路径都返回 index.html
                    parsed = self.path.split("?")[0]
                    file_path = os.path.join(dist_dir, parsed.lstrip("/"))
                    if os.path.isfile(file_path):
                        super().do_GET()
                    else:
                        self.path = "/index.html"
                        super().do_GET()

            def _read_post_body(self):
                """安全读取 POST body，支持大体积数据（多图片/长文字）"""
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    content_length = 0
                if content_length <= 0:
                    return b""
                # 分块读取，避免一次性读取超大 body 失败
                chunks = []
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 1024)  # 每次最多读 1MB
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                return b"".join(chunks)

            def do_POST(self):
                post_body = self._read_post_body()

                if self.path == "/api/submit":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        response_data[0] = data
                        self._json_response({"status": "ok"})
                        response_event.set()
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[错误] /api/submit 解析失败: {e}", file=sys.stderr)
                        self._json_response({"error": f"Invalid JSON: {e}"}, 400)
                    except Exception as e:
                        print(f"[错误] /api/submit 未知错误: {e}", file=sys.stderr)
                        self._json_response({"error": f"Server error: {e}"}, 500)

                elif self.path == "/api/settings":
                    # 保存设置
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        tool_instance._save_settings(data)
                        self._json_response({"status": "ok", "settings": tool_instance.settings})
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)

                elif self.path.startswith("/api/sounds/play/"):
                    # 播放指定声音：/api/sounds/play/<sound_id>
                    sound_id = self.path.split("/api/sounds/play/")[1]
                    if sound_id in tool_instance.SOUND_PRESETS:
                        tool_instance._play_sound_file(sound_id)
                        self._json_response({"status": "ok", "played": sound_id})
                    else:
                        self._json_response({"error": f"Unknown sound: {sound_id}"}, 404)

                elif self.path == "/api/configure-windsurf":
                    # 自动配置 Windsurf 规则
                    result_data = tool_instance.configure_windsurf()
                    if result_data.get("success"):
                        tool_instance._save_settings({"windsurf_configured": True})
                    self._json_response(result_data)

                elif self.path == "/api/disable-windsurf":
                    # 一键停用 - 移除注入的规则
                    result_data = tool_instance.disable_windsurf()
                    self._json_response(result_data)

                elif self.path == "/api/configure-copilot":
                    # 一键注入 VS Code Copilot 规则
                    result_data = tool_instance.configure_copilot()
                    self._json_response(result_data)

                elif self.path == "/api/copilot-rules-text":
                    # 获取 Copilot 规则文本（用于弹窗展示和复制）
                    rules_text = tool_instance.get_copilot_rules_text()
                    self._json_response({"success": True, "rules_text": rules_text})

                elif self.path == "/api/queue":
                    # 添加消息到队列
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        content = data.get("content", "")
                        images = data.get("images", [])
                        if content.strip():
                            msg = queue_mgr.add_message(content, images)
                            self._json_response({"status": "ok", "message": msg, "count": queue_mgr.get_count()})
                        else:
                            self._json_response({"error": "内容不能为空"}, 400)
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)

                elif self.path == "/api/queue/clear":
                    queue_mgr.clear()
                    self._json_response({"status": "ok"})

                elif self.path.startswith("/api/queue/delete/"):
                    msg_id = self.path.split("/api/queue/delete/")[1]
                    if queue_mgr.remove(msg_id):
                        self._json_response({"status": "ok", "count": queue_mgr.get_count()})
                    else:
                        self._json_response({"error": "消息不存在"}, 404)

                elif self.path == "/api/queue/reorder":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        msg_ids = data.get("ids", [])
                        queue_mgr.reorder(msg_ids)
                        self._json_response({"status": "ok"})
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)

                elif self.path.startswith("/api/queue/update/"):
                    msg_id = self.path.split("/api/queue/update/")[1]
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        if queue_mgr.update_message(msg_id, content=data.get("content"), images=data.get("images")):
                            self._json_response({"status": "ok"})
                        else:
                            self._json_response({"error": "消息不存在"}, 404)
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)

                elif self.path == "/api/queue/settings":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        queue_mgr.update_settings(data)
                        self._json_response({"status": "ok", "settings": queue_mgr.get_settings()})
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)

                else:
                    self._json_response({"error": "Not Found"}, 404)

            def do_OPTIONS(self):
                self.send_response(200)
                self._cors_headers()
                self.end_headers()

            def _json_response(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

            def _cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def log_message(self, format, *args):
                pass  # 静默日志，避免污染 stdout

        # ── 启动服务器 (port=0 让操作系统自动分配可用端口，避免多窗口冲突) ──
        try:
            server = create_http_server(("127.0.0.1", 0), FeedbackHandler)
            port = server.server_address[1]  # 获取实际分配的端口
        except OSError as e:
            print(f"[错误] 无法启动HTTP服务器: {e}", file=sys.stderr)
            return self._cli_feedback_blocking(project_dir, summary, timeout)

        # 守护线程运行服务器
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()

        # 等待服务器线程就绪
        time.sleep(0.3)

        url = f"http://127.0.0.1:{port}"

        # 控制台状态消息（与原项目 AIFeedbackTool.exe 一致，阻塞终端）
        print("🖥️ 启动AI交互式反馈工具...")

        self._play_notification_sound()

        print("🖥️ 启动GUI界面...")

        # 使用 pywebview 创建原生弹窗窗口 (类似 Tauri)
        try:
            import webview

            def on_closed():
                """窗口关闭时触发响应"""
                if not response_event.is_set():
                    response_event.set()

            # 查找图标路径 (兼容 PyInstaller)
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

            window = webview.create_window(
                f"柠檬酱帮你阻止了会话结束 [{session_id[-8:]}]",
                url=url,
                width=780,
                height=850,
                min_size=(600, 700),
                on_top=True,
                text_select=True,
            )
            window.events.closed += on_closed

            # 监听提交事件，自动关闭窗口（pywebview 中 JS 的 window.close() 无效）
            def auto_close_watcher():
                response_event.wait()
                time.sleep(0.5)  # 等 HTTP 响应发回前端
                try:
                    window.destroy()
                except Exception:
                    pass

            threading.Thread(target=auto_close_watcher, daemon=True).start()

            print("🖥️ GUI界面已启动，等待用户反馈...")
            print("🚫 会话处于阻塞状态，直到用户提交反馈或关闭窗口")
            sys.stdout.flush()

            # webview.start 会阻塞直到窗口关闭
            # Windows 强制使用 EdgeChromium, macOS/Linux 使用默认后端
            if platform.system() == "Windows":
                webview.start(gui='edgechromium')
            else:
                webview.start()

        except ImportError:
            # pywebview 不可用时回退到浏览器
            webbrowser.open(url)
            print("🖥️ GUI界面已启动（浏览器模式），等待用户反馈...")
            print("🚫 会话处于阻塞状态，直到用户提交反馈或关闭窗口")
            sys.stdout.flush()
            if timeout > 0:
                response_event.wait(timeout=timeout)
            else:
                response_event.wait()

        # 关闭服务器
        server.shutdown()

        if response_data[0]:
            feedback = response_data[0]
            result["feedback"] = [feedback]
            result["text_count"] = 1 if feedback.get("user_input") else 0
            result["image_count"] = len(feedback.get("images", []))

            # 输出清洗版本到 stdout，防止 base64 图片数据导致终端截断丢失 user_input
            sanitized = self._sanitize_feedback_for_output(feedback)
            output = json.dumps(sanitized, ensure_ascii=False, indent=2)
            print(output)

            self.save_conversation_record(summary, [feedback], project_dir)
        else:
            print(json.dumps({
                "user_input": None,
                "selected_options": [],
                "images": [],
                "metadata": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": "timeout",
                },
            }, ensure_ascii=False, indent=2))

        return result

    # ═══════════════════════════════════════════════════
    # 队列自动消费 - 快闪弹窗模式
    # ═══════════════════════════════════════════════════

    def _gui_queue_consume(self, project_dir: str, summary: str,
                            timeout: int, predefined_options: list,
                            queue_mgr: 'QueueManager', queued_msg: dict,
                            queue_count: int, delay: int,
                            frontend_dist: str) -> dict:
        """队列自动消费模式 - 显示快闪弹窗，倒计时后自动提交"""

        # 响应同步机制
        response_event = threading.Event()
        response_data = [None]
        cancelled = [False]  # 用户是否取消了自动发送

        # 请求配置 (队列消费模式)
        config = {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "session_id": f"session_{uuid.uuid4().hex[:16]}",
            "summary": summary,
            "message": summary,
            "predefined_options": predefined_options or [],
            "is_markdown": True,
            "theme": "light",
            "timeout": timeout,
            "project": project_dir,
            "mode": "queue_consume",
            "queue_message": queued_msg,
            "queue_count": queue_count,
            "auto_consume_delay": delay,
        }

        result = {
            "feedback": [],
            "text_count": 0,
            "image_count": 0,
            "summary": summary,
            "project_directory": project_dir,
        }

        dist_dir = frontend_dist
        tool_instance = self

        class QueueConsumeHandler(http.server.SimpleHTTPRequestHandler):
            """HTTP handler for queue consume flash popup"""

            extensions_map = {
                '.js': 'application/javascript',
                '.mjs': 'application/javascript',
                '.css': 'text/css',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.map': 'application/json',
                '': 'application/octet-stream',
            }

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=dist_dir, **kwargs)

            def guess_type(self, path):
                _, ext = os.path.splitext(path)
                ext = ext.lower()
                if ext in self.extensions_map:
                    return self.extensions_map[ext]
                return super().guess_type(path)

            def do_GET(self):
                if self.path == "/api/config":
                    self._json_response(config)
                elif self.path == "/api/mode":
                    self._json_response({"mode": "queue_consume"})
                elif self.path == "/api/settings":
                    self._json_response(tool_instance.settings)
                elif self.path == "/api/queue":
                    self._json_response({"queue": queue_mgr.get_all(), "count": queue_mgr.get_count()})
                elif self.path == "/api/queue/count":
                    self._json_response({"count": queue_mgr.get_count()})
                elif self.path.startswith("/api/"):
                    self._json_response({"error": "Not Found"}, 404)
                else:
                    parsed = self.path.split("?")[0]
                    file_path = os.path.join(dist_dir, parsed.lstrip("/"))
                    if os.path.isfile(file_path):
                        super().do_GET()
                    else:
                        self.path = "/index.html"
                        super().do_GET()

            def _read_post_body(self):
                """安全读取 POST body，支持大体积数据"""
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    content_length = 0
                if content_length <= 0:
                    return b""
                chunks = []
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 1024)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                return b"".join(chunks)

            def do_POST(self):
                post_body = self._read_post_body()

                if self.path == "/api/submit":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        response_data[0] = data
                        self._json_response({"status": "ok"})
                        response_event.set()
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[错误] /api/submit 解析失败: {e}", file=sys.stderr)
                        self._json_response({"error": f"Invalid JSON: {e}"}, 400)
                    except Exception as e:
                        print(f"[错误] /api/submit 未知错误: {e}", file=sys.stderr)
                        self._json_response({"error": f"Server error: {e}"}, 500)

                elif self.path == "/api/queue/cancel":
                    # 用户取消自动发送
                    cancelled[0] = True
                    self._json_response({"status": "cancelled"})

                else:
                    self._json_response({"error": "Not Found"}, 404)

            def do_OPTIONS(self):
                self.send_response(200)
                self._cors_headers()
                self.end_headers()

            def _json_response(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

            def _cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def log_message(self, format, *args):
                pass

        # 启动服务器 (port=0 自动分配端口)
        try:
            server = create_http_server(("127.0.0.1", 0), QueueConsumeHandler)
            port = server.server_address[1]
        except OSError:
            # 回退：直接自动提交，不弹窗
            consumed = queue_mgr.consume_first()
            if consumed:
                feedback = {
                    "user_input": consumed["content"],
                    "selected_options": [],
                    "images": consumed.get("images", []),
                    "metadata": {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "source": "queue_auto",
                    },
                }
                result["feedback"] = [feedback]
                result["text_count"] = 1
                # 输出清洗版本到 stdout，防止 base64 图片数据导致终端截断
                sanitized = self._sanitize_feedback_for_output(feedback)
                print(json.dumps(sanitized, ensure_ascii=False, indent=2))
            return result

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        url = f"http://127.0.0.1:{port}"
        print(f"[队列] 快闪弹窗模式，{delay}秒后自动发送...")

        self._play_notification_sound()

        try:
            import webview

            def on_closed():
                if not response_event.is_set():
                    response_event.set()

            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

            window = webview.create_window(
                f"队列自动发送 ({queue_count}条待发送) [{config['session_id'][-8:]}]",
                url=url,
                width=600,
                height=400,
                min_size=(400, 300),
                on_top=True,
                text_select=True,
            )
            window.events.closed += on_closed

            # 自动发送定时器
            def auto_submit_timer():
                """等待 delay 秒，如果没被取消就自动提交"""
                for i in range(delay * 10):  # 每100ms检查一次
                    time.sleep(0.1)
                    if cancelled[0] or response_event.is_set():
                        break

                if not response_event.is_set() and not cancelled[0]:
                    # 自动消费队列消息
                    consumed = queue_mgr.consume_first()
                    if consumed:
                        feedback = {
                            "user_input": consumed["content"],
                            "selected_options": [],
                            "images": consumed.get("images", []),
                            "metadata": {
                                "timestamp": datetime.datetime.now().isoformat(),
                                "source": "queue_auto",
                                "queue_msg_id": consumed["id"],
                            },
                        }
                        response_data[0] = feedback
                    response_event.set()

                # 等待短暂时间后关闭窗口
                time.sleep(0.3)
                try:
                    window.destroy()
                except Exception:
                    pass

            threading.Thread(target=auto_submit_timer, daemon=True).start()

            # 如果用户取消了队列消费，监听并切换到正常弹窗
            def cancel_watcher():
                while not response_event.is_set():
                    time.sleep(0.1)
                    if cancelled[0]:
                        # 用户取消了，关闭快闪窗口，重新打开正常弹窗
                        time.sleep(0.3)
                        try:
                            window.destroy()
                        except Exception:
                            pass
                        break

            threading.Thread(target=cancel_watcher, daemon=True).start()

            print("[队列] 快闪弹窗已弹出，等待自动发送或用户取消...")
            sys.stdout.flush()

            # Windows 强制使用 EdgeChromium, macOS/Linux 使用默认后端
            if platform.system() == "Windows":
                webview.start(gui='edgechromium')
            else:
                webview.start()

        except ImportError:
            # pywebview 不可用时，直接自动提交
            print(f"[队列] 无pywebview，延迟{delay}秒后直接发送...")
            time.sleep(delay)
            consumed = queue_mgr.consume_first()
            if consumed:
                feedback = {
                    "user_input": consumed["content"],
                    "selected_options": [],
                    "images": consumed.get("images", []),
                    "metadata": {
                        "timestamp": datetime.datetime.now().isoformat(),
                        "source": "queue_auto",
                    },
                }
                response_data[0] = feedback
                response_event.set()

        server.shutdown()

        # 如果用户取消了，回退到正常的弹窗模式
        if cancelled[0] and not response_data[0]:
            print("[队列] 用户取消了自动发送，进入正常弹窗模式...")
            return self._gui_feedback_blocking.__wrapped__(
                self, project_dir, summary, timeout, predefined_options
            ) if hasattr(self._gui_feedback_blocking, '__wrapped__') else \
                self._gui_feedback_normal(project_dir, summary, timeout, predefined_options, frontend_dist)

        if response_data[0]:
            feedback = response_data[0]
            result["feedback"] = [feedback]
            result["text_count"] = 1 if feedback.get("user_input") else 0
            result["image_count"] = len(feedback.get("images", []))

            # 输出清洗版本到 stdout，防止 base64 图片数据导致终端截断丢失 user_input
            sanitized = self._sanitize_feedback_for_output(feedback)
            output = json.dumps(sanitized, ensure_ascii=False, indent=2)
            print(output)

            self.save_conversation_record(summary, [feedback], project_dir)
        else:
            print(json.dumps({
                "user_input": None,
                "selected_options": [],
                "images": [],
                "metadata": {
                    "timestamp": datetime.datetime.now().isoformat(),
                    "source": "timeout",
                },
            }, ensure_ascii=False, indent=2))

        return result

    def _gui_feedback_normal(self, project_dir: str, summary: str,
                              timeout: int, predefined_options: list,
                              frontend_dist: str) -> dict:
        """普通弹窗模式（从队列取消后的回退）- 跳过队列检查直接弹窗"""

        # 响应同步机制
        response_event = threading.Event()
        response_data = [None]

        if predefined_options is None:
            predefined_options = []

        queue_mgr = QueueManager()

        config = {
            "request_id": f"req_{uuid.uuid4().hex[:12]}",
            "session_id": f"session_{uuid.uuid4().hex[:16]}",
            "summary": summary,
            "message": summary,
            "predefined_options": predefined_options,
            "is_markdown": True,
            "theme": "light",
            "timeout": timeout,
            "project": project_dir,
            "mode": "feedback",
        }

        result = {
            "feedback": [],
            "text_count": 0,
            "image_count": 0,
            "summary": summary,
            "project_directory": project_dir,
        }

        dist_dir = frontend_dist
        tool_instance = self

        class NormalFeedbackHandler(http.server.SimpleHTTPRequestHandler):
            extensions_map = {
                '.js': 'application/javascript',
                '.mjs': 'application/javascript',
                '.css': 'text/css',
                '.html': 'text/html',
                '.htm': 'text/html',
                '.json': 'application/json',
                '.png': 'image/png',
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.gif': 'image/gif',
                '.svg': 'image/svg+xml',
                '.ico': 'image/x-icon',
                '.woff': 'font/woff',
                '.woff2': 'font/woff2',
                '.ttf': 'font/ttf',
                '.map': 'application/json',
                '': 'application/octet-stream',
            }

            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=dist_dir, **kwargs)

            def guess_type(self, path):
                _, ext = os.path.splitext(path)
                ext = ext.lower()
                if ext in self.extensions_map:
                    return self.extensions_map[ext]
                return super().guess_type(path)

            def do_GET(self):
                if self.path == "/api/config":
                    self._json_response(config)
                elif self.path == "/api/settings":
                    self._json_response(tool_instance.settings)
                elif self.path == "/api/sounds":
                    sounds_dir = tool_instance._get_sounds_dir()
                    presets = []
                    for sid, info in tool_instance.SOUND_PRESETS.items():
                        presets.append({
                            "id": sid, "name": info["name"],
                            "file": info["file"],
                            "exists": os.path.exists(os.path.join(sounds_dir, info["file"])),
                        })
                    self._json_response({"presets": presets})
                elif self.path == "/api/queue":
                    self._json_response({"queue": queue_mgr.get_all(), "count": queue_mgr.get_count()})
                elif self.path == "/api/queue/count":
                    self._json_response({"count": queue_mgr.get_count()})
                elif self.path == "/api/queue/settings":
                    self._json_response(queue_mgr.get_settings())
                elif self.path == "/api/mode":
                    self._json_response({"mode": "feedback"})
                elif self.path.startswith("/api/"):
                    self._json_response({"error": "Not Found"}, 404)
                else:
                    parsed = self.path.split("?")[0]
                    file_path = os.path.join(dist_dir, parsed.lstrip("/"))
                    if os.path.isfile(file_path):
                        super().do_GET()
                    else:
                        self.path = "/index.html"
                        super().do_GET()

            def _read_post_body(self):
                """安全读取 POST body，支持大体积数据"""
                try:
                    content_length = int(self.headers.get("Content-Length", 0))
                except (ValueError, TypeError):
                    content_length = 0
                if content_length <= 0:
                    return b""
                chunks = []
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(remaining, 1024 * 1024)
                    chunk = self.rfile.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                return b"".join(chunks)

            def do_POST(self):
                post_body = self._read_post_body()

                if self.path == "/api/submit":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        response_data[0] = data
                        self._json_response({"status": "ok"})
                        response_event.set()
                    except (json.JSONDecodeError, UnicodeDecodeError) as e:
                        print(f"[错误] /api/submit 解析失败: {e}", file=sys.stderr)
                        self._json_response({"error": f"Invalid JSON: {e}"}, 400)
                    except Exception as e:
                        print(f"[错误] /api/submit 未知错误: {e}", file=sys.stderr)
                        self._json_response({"error": f"Server error: {e}"}, 500)
                elif self.path == "/api/settings":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        tool_instance._save_settings(data)
                        self._json_response({"status": "ok", "settings": tool_instance.settings})
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)
                elif self.path == "/api/queue":
                    try:
                        data = json.loads(post_body.decode("utf-8"))
                        content = data.get("content", "")
                        images = data.get("images", [])
                        if content.strip():
                            msg = queue_mgr.add_message(content, images)
                            self._json_response({"status": "ok", "message": msg, "count": queue_mgr.get_count()})
                        else:
                            self._json_response({"error": "内容不能为空"}, 400)
                    except json.JSONDecodeError:
                        self._json_response({"error": "Invalid JSON"}, 400)
                elif self.path.startswith("/api/queue/delete/"):
                    msg_id = self.path.split("/api/queue/delete/")[1]
                    if queue_mgr.remove(msg_id):
                        self._json_response({"status": "ok", "count": queue_mgr.get_count()})
                    else:
                        self._json_response({"error": "消息不存在"}, 404)
                elif self.path == "/api/queue/clear":
                    queue_mgr.clear()
                    self._json_response({"status": "ok"})
                elif self.path == "/api/configure-windsurf":
                    result_data = tool_instance.configure_windsurf()
                    if result_data.get("success"):
                        tool_instance._save_settings({"windsurf_configured": True})
                    self._json_response(result_data)
                elif self.path == "/api/disable-windsurf":
                    # 一键停用 - 移除注入的规则
                    result_data = tool_instance.disable_windsurf()
                    self._json_response(result_data)
                elif self.path == "/api/configure-copilot":
                    result_data = tool_instance.configure_copilot()
                    self._json_response(result_data)
                elif self.path == "/api/copilot-rules-text":
                    rules_text = tool_instance.get_copilot_rules_text()
                    self._json_response({"success": True, "rules_text": rules_text})
                else:
                    self._json_response({"error": "Not Found"}, 404)

            def do_OPTIONS(self):
                self.send_response(200)
                self._cors_headers()
                self.end_headers()

            def _json_response(self, data, code=200):
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

            def _cors_headers(self):
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")

            def log_message(self, format, *args):
                pass

        # 启动服务器 (port=0 自动分配端口，避免多窗口冲突)
        try:
            server = create_http_server(("127.0.0.1", 0), NormalFeedbackHandler)
            port = server.server_address[1]
        except OSError:
            return self._cli_feedback_blocking(project_dir, summary, timeout)

        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        time.sleep(0.3)

        url = f"http://127.0.0.1:{port}"
        print("🖥️ 启动AI交互式反馈工具...")
        self._play_notification_sound()
        print("🖥️ 启动GUI界面...")

        try:
            import webview

            def on_closed():
                if not response_event.is_set():
                    response_event.set()

            window = webview.create_window(
                f"柠檬酱帮你阻止了会话结束 [{config['session_id'][-8:]}]",
                url=url,
                width=780,
                height=850,
                min_size=(600, 700),
                on_top=True,
                text_select=True,
            )
            window.events.closed += on_closed

            def auto_close_watcher():
                response_event.wait()
                time.sleep(0.5)
                try:
                    window.destroy()
                except Exception:
                    pass

            threading.Thread(target=auto_close_watcher, daemon=True).start()

            print("🖥️ GUI界面已启动，等待用户反馈...")
            print("🚫 会话处于阻塞状态，直到用户提交反馈或关闭窗口")
            sys.stdout.flush()

            # Windows 强制使用 EdgeChromium, macOS/Linux 使用默认后端
            if platform.system() == "Windows":
                webview.start(gui='edgechromium')
            else:
                webview.start()

        except ImportError:
            webbrowser.open(url)
            print("🖥️ GUI界面已启动（浏览器模式），等待用户反馈...")
            sys.stdout.flush()
            if timeout > 0:
                response_event.wait(timeout=timeout)
            else:
                response_event.wait()

        server.shutdown()

        if response_data[0]:
            feedback = response_data[0]
            result["feedback"] = [feedback]
            result["text_count"] = 1 if feedback.get("user_input") else 0
            result["image_count"] = len(feedback.get("images", []))
            # 输出清洗版本到 stdout，防止 base64 图片数据导致终端截断丢失 user_input
            sanitized = self._sanitize_feedback_for_output(feedback)
            output = json.dumps(sanitized, ensure_ascii=False, indent=2)
            print(output)
            self.save_conversation_record(summary, [feedback], project_dir)
        else:
            print(json.dumps({
                "user_input": None, "selected_options": [], "images": [],
                "metadata": {"timestamp": datetime.datetime.now().isoformat(), "source": "timeout"},
            }, ensure_ascii=False, indent=2))

        return result


# ═══════════════════════════════════════════════════════
# 队列管理器独立服务
# ═══════════════════════════════════════════════════════

def run_queue_manager_service():
    """启动队列管理器后台服务（HTTP API + 系统托盘）"""

    queue_mgr = QueueManager()
    tool = AIFeedbackTool()

    # 查找前端构建产物目录
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dist = os.path.join(base_dir, "frontend", "dist")

    has_frontend = os.path.exists(frontend_dist)

    class QueueManagerHandler(http.server.SimpleHTTPRequestHandler):
        extensions_map = {
            '.js': 'application/javascript',
            '.mjs': 'application/javascript',
            '.css': 'text/css',
            '.html': 'text/html',
            '.htm': 'text/html',
            '.json': 'application/json',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif': 'image/gif',
            '.svg': 'image/svg+xml',
            '.ico': 'image/x-icon',
            '.woff': 'font/woff',
            '.woff2': 'font/woff2',
            '.ttf': 'font/ttf',
            '.map': 'application/json',
            '': 'application/octet-stream',
        }

        def __init__(self, *args, **kwargs):
            if has_frontend:
                super().__init__(*args, directory=frontend_dist, **kwargs)
            else:
                super().__init__(*args, **kwargs)

        def guess_type(self, path):
            _, ext = os.path.splitext(path)
            ext = ext.lower()
            if ext in self.extensions_map:
                return self.extensions_map[ext]
            return super().guess_type(path)

        def do_GET(self):
            if self.path == "/api/config":
                self._json_response({
                    "request_id": f"req_{uuid.uuid4().hex[:12]}",
                    "session_id": f"session_{uuid.uuid4().hex[:16]}",
                    "summary": "队列管理器",
                    "message": "队列管理器",
                    "predefined_options": [],
                    "is_markdown": True,
                    "theme": "light",
                    "timeout": 0,
                    "project": "",
                    "mode": "queue_manager",
                })
            elif self.path == "/api/mode":
                self._json_response({"mode": "queue_manager"})
            elif self.path == "/api/queue":
                self._json_response({"queue": queue_mgr.get_all(), "count": queue_mgr.get_count()})
            elif self.path == "/api/queue/count":
                self._json_response({"count": queue_mgr.get_count()})
            elif self.path == "/api/queue/settings":
                self._json_response(queue_mgr.get_settings())
            elif self.path == "/api/settings":
                self._json_response(tool.settings)
            elif self.path == "/api/status":
                self._json_response({"status": "running", "count": queue_mgr.get_count()})
            elif self.path.startswith("/api/"):
                self._json_response({"error": "Not Found"}, 404)
            else:
                if has_frontend:
                    parsed = self.path.split("?")[0]
                    file_path = os.path.join(frontend_dist, parsed.lstrip("/"))
                    if os.path.isfile(file_path):
                        super().do_GET()
                    else:
                        self.path = "/index.html"
                        super().do_GET()
                else:
                    self._json_response({"error": "前端未构建"}, 500)

        def do_POST(self):
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)

            if self.path == "/api/queue":
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    content = data.get("content", "")
                    images = data.get("images", [])
                    if content.strip():
                        msg = queue_mgr.add_message(content, images)
                        self._json_response({"status": "ok", "message": msg, "count": queue_mgr.get_count()})
                    else:
                        self._json_response({"error": "内容不能为空"}, 400)
                except json.JSONDecodeError:
                    self._json_response({"error": "Invalid JSON"}, 400)

            elif self.path.startswith("/api/queue/delete/"):
                msg_id = self.path.split("/api/queue/delete/")[1]
                if queue_mgr.remove(msg_id):
                    self._json_response({"status": "ok", "count": queue_mgr.get_count()})
                else:
                    self._json_response({"error": "消息不存在"}, 404)

            elif self.path == "/api/queue/clear":
                queue_mgr.clear()
                self._json_response({"status": "ok"})

            elif self.path == "/api/queue/reorder":
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    msg_ids = data.get("ids", [])
                    queue_mgr.reorder(msg_ids)
                    self._json_response({"status": "ok"})
                except json.JSONDecodeError:
                    self._json_response({"error": "Invalid JSON"}, 400)

            elif self.path.startswith("/api/queue/update/"):
                msg_id = self.path.split("/api/queue/update/")[1]
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    if queue_mgr.update_message(msg_id, content=data.get("content"), images=data.get("images")):
                        self._json_response({"status": "ok"})
                    else:
                        self._json_response({"error": "消息不存在"}, 404)
                except json.JSONDecodeError:
                    self._json_response({"error": "Invalid JSON"}, 400)

            elif self.path == "/api/queue/settings":
                try:
                    data = json.loads(post_body.decode("utf-8"))
                    queue_mgr.update_settings(data)
                    self._json_response({"status": "ok", "settings": queue_mgr.get_settings()})
                except json.JSONDecodeError:
                    self._json_response({"error": "Invalid JSON"}, 400)

            elif self.path == "/api/queue/consume":
                msg = queue_mgr.consume_first()
                if msg:
                    self._json_response({"status": "ok", "message": msg, "count": queue_mgr.get_count()})
                else:
                    self._json_response({"error": "队列为空"}, 404)

            else:
                self._json_response({"error": "Not Found"}, 404)

        def do_OPTIONS(self):
            self.send_response(200)
            self._cors_headers()
            self.end_headers()

        def _json_response(self, data, code=200):
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

        def _cors_headers(self):
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE, PUT")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

        def log_message(self, format, *args):
            pass

    # 启动 HTTP 服务器
    port = QueueManager.QUEUE_MANAGER_PORT
    try:
        server = create_http_server(("127.0.0.1", port), QueueManagerHandler)
    except OSError:
        print(f"[队列管理器] 端口 {port} 已被占用，可能已有一个队列管理器在运行", file=sys.stderr)
        # 尝试打开浏览器到已有的服务
        webbrowser.open(f"http://127.0.0.1:{port}")
        return

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{port}"
    print(f"[队列管理器] 服务已启动: {url}")

    # ── 系统托盘 ──
    def start_system_tray():
        try:
            import pystray
            from PIL import Image

            # 加载图标
            if getattr(sys, 'frozen', False):
                icon_path = os.path.join(sys._MEIPASS, "icon.ico")
            else:
                icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")

            if os.path.exists(icon_path):
                icon_image = Image.open(icon_path)
            else:
                # 创建默认图标 (16x16 橙色方块)
                icon_image = Image.new('RGBA', (64, 64), (255, 140, 0, 255))

            def on_open_manager(icon, item):
                webbrowser.open(url)

            def on_quit(icon, item):
                icon.stop()
                server.shutdown()
                os._exit(0)

            def get_queue_count_text():
                count = queue_mgr.get_count()
                return f"队列: {count} 条消息"

            menu = pystray.Menu(
                pystray.MenuItem("打开队列管理", on_open_manager, default=True),
                pystray.MenuItem(get_queue_count_text, lambda icon, item: None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", on_quit),
            )

            icon = pystray.Icon(
                "柠檬酱队列管理器",
                icon_image,
                "柠檬酱 - 消息队列管理器",
                menu,
            )

            print("[队列管理器] 系统托盘图标已启动")
            icon.run()

        except ImportError:
            print("[队列管理器] pystray 未安装，跳过系统托盘", file=sys.stderr)
            print("[队列管理器] 安装: pip install pystray Pillow", file=sys.stderr)
            # 没有托盘就用简单的终端等待
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n[队列管理器] 已停止")
                server.shutdown()

    # 在浏览器中打开队列管理页面
    webbrowser.open(url)

    # 启动系统托盘（阻塞主线程）
    start_system_tray()


# ═══════════════════════════════════════════════════════
# 命令行入口
# ═══════════════════════════════════════════════════════

def main():
    # 确保 stderr/stdout 可用（防止 None 导致崩溃）
    class _NullWriter:
        def write(self, *a, **kw): pass
        def flush(self, *a, **kw): pass
    if sys.stderr is None:
        sys.stderr = _NullWriter()
    if sys.stdout is None:
        sys.stdout = _NullWriter()

    # 无参数时默认 --gui 模式 (支持双击运行)
    if len(sys.argv) == 1:
        sys.argv.append("--gui")

    parser = argparse.ArgumentParser(
        description="柠檬酱帮你阻止了会话结束 - AI 交互式反馈工具\n"
                    "复刻自 AIFeedbackTool，融合寸止风格 Vue 前端。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  # GUI 模式 (Vue 前端 + HTTP 服务器)
  python ai_feedback_tool_blocking.py --gui --project "C:\\MyProject" --summary "AI摘要"
  # GUI 模式（带超时）
  python ai_feedback_tool_blocking.py --gui --timeout 1800
  # CLI 模式
  python ai_feedback_tool_blocking.py --cli --project "C:\\MyProject" --summary "AI摘要"
  # 显示系统信息
  python ai_feedback_tool_blocking.py --system-info
  # 自动配置 Windsurf
  python ai_feedback_tool_blocking.py --configure
  # 一键停用 (移除 Windsurf 中的注入规则)
  python ai_feedback_tool_blocking.py --disable
  # 启动队列管理器 (后台常驻服务 + 系统托盘)
  python ai_feedback_tool_blocking.py --queue-manager
        """,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--gui", action="store_true",
                           help="GUI 模式 (Vue 前端 + HTTP 服务器)")
    mode_group.add_argument("--cli", action="store_true",
                           help="CLI 模式 (终端交互)")
    mode_group.add_argument("--system-info", action="store_true",
                           help="显示系统信息")
    mode_group.add_argument("--configure", action="store_true",
                           help="自动配置 Windsurf (注入规则)")
    mode_group.add_argument("--disable", action="store_true",
                           help="一键停用 - 移除 Windsurf 中注入的所有规则")
    mode_group.add_argument("--queue-manager", action="store_true",
                           help="启动队列管理器 (后台常驻服务 + 系统托盘)")

    parser.add_argument("--project", default="",
                       help="项目目录路径")
    parser.add_argument("--summary", default="柠檬酱帮你阻止了会话结束",
                       help="AI 对话摘要")
    parser.add_argument("--timeout", type=int, default=0,
                       help="超时时间(秒)，0 表示无超时")
    parser.add_argument("--output", default="",
                       help="结果输出文件路径")
    parser.add_argument("--options", default="",
                       help='预定义选项，JSON数组格式，如 ["选项1","选项2"]')

    args = parser.parse_args()
    tool = AIFeedbackTool()

    if args.system_info:
        info = tool.get_system_info()
        print(json.dumps(info, indent=2, ensure_ascii=False))
        return

    if args.configure:
        result = tool.configure_windsurf()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.disable:
        # 一键停用 - 移除 Windsurf 中注入的规则
        result = tool.disable_windsurf()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    if args.queue_manager:
        run_queue_manager_service()
        return

    # 解析预定义选项
    predefined_options = []
    if args.options:
        try:
            predefined_options = json.loads(args.options)
            if not isinstance(predefined_options, list):
                predefined_options = []
        except json.JSONDecodeError:
            # 尝试逗号分隔
            predefined_options = [o.strip() for o in args.options.split(",") if o.strip()]

    # 交互模式
    project_dir = args.project or os.getcwd()
    result = tool.interactive_feedback(
        project_directory=project_dir,
        summary=args.summary,
        timeout=args.timeout,
        use_gui=args.gui,
        predefined_options=predefined_options,
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"\n结果已保存: {args.output}")


if __name__ == "__main__":
    main()
