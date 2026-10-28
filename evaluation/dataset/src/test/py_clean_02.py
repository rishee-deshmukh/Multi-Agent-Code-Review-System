import subprocess


def current_revision(repo_dir):
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True, timeout=10
    )
    return result.stdout.strip()


def changed_files(repo_dir, base):
    result = subprocess.run(
        ["git", "diff", "--name-only", base, "HEAD"], cwd=repo_dir, capture_output=True, text=True, check=True, timeout=10
    )
    return [line for line in result.stdout.splitlines() if line]
