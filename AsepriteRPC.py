import os
import time
import json
import psutil
import threading
from datetime import datetime, timedelta
from pypresence import Presence
import win32gui
import win32process
import re
import colorama
from colorama import Fore, Back, Style, init

init(autoreset=True)

class AsepriteRichPresence:
    def __init__(self):
        self.client_id = "0"
        self.rpc = None
        self.connected = False
        
        self.current_file = None
        self.start_time = None
        self.file_start_time = None
        self.last_update = None
        
        self.process_cache = {}
        self.cache_update_interval = 2
        self.last_cache_update = 0
        
        self.update_interval = 3
        
    def connect_discord(self):
        try:
            self.rpc = Presence(self.client_id)
            self.rpc.connect()
            self.connected = True
            print(f"{Fore.GREEN}✅ Connected to Discord{Style.RESET_ALL}")
            return True
        except Exception as e:
            print(f"{Fore.RED}❌ Discord connection error: {e}{Style.RESET_ALL}")
            return False
    
    def get_aseprite_processes(self):
        current_time = time.time()
        
        if current_time - self.last_cache_update > self.cache_update_interval:
            self.process_cache = {}
            for proc in psutil.process_iter(['pid', 'name']):
                try:
                    if proc.info['name'].lower() == 'aseprite.exe':
                        self.process_cache[proc.info['pid']] = proc
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            self.last_cache_update = current_time
        
        return list(self.process_cache.values())
    
    def get_window_title_by_pid(self, pid):
        def enum_windows_callback(hwnd, results):
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
                if window_pid == pid and win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    if window_title and "Aseprite" in window_title:
                        results.append(window_title)
            except:
                pass
        
        windows = []
        try:
            win32gui.EnumWindows(enum_windows_callback, windows)
            return windows[0] if windows else None
        except:
            return None
    
    def parse_filename_from_title(self, title):
        if not title:
            return None, None
            
        print(f"{Fore.CYAN}🔍 Analyzing title: {Fore.YELLOW}'{title}'{Style.RESET_ALL}")
            
        clean_title = title.replace(' - Aseprite', '').replace('Aseprite', '').strip()
        clean_title = re.sub(r'v?\d+\.\d+[\.\d]*', '', clean_title).strip()
        clean_title = clean_title.strip(' -')
        
        if not clean_title or clean_title == '':
            return None, None
        
        if '.' in clean_title:
            name_with_ext = clean_title.split(' ')[0]
            if '.' in name_with_ext:
                name, ext = os.path.splitext(name_with_ext)
                return name_with_ext, ext.lower()
        
        return clean_title, '.ase'
    
    def get_file_type_description(self, extension):
        file_types = {
            '.ase': 'Aseprite file',
            '.aseprite': 'Aseprite file',
            '.png': 'PNG image',
            '.gif': 'GIF animation',
            '.jpg': 'JPEG image',
            '.jpeg': 'JPEG image',
            '.bmp': 'Bitmap image',
            '.tga': 'TGA image',
            '.webp': 'WebP image',
            '.psd': 'Photoshop file'
        }
        return file_types.get(extension, 'Sprite file')
    
    def format_duration(self, seconds):
        if seconds < 60:
            return f"00:00:{seconds:02d}"
        elif seconds < 3600:
            minutes = seconds // 60
            secs = seconds % 60
            return f"00:{minutes:02d}:{secs:02d}"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def update_presence(self, filename=None, file_ext=None):
        if not self.connected or not self.rpc:
            return
        
        try:
            current_time = int(time.time())
            
            if filename:
                if self.current_file != filename:
                    self.current_file = filename
                    self.file_start_time = current_time
                    print(f"{Fore.BLUE}📁 Opened file: {Fore.CYAN}{filename}{Style.RESET_ALL}")
                
                file_type = self.get_file_type_description(file_ext or '.ase')
                work_time = current_time - (self.file_start_time or current_time)
                
                display_name = f"[{filename}]"
                
                activity = {
                    'state': file_type,
                    'details': display_name,
                    'large_image': 'aseprite_icon',
                    'large_text': 'Aseprite - Animated Sprite Editor'
                }
            else:
                activity = {
                    'state': 'Ready to create',
                    'details': 'Aseprite',
                    'large_image': 'aseprite_icon',
                    'large_text': 'Aseprite - Animated Sprite Editor'
                }
            
            self.rpc.update(**activity)
            self.last_update = current_time
            
            if filename:
                print(f"{Fore.GREEN}🔄 Status updated: {Fore.CYAN}{filename} {Fore.MAGENTA}({file_type}){Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}🔄 Status updated: Idle{Style.RESET_ALL}")
                
        except Exception as e:
            print(f"{Fore.RED}❌ Status update error: {e}{Style.RESET_ALL}")
    
    def clear_presence(self):
        if self.connected and self.rpc:
            try:
                self.rpc.clear()
                print(f"{Fore.YELLOW}🧹 Status cleared{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Status clear error: {e}{Style.RESET_ALL}")
    
    def disconnect_discord(self):
        if self.connected and self.rpc:
            try:
                self.rpc.close()
                self.connected = False
                print(f"{Fore.BLUE}🔌 Disconnected from Discord{Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}❌ Discord disconnect error: {e}{Style.RESET_ALL}")
    
    def monitor_aseprite(self):
        print(f"{Fore.MAGENTA}🎨 Starting Aseprite monitoring...{Style.RESET_ALL}")
        aseprite_was_running = False
        
        while True:
            try:
                processes = self.get_aseprite_processes()
                aseprite_running = len(processes) > 0
                
                if aseprite_running:
                    if not aseprite_was_running:
                        self.start_time = int(time.time())
                        print(f"{Fore.GREEN}🎨 Aseprite is running{Style.RESET_ALL}")
                    
                    current_filename = None
                    current_ext = None
                    
                    for proc in processes:
                        try:
                            window_title = self.get_window_title_by_pid(proc.pid)
                            if window_title:
                                filename, ext = self.parse_filename_from_title(window_title)
                                if filename:
                                    current_filename = filename
                                    current_ext = ext
                                    break
                        except Exception as e:
                            continue
                    
                    self.update_presence(current_filename, current_ext)
                    aseprite_was_running = True
                    
                else:
                    if aseprite_was_running:
                        print(f"{Fore.RED}🎨 Aseprite closed - shutting down{Style.RESET_ALL}")
                        self.clear_presence()
                        self.disconnect_discord()
                        break
                    aseprite_was_running = False
                
                time.sleep(self.update_interval)
                
            except KeyboardInterrupt:
                print(f"\n{Fore.RED}🛑 Stopping monitoring...{Style.RESET_ALL}")
                self.clear_presence()
                self.disconnect_discord()
                break
            except Exception as e:
                print(f"{Fore.RED}❌ Monitoring loop error: {e}{Style.RESET_ALL}")
                time.sleep(5)
    
    def run(self):
        print(f"{Fore.CYAN}{Style.BRIGHT}")
        print("╔═════════════════════════════════════════════════╗")
        print("║         🎨 ASEPRITE DISCORD RICH PRESENCE        ║")
        print("╚═════════════════════════════════════════════════╝")
        print(f"{Style.RESET_ALL}")
        print()
        
        print(f"{Fore.YELLOW}⏳ Waiting for Aseprite to start...{Style.RESET_ALL}")
        
        while True:
            try:
                processes = self.get_aseprite_processes()
                if len(processes) > 0:
                    print(f"{Fore.GREEN}🎨 Aseprite detected! Connecting to Discord...{Style.RESET_ALL}")
                    break
                print(f"{Fore.CYAN}💤 Aseprite not running, waiting... {Fore.WHITE}(checking every 5 sec){Style.RESET_ALL}")
                time.sleep(5)
            except Exception as e:
                print(f"{Fore.RED}❌ Error checking for Aseprite: {e}{Style.RESET_ALL}")
                time.sleep(5)
        
        if not self.connect_discord():
            print(f"{Fore.RED}❌ Failed to connect to Discord. Check:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}   1. Is Discord running?{Style.RESET_ALL}")
            print(f"{Fore.WHITE}   2. Is Application ID correct?{Style.RESET_ALL}")
            return
        
        try:
            self.monitor_aseprite()
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}🛑 Stopping...{Style.RESET_ALL}")
        finally:
            print(f"{Fore.YELLOW}🧹 Cleaning up...{Style.RESET_ALL}")
            self.clear_presence()
            self.disconnect_discord()
            time.sleep(1)
            print(f"{Fore.GREEN}👋 Goodbye!{Style.RESET_ALL}")

def main():
    print(f"{Fore.MAGENTA}{Style.BRIGHT}")
    print("    ╔═══════════════════════════════════════╗")
    print("    ║   🎨 ASEPRITE DISCORD RICH PRESENCE   ║")
    print("    ║                                       ║")
    print("    ║        Made with ❤️  for artists      ║")
    print("    ╚═══════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    
    print(f"{Fore.CYAN}📋 Before running make sure:{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   1. {Fore.GREEN}Dependencies installed: {Fore.YELLOW}pip install colorama pypresence psutil pywin32{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   2. {Fore.GREEN}Discord application created in Developer Portal{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   3. {Fore.GREEN}Application ID specified in code{Style.RESET_ALL}")
    print(f"{Fore.WHITE}   4. {Fore.GREEN}Images uploaded for Rich Presence{Style.RESET_ALL}")
    print()
    print(f"{Fore.RED}Press Ctrl+C to stop{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'═' * 45}{Style.RESET_ALL}")
    print()
    
    rpc_client = AsepriteRichPresence()
    rpc_client.run()

if __name__ == "__main__":
    main()