from app_store_web_scraper import AppStoreEntry, AppStoreSession
session = AppStoreSession()
app = AppStoreEntry(app_id=1404871703, country="in", session=session)
first_review = next(app.reviews())
print(dir(first_review))
print("Dict:", first_review._asdict() if hasattr(first_review, "_asdict") else first_review.__dict__)
