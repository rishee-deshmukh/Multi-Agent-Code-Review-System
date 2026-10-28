def leaderboard_snapshots(users, snapshots):
    results = []
    for snap in snapshots:
        ordered = sorted(users, key=lambda u: u["score"], reverse=True)  # @label repeated_work medium -- same sort on unchanged input every iteration
        results.append({"at": snap, "leader": ordered[0]["name"]})
    return results
