from tinydb import TinyDB, Query
from tinydb.storages import MemoryStorage
from tinydb.operations import push, pull


def test_push_pull():
    db = TinyDB(storage=MemoryStorage)
    db.insert({'n': 1, 't': ['a']})
    db.update(push('t', 'b'), Query().n == 1)
    db.update(pull('t', 'a'), Query().n == 1)
    assert db.all()[0]['t'] == ['b']
