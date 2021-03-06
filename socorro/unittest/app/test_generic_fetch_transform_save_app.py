# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import unittest

from nose.tools import eq_, ok_, assert_raises

from socorro.app.fetch_transform_save_app import FetchTransformSaveApp
from socorro.lib.threaded_task_manager import ThreadedTaskManager
from socorro.lib.util import DotDict, SilentFakeLogger


class TestFetchTransformSaveApp(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_bogus_source_iter_and_worker(self):
        class TestFTSAppClass(FetchTransformSaveApp):
            def __init__(self, config):
                super(TestFTSAppClass, self).__init__(config)
                self.the_list = []

            def _setup_source_and_destination(self):
                pass

            def source_iterator(self):
                for x in xrange(5):
                    yield ((x,), {})

            def transform(self, anItem):
                self.the_list.append(anItem)

        logger = SilentFakeLogger()
        config = DotDict({
          'logger': logger,
          'number_of_threads': 2,
          'maximum_queue_size': 2,
          'source': DotDict({'crashstorage_class': None}),
          'destination': DotDict({'crashstorage_class': None}),
          'producer_consumer': DotDict({'producer_consumer_class':
                                          ThreadedTaskManager,
                                        'logger': logger,
                                        'number_of_threads': 1,
                                        'maximum_queue_size': 1}
                                      )
        })

        fts_app = TestFTSAppClass(config)
        fts_app.main()
        ok_(len(fts_app.the_list) == 5,
                        'expected to do 5 inserts, '
                          'but %d were done instead' % len(fts_app.the_list))
        ok_(sorted(fts_app.the_list) == range(5),
                        'expected %s, but got %s' % (range(5),
                                                     sorted(fts_app.the_list)))

    def test_bogus_source_and_destination(self):
        class NonInfiniteFTSAppClass(FetchTransformSaveApp):
            def source_iterator(self):
                for x in self.source.new_crashes():
                    yield ((x,), {})

        class FakeStorageSource(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict({'1234': DotDict({'ooid': '1234',
                                                       'Product': 'FireSquid',
                                                       'Version': '1.0'}),
                                      '1235': DotDict({'ooid': '1235',
                                                       'Product': 'ThunderRat',
                                                       'Version': '1.0'}),
                                      '1236': DotDict({'ooid': '1236',
                                                       'Product': 'Caminimal',
                                                       'Version': '1.0'}),
                                      '1237': DotDict({'ooid': '1237',
                                                       'Product': 'Fennicky',
                                                       'Version': '1.0'}),
                                     })

            def get_raw_crash(self, ooid):
                return self.store[ooid]

            def get_raw_dumps(self, ooid):
                return {'upload_file_minidump': 'this is a fake dump'}

            def new_crashes(self):
                for k in self.store.keys():
                    yield k

        class FakeStorageDestination(object):

            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

        logger = SilentFakeLogger()
        config = DotDict({
          'logger': logger,
          'number_of_threads': 2,
          'maximum_queue_size': 2,
          'source': DotDict({'crashstorage_class':
                                 FakeStorageSource}),
          'destination': DotDict({'crashstorage_class':
                                     FakeStorageDestination}),
          'producer_consumer': DotDict({'producer_consumer_class':
                                          ThreadedTaskManager,
                                        'logger': logger,
                                        'number_of_threads': 1,
                                        'maximum_queue_size': 1}
                                      )
        })

        fts_app = NonInfiniteFTSAppClass(config)
        fts_app.main()

        source = fts_app.source
        destination = fts_app.destination

        eq_(source.store, destination.store)
        eq_(len(destination.dumps), 4)
        eq_(destination.dumps['1237'],
                         source.get_raw_dumps('1237'))

    def test_source_iterator(self):

        class FakeStorageSource(object):

            def __init__(self):
                self.first = True

            def new_crashes(self):
                if self.first:
                    self.first = False
                else:
                    for k in range(999):
                        yield k
                    for k in range(2):
                        yield None

        class FakeStorageDestination(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

        logger = SilentFakeLogger()
        config = DotDict({
          'logger': logger,
          'number_of_threads': 2,
          'maximum_queue_size': 2,
          'source': DotDict({'crashstorage_class':
                                 FakeStorageSource}),
          'destination': DotDict({'crashstorage_class':
                                     FakeStorageDestination}),
          'producer_consumer': DotDict({'producer_consumer_class':
                                          ThreadedTaskManager,
                                        'logger': logger,
                                        'number_of_threads': 1,
                                        'maximum_queue_size': 1}
                                      )
        })

        fts_app = FetchTransformSaveApp(config)
        fts_app.source = FakeStorageSource()
        fts_app.destination = FakeStorageDestination
        error_detected = False
        for x, y in zip(xrange(1002), (a for a in fts_app.source_iterator())):
            if x == 0:
                ok_(y is None)
            elif x < 1000:
                if x - 1 != y[0][0] and not error_detected:
                    error_detected = True
                    eq_(x, y,
                                     'iterator fails on iteration %d' % x)
            else:
                if y is not None and not error_detected:
                    error_detected = True
                    ok_(x is None,
                                    'iterator fails on iteration %d' % x)

    def test_no_source(self):

        class FakeStorageDestination(object):

            def __init__(self, config, quit_check_callback):
                self.store = DotDict()
                self.dumps = DotDict()

            def save_raw_crash(self, raw_crash, dump, crash_id):
                self.store[crash_id] = raw_crash
                self.dumps[crash_id] = dump

        logger = SilentFakeLogger()
        config = DotDict({
          'logger': logger,
          'number_of_threads': 2,
          'maximum_queue_size': 2,
          'source': DotDict({'crashstorage_class':
                                 None}),
          'destination': DotDict({'crashstorage_class':
                                     FakeStorageDestination}),
          'producer_consumer': DotDict({'producer_consumer_class':
                                          ThreadedTaskManager,
                                        'logger': logger,
                                        'number_of_threads': 1,
                                        'maximum_queue_size': 1}
                                      )
        })

        fts_app = FetchTransformSaveApp(config)

        assert_raises(TypeError, fts_app.main)

    def test_no_destination(self):
        class FakeStorageSource(object):
            def __init__(self, config, quit_check_callback):
                self.store = DotDict({'1234': DotDict({'ooid': '1234',
                                                       'Product': 'FireSquid',
                                                       'Version': '1.0'}),
                                      '1235': DotDict({'ooid': '1235',
                                                       'Product': 'ThunderRat',
                                                       'Version': '1.0'}),
                                      '1236': DotDict({'ooid': '1236',
                                                       'Product': 'Caminimal',
                                                       'Version': '1.0'}),
                                      '1237': DotDict({'ooid': '1237',
                                                       'Product': 'Fennicky',
                                                       'Version': '1.0'}),
                                     })

            def get_raw_crash(self, ooid):
                return self.store[ooid]

            def get_raw_dump(self, ooid):
                return 'this is a fake dump'

            def new_ooids(self):
                for k in self.store.keys():
                    yield k



        logger = SilentFakeLogger()
        config = DotDict({
          'logger': logger,
          'number_of_threads': 2,
          'maximum_queue_size': 2,
          'source': DotDict({'crashstorage_class':
                                 FakeStorageSource}),
          'destination': DotDict({'crashstorage_class':
                                     None}),
          'producer_consumer': DotDict({'producer_consumer_class':
                                          ThreadedTaskManager,
                                        'logger': logger,
                                        'number_of_threads': 1,
                                        'maximum_queue_size': 1}
                                      )

        })

        fts_app = FetchTransformSaveApp(config)

        assert_raises(TypeError, fts_app.main)
