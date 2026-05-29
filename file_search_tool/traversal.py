"""Recursive filesystem traversal."""

from __future__ import annotations

import stat
from pathlib import Path
from typing import Iterator

from file_search_tool.errors import TraversalError
from file_search_tool.models import FileEntry, SearchOptions, SearchStats
from file_search_tool.utils import is_hidden_relative, matches_any_pattern, relative_to_root


def _directory_identity(path: Path) -> tuple[int, int] | str:
    try:
        info = path.stat(follow_symlinks=True)
    except OSError:
        return str(path.resolve(strict=False))
    device = getattr(info, "st_dev", None)
    inode = getattr(info, "st_ino", None)
    if device is None or inode is None:
        return str(path.resolve(strict=False))
    return (device, inode)


def _record_access_error(
    path: Path,
    exc: OSError,
    stats: SearchStats | None,
    warnings: list[str] | None,
) -> None:
    if stats is not None:
        stats.permission_errors += 1
        stats.entries_skipped += 1
    if warnings is not None:
        warnings.append(f"cannot access: {path}: {exc}")


def _make_entry(
    path: Path,
    root: Path,
    depth: int,
    follow_symlinks: bool,
    stats: SearchStats | None = None,
    warnings: list[str] | None = None,
) -> FileEntry | None:
    try:
        info = path.stat(follow_symlinks=follow_symlinks)
    except OSError:
        try:
            info = path.lstat()
        except OSError as exc:
            _record_access_error(path, exc, stats, warnings)
            return None

    mode = info.st_mode
    is_symlink = path.is_symlink()
    is_dir = stat.S_ISDIR(mode)
    is_file = stat.S_ISREG(mode)
    relative = relative_to_root(path, root)
    size = info.st_size if is_file else None
    return FileEntry(
        path=path,
        root=root,
        relative_path=relative,
        is_file=is_file,
        is_dir=is_dir,
        is_symlink=is_symlink,
        size=size,
        mtime=info.st_mtime,
        depth=depth,
    )


def walk(
    root: Path,
    options: SearchOptions,
    stats: SearchStats | None = None,
    warnings: list[str] | None = None,
) -> Iterator[FileEntry]:
    """Walk a filesystem tree recursively without using os.walk."""

    root = Path(root).expanduser()
    if not root.exists():
        raise TraversalError(f"root path does not exist: {root}")

    resolved_root = root.resolve(strict=False)
    visited_dirs: set[tuple[int, int] | str] = set()

    def should_skip(path: Path, relative: Path, is_root: bool) -> bool:
        if is_root:
            return False
        if not options.include_hidden and is_hidden_relative(relative):
            if stats is not None:
                stats.entries_skipped += 1
            return True
        if matches_any_pattern(
            path.name,
            relative,
            options.exclude_patterns,
            case_sensitive=options.case_sensitive,
        ):
            if stats is not None:
                stats.entries_skipped += 1
            return True
        return False

    def recurse(path: Path, depth: int, is_root: bool = False) -> Iterator[FileEntry]:
        relative = relative_to_root(path, resolved_root)
        if should_skip(path, relative, is_root):
            return

        entry = _make_entry(path, resolved_root, depth, options.follow_symlinks, stats, warnings)
        if entry is None:
            return

        if entry.is_dir and options.follow_symlinks:
            identity = _directory_identity(path)
            if identity in visited_dirs:
                if stats is not None:
                    stats.symlink_cycles_skipped += 1
                    stats.entries_skipped += 1
                if warnings is not None:
                    warnings.append(f"symlink cycle skipped: {path}")
                return
            visited_dirs.add(identity)

        if entry.is_dir:
            if stats is not None:
                stats.dirs_scanned += 1
        elif entry.is_file:
            if stats is not None:
                stats.files_scanned += 1

        yield entry

        if not entry.is_dir:
            return
        if entry.is_symlink and not options.follow_symlinks:
            return
        if options.max_depth is not None and depth >= options.max_depth:
            return

        try:
            children = sorted(path.iterdir(), key=lambda child: child.name.casefold())
        except PermissionError:
            if stats is not None:
                stats.permission_errors += 1
                stats.entries_skipped += 1
            if warnings is not None:
                warnings.append(f"permission denied: {path}")
            return
        except OSError as exc:
            if stats is not None:
                stats.permission_errors += 1
                stats.entries_skipped += 1
            if warnings is not None:
                warnings.append(f"cannot read directory: {path}: {exc}")
            return

        for child in children:
            yield from recurse(child, depth + 1)

    yield from recurse(resolved_root, 0, is_root=True)
