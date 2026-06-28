import configparser
import time
from watchdog.events import FileSystemEventHandler

class AxelChatHandler(FileSystemEventHandler):
    def __init__(self, queue, loop):
        self.queue = queue
        self.loop = loop
        self.last_idx = -1

    def on_modified(self, event):
        if event.src_path.endswith("messages.ini"):
            self.process_file(event.src_path)

    def process_file(self, path):
        config = configparser.ConfigParser()
        try: config.read(path, encoding='utf-8')
        except: config.read(path, encoding='cp1251')

        for section in config.sections():
            try:
                idx = int(section)
                if idx > self.last_idx:
                    self.last_idx = idx
                    data = {
                        'author': config.get(section, 'author', fallback='Anon'),
                        'message': config.get(section, 'message', fallback=''),
                        'service': config.get(section, 'service', fallback='unknown')
                    }
                    priority = 1 if "донат" in data['message'].lower() else 2 if "векса" in data['message'].lower() else 3
                    
                    self.loop.call_soon_threadsafe(
                        self.queue.put_nowait, (priority, time.time(), data)
                    )
            except: continue
