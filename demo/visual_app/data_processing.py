import pandas as pd
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time


file_path = "C:/keo/salesup/demo/final_schedule_data_with_metrics2.csv" 

# 데이터 전처리 함수
def preprocess_data(df):
    df['기록_날짜'] = pd.to_datetime(df['기록_날짜'])
    # 추가 전처리 작업 수행
    df['연도'] = df['기록_날짜'].dt.year
    df['월'] = df['기록_날짜'].dt.month
    # 필요에 따라 다른 전처리 추가

    return df

# 기본 데이터 로드 및 전처리 처리 함수
def load_data(file_path=file_path):
    try:
        data = pd.read_csv(file_path)
        print("Data loaded successfully.")
        # 전처리 함수 호출
        data = preprocess_data(data)
        return data
    except Exception as e:
        print(f"Error loading data: {e}")
        return None

# 파일 변경 이벤트 핸들러
class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, file_path, update_callback):
        super().__init__()
        self.file_path = file_path
        self.update_callback = update_callback

    def on_modified(self, event):
        if event.src_path == self.file_path:
            print(f"File {event.src_path} has been modified.")
            self.update_callback(self.file_path)

# 자동 업데이트 기능을 위한 메인 함수
def watch_file(file_path=file_path):
    event_handler = FileChangeHandler(file_path, load_data)
    observer = Observer()
    observer.schedule(event_handler, path=file_path, recursive=False)
    observer.start()
    print(f"Started watching {file_path}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    data = load_data()  # 전역 경로 사용
    watch_file()  # 전역 경로 사용