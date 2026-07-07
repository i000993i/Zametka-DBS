import sys
sys.path.insert(0, '.')

from zametka_dbs.core.config import get_config
c = get_config()
v = c.get('theme')
assert v in ('dark', 'light'), f'unexpected theme: {v}'

c.set('_test_key', 123)
assert c.get('_test_key') == 123
c.set('_test_key', None)

from zametka_dbs.search.engine import SearchEngine
assert SearchEngine() is not None

from zametka_dbs.markdown.wikilinks import parse_wikilinks
assert parse_wikilinks('[[test]]') == ['test']

from zametka_dbs.ui.pinned_widget import PinnedWidget
pw = PinnedWidget.__new__(PinnedWidget)
assert pw._ensure_list('["a"]') == ['a']

print('All fallback tests passed')
