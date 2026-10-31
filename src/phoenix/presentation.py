"""Human labels for saved aware timestamps; no evidence changes."""
from datetime import datetime,timedelta
from ledger import clock,LOCAL_TZ


def date_label(value,now=None):
    if value is None:return 'Not scheduled'
    date=datetime.fromisoformat(value).astimezone(LOCAL_TZ)
    today=(now or clock()).astimezone(LOCAL_TZ).date()
    day='Today' if date.date()==today else 'Tomorrow' if date.date()==today+timedelta(days=1) else date.strftime('%d %b')
    return day+', '+date.strftime('%I:%M %p').lstrip('0')+' · '+date.strftime('%d %b %Y')+' IST'
