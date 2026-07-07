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
result = parse_wikilinks('[[test]]')
assert len(result) == 1
assert result[0]['target'] == 'test'

from zametka_dbs.ui.pinned_widget import PinnedWidget
assert PinnedWidget._ensure_list('["a"]') == ['a']

print('All fallback tests passed')
