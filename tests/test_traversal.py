"""Test the traversal."""

from pathlib import Path

from file_search_tool.models import SearchOptions, SearchStats
from file_search_tool.traversal import walk


def names(entries):
    return [entry.relative_path.as_posix() for entry in entries]


def test_recursive_traversal_finds_nested_files(tmp_path: Path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("print('hi')", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions()))

    assert "src" in names(entries)
    assert "src/app.py" in names(entries)


def test_max_depth_stops_descent_but_keeps_entry_at_depth(tmp_path: Path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "b" / "deep.txt").write_text("deep", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions(max_depth=1)))

    assert "a" in names(entries)
    assert "a/b" not in names(entries)


def test_hidden_files_are_skipped_by_default(tmp_path: Path):
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("ok", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions()))

    assert ".env" not in names(entries)
    assert "visible.txt" in names(entries)


def test_all_includes_hidden_files(tmp_path: Path):
    (tmp_path / ".env").write_text("secret", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions(include_hidden=True)))

    assert ".env" in names(entries)


def test_exclude_skips_directory_before_descent(tmp_path: Path):
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "package.json").write_text("{}", encoding="utf-8")
    stats = SearchStats()

    entries = list(walk(tmp_path, SearchOptions(exclude_patterns=["node_modules"]), stats))

    assert "node_modules" not in names(entries)
    assert "node_modules/package.json" not in names(entries)
    assert stats.entries_skipped >= 1


def test_traversal_order_is_deterministic(tmp_path: Path):
    (tmp_path / "b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")

    entries = [entry.relative_path.as_posix() for entry in walk(tmp_path, SearchOptions())]

    assert entries[:3] == [".", "a.txt", "b.txt"]


def test_root_file_yields_single_entry(tmp_path: Path):
    target = tmp_path / "solo.txt"
    target.write_text("solo", encoding="utf-8")

    entries = list(walk(target, SearchOptions()))

    assert len(entries) == 1
    assert entries[0].relative_path.as_posix() == "."
    assert entries[0].is_file


def test_max_depth_zero_yields_root_only(tmp_path: Path):
    (tmp_path / "child.txt").write_text("child", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions(max_depth=0)))

    assert names(entries) == ["."]


def test_permission_denied_on_iterdir_is_recorded(tmp_path: Path, monkeypatch):
    (tmp_path / "locked").mkdir()
    real_iterdir = Path.iterdir

    def fake_iterdir(self):
        if self.name == "locked":
            raise PermissionError("denied")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    stats = SearchStats()
    warnings: list[str] = []

    entries = list(walk(tmp_path, SearchOptions(), stats, warnings))

    assert "locked" in names(entries)
    assert stats.permission_errors >= 1
    assert any("permission denied" in warning for warning in warnings)


def test_os_error_on_iterdir_is_recorded(tmp_path: Path, monkeypatch):
    (tmp_path / "broken").mkdir()
    real_iterdir = Path.iterdir

    def fake_iterdir(self):
        if self.name == "broken":
            raise OSError("boom")
        return real_iterdir(self)

    monkeypatch.setattr(Path, "iterdir", fake_iterdir)
    stats = SearchStats()
    warnings: list[str] = []

    list(walk(tmp_path, SearchOptions(), stats, warnings))

    assert stats.permission_errors >= 1
    assert any("cannot read directory" in warning for warning in warnings)


def test_stat_failure_falls_back_to_lstat(tmp_path: Path, monkeypatch):
    target = tmp_path / "weird.txt"
    target.write_text("x", encoding="utf-8")
    real_stat = Path.stat

    def fake_stat(self, *args, **kwargs):
        if self.name == "weird.txt":
            raise OSError("stat blocked")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    entries = list(walk(tmp_path, SearchOptions()))

    assert "weird.txt" in names(entries)


def test_unreadable_entry_is_skipped(tmp_path: Path, monkeypatch):
    target = tmp_path / "ghost.txt"
    target.write_text("x", encoding="utf-8")
    real_stat = Path.stat
    real_lstat = Path.lstat

    def fake_stat(self, *args, **kwargs):
        if self.name == "ghost.txt":
            raise OSError("no stat")
        return real_stat(self, *args, **kwargs)

    def fake_lstat(self, *args, **kwargs):
        if self.name == "ghost.txt":
            raise OSError("no lstat")
        return real_lstat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)
    monkeypatch.setattr(Path, "lstat", fake_lstat)
    stats = SearchStats()
    warnings: list[str] = []

    entries = list(walk(tmp_path, SearchOptions(), stats, warnings))

    assert "ghost.txt" not in names(entries)
    assert stats.permission_errors >= 1
    assert any("cannot access" in warning for warning in warnings)


def test_directory_identity_falls_back_when_stat_fails(tmp_path: Path, monkeypatch):
    from file_search_tool.traversal import _directory_identity

    target = tmp_path / "dir"
    target.mkdir()
    real_stat = Path.stat

    def fake_stat(self, *args, **kwargs):
        if self == target:
            raise OSError("stat failed")
        return real_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", fake_stat)

    identity = _directory_identity(target)

    assert isinstance(identity, str)
    assert str(target.resolve()) in identity or target.name in identity


def test_directory_identity_falls_back_without_device_or_inode(tmp_path: Path, monkeypatch):
    from file_search_tool.traversal import _directory_identity
    from types import SimpleNamespace

    target = tmp_path / "dir"
    target.mkdir()

    def fake_stat(self, *args, **kwargs):
        return SimpleNamespace(st_mode=0o40755, st_size=0, st_mtime=0.0, st_dev=None, st_ino=None)

    monkeypatch.setattr(Path, "stat", fake_stat)

    identity = _directory_identity(target)

    assert isinstance(identity, str)


def test_hidden_files_increment_skip_stats(tmp_path: Path):
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    stats = SearchStats()

    list(walk(tmp_path, SearchOptions(), stats))

    assert stats.entries_skipped >= 1


def test_symlink_directory_is_not_descended_without_follow(tmp_path: Path, monkeypatch):
    link = tmp_path / "link"
    link.mkdir()
    (link / "inside.txt").write_text("x", encoding="utf-8")
    real_is_symlink = Path.is_symlink

    def fake_is_symlink(self: Path) -> bool:
        if self == link:
            return True
        return real_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", fake_is_symlink)

    entries = list(walk(tmp_path, SearchOptions(follow_symlinks=False)))

    assert "link" in names(entries)
    assert "link/inside.txt" not in names(entries)


def test_hidden_nested_file_is_skipped(tmp_path: Path):
    (tmp_path / "visible").mkdir()
    (tmp_path / "visible" / ".secret").write_text("x", encoding="utf-8")
    (tmp_path / "visible" / "open.txt").write_text("x", encoding="utf-8")

    entries = list(walk(tmp_path, SearchOptions()))

    assert "visible/open.txt" in names(entries)
    assert "visible/.secret" not in names(entries)


def test_duplicate_directory_identity_skips_revisit(tmp_path: Path, monkeypatch):
    from file_search_tool import traversal as traversal_module

    shared = (42, 42)
    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "child").mkdir()
    (tmp_path / "a" / "child" / "leaf.txt").write_text("x", encoding="utf-8")

    original = traversal_module._directory_identity

    def fake_identity(path: Path):
        if path.name in {"a", "child"}:
            return shared
        return original(path)

    monkeypatch.setattr(traversal_module, "_directory_identity", fake_identity)
    stats = SearchStats()
    warnings: list[str] = []

    entries = list(walk(tmp_path, SearchOptions(follow_symlinks=True), stats, warnings))

    assert names(entries) == [".", "a"]
    assert stats.symlink_cycles_skipped >= 1
    assert any("symlink cycle skipped" in warning for warning in warnings)

