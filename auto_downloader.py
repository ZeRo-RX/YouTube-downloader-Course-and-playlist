import sys
import os
import time
import datetime
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TARGET_HOUR = 2
TARGET_MINUTE = 10
CHECK_INTERVAL = 30


def load_youtube_downloader():
    module_path = os.path.join(BASE_DIR, "youtube_downloader.py")
    spec = importlib.util.spec_from_file_location("youtube_downloader", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["youtube_downloader"] = module
    spec.loader.exec_module(module)
    return module


def should_run_now():
    now = datetime.datetime.now()
    return now.hour == TARGET_HOUR and now.minute == TARGET_MINUTE


def main():
    print("Auto Downloader Scheduler Started")
    print(f"Target time: {TARGET_HOUR:02d}:{TARGET_MINUTE:02d}")
    print(f"Checking every {CHECK_INTERVAL} seconds...")
    print("Press Ctrl+C to stop")
    print()

    last_ran_date = None

    while True:
        try:
            now = datetime.datetime.now()
            current_date = now.date()

            if should_run_now() and last_ran_date != current_date:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Trigger time reached!")
                print("Loading youtube_downloader module...")

                yt = load_youtube_downloader()

                print("Starting auto download...")
                yt.run_download_all_noninteractive()

                last_ran_date = current_date
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Auto download completed.")

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            break
        except Exception as e:
            print(f"Scheduler error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
