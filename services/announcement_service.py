from app.extensions import client
from app.config import Config

def get_announcements():
    if Config.ISTEST_MODE:
        return []
    
    announcements = list(client.ht_server.announcement.find({}))
    for a in announcements:
        a.pop('_id', None)
    return announcements
