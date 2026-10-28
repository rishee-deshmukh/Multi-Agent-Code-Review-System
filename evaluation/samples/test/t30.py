def leaderboard_snapshots(users, snapshots):
    results = []
    for snap in snapshots:
        ordered = sorted(users, key=lambda u: u["score"], reverse=True)
        results.append({"at": snap, "leader": ordered[0]["name"]})
    return results
