# mypy: allow-untyped-defs

import json

import pytest

from tools.ci import test262_web_features
from tools.ci.test262_web_features import normalize_manifest, validate_manifest


def write_test262_tree(repo_root):
    test262_root = repo_root / "third_party" / "test262"
    (test262_root / "test").mkdir(parents=True)
    (test262_root / "test" / "a.js").write_text("")
    (test262_root / "test" / "b.js").write_text("")
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
    ({"version": 1, "data": {"array": ["test/c.js"]}}, ["array lists a missing test: test/c.js"]),
    ({"version": 1, "data": {"array": ["harness/a.js"]}}, ["array lists a missing test: harness/a.js"]),
])
def test_validate_manifest_errors(tmp_path, manifest, expected):
    test262_root = write_test262_tree(tmp_path)
    assert validate_manifest(manifest, str(test262_root)) == expected


def test_normalize_manifest():
    manifest = {"version": 1, "data": {"array": ["test/b.js", "./test/a.js", "test/a.js"]}}
    assert normalize_manifest(manifest) == {"version": 1, "data": {"array": ["test/a.js", "test/b.js"]}}


def run_main(tmp_path, monkeypatch, manifest):
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(test262_web_features, "wpt_root", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["test262_web_features.py", str(manifest_path)])
    return test262_web_features.main(), manifest_path.read_text()


def test_main(tmp_path, monkeypatch):
    write_test262_tree(tmp_path)
    first = run_main(tmp_path, monkeypatch, {"version": 1, "data": {
        "javascript": ["test/b.js", "./test/a.js"], "array": ["test/a.js"]}})
    second = run_main(tmp_path, monkeypatch, {"version": 1, "data": {
        "array": ["./test/a.js"], "javascript": ["test/a.js", "test/b.js"]}})

    assert first == second == (0, (
        '{\n'
        '  "data": {\n'
        '    "array": [\n'
        '      "test/a.js"\n'
        '    ],\n'
        '    "javascript": [\n'
        '      "test/a.js",\n'
        '      "test/b.js"\n'
        '    ]\n'
        '  },\n'
        '  "version": 1\n'
        '}\n'))


def test_main_invalid(tmp_path, monkeypatch, capsys):
    write_test262_tree(tmp_path)
    manifest = {"version": 1, "data": {"array": ["test/c.js"]}}

    assert run_main(tmp_path, monkeypatch, manifest) == (1, json.dumps(manifest))
    assert capsys.readouterr().err == "array lists a missing test: test/c.js\n"
