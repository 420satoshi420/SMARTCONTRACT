import json, pathlib
from datetime import datetime

RESULTS_DIR = pathlib.Path("../results")
LEADERBOARD_FILE = RESULTS_DIR / "leaderboard.json"

def update_leaderboard(f):
    if not LEADERBOARD_FILE.exists():
        data = {"goal_usd": 2088, "total_potential_usd": 0, "findings": [], "goal_hit": False}
    else:
        try:
            data = json.loads(LEADERBOARD_FILE.read_text())
        except Exception:
            data = {"goal_usd": 2088, "total_potential_usd": 0, "findings": [], "goal_hit": False}
            
    data['findings'].append({
        "date": datetime.now().isoformat(),
        "repo": f.get('repo'),
        "bounty_estimate": f.get('bounty_estimate', 0),
        "confidence": f.get('confidence', 0),
        "score": f.get('score', 0)
    })
    total = sum([x.get('bounty_estimate', 0) for x in data['findings']])
    data['total_potential_usd'] = total
    data['goal_progress_percent'] = min(100, int((total / 2088) * 100))
    data['goal_hit'] = total >= 2088
    LEADERBOARD_FILE.write_text(json.dumps(data, indent=2))
    return data

def get_leaderboard():
    if not LEADERBOARD_FILE.exists():
        return {"goal_usd": 2088, "total_potential_usd": 0, "goal_progress_percent": 0, "findings": []}
    try:
        return json.loads(LEADERBOARD_FILE.read_text())
    except Exception:
        return {"goal_usd": 2088, "total_potential_usd": 0, "goal_progress_percent": 0, "findings": []}
