import os
import sys

# `python -m folio` puts the folder it is run from first on the import path. That folder is a library,
# which is content, not code, so it is dropped before anything else is imported. This cannot stop a
# `folio/` package in that folder: Python imports it in place of this one, before this line. The
# `folio` command, `folio up` and `python -P -m folio` do not look in that folder at all.
if sys.path and sys.path[0] in ("", os.getcwd()):
    del sys.path[0]

from .cli import main  # noqa: E402

sys.exit(main())
