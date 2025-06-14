import cv2
import numpy as np
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
import threading
from queue import Queue
import sys

# 主题颜色
THEME_COLOR = "#defaee" # 主背景颜色
SECONDARY_COLOR = "#b4fae6" # 窗口颜色
ACCENT_COLOR = "#73c2cd"    # 按钮背景颜色
TEXT_COLOR = "#29596a"  # 文字颜色
HIGHLIGHT_COLOR = "#FFFFFF" # 高亮颜色

class VideoToASCII:     #转换核心类
    def __init__(self, video_path=None, cols=100, fps=24, max_height=600):
        self.video_path = video_path
        self.cols = cols
        self.fps = fps
        self.max_height = max_height
        self.ascii_chars = "@%#*+=-:. "  # 从暗到亮的字符
        self.ascii_frames = []
        self.running = False
        self.frame_queue = Queue()
        self.total_frames = 0
        self.processed_frames = 0
        
        # 字符宽高比 (Courier字体大约为0.5)
        self.char_aspect_ratio = 0.5
        
        # 字体设置
        self.font_size = 8
        self.font_family = "Courier"
    
    def get_video_info(self):
        """获取视频信息"""
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            return None
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps
        
        cap.release()
        
        return {
            "fps": fps,
            "frame_count": frame_count,
            "width": width,
            "height": height,
            "duration": duration
        }
    
    def calculate_optimal_size(self, frame):
        """计算最佳转换尺寸，保持原始比例"""
        height, width = frame.shape[:2]
        
        # 限制最大高度
        if height > self.max_height:
            scale = self.max_height / height
            width = int(width * scale)
            height = self.max_height
            frame = cv2.resize(frame, (width, height))
        
        # 计算字符行数，保持原始比例
        cell_width = width / self.cols
        cell_height = cell_width / self.char_aspect_ratio
        rows = int(height / cell_height)
        
        return (self.cols, rows)
    
    def convert_frame_to_ascii(self, frame):        #将单个帧转换为ASCII艺术
        """将单个帧转换为ASCII艺术"""
        # 转换为灰度图
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        height, width = gray.shape
        
        # 计算最佳尺寸
        cols, rows = self.calculate_optimal_size(frame)
        
        # 调整图像大小
        resized = cv2.resize(gray, (cols, rows))
        
        # 将灰度值映射到ASCII字符
        ascii_str = ""
        for i in range(rows):
            for j in range(cols):
                pixel = int(resized[i, j])
                index = min(pixel * len(self.ascii_chars) // 256, len(self.ascii_chars)-1)  # 像素值映射到ASCII字符列表的索引上
                ascii_str += self.ascii_chars[index]
            ascii_str += "\n"
        
        self.processed_frames += 1
        return ascii_str
    
    def process_video(self):        #处理视频
        """处理视频并生成ASCII帧"""
        try:
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                raise ValueError("无法打开视频文件")
            
            self.total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) # 获取视频总帧数
            self.processed_frames = 0   # 初始化已处理帧数
                
            while cap.isOpened() and self.running: # 读取视频帧
                ret, frame = cap.read() # ret为True表示成功读取帧，frame为读取到的帧
                if not ret: 
                    break
                
                ascii_frame = self.convert_frame_to_ascii(frame) # 将帧转换为ASCII艺术
                self.frame_queue.put(ascii_frame) # 将ASCII艺术帧放入队列
                
                # 控制处理速度
                if self.frame_queue.qsize() > 10:
                    time.sleep(0.1)
            
            cap.release()
        except Exception as e:
            print(f"视频处理错误: {e}")
        finally:
            self.frame_queue.put(None)  # 结束信号
    
    def play_in_console(self):              #在控制台中播放ASCII艺术
        """在控制台中播放ASCII艺术"""
        try:
            # 获取终端大小
            try:
                import shutil
                console_size = shutil.get_terminal_size()
                console_width = console_size.columns
                console_height = console_size.lines
            except:
                console_width = 80
                console_height = 24
            
            # 创建清屏字符串
            clear_screen = "\033[2J\033[H"  # ANSI清屏代码
            
            while self.running:
                ascii_frame = self.frame_queue.get()
                if ascii_frame is None:
                    break
                
                # 清屏并打印新帧
                sys.stdout.write(clear_screen)
                sys.stdout.write(ascii_frame)
                sys.stdout.flush()
                time.sleep(1/self.fps)
        except Exception as e:
            print(f"控制台播放错误: {e}")
        finally:
            # 恢复光标位置
            sys.stdout.write("\033[0;0H")
            sys.stdout.flush()
    
    def start_processing(self):
        """启动视频处理线程"""
        self.running = True
        self.processing_thread = threading.Thread(target=self.process_video)
        self.processing_thread.start()
    
    def start_console_playback(self):
        """启动控制台播放线程"""
        self.console_thread = threading.Thread(target=self.play_in_console)
        self.console_thread.start()
    
    def stop(self):
        """停止所有线程"""
        self.running = False
        if hasattr(self, 'processing_thread'):
            self.processing_thread.join()
        if hasattr(self, 'console_thread'):
            self.console_thread.join()

class StyledButton(ttk.Button):
    """自定义样式按钮"""
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self.configure(style="Accent.TButton")

class ASCIIPlayerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ASCII 艺术视频播放器")
        self.geometry("900x700")
        self.configure(bg=THEME_COLOR)
        
        # 设置窗口图标
        try:
            self.iconbitmap(r"F:\python\python_ASCIIART\logo\ASCII.ico")  
        except tk.TclError as e:
            print(f"无法加载图标: {e}")
        
        # 创建转换器实例
        self.ascii_converter = None

        # 字体设置
        self.font_size = 8
        self.font_family = "Courier"

        # #设置背景图
        # self.bg_image = tk.PhotoImage(file="png/ACG_charm.png")  
        # self.bg_label = ttk.Label(self, image=self.bg_image)
        # self.bg_label.place(relwidth=1, relheight=1)  

        
        # 设置样式
        self.setup_styles()
        
        # 设置UI
        self.create_widgets()
    
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style(self)
        
        # 主题设置
        style.theme_use("clam")
        
        # 配置颜色
        style.configure(".", background=THEME_COLOR, foreground=TEXT_COLOR)
        style.configure("TFrame", background=THEME_COLOR)
        style.configure("TLabel", background=THEME_COLOR, foreground=TEXT_COLOR)
        style.configure("TButton", background=SECONDARY_COLOR, foreground=TEXT_COLOR)
        style.configure("TEntry", fieldbackground=SECONDARY_COLOR, foreground=TEXT_COLOR)
        style.configure("TRadiobutton", background=THEME_COLOR, foreground=TEXT_COLOR)
        
        # 强调按钮样式
        style.configure("Accent.TButton", background=ACCENT_COLOR, foreground=TEXT_COLOR)
        style.map("Accent.TButton",
                 background=[("active", HIGHLIGHT_COLOR), ("pressed", HIGHLIGHT_COLOR)])
        
        # 进度条样式
        style.configure("TProgressbar", 
                       troughcolor=SECONDARY_COLOR, 
                       background=ACCENT_COLOR,
                       lightcolor=ACCENT_COLOR,
                       darkcolor=ACCENT_COLOR)
        

    def create_widgets(self):
        """创建界面组件"""
        # 主容器
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        
        # 顶部控制面板
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 文件选择区域
        file_frame = ttk.Frame(control_frame)
        file_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.file_button = StyledButton(file_frame, text="选择视频", command=self.select_video)
        self.file_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.file_label = ttk.Label(file_frame, text="未选择文件")
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 播放控制按钮
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(side=tk.RIGHT)
        
        self.start_button = StyledButton(button_frame, text="▶ 播放", command=self.start_playback, state=tk.DISABLED)
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = StyledButton(button_frame, text="■ 停止", command=self.stop_playback, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
        
        # 参数设置区域
        settings_frame = ttk.LabelFrame(main_frame, text="播放设置", padding=(10, 5))
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 播放模式选择
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(mode_frame, text="播放模式:").pack(side=tk.LEFT)
        
        self.play_mode = tk.StringVar(value="gui")
        ttk.Radiobutton(mode_frame, text="窗口播放", variable=self.play_mode, value="gui").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Radiobutton(mode_frame, text="控制台播放", variable=self.play_mode, value="console").pack(side=tk.LEFT)
        
        # 参数设置
        param_frame = ttk.Frame(settings_frame)
        param_frame.pack(fill=tk.X)
        
        ttk.Label(param_frame, text="宽度(字符数):").grid(row=0, column=0, sticky="e", padx=(0, 5))
        self.cols_entry = ttk.Entry(param_frame, width=5)
        self.cols_entry.insert(0, "100")
        self.cols_entry.grid(row=0, column=1, sticky="w", padx=(0, 15))
        
        ttk.Label(param_frame, text="帧率(FPS):").grid(row=0, column=2, sticky="e", padx=(0, 5))
        self.fps_entry = ttk.Entry(param_frame, width=5)
        self.fps_entry.insert(0, "24")
        self.fps_entry.grid(row=0, column=3, sticky="w", padx=(0, 15))
        
        ttk.Label(param_frame, text="最大高度(像素):").grid(row=0, column=4, sticky="e", padx=(0, 5))
        self.max_height_entry = ttk.Entry(param_frame, width=5)
        self.max_height_entry.insert(0, "600")
        self.max_height_entry.grid(row=0, column=5, sticky="w")
        
        # 视频信息区域
        info_frame = ttk.LabelFrame(main_frame, text="视频信息", padding=(10, 5))
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_labels = {
            "filename": ttk.Label(info_frame, text="文件: -"),
            "resolution": ttk.Label(info_frame, text="分辨率: -"),
            "duration": ttk.Label(info_frame, text="时长: -"),
            "frames": ttk.Label(info_frame, text="总帧数: -")
        }
        
        for i, (_, label) in enumerate(self.info_labels.items()):
            label.grid(row=0, column=i, padx=10, sticky="w")
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100, style="TProgressbar")
        self.progress_bar.pack(fill=tk.X,pady=10)
        
        self.progress_label = ttk.Label(main_frame, text="准备就绪")
        self.progress_label.pack(fill=tk.X)
        
        # 显示区域
        display_frame = ttk.Frame(main_frame)
        display_frame.pack(fill=tk.BOTH, expand=True)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(display_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.text_widget = tk.Text(
            display_frame, 
            font=(self.font_family, self.font_size), 
            width=100, 
            height=30,
            yscrollcommand=scrollbar.set,
            bg=SECONDARY_COLOR,
            fg=TEXT_COLOR,
            insertbackground=TEXT_COLOR,
            selectbackground=ACCENT_COLOR
        )
        self.text_widget.pack(fill=tk.BOTH, expand=True)
        
        scrollbar.config(command=self.text_widget.yview)
    
    def select_video(self):
        """选择视频文件"""
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.avi *.mov *.mkv"), ("所有文件", "*.*")]
        )
        
        if file_path:
            self.video_path = file_path
            self.file_label.config(text=os.path.basename(file_path))
            self.start_button.config(state=tk.NORMAL)
            
            # 显示视频信息
            self.show_video_info(file_path)
    
    def show_video_info(self, file_path):
        """显示视频信息"""
        if self.ascii_converter is None:
            self.ascii_converter = VideoToASCII()
            
        
        self.ascii_converter.video_path = file_path
        video_info = self.ascii_converter.get_video_info()

        
        if video_info:
            self.info_labels["filename"].config(text=f"文件: {os.path.basename(file_path)}")
            self.info_labels["resolution"].config(text=f"分辨率: {video_info['width']}x{video_info['height']}")
            self.info_labels["duration"].config(text=f"时长: {video_info['duration']:.2f}秒")
            self.info_labels["frames"].config(text=f"总帧数: {video_info['frame_count']}")
    
    def start_playback(self):
        """开始播放"""
        if not hasattr(self, 'video_path') or not self.video_path:
            messagebox.showerror("错误", "请先选择视频文件")
            return
            
        try:
            cols = int(self.cols_entry.get())
            fps = int(self.fps_entry.get())
            max_height = int(self.max_height_entry.get())
            
            # 创建转换器实例
            self.ascii_converter = VideoToASCII(
                video_path=self.video_path,
                cols=cols,
                fps=fps,
                max_height=max_height
            )
            
            # 重置进度
            self.progress_var.set(0)
            self.progress_label.config(text="准备播放...")
            
            # 根据选择的模式播放
            mode = self.play_mode.get()
            if mode == "gui":
                self.play_in_gui()
            elif mode == "console":
                self.play_in_console()
            
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            
        except ValueError as e:
            messagebox.showerror("错误", f"参数错误: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"播放失败: {e}")
    
    def play_in_gui(self):
        """在GUI中播放"""
        self.ascii_converter.start_processing()
        self.update_gui_frame()
    
    def play_in_console(self):
        """在控制台中播放"""
        self.ascii_converter.start_processing()
        self.ascii_converter.start_console_playback()
        self.monitor_progress()
    
    def monitor_progress(self):
        """监控处理进度"""
        if not self.ascii_converter or not self.ascii_converter.running:
            return
        
        if self.ascii_converter.total_frames > 0:
            progress = (self.ascii_converter.processed_frames / self.ascii_converter.total_frames) * 100
            self.progress_var.set(progress)
            self.progress_label.config(
                text=f"处理中: {self.ascii_converter.processed_frames}/{self.ascii_converter.total_frames} 帧 "
                     f"({progress:.1f}%)"
            )
        
        self.after(500, self.monitor_progress)
    
    def update_gui_frame(self):
        """更新GUI中的帧"""
        if not self.ascii_converter or not self.ascii_converter.running:
            return
            
        try:
            ascii_frame = self.ascii_converter.frame_queue.get_nowait()
            if ascii_frame is None:  # 结束信号
                self.stop_playback()
                return
                
            self.text_widget.delete(1.0, tk.END)
            self.text_widget.insert(tk.END, ascii_frame)
            self.text_widget.see(tk.END)
            
            # 更新进度
            if self.ascii_converter.total_frames > 0:
                progress = (self.ascii_converter.processed_frames / self.ascii_converter.total_frames) * 100
                self.progress_var.set(progress)
                self.progress_label.config(
                    text=f"处理中: {self.ascii_converter.processed_frames}/{self.ascii_converter.total_frames} 帧 "
                         f"({progress:.1f}%)"
                )
        except:
            pass  # 队列为空
            
        self.after(50, self.update_gui_frame)
    
    def stop_playback(self):
        """停止播放"""
        if self.ascii_converter:
            self.ascii_converter.stop()
        
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_label.config(text="播放已停止")
    
    def on_closing(self):
        """窗口关闭事件处理"""
        self.stop_playback()
        self.destroy()

def main():
    app = ASCIIPlayerGUI()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()

if __name__ == "__main__":
    main()