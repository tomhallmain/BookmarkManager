import gettext
import locale
import os
from pathlib import Path

from utils.logger import logger

_LOCALE_DIR = str(Path(__file__).resolve().parent.parent / "locale")
_DEFAULT_LOCALE = "en"


def _language_code(raw):
    """Reduce a locale string such as "de_DE.UTF-8" to its language code ("de")."""
    if not raw:
        return None
    code = raw.split(".")[0].split("_")[0]
    if not code or code in ("C", "POSIX"):
        return None
    return code


def _detect_locale():
    detected = _language_code(os.environ.get("LANG"))
    if detected is None:
        try:
            detected = _language_code(locale.getlocale()[0])
        except ValueError:
            detected = None
    return detected or _DEFAULT_LOCALE


class I18N:
    localedir = _LOCALE_DIR
    locale = _detect_locale()
    # fallback=True: with no compiled catalog for the locale (or no locale/ dir at
    # all), gettext returns the source strings unchanged.
    translate = gettext.translation('base', localedir, languages=[locale], fallback=True)

    @staticmethod
    def install_locale(locale, verbose=True):
        I18N.locale = locale
        I18N.translate = gettext.translation('base', I18N.localedir, languages=[locale], fallback=True)
        I18N.translate.install()
        if verbose:
            logger.info(I18N._("Switched locale to: {0}").format(locale))

    @staticmethod
    def _(s):
        # return gettext.gettext(s)
        try:
            return I18N.translate.gettext(s)
        except KeyError:
            return s


'''
NOTE when gathering the translation strings, set _() == to gettext.gettext() instead of the above, and run:

    ```python C:\\Python310\\Tools\\i18n\\pygettext.py -d base -o locale\\base.pot .```

in the base directory. The POT output file can be used as source for the PO files in each locale.
Run personal script C:\\Scripts\\i18n_manager.py to generate new PO files and look for invalid translations.

Bonus command:
    ```git diff locale\\de\\LC_MESSAGES\\base.po locale\\de\\LC_MESSAGES\\base1.po | rg -v "^.*#" | rg -C 3 "^(-|\\+)"```

Then for each locale once the PO files are set up as desired, run below in the deepest locale directory to produce the MO file from the PO file:
    ```python C:\\Python310\\Tools\\i18n\\msgfmt.py -o base.mo base```
'''

_ = I18N._
