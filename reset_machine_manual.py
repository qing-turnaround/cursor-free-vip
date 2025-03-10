import os
import sys
import json
import locale
import uuid
import hashlib
import shutil
import sqlite3
import platform
import re
import tempfile
from colorama import Fore, Style, init
from typing import Tuple
import configparser
from new_signup import get_user_documents_path
import traceback

# Initialize colorama
init()

# Define emoji constants
EMOJI = {
    "FILE": "📄",
    "BACKUP": "💾",
    "SUCCESS": "✅",
    "ERROR": "❌",
    "INFO": "ℹ️",
    "RESET": "🔄",
}

def get_cursor_paths(translator=None) -> Tuple[str, str]:
    """ Get Cursor related paths"""
    system = platform.system()
    
    # 讀取配置文件
    config = configparser.ConfigParser()
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    
    if not os.path.exists(config_file):
        raise OSError(translator.get('reset.config_not_found') if translator else "找不到配置文件")
        
    if os.path.exists(config_file):
        try:
            # 尝试用UTF-8编码读取
            config.read(config_file, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # 尝试系统默认编码
                import locale
                config.read(config_file, encoding=locale.getpreferredencoding())
            except:
                try:
                    # 尝试GBK编码（中文Windows常用）
                    config.read(config_file, encoding='gbk')
                except:
                    # 二进制方式读取并转换
                    with open(config_file, 'rb') as f:
                        content = f.read()
                    # 清除BOM标记
                    content = content.replace(b'\xef\xbb\xbf', b'')
                    with open(config_file + '.tmp', 'w', encoding='utf-8') as f:
                        f.write(content.decode('latin-1'))
                    config.read(config_file + '.tmp', encoding='utf-8')
                    os.remove(config_file + '.tmp')  # 清理临时文件
    
    # 根據系統獲取路徑
    if system == "Darwin":
        section = 'MacPaths'
    elif system == "Windows":
        section = 'WindowsPaths'
    elif system == "Linux":
        section = 'LinuxPaths'
    else:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")
        
    if not config.has_section(section) or not config.has_option(section, 'cursor_path'):
        raise OSError(translator.get('reset.path_not_configured') if translator else "未配置 Cursor 路徑")
        
    base_path = config.get(section, 'cursor_path')
    
    if not os.path.exists(base_path):
        raise OSError(translator.get('reset.path_not_found', path=base_path) if translator else f"找不到 Cursor 路徑: {base_path}")
        
    pkg_path = os.path.join(base_path, "package.json")
    main_path = os.path.join(base_path, "out/main.js")
    
    # 檢查文件是否存在
    if not os.path.exists(pkg_path):
        raise OSError(translator.get('reset.package_not_found', path=pkg_path) if translator else f"找不到 package.json: {pkg_path}")
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.main_not_found', path=main_path) if translator else f"找不到 main.js: {main_path}")
    
    return (pkg_path, main_path)

def get_cursor_machine_id_path(translator=None) -> str:
    """
    Get Cursor machineId file path based on operating system
    Returns:
        str: Path to machineId file
    """
    # Read configuration
    config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
    config_file = os.path.join(config_dir, "config.ini")
    config = configparser.ConfigParser()
    
    if os.path.exists(config_file):
        try:
            # 尝试用UTF-8编码读取
            config.read(config_file, encoding='utf-8')
        except UnicodeDecodeError:
            try:
                # 尝试系统默认编码
                import locale
                config.read(config_file, encoding=locale.getpreferredencoding())
            except:
                try:
                    # 尝试GBK编码（中文Windows常用）
                    config.read(config_file, encoding='gbk')
                except:
                    # 二进制方式读取并转换
                    with open(config_file, 'rb') as f:
                        content = f.read()
                    # 清除BOM标记
                    content = content.replace(b'\xef\xbb\xbf', b'')
                    with open(config_file + '.tmp', 'w', encoding='utf-8') as f:
                        f.write(content.decode('latin-1'))
                    config.read(config_file + '.tmp', encoding='utf-8')
                    os.remove(config_file + '.tmp')  # 清理临时文件
    
    if sys.platform == "win32":  # Windows
        if not config.has_section('WindowsPaths'):
            config.add_section('WindowsPaths')
            # 使用更健壮的方式获取环境变量
            appdata = os.environ.get("APPDATA")
            if appdata is None:
                # 尝试使用Windows API获取路径
                try:
                    import ctypes
                    from ctypes import windll, wintypes
                    
                    CSIDL_APPDATA = 26  # AppData文件夹
                    SHGFP_TYPE_CURRENT = 0  # 获取当前路径而非默认路径
                    
                    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                    windll.shell32.SHGetFolderPathW(None, CSIDL_APPDATA, None, SHGFP_TYPE_CURRENT, buf)
                    
                    if buf.value:
                        appdata = buf.value
                    else:
                        appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
                except:
                    appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
            
            config.set('WindowsPaths', 'machine_id_path', 
                os.path.join(appdata, "Cursor", "machineId"))
        return config.get('WindowsPaths', 'machine_id_path')
        
    elif sys.platform == "linux":  # Linux
        if not config.has_section('LinuxPaths'):
            config.add_section('LinuxPaths')
            config.set('LinuxPaths', 'machine_id_path',
                os.path.expanduser("~/.config/Cursor/machineId"))
        return config.get('LinuxPaths', 'machine_id_path')
        
    elif sys.platform == "darwin":  # macOS
        if not config.has_section('MacPaths'):
            config.add_section('MacPaths')
            config.set('MacPaths', 'machine_id_path',
                os.path.expanduser("~/Library/Application Support/Cursor/machineId"))
        return config.get('MacPaths', 'machine_id_path')
        
    else:
        raise OSError(f"Unsupported operating system: {sys.platform}")

    # Save any changes to config file
    with open(config_file, 'w', encoding='utf-8') as f:
        config.write(f)

def get_workbench_cursor_path(translator=None) -> str:
    """Get Cursor workbench.desktop.main.js path"""
    system = platform.system()
    
    paths_map = {
        "Darwin": {  # macOS
            "base": "/Applications/Cursor.app/Contents/Resources/app",
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Windows": {
            "base": os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor", "resources", "app"),
            "main": "out/vs/workbench/workbench.desktop.main.js"
        },
        "Linux": {
            "bases": ["/opt/Cursor/resources/app", "/usr/share/cursor/resources/app"],
            "main": "out/vs/workbench/workbench.desktop.main.js"
        }
    }

    if system not in paths_map:
        raise OSError(translator.get('reset.unsupported_os', system=system) if translator else f"不支持的操作系统: {system}")

    if system == "Linux":
        for base in paths_map["Linux"]["bases"]:
            main_path = os.path.join(base, paths_map["Linux"]["main"])
            if os.path.exists(main_path):
                return main_path
        raise OSError(translator.get('reset.linux_path_not_found') if translator else "在 Linux 系统上未找到 Cursor 安装路径")

    base_path = paths_map[system]["base"]
    main_path = os.path.join(base_path, paths_map[system]["main"])
    
    if not os.path.exists(main_path):
        raise OSError(translator.get('reset.file_not_found', path=main_path) if translator else f"未找到 Cursor main.js 文件: {main_path}")
        
    return main_path

def version_check(version: str, min_version: str = "", max_version: str = "", translator=None) -> bool:
    """Version number check"""
    version_pattern = r"^\d+\.\d+\.\d+$"
    try:
        if not re.match(version_pattern, version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False

        def parse_version(ver: str) -> Tuple[int, ...]:
            return tuple(map(int, ver.split(".")))

        current = parse_version(version)

        if min_version and current < parse_version(min_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_low', version=version, min_version=min_version)}{Style.RESET_ALL}")
            return False

        if max_version and current > parse_version(max_version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_too_high', version=version, max_version=max_version)}{Style.RESET_ALL}")
            return False

        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_check_error', error=str(e))}{Style.RESET_ALL}")
        return False

def check_cursor_version(translator) -> bool:
    """Check Cursor version"""
    try:
        pkg_path, _ = get_cursor_paths(translator)
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.reading_package_json', path=pkg_path)}{Style.RESET_ALL}")
        
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except UnicodeDecodeError:
            # 如果 UTF-8 讀取失敗，嘗試其他編碼
            with open(pkg_path, "r", encoding="latin-1") as f:
                data = json.load(f)
                
        if not isinstance(data, dict):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
            return False
            
        if "version" not in data:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_version_field')}{Style.RESET_ALL}")
            return False
            
        version = str(data["version"]).strip()
        if not version:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_field_empty')}{Style.RESET_ALL}")
            return False
            
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.found_version', version=version)}{Style.RESET_ALL}")
        
        # 檢查版本格式
        if not re.match(r"^\d+\.\d+\.\d+$", version):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_version_format', version=version)}{Style.RESET_ALL}")
            return False
            
        # 比較版本
        try:
            current = tuple(map(int, version.split(".")))
            min_ver = (0, 45, 0)  # 直接使用元組而不是字符串
            
            if current >= min_ver:
                print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.version_check_passed', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.version_too_low', version=version, min_version='0.45.0')}{Style.RESET_ALL}")
                return False
        except ValueError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_parse_error', error=str(e))}{Style.RESET_ALL}")
            return False
            
    except FileNotFoundError as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.package_not_found', path=pkg_path)}{Style.RESET_ALL}")
        return False
    except json.JSONDecodeError as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.invalid_json_object')}{Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.check_version_failed', error=str(e))}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}{EMOJI['INFO']} {translator.get('reset.stack_trace')}: {traceback.format_exc()}{Style.RESET_ALL}")
        return False

def modify_workbench_js(file_path: str, translator=None) -> bool:
    """
    Modify file content
    """
    try:
        # Save original file permissions
        original_stat = os.stat(file_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", errors="ignore", delete=False) as tmp_file:
            # Read original content
            with open(file_path, "r", encoding="utf-8", errors="ignore") as main_file:
                content = main_file.read()

            if sys.platform == "win32":
                # Define replacement patterns
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"qing-turnaround GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/qing-turnaround/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "linux":
                CButton_old_pattern = r'$(k,E(Ks,{title:"Upgrade to Pro",size:"small",get codicon(){return F.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'$(k,E(Ks,{title:"qing-turnaround GitHub",size:"small",get codicon(){return F.rocket},get onClick(){return function(){window.open("https://github.com/qing-turnaround/cursor-free-vip","_blank")}}}),null)'
            elif sys.platform == "darwin":
                CButton_old_pattern = r'M(x,I(as,{title:"Upgrade to Pro",size:"small",get codicon(){return $.rocket},get onClick(){return t.pay}}),null)'
                CButton_new_pattern = r'M(x,I(as,{title:"qing-turnaround GitHub",size:"small",get codicon(){return $.rocket},get onClick(){return function(){window.open("https://github.com/qing-turnaround/cursor-free-vip","_blank")}}}),null)'

            CBadge_old_pattern = r'<div>Pro Trial'
            CBadge_new_pattern = r'<div>Pro'

            CToast_old_pattern = r'notifications-toasts'
            CToast_new_pattern = r'notifications-toasts hidden'

            # Replace content
            content = content.replace(CButton_old_pattern, CButton_new_pattern)
            content = content.replace(CBadge_old_pattern, CBadge_new_pattern)
            content = content.replace(CToast_old_pattern, CToast_new_pattern)

            # Write to temporary file
            tmp_file.write(content)
            tmp_path = tmp_file.name

        # Backup original file
        backup_path = file_path + ".backup"
        if os.path.exists(backup_path):
            os.remove(backup_path)
        shutil.copy2(file_path, backup_path)
        
        # Move temporary file to original position
        if os.path.exists(file_path):
            os.remove(file_path)
        shutil.move(tmp_path, file_path)

        # Restore original permissions
        os.chmod(file_path, original_mode)
        if os.name != "nt":  # Not Windows
            os.chown(file_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            try:
                os.unlink(tmp_path)
            except:
                pass
        return False

def modify_main_js(main_path: str, translator) -> bool:
    """Modify main.js file"""
    try:
        original_stat = os.stat(main_path)
        original_mode = original_stat.st_mode
        original_uid = original_stat.st_uid
        original_gid = original_stat.st_gid

        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            with open(main_path, "r", encoding="utf-8") as main_file:
                content = main_file.read()

            patterns = {
                r"async getMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMachineId(){return \1}",
                r"async getMacMachineId\(\)\{return [^??]+\?\?([^}]+)\}": r"async getMacMachineId(){return \1}",
            }

            for pattern, replacement in patterns.items():
                content = re.sub(pattern, replacement, content)

            tmp_file.write(content)
            tmp_path = tmp_file.name

        shutil.copy2(main_path, main_path + ".old")
        shutil.move(tmp_path, main_path)

        os.chmod(main_path, original_mode)
        if os.name != "nt":
            os.chown(main_path, original_uid, original_gid)

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.file_modified')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.modify_file_failed', error=str(e))}{Style.RESET_ALL}")
        if "tmp_path" in locals():
            os.unlink(tmp_path)
        return False

def patch_cursor_get_machine_id(translator) -> bool:
    """Patch Cursor getMachineId function"""
    try:
        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.start_patching')}...{Style.RESET_ALL}")
        
        # Get paths
        pkg_path, main_path = get_cursor_paths(translator)
        
        # Check file permissions
        for file_path in [pkg_path, main_path]:
            if not os.path.isfile(file_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.file_not_found', path=file_path)}{Style.RESET_ALL}")
                return False
            if not os.access(file_path, os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.no_write_permission', path=file_path)}{Style.RESET_ALL}")
                return False

        # Get version number
        try:
            with open(pkg_path, "r", encoding="utf-8") as f:
                version = json.load(f)["version"]
            print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.current_version', version=version)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.read_version_failed', error=str(e))}{Style.RESET_ALL}")
            return False

        # Check version
        if not version_check(version, min_version="0.45.0", translator=translator):
            print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.version_not_supported')}{Style.RESET_ALL}")
            return False

        print(f"{Fore.CYAN}{EMOJI['INFO']} {translator.get('reset.version_check_passed')}{Style.RESET_ALL}")

        # Backup file
        backup_path = main_path + ".bak"
        if not os.path.exists(backup_path):
            shutil.copy2(main_path, backup_path)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.backup_created', path=backup_path)}{Style.RESET_ALL}")

        # Modify file
        if not modify_main_js(main_path, translator):
            return False

        print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {translator.get('reset.patch_completed')}{Style.RESET_ALL}")
        return True

    except Exception as e:
        print(f"{Fore.RED}{EMOJI['ERROR']} {translator.get('reset.patch_failed', error=str(e))}{Style.RESET_ALL}")
        return False

class MachineIDResetter:
    def __init__(self, translator=None):
        self.translator = translator

        # Read configuration
        config_dir = os.path.join(get_user_documents_path(), ".cursor-free-vip")
        config_file = os.path.join(config_dir, "config.ini")
        config = configparser.ConfigParser()
        
        if not os.path.exists(config_file):
            raise FileNotFoundError(f"Config file not found: {config_file}")
        
        if os.path.exists(config_file):
            try:
                # 尝试用UTF-8编码读取
                config.read(config_file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    # 尝试系统默认编码
                    import locale
                    config.read(config_file, encoding=locale.getpreferredencoding())
                except:
                    try:
                        # 尝试GBK编码（中文Windows常用）
                        config.read(config_file, encoding='gbk')
                    except:
                        # 二进制方式读取并转换
                        with open(config_file, 'rb') as f:
                            content = f.read()
                        # 清除BOM标记
                        content = content.replace(b'\xef\xbb\xbf', b'')
                        with open(config_file + '.tmp', 'w', encoding='utf-8') as f:
                            f.write(content.decode('latin-1'))
                        config.read(config_file + '.tmp', encoding='utf-8')
                        os.remove(config_file + '.tmp')  # 清理临时文件

        # Check operating system
        if sys.platform == "win32":  # Windows
            # 使用更健壮的方式获取环境变量
            appdata = os.environ.get("APPDATA")
            if appdata is None:
                # 尝试使用Windows API获取路径
                try:
                    import ctypes
                    from ctypes import windll, wintypes
                    
                    CSIDL_APPDATA = 26  # AppData文件夹
                    SHGFP_TYPE_CURRENT = 0  # 获取当前路径而非默认路径
                    
                    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
                    windll.shell32.SHGetFolderPathW(None, CSIDL_APPDATA, None, SHGFP_TYPE_CURRENT, buf)
                    
                    if buf.value:
                        appdata = buf.value
                    else:
                        appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
                except:
                    appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming")
            
            if not config.has_section('WindowsPaths'):
                config.add_section('WindowsPaths')
                config.set('WindowsPaths', 'storage_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "storage.json"
                ))
                config.set('WindowsPaths', 'sqlite_path', os.path.join(
                    appdata, "Cursor", "User", "globalStorage", "state.vscdb"
                ))
                
            self.db_path = config.get('WindowsPaths', 'storage_path')
            self.sqlite_path = config.get('WindowsPaths', 'sqlite_path')
            
        elif sys.platform == "darwin":  # macOS
            if not config.has_section('MacPaths'):
                config.add_section('MacPaths')
                config.set('MacPaths', 'storage_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/storage.json"
                )))
                config.set('MacPaths', 'sqlite_path', os.path.abspath(os.path.expanduser(
                    "~/Library/Application Support/Cursor/User/globalStorage/state.vscdb"
                )))
                
            self.db_path = config.get('MacPaths', 'storage_path')
            self.sqlite_path = config.get('MacPaths', 'sqlite_path')
            
        elif sys.platform == "linux":  # Linux
            if not config.has_section('LinuxPaths'):
                config.add_section('LinuxPaths')
                # 获取实际用户的主目录
                sudo_user = os.environ.get('SUDO_USER')
                actual_home = f"/home/{sudo_user}" if sudo_user else os.path.expanduser("~")
                
                config.set('LinuxPaths', 'storage_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/Cursor/User/globalStorage/storage.json"
                )))
                config.set('LinuxPaths', 'sqlite_path', os.path.abspath(os.path.join(
                    actual_home,
                    ".config/Cursor/User/globalStorage/state.vscdb"
                )))
                
            self.db_path = config.get('LinuxPaths', 'storage_path')
            self.sqlite_path = config.get('LinuxPaths', 'sqlite_path')
            
        else:
            raise NotImplementedError(f"Not Supported OS: {sys.platform}")

        # Save any changes to config file
        with open(config_file, 'w', encoding='utf-8') as f:
            config.write(f)

    def generate_new_ids(self):
        """Generate new machine ID"""
        # Generate new UUID
        dev_device_id = str(uuid.uuid4())

        # Generate new machineId (64 characters of hexadecimal)
        machine_id = hashlib.sha256(os.urandom(32)).hexdigest()

        # Generate new macMachineId (128 characters of hexadecimal)
        mac_machine_id = hashlib.sha512(os.urandom(64)).hexdigest()

        # Generate new sqmId
        sqm_id = "{" + str(uuid.uuid4()).upper() + "}"

        self.update_machine_id_file(dev_device_id)

        return {
            "telemetry.devDeviceId": dev_device_id,
            "telemetry.macMachineId": mac_machine_id,
            "telemetry.machineId": machine_id,
            "telemetry.sqmId": sqm_id,
            "storage.serviceMachineId": dev_device_id,  # Add storage.serviceMachineId
        }

    def update_sqlite_db(self, new_ids):
        """Update machine ID in SQLite database"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_sqlite')}...{Style.RESET_ALL}")
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS ItemTable (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            """)

            updates = [
                (key, value) for key, value in new_ids.items()
            ]

            for key, value in updates:
                cursor.execute("""
                    INSERT OR REPLACE INTO ItemTable (key, value) 
                    VALUES (?, ?)
                """, (key, value))
                print(f"{EMOJI['INFO']} {Fore.CYAN} {self.translator.get('reset.updating_pair')}: {key}{Style.RESET_ALL}")

            conn.commit()
            conn.close()
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.sqlite_success')}{Style.RESET_ALL}")
            return True

        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.sqlite_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_system_ids(self, new_ids):
        """Update system-level IDs"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.updating_system_ids')}...{Style.RESET_ALL}")
            
            if sys.platform.startswith("win"):
                self._update_windows_machine_guid()
            elif sys.platform == "darwin":
                self._update_macos_platform_uuid(new_ids)
                
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.system_ids_updated')}{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.system_ids_update_failed', error=str(e))}{Style.RESET_ALL}")
            return False

    def _update_windows_machine_guid(self):
        """Update Windows MachineGuid"""
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                "SOFTWARE\\Microsoft\\Cryptography",
                0,
                winreg.KEY_WRITE | winreg.KEY_WOW64_64KEY
            )
            new_guid = str(uuid.uuid4())
            winreg.SetValueEx(key, "MachineGuid", 0, winreg.REG_SZ, new_guid)
            winreg.CloseKey(key)
            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.windows_machine_guid_updated')}{Style.RESET_ALL}")
        except PermissionError:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_denied')}{Style.RESET_ALL}")
            raise
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_windows_machine_guid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def _update_macos_platform_uuid(self, new_ids):
        """Update macOS Platform UUID"""
        try:
            uuid_file = "/var/root/Library/Preferences/SystemConfiguration/com.apple.platform.uuid.plist"
            if os.path.exists(uuid_file):
                # Use sudo to execute plutil command
                cmd = f'sudo plutil -replace "UUID" -string "{new_ids["telemetry.macMachineId"]}" "{uuid_file}"'
                result = os.system(cmd)
                if result == 0:
                    print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.macos_platform_uuid_updated')}{Style.RESET_ALL}")
                else:
                    raise Exception(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.failed_to_execute_plutil_command')}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.update_macos_platform_uuid_failed', error=str(e))}{Style.RESET_ALL}")
            raise

    def reset_machine_ids(self):
        """Reset machine ID and backup original file"""
        try:
            print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.checking')}...{Style.RESET_ALL}")

            if not os.path.exists(self.db_path):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.not_found')}: {self.db_path}{Style.RESET_ALL}")
                return False

            if not os.access(self.db_path, os.R_OK | os.W_OK):
                print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.no_permission')}{Style.RESET_ALL}")
                return False

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.reading')}...{Style.RESET_ALL}")
            with open(self.db_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            backup_path = self.db_path + ".bak"
            if not os.path.exists(backup_path):
                print(f"{Fore.YELLOW}{EMOJI['BACKUP']} {self.translator.get('reset.creating_backup')}: {backup_path}{Style.RESET_ALL}")
                shutil.copy2(self.db_path, backup_path)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_exists')}{Style.RESET_ALL}")

            print(f"{Fore.CYAN}{EMOJI['RESET']} {self.translator.get('reset.generating')}...{Style.RESET_ALL}")
            new_ids = self.generate_new_ids()

            # Update configuration file
            config.update(new_ids)

            print(f"{Fore.CYAN}{EMOJI['FILE']} {self.translator.get('reset.saving_json')}...{Style.RESET_ALL}")
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=4)

            # Update SQLite database
            self.update_sqlite_db(new_ids)

            # Update system IDs
            self.update_system_ids(new_ids)


            ### Remove In v1.7.02
            # Modify workbench.desktop.main.js
            
            # workbench_path = get_workbench_cursor_path(self.translator)
            # modify_workbench_js(workbench_path, self.translator)

            ### Remove In v1.7.02
            # Check Cursor version and perform corresponding actions
            
            greater_than_0_45 = check_cursor_version(self.translator)
            if greater_than_0_45:
                print(f"{Fore.CYAN}{EMOJI['INFO']} {self.translator.get('reset.detecting_version')} >= 0.45.0，{self.translator.get('reset.patching_getmachineid')}{Style.RESET_ALL}")
                patch_cursor_get_machine_id(self.translator)
            else:
                print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.version_less_than_0_45')}{Style.RESET_ALL}")

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.success')}{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{self.translator.get('reset.new_id')}:{Style.RESET_ALL}")
            for key, value in new_ids.items():
                print(f"{EMOJI['INFO']} {key}: {Fore.GREEN}{value}{Style.RESET_ALL}")

            return True

        except PermissionError as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.permission_error', error=str(e))}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.run_as_admin')}{Style.RESET_ALL}")
            return False
        except Exception as e:
            print(f"{Fore.RED}{EMOJI['ERROR']} {self.translator.get('reset.process_error', error=str(e))}{Style.RESET_ALL}")
            return False

    def update_machine_id_file(self, machine_id: str) -> bool:
        """
        Update machineId file with new machine_id
        Args:
            machine_id (str): New machine ID to write
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get the machineId file path
            machine_id_path = get_cursor_machine_id_path()
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(machine_id_path), exist_ok=True)

            # Create backup if file exists
            if os.path.exists(machine_id_path):
                backup_path = machine_id_path + ".backup"
                try:
                    shutil.copy2(machine_id_path, backup_path)
                    print(f"{Fore.GREEN}{EMOJI['INFO']} {self.translator.get('reset.backup_created', path=backup_path) if self.translator else f'Backup created at: {backup_path}'}{Style.RESET_ALL}")
                except Exception as e:
                    print(f"{Fore.YELLOW}{EMOJI['INFO']} {self.translator.get('reset.backup_creation_failed', error=str(e)) if self.translator else f'Could not create backup: {str(e)}'}{Style.RESET_ALL}")

            # Write new machine ID to file
            with open(machine_id_path, "w", encoding="utf-8") as f:
                f.write(machine_id)

            print(f"{Fore.GREEN}{EMOJI['SUCCESS']} {self.translator.get('reset.update_success') if self.translator else 'Successfully updated machineId file'}{Style.RESET_ALL}")
            return True

        except Exception as e:
            error_msg = f"Failed to update machineId file: {str(e)}"
            if self.translator:
                error_msg = self.translator.get('reset.update_failed', error=str(e))
            print(f"{Fore.RED}{EMOJI['ERROR']} {error_msg}{Style.RESET_ALL}")
            return False

def run(translator=None):
    """Convenient function for directly calling the reset function"""
    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{EMOJI['RESET']} {translator.get('reset.title')}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*50}{Style.RESET_ALL}")

    resetter = MachineIDResetter(translator)  # Correctly pass translator
    resetter.reset_machine_ids()

    print(f"\n{Fore.CYAN}{'='*50}{Style.RESET_ALL}")
    input(f"{EMOJI['INFO']} {translator.get('reset.press_enter')}...")

if __name__ == "__main__":
    from main import translator as main_translator
    run(main_translator)