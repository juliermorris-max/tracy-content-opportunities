"""Two UTC triggers, one Barcelona-local morning run, including DST changes."""
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

def should_run(event, schedule, now=None):
    if event != 'schedule': return True
    local=(now or datetime.now(timezone.utc)).astimezone(ZoneInfo('Europe/Madrid'))
    utc_hour=8-int(local.utcoffset().total_seconds()/3600)
    # Use nominal cron slot, not actual runner hour: GitHub can start late.
    return schedule == f'17 {utc_hour} * * *'

if __name__=='__main__':
    value='true' if should_run(os.environ.get('EVENT_NAME','workflow_dispatch'),os.environ.get('EVENT_SCHEDULE','')) else 'false'
    with open(os.environ['GITHUB_OUTPUT'],'a') as f: f.write(f'run={value}\n')
