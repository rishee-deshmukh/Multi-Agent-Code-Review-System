import os
import tarfile


def import_backup(archive_path, dest):
    os.makedirs(dest, exist_ok=True)
    with tarfile.open(archive_path) as tar:
        names = tar.getnames()
        tar.extractall(dest)  # @label path_traversal high -- members may be absolute or contain ../ and are written outside dest
    return sorted(names)


def backup_size(archive_path):
    return os.path.getsize(archive_path)
