import acoustid
import os

API_KEY = os.getenv("ACOUSTID_API_KEY")

file_path = "/mnt/work_area/STT_work/Victory Heat Rally- OST/'27 - RoBKTA - Galactic Rest Stop.mp3'"

for score, recording_id, title, artist in acoustid.match(API_KEY, file_path):
    print("Score:", score)
    print("Title:", title)
    print("Artist:", artist)
    print("Recording ID:", recording_id)
    print("-" * 40)
