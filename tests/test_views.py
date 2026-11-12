"""Views: pages a provider draws from data, shown in the shell beside the documents (views.py)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import found, folio

from folio.errors import FolioError
from folio.site.site import Site, export

PROVIDER = '''
from folio.views import View

class Demo:
    prefix, title, home = "demo", "Demo", True
    def __init__(self, root): self.root = root
    def get(self, path):
        pages = {"": "Front", "one": "Page one"}
        if path not in pages:
            return None
        return View(title=pages[path], main='<p>drawn from data</p><a href="/demo/">front</a> <a href="/content/">library</a>', description="A view.", genre="view", status="open",
                    head="<style>.x{}</style>", panels=[("Needs", "<ul><li>nothing</li></ul>")], path="data/one.md")
    def rail(self): return [{"title": "Front", "url": "/demo/"}, {"title": "Group", "url": "/demo/one/", "status": "open", "items": []}]
    def search(self): return [{"id": "", "genre": "view", "part": None, "path": "demo/one", "url": "/demo/one/", "title": "Page one",
                               "description": "", "tags": [], "status": "open", "text": "drawn from data"}]
    def paths(self): return ["", "one"]
    def stamp(self): return "1"
    def backlinks(self): return {"content/concepts/softmax/index.html": [{"title": "Page one", "url": "/demo/one/", "status": "open"}]}

def provider(root):
    return Demo(root)
'''


@pytest.fixture
def with_views(sample: Path, tmp_path: Path, monkeypatch) -> Path:
    mods = tmp_path / "mods"
    mods.mkdir()
    (mods / "demoviews.py").write_text(PROVIDER)
    monkeypatch.syspath_prepend(str(mods))
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + "views: [demoviews]\n")
    return sample


def test_a_view_is_served_in_the_shell(with_views: Path) -> None:
    site = Site.load(with_views)
    page = site.get("demo/one/").body.decode()
    assert '<meta name="title" content="Page one">' in page and '<meta name="genre" content="view">' in page
    assert '<meta name="folio-source" content="demo/one">' in page and "/shell/folio.js" in page
    assert '<meta name="folio-path" content="data/one.md">' in page  # the header's copy-path control reads it
    assert "<p>drawn from data</p>" in page and '<section data-folio-panel="Needs">' in page and "<style>.x{}</style>" in page
    assert site.get("demo/one") is not None and site.get("demo/one/index.html") is not None
    assert site.get("demo/missing/") is None
    # A provider that asks for the front page gets it.
    assert "url=/demo/" in site.get("").body.decode()


def test_views_reach_the_rail_the_search_and_the_documents_they_point_at(with_views: Path) -> None:
    site = Site.load(with_views)
    views = site.site_data()["views"]
    assert views[0]["prefix"] == "demo" and views[0]["home"] is True and views[0]["rail"][1]["items"] == []
    assert views[0]["backlinks"]["content/concepts/softmax/index.html"][0]["url"] == "/demo/one/"
    entries = json.loads(site.get(".folio/search.json").body)
    assert any(e["url"] == "/demo/one/" for e in entries) and any(e["genre"] == "concept" for e in entries)


def test_a_link_from_a_document_to_a_view_resolves(with_views: Path, monkeypatch, capsys) -> None:
    note = with_views / "content/concepts/softmax/index.html"
    note.write_text(note.read_text().replace("</main>", '<p>See <a href="/demo/one/">the view</a> and <a href="/demo/nope/">a hole</a>.</p></main>'))
    folio(with_views, "check", monkeypatch=monkeypatch)
    out = capsys.readouterr().out
    assert "`/demo/nope/` resolves to nothing" in out and "`/demo/one/` resolves" not in out


def test_views_are_exported(with_views: Path, tmp_path: Path) -> None:
    written = export(with_views, tmp_path / "site")
    assert "demo/index.html" in written and "demo/one/index.html" in written
    assert "drawn from data" in (tmp_path / "site/demo/one/index.html").read_text()


def test_a_provider_that_cannot_be_loaded_is_named(sample: Path) -> None:
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + "views: [no_such_module_here]\n")
    with pytest.raises(FolioError, match="no_such_module_here"):
        Site.load(sample)


def test_a_repository_with_no_commit_yet_has_no_dates(tmp_path) -> None:
    import subprocess

    from folio.site import dates

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "page.html").write_text("x")
    assert dates.from_git(tmp_path) == {}


def _provider(tmp_path: Path, monkeypatch, sample: Path, name: str, body: str, where: Path | None = None) -> Path:
    """A library whose charter names one provider module, written outside the library unless `where` says."""
    mods = where or tmp_path / "mods"
    mods.mkdir(exist_ok=True)
    (mods / f"{name}.py").write_text(body)
    monkeypatch.syspath_prepend(str(mods))
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + f"views: [{name}]\n")
    return sample


def _simple(prefix: str = "p", extra: str = "", home: bool = False) -> str:
    return f'''
from folio.views import View
class P:
    prefix, title, home = {prefix!r}, "P", {home!r}
    calls = 0
    def get(self, path): return View(title="T", main="<p>x</p>") if path == "" else None
    def rail(self): return [{{"title": "T", "url": "/p/"}}]
    def search(self): return []
    def paths(self): return [""]
    def stamp(self): return "1"
    def backlinks(self): return {{}}
{extra}
def provider(root): return P()
'''


def test_a_view_takes_the_base_like_a_document(with_views: Path, tmp_path: Path) -> None:
    page = Site.load(with_views, base="/sub/").get("demo/one/").body.decode()
    assert 'href="/sub/shell/folio.css"' in page and 'src="/sub/shell/folio.js"' in page
    assert 'href="/sub/demo/"' in page and 'href="/sub/content/"' in page
    assert 'href="/shell/' not in page and 'href="/demo/' not in page
    export(with_views, tmp_path / "site", base="/sub/")
    written = (tmp_path / "site/demo/one/index.html").read_text()
    assert 'href="/sub/shell/folio.css"' in written and 'href="/sub/demo/"' in written and 'href="/sub/content/"' in written
    # At the root nothing is added.
    assert 'href="/shell/folio.css"' in Site.load(with_views).get("demo/one/").body.decode()


def test_a_view_without_its_closing_slash_redirects(with_views: Path) -> None:
    got = Site.load(with_views, base="/sub/").get("demo/one")
    assert got.status == 301 and got.location == "/sub/demo/one/"
    assert Site.load(with_views).get("demo").location == "/demo/"
    assert Site.load(with_views).get("demo/missing") is None


def test_export_counts_views_as_pages(with_views: Path, tmp_path: Path) -> None:
    from folio.site.site import export_site

    written, pages = export_site(with_views, tmp_path / "site")
    assert "demo/index.html" in pages and "demo/one/index.html" in pages


def test_a_library_cannot_bring_its_own_provider(sample: Path, tmp_path: Path, monkeypatch) -> None:
    _provider(tmp_path, monkeypatch, sample, "libview_inside", "raise SystemExit('the library ran code')\n", where=sample)
    with pytest.raises(FolioError, match="libview_inside.*inside the library"):
        Site.load(sample)
    assert "libview_inside" not in sys.modules  # refused before it is imported
    assert "inside the library" in found(sample, "views")[0].message


def test_the_repository_that_holds_the_library_cannot_bring_one_either(sample: Path, tmp_path: Path, monkeypatch) -> None:
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    lib = repo / "docs"
    sample.rename(lib)
    _provider(tmp_path, monkeypatch, lib, "libview_in_repo", _simple(), where=repo / "tools")
    with pytest.raises(FolioError, match="libview_in_repo.*inside the repository"):
        Site.load(lib)
    assert "libview_in_repo" not in sys.modules


def test_python_m_folio_does_not_import_from_the_folder_it_runs_in(sample: Path) -> None:
    import folio as package

    (sample / "libview_cwd.py").write_text("raise SystemExit('the library ran code')\n")
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + "views: [libview_cwd]\n")
    env = dict(os.environ, PYTHONPATH=str(Path(package.__file__).resolve().parents[1]))
    env.pop("PYTHONSAFEPATH", None)
    done = subprocess.run([sys.executable, "-m", "folio", "check"], cwd=sample, env=env, capture_output=True, text=True)
    out = done.stdout + done.stderr
    assert "the library ran code" not in out and done.returncode != 0
    assert "libview_cwd" in out and "not installed" in out, out


def test_check_reports_a_provider_that_is_not_installed(sample: Path, monkeypatch, capsys) -> None:
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + "views: [no_such_module_here.site]\n")
    problems = found(sample, "views")
    assert len(problems) == 1 and problems[0].path == "folio.yaml"
    assert "no_such_module_here.site" in problems[0].message and "not installed" in problems[0].message
    assert folio(sample, "check", monkeypatch=monkeypatch) != 0
    out = capsys.readouterr()
    assert "not installed" in out.out and "Traceback" not in out.out + out.err


def test_check_passes_a_provider_that_loads(with_views: Path) -> None:
    assert found(with_views, "views") == []


@pytest.mark.parametrize("name, body, message", [
    ("pv_import_fails", "1 / 0\n", "pv_import_fails.*cannot be imported.*ZeroDivisionError"),
    ("pv_needs_other", "import no_such_dependency_here\n", "pv_needs_other.*cannot be imported.*no_such_dependency_here"),
    ("pv_no_provider", "x = 1\n", "pv_no_provider.*has no `provider"),
    ("pv_provider_fails", "def provider(root): raise RuntimeError('no data')\n", "pv_provider_fails.*failed.*no data"),
    ("pv_no_prefix", "def provider(root): return object()\n", "pv_no_prefix.*has no `prefix`"),
])
def test_a_provider_that_does_not_load_is_named(sample, tmp_path, monkeypatch, name, body, message) -> None:
    _provider(tmp_path, monkeypatch, sample, name, body)
    with pytest.raises(FolioError, match=message):
        Site.load(sample)
    assert found(sample, "views")


@pytest.mark.parametrize("prefix, message", [
    ("", "empty prefix"),
    ("a/b", "holds a `/`.*exactly one path segment"),
    ("index.html", "a path folio serves itself"),
    ("content", "a path folio serves itself"),
    (".folio", "a path folio serves itself"),
    ("..", "starts with a letter or a digit"),
    ("a b", "holds only letters"),
])
def test_a_prefix_is_one_plain_path_segment(sample, tmp_path, monkeypatch, prefix, message) -> None:
    name = "pv_prefix_" + prefix.encode().hex()  # a module name of its own: an imported module stays imported
    _provider(tmp_path, monkeypatch, sample, name, _simple(prefix))
    with pytest.raises(FolioError, match=f"{name}.*{message}"):
        Site.load(sample)


def test_two_providers_cannot_share_a_prefix_or_the_front_page(sample, tmp_path, monkeypatch) -> None:
    mods = tmp_path / "mods"
    mods.mkdir()
    monkeypatch.syspath_prepend(str(mods))
    for name, prefix in (("pv_two_a", "same"), ("pv_two_b", "same"), ("pv_two_c", "c"), ("pv_two_d", "d")):
        (mods / f"{name}.py").write_text(_simple(prefix, home=name in ("pv_two_c", "pv_two_d")))
    charter = sample / "folio.yaml"
    before = charter.read_text()
    charter.write_text(before + "views: [pv_two_a, pv_two_b]\n")
    with pytest.raises(FolioError, match="`pv_two_a` and `pv_two_b` both take the prefix `same`"):
        Site.load(sample)
    charter.write_text(before + "views: [pv_two_c, pv_two_d]\n")
    with pytest.raises(FolioError, match="`pv_two_c`, `pv_two_d` each ask for the site's front page"):
        Site.load(sample)


FAILS = '''
    def get(self, path): raise RuntimeError("the data is broken")
    def rail(self): raise RuntimeError("no rail")
    def search(self): raise RuntimeError("no search")
    def backlinks(self): raise RuntimeError("no backlinks")
    def paths(self): raise RuntimeError("no paths")
'''


def test_a_view_that_raises_is_a_500_and_the_site_stands(sample, tmp_path, monkeypatch, capsys) -> None:
    _provider(tmp_path, monkeypatch, sample, "pv_get_fails", _simple(extra=FAILS))
    site = Site.load(sample, base="/sub/", live=True)
    got = site.get("p/")
    assert got.status == 500 and "This view failed" in got.body.decode() and "/sub/shell/folio.css" in got.body.decode()
    assert "the data is broken" not in got.body.decode()  # the traceback is for the log, not the reader
    err = capsys.readouterr().err
    assert "pv_get_fails" in err and "Traceback" in err and "the data is broken" in err
    assert site.get("content/concepts/softmax/").status == 200
    # The rail, the search and the backlinks of a provider that fails are empty, and logged.
    assert site.site_data()["views"][0]["rail"] == [] and site.site_data()["views"][0]["backlinks"] == {}
    assert any(e["genre"] == "concept" for e in json.loads(site.get(".folio/search.json").body))
    assert site.view_paths() == []
    err = capsys.readouterr().err
    assert "rail()" in err and "search()" in err and "backlinks()" in err and "paths()" in err


def test_the_server_answers_500_for_a_view_that_raises_and_asks_again(sample, tmp_path, monkeypatch) -> None:
    from folio.site.serve import LiveSite

    _provider(tmp_path, monkeypatch, sample, "pv_live_fails", _simple(extra='''
    def get(self, path):
        P.calls += 1
        if P.calls == 1:
            raise RuntimeError("once")
        return View(title="T", main="<p>back</p>")
'''))
    live = LiveSite(sample)
    assert live.get("p/")[0].status == 500
    assert live.get("p/")[0].status == 200  # a failure is not kept


def test_an_export_stops_when_a_provider_fails(sample, tmp_path, monkeypatch) -> None:
    _provider(tmp_path, monkeypatch, sample, "pv_export_fails", _simple(extra=FAILS))
    with pytest.raises(FolioError, match="pv_export_fails.*failed in"):
        export(sample, tmp_path / "site")


def test_a_stamp_that_raises_keeps_the_last_one(sample, tmp_path, monkeypatch, capsys) -> None:
    from folio.site.serve import LiveSite

    _provider(tmp_path, monkeypatch, sample, "pv_stamp_fails", _simple(extra='''
    def stamp(self):
        P.calls += 1
        if P.calls > 2:
            raise RuntimeError("the store is away")
        return "s1"
'''))
    live = LiveSite(sample)
    site = live.current()
    provider = site.views[0]
    assert provider.stamp() == "s1"
    before = live.stamp()
    assert provider.stamp() == "s1" and live.stamp() == before  # it raises now: the last stamp stands
    assert "the store is away" in capsys.readouterr().err
    assert live.current() is site and live.get("content/concepts/softmax/")[0].status == 200


def test_a_library_under_the_pythons_prefix_still_cannot_bring_a_provider(sample, tmp_path, monkeypatch) -> None:
    # A venv made at the repository's root, or a system Python whose prefix is above the library.
    for name in ("prefix", "base_prefix", "exec_prefix"):
        monkeypatch.setattr(sys, name, str(tmp_path))
    _provider(tmp_path, monkeypatch, sample, "libview_under_prefix", "raise SystemExit('the library ran code')\n", where=sample)
    with pytest.raises(FolioError, match="libview_under_prefix.*inside the library"):
        Site.load(sample)
    assert "libview_under_prefix" not in sys.modules


def test_a_provider_installed_in_an_environment_kept_in_the_repository_loads(sample, tmp_path, monkeypatch) -> None:
    import sysconfig

    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    lib = repo / "docs"
    sample.rename(lib)
    packages = repo / ".venv/lib/site-packages"
    packages.mkdir(parents=True)
    real = sysconfig.get_paths()
    monkeypatch.setattr(sysconfig, "get_paths", lambda *a, **k: {**real, "purelib": str(packages), "platlib": str(packages)})
    _provider(tmp_path, monkeypatch, lib, "pv_in_site_packages", _simple(), where=packages)
    assert Site.load(lib).views[0].prefix == "p"
    # A link from there into the repository is where the code really is: refused.
    (repo / "tools").mkdir()
    (repo / "tools/impl.py").write_text("raise SystemExit('the library ran code')\n")
    (packages / "pv_linked_out.py").symlink_to(repo / "tools/impl.py")
    charter = lib / "folio.yaml"
    charter.write_text(charter.read_text().replace("views: [pv_in_site_packages]", "views: [pv_linked_out]"))
    with pytest.raises(FolioError, match="pv_linked_out.*inside the repository"):
        Site.load(lib)


def test_a_module_of_an_outside_package_that_is_really_in_the_library_is_refused(sample, tmp_path, monkeypatch) -> None:
    package = tmp_path / "mods" / "pk_outside"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (sample / "impl.py").write_text("raise SystemExit('the library ran code')\n")
    (package / "prov.py").symlink_to(sample / "impl.py")
    monkeypatch.syspath_prepend(str(tmp_path / "mods"))
    charter = sample / "folio.yaml"
    charter.write_text(charter.read_text() + "views: [pk_outside.prov]\n")
    with pytest.raises(FolioError, match=r"pk_outside\.prov.*inside the library"):
        Site.load(sample)
    assert "pk_outside.prov" not in sys.modules  # refused before any of its code ran
    charter.write_text(charter.read_text().replace("pk_outside.prov", "pk_outside.absent"))
    with pytest.raises(FolioError, match=r"pk_outside\.absent.*not installed"):
        Site.load(sample)


def test_folio_up_does_not_run_a_folio_package_the_library_holds(sample, tmp_path, monkeypatch) -> None:
    import urllib.request

    import folio as package
    from folio.site import serve

    ran = tmp_path / "the-library-ran-code"
    (sample / "folio").mkdir()
    (sample / "folio/__init__.py").write_text(f"open({str(ran)!r}, 'w').write('x')\nraise SystemExit('hostile')\n")
    (sample / "yaml.py").write_text(f"open({str(ran)!r}, 'w').write('x')\nraise SystemExit('hostile')\n")
    monkeypatch.setenv("PYTHONPATH", str(Path(package.__file__).resolve().parents[1]))
    monkeypatch.delenv("PYTHONSAFEPATH", raising=False)
    try:
        assert "serving" in serve.up(sample, port=5196)
        for _ in range(50):
            try:
                assert urllib.request.urlopen("http://127.0.0.1:5196/content/", timeout=2).status == 200
                break
            except OSError:
                import time
                time.sleep(0.1)
        else:
            raise AssertionError((sample / serve.LOG_FILE).read_text())
    finally:
        serve.down(sample)
    assert not ran.exists()
    # The same folder, entered by `-m`, is what the bootstrap is for: Python finds the library's package first.
    done = subprocess.run([sys.executable, "-m", "folio", "check"], cwd=sample, capture_output=True, text=True,
                          env=dict(os.environ, PYTHONSAFEPATH=""))
    assert ran.exists() and "hostile" in done.stderr  # documented: `python -m folio` in a library's folder is not covered


COMES_BACK = '''
    def rail(self):
        P.calls += 1
        if P.calls == 1:
            raise RuntimeError("the store is away")
        return [{"title": "T", "url": "/p/"}]
    def search(self):
        P.calls += 1
        if P.calls == 1:
            raise RuntimeError("the store is away")
        return [{"id": "", "genre": "view", "part": None, "path": "p", "url": "/p/", "title": "T", "description": "",
                 "tags": [], "status": "", "text": "x"}]
'''


def test_a_rail_that_failed_once_is_asked_again(sample, tmp_path, monkeypatch) -> None:
    from folio.site.serve import LiveSite

    _provider(tmp_path, monkeypatch, sample, "pv_rail_comes_back", _simple(extra=COMES_BACK))
    live = LiveSite(sample)
    assert live.site_data()["views"][0]["rail"] == []
    assert live.site_data()["views"][0]["rail"] == [{"title": "T", "url": "/p/"}]  # not kept empty until a file changes
    assert live.site_data()["views"][0]["rail"] == [{"title": "T", "url": "/p/"}]


def test_a_search_list_that_failed_once_is_asked_again(sample, tmp_path, monkeypatch) -> None:
    from folio.site.serve import LiveSite

    _provider(tmp_path, monkeypatch, sample, "pv_search_comes_back", _simple(extra=COMES_BACK))
    live = LiveSite(sample)
    first = json.loads(live.get(".folio/search.json")[0].body)
    assert not any(e["url"] == "/p/" for e in first) and any(e["genre"] == "concept" for e in first)
    assert any(e["url"] == "/p/" for e in json.loads(live.get(".folio/search.json")[0].body))
