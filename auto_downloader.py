import sys
import os
import time
import datetime
import importlib.util

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHECK_INTERVAL = 30


def load_youtube_downloader():
    module_path = os.path.join(BASE_DIR, "youtube_downloader.py")
    spec = importlib.util.spec_from_file_location("youtube_downloader", module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["youtube_downloader"] = module
    spec.loader.exec_module(module)
    return module


def get_target_time():
    print("=" * 60)
    print("AUTO DOWNLOADER SCHEDULER")
    print("=" * 60)
    print("Enter the time to run daily downloads (24-hour format)")
    print("Example: 02:30 for 2:30 AM, 14:00 for 2:00 PM")
    print()

    while True:
        time_input = input("Target time (HH:MM): ").strip()
        if not time_input:
            print("Please enter a time.")
            continue

        try:
            parts = time_input.split(":")
            if len(parts) != 2:
                raise ValueError

            hour = int(parts[0])
            minute = int(parts[1])

            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                print("Invalid time. Hour must be 0-23, minute 0-59.")
                continue

            return hour, minute

        except ValueError:
            print("Invalid format. Use HH:MM (e.g., 02:30)")


def should_run_now(target_hour, target_minute):
    now = datetime.datetime.now()
    target = now.replace(hour=target_hour, minute=target_minute, second=0, microsecond=0)
    return now >= target


def main():
    target_hour, target_minute = get_target_time()

    print()
    print("=" * 60)
    print(f"Scheduler configured: Daily at {target_hour:02d}:{target_minute:02d}")
    print(f"Checking every {CHECK_INTERVAL} seconds...")
    print("Press Ctrl+C to stop")
    print("=" * 60)
    print()

    last_ran_date = None
    yt_module = None

    while True:
        try:
            now = datetime.datetime.now()
            current_date = now.date()

            if should_run_now(target_hour, target_minute) and last_ran_date != current_date:
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Trigger time reached!")

                if yt_module is None:
                    print("Loading youtube_downloader module...")
                    yt_module = load_youtube_downloader()

                print("Starting auto download...")
                yt_module.run_download_all_noninteractive()

                last_ran_date = current_date
                print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Auto download completed.")
                print()

            time.sleep(CHECK_INTERVAL)

        except KeyboardInterrupt:
            print("\nScheduler stopped by user.")
            break
        except Exception as e:
            print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scheduler error: {e}")
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()