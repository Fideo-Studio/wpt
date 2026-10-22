# mypy: allow-untyped-defs

import json

import pytest

from tools.ci import check_test262_web_features
from tools.ci.check_test262_web_features import validate_manifest


def write_test262_tree(repo_root):
    test262_root = repo_root / "third_party" / "test262"
    (test262_root / "test").mkdir(parents=True)
    (test262_root / "test" / "a.js").write_text("")
    return test262_root


def test_validate_manifest(tmp_path):
    test262_root = write_test262_tree(tmp_path)
    manifest = {"version": 1, "data": {"array": ["test/a.js", "./test/a.js"]}}
    assert validate_manifest(manifest, str(test262_root)) == []


@pytest.mark.parametrize("manifest,expected", [
    ({"version": 2, "data": {}}, ["Expected a manifest object with version 1"]),
    ([], ["Expected a manifest object with version 1"]),
    ({"version": 1}, ["Expected data to map web-feature IDs to lists of test paths"]),
    ({"version": 1, "data": {"array": "test/a.js"}}, ["Expected a list of test paths for array"]),
    ({"version": 1, "data": {"array": ["test/b.js"]}}, ["array lists a missing test: test/b.js"]),
    ({"version": 1, "data": {"array": ["harness/a.js"]}}, ["array lists a missing test: harness/a.js"]),
])
def test_validate_manifest_errors(tmp_path, manifest, expected):
    test262_root = write_test262_tree(tmp_path)
    assert validate_manifest(manifest, str(test262_root)) == expected


def test_main(tmp_path, monkeypatch, capsys):
    write_test262_tree(tmp_path)
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps({"version": 1, "data": {"array": ["test/b.js"]}}))
    monkeypatch.setattr(check_test262_web_features, "wpt_root", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["check_test262_web_features.py", str(manifest_path)])

    assert check_test262_web_features.main() == 1
    assert capsys.readouterr().err == "array lists a missing test: test/b.js\n"
