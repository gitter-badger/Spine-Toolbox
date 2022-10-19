######################################################################################################################
# Copyright (C) 2017-2021 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
The SpineDBWorker class

:authors: P. Vennström (VTT) and M. Marin (KTH)
:date:   2.10.2019
"""

import os
import itertools
from enum import Enum, unique, auto
from PySide2.QtCore import QObject, QTimer, Signal, Slot, QSemaphore, QMutex, QThread
from spinedb_api import DiffDatabaseMapping, SpineDBAPIError
from spinetoolbox.helpers import busy_effect


@unique
class _Event(Enum):
    FETCH = auto()
    FETCH_STATUS_CHANGE = auto()
    ADD_OR_UPDATE_ITEMS = auto()
    READD_ITEMS = auto()
    REMOVE_ITEMS = auto()
    COMMIT_SESSION = auto()
    ROLLBACK_SESSION = auto()


class SpineDBWorker(QObject):
    """Does all the communication with a certain DB for SpineDBManager, in a non-GUI thread."""

    _something_happened = Signal(object, tuple)

    def __init__(self, db_mngr, db_url):
        super().__init__()
        self._db_mngr = db_mngr
        self._db_url = db_url
        self._db_map = None
        self._queries = {}
        self._query_has_elements_by_key = {}
        self._query_keys = {}
        self._iterators = {}
        self._busy_parents = set()
        self._fetched_parents = set()
        self._fetched_item_types = set()
        self.commit_cache = {}
        self._executor = PythonLikeQThreadPoolExecutor(max_workers=1)
        self._something_happened.connect(self._handle_something_happened)

    def clean_up(self):
        self._executor.shutdown()
        self.deleteLater()

    @Slot(object, tuple)
    def _handle_something_happened(self, event, args):
        {
            _Event.FETCH: self._fetch_event,
            _Event.FETCH_STATUS_CHANGE: self._fetch_status_change_event,
            _Event.ADD_OR_UPDATE_ITEMS: self._add_or_update_items_event,
            _Event.READD_ITEMS: self._readd_items_event,
            _Event.REMOVE_ITEMS: self._remove_items_event,
            _Event.COMMIT_SESSION: self._commit_session_event,
            _Event.ROLLBACK_SESSION: self._rollback_session_event,
        }[event](*args)

    def _db_map_lock(func):  # pylint: disable=no-self-argument
        def new_function(self, *args, **kwargs):
            lock = self._db_mngr.db_map_locks.get(self._db_map)
            if lock is None or not lock.tryLock():
                return
            try:
                return func(self, *args, **kwargs)
            finally:
                lock.unlock()

        return new_function

    def query(self, sq_name):
        """For tests."""
        return self._executor.submit(self._query, sq_name).result()

    def _query(self, sq_name):
        return self._db_map.query(getattr(self._db_map, sq_name)).all()

    def get_db_map(self, *args, **kwargs):
        return self._executor.submit(self._get_db_map, *args, **kwargs).result()

    def _get_db_map(self, *args, **kwargs):
        self._db_map = DiffDatabaseMapping(self._db_url, *args, **kwargs)
        return self._db_map

    def reset_queries(self, item_type=None):
        parents = list(self._queries)
        for parent in parents:
            if item_type is not None and parent.fetch_item_type != item_type:
                continue
            self._iterators.pop(parent, None)
            query = self._queries.pop(parent)
            key = self._query_keys.pop(query)
            self._query_has_elements_by_key.pop(key, None)
            self._fetched_parents.discard(parent)
            self._fetched_item_types.discard(parent.fetch_item_type)
            parent.fetch_status_change()

    def can_fetch_more(self, parent):
        if parent in self._fetched_parents | self._busy_parents:
            return False
        query = self._queries.get(parent)
        if query is None:
            # Query not made yet. Init query and return True
            self._executor.submit(self._init_query, parent)
            return True
        return self._query_has_elements(query)

    @busy_effect
    @_db_map_lock
    def _init_query(self, parent):
        """Initializes query for parent."""
        query = self._get_query(parent)
        if not self._query_has_elements(query):
            self._fetched_parents.add(parent)
            self._something_happened.emit(_Event.FETCH_STATUS_CHANGE, (parent,))

    def _fetch_status_change_event(self, parent):
        parent.fetch_status_change()

    def _get_query(self, parent):
        """Creates a query for parent. Stores both the query and whether or not it has elements."""
        if parent not in self._queries:
            query = self._make_query_for_parent(parent)
            key = self._make_query_key(query)
            if key not in self._query_has_elements_by_key:
                self._query_has_elements_by_key[key] = bool(query.first())
            self._queries[parent] = query
        return self._queries[parent]

    def _query_has_elements(self, query):
        return self._query_has_elements_by_key[self._make_query_key(query)]

    def _make_query_key(self, query):
        if query not in self._query_keys:
            self._query_keys[query] = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
        return self._query_keys[query]

    def fetch_more(self, parent):
        """Fetches items from the database.

        Args:
            parent (object)
        """
        self._busy_parents.add(parent)
        self._executor.submit(self._fetch_more, parent)

    @busy_effect
    @_db_map_lock
    def _fetch_more(self, parent):
        query = self._get_query(parent)
        iterator = self._get_iterator(parent, query)
        chunk = next(iterator, [])
        self._something_happened.emit(_Event.FETCH, (parent, chunk))

    def _fetch_event(self, parent, chunk):
        # Mark parent as unbusy, but after emitting the 'added' signal below otherwise we have an infinite fetch loop
        QTimer.singleShot(0, lambda parent=parent: self._busy_parents.discard(parent))
        if chunk:
            signal = self._db_mngr.added_signals[parent.fetch_item_type]
            signal.emit({self._db_map: chunk})
        else:
            self._fetched_parents.add(parent)

    def fetch_all(self, item_types=None, only_descendants=False, include_ancestors=False):
        if item_types is None:
            item_types = set(self._db_mngr.added_signals)
        if only_descendants:
            item_types = {
                descendant
                for item_type in item_types
                for descendant in self._db_map.descendant_tablenames.get(item_type, ())
            }
        if include_ancestors:
            item_types |= {
                ancestor for item_type in item_types for ancestor in self._db_map.ancestor_tablenames.get(item_type, ())
            }
        item_types -= self._fetched_item_types
        if not item_types:
            # FIXME: Needed? QCoreApplication.processEvents()
            return
        _ = self._executor.submit(self._fetch_all, item_types).result()

    @busy_effect
    @_db_map_lock
    def _fetch_all(self, item_types):
        for item_type in item_types:
            query, _ = self._make_query_for_item_type(item_type)
            for chunk in _make_iterator(query):
                self._populate_commit_cache(item_type, chunk)
                self._db_mngr.cache_items(item_type, {self._db_map: chunk})
            self._fetched_item_types.add(item_type)

    def _make_query_for_parent(self, parent):
        """Makes a database query for given item type.

        Args:
            parent (object): the object that requests the fetching

        Returns:
            Query: database query
        """
        query, subquery = self._make_query_for_item_type(parent.fetch_item_type)
        return parent.filter_query(query, subquery, self._db_map)

    def _make_query_for_item_type(self, item_type):
        subquery_name = self._db_map.cache_sqs[item_type]
        subquery = getattr(self._db_map, subquery_name)
        query = self._db_map.query(subquery)
        return query, subquery

    def _get_iterator(self, parent, query):
        if parent not in self._iterators:
            self._iterators[parent] = _make_iterator(query)
        return self._iterators[parent]

    def _populate_commit_cache(self, item_type, items):
        if item_type == "commit":
            return
        if item_type == "entity_group":  # FIXME: the entity_group table has no commit_id column :(
            return
        for item in items:
            self.commit_cache.setdefault(item["commit_id"], {}).setdefault(item_type, list()).append(item["id"])

    def close_db_map(self):
        _ = self._executor.submit(self._close_db_map).result()

    def _close_db_map(self):
        if not self._db_map.connection.closed:
            self._db_map.connection.close()

    def get_entity_metadata(self, entity_id):
        """Queries metadata records for a single entity synchronously.

        Args:
            entity_id (int): entity id

        Returns:
            list of namedtuple: entity metadata records
        """
        return self._executor.submit(self._get_entity_metadata, entity_id).result()

    def _get_entity_metadata(self, entity_id):
        """Queries metadata records for a single entity.

        Args:
            entity_id (int): entity id

        Returns:
            list of namedtuple: entity metadata records
        """
        sq = self._db_map.ext_entity_metadata_sq
        return self._db_map.query(sq).filter(sq.c.entity_id == entity_id).all()

    def get_parameter_value_metadata(self, parameter_value_id):
        """Queries metadata records for a single parameter value synchronously.

        Args:
            parameter_value_id (int): parameter value id

        Returns:
            list of namedtuple: parameter value metadata records
        """
        return self._executor.submit(self._get_parameter_value_metadata, parameter_value_id).result()

    def _get_parameter_value_metadata(self, parameter_value_id):
        """Queries metadata records for a single parameter value.

        Args:
            parameter_value_id (int): parameter value id

        Returns:
            list of namedtuple: parameter value metadata records
        """
        sq = self._db_map.ext_parameter_value_metadata_sq
        return self._db_map.query(sq).filter(sq.c.parameter_value_id == parameter_value_id).all()

    def add_or_update_items(self, items, method_name, item_type, signal_name, check, cache):
        """Adds or updates items in db.

        Args:
            items (dict): lists of items to add or update
            method_name (str): attribute of DiffDatabaseMapping to call for performing the operation
            item_type (str): item type
            signal_name (str) : signal attribute of SpineDBManager to emit if successful
            check (bool): Whether or not to check integrity
            cache (dict): Cache
        """
        self._executor.submit(self._add_or_update_items, items, method_name, item_type, signal_name, check, cache)

    @busy_effect
    def _add_or_update_items(self, items, method_name, item_type, signal_name, check, cache):
        items, errors = getattr(self._db_map, method_name)(*items, check=check, return_items=True, cache=cache)
        items = [self._db_map.db_to_cache(cache, item_type, item) for item in items]
        self._something_happened.emit(_Event.ADD_OR_UPDATE_ITEMS, (items, errors, signal_name))

    def _add_or_update_items_event(self, items, errors, signal_name):
        signal = getattr(self._db_mngr, signal_name)
        signal.emit({self._db_map: items})
        if errors:
            self._db_mngr.error_msg.emit({self._db_map: errors})

    def readd_items(self, items, method_name, item_type, signal_name, cache):
        """Adds or updates items in db.

        Args:
            items (dict): lists of items to add or update
            method_name (str): attribute of DiffDatabaseMapping to call for performing the operation
            item_type (str): item type
            signal_name (str) : signal attribute of SpineDBManager to emit if successful
        """
        self._executor.submit(self._readd_items, items, method_name, item_type, signal_name, cache)

    @busy_effect
    def _readd_items(self, items, method_name, item_type, signal_name, cache):
        getattr(self._db_map, method_name)(*items, readd=True, cache=cache)
        items = [self._db_map.db_to_cache(cache, item_type, item) for item in items]
        self._something_happened.emit(_Event.READD_ITEMS, (items, signal_name))

    def _readd_items_event(self, items, signal_name):
        signal = getattr(self._db_mngr, signal_name)
        signal.emit({self._db_map: items})

    def remove_items(self, ids_per_type):
        """Removes items from database.

        Args:
            ids_per_type (dict): lists of items to remove keyed by item type (str)
        """
        self._executor.submit(self._remove_items, ids_per_type)

    @busy_effect
    def _remove_items(self, ids_per_type):
        try:
            self._db_map.remove_items(**ids_per_type)
            errors = []
        except SpineDBAPIError as err:
            errors = [err]
        self._something_happened.emit(_Event.REMOVE_ITEMS, (ids_per_type, errors))

    def _remove_items_event(self, ids_per_type, errors):
        if errors:
            self._db_mngr.error_msg.emit({self._db_map: errors})
        self._db_mngr.items_removed.emit({self._db_map: ids_per_type})

    def commit_session(self, commit_msg, cookie=None):
        """Initiates commit session.

        Args:
            commit_msg (str): commit message
            cookie (Any): a cookie to include in session_committed signal
        """
        # Make sure that the worker thread has a reference to undo stacks even if they get deleted
        # in the GUI thread.
        undo_stack = self._db_mngr.undo_stack[self._db_map]
        self._executor.submit(self._commit_session, commit_msg, undo_stack, cookie)

    def _commit_session(self, commit_msg, undo_stack, cookie=None):
        """Commits session for given database maps.

        Args:
            commit_msg (str): commit message
            undo_stack (AgedUndoStack): undo stack that outlive the DB manager
            cookie (Any): a cookie to include in session_committed signal
        """
        try:
            self._db_map.commit_session(commit_msg)
            errors = []
        except SpineDBAPIError as e:
            errors = [e.msg]
        self._something_happened.emit(_Event.COMMIT_SESSION, (errors, undo_stack, cookie))

    def _commit_session_event(self, errors, undo_stack, cookie):
        undo_stack.setClean()
        if errors:
            self._db_mngr.error_msg.emit({self._db_map: errors})
        else:
            self._db_mngr.session_committed.emit({self._db_map}, cookie)

    def rollback_session(self):
        """Initiates rollback session action for given database maps in the worker thread.

        Args:
            dirty_db_maps (Iterable of DiffDatabaseMapping): database mapping to roll back
        """
        # Make sure that the worker thread has a reference to undo stacks even if they get deleted
        # in the GUI thread.
        undo_stack = self._db_mngr.undo_stack[self._db_map]
        self._executor.submit(self._rollback_session, undo_stack)

    def _rollback_session(self, undo_stack):
        """Rolls back session for given database maps.

        Args:
            undo_stack (AgedUndoStack): undo stack that outlive the DB manager
        """
        try:
            self._db_map.rollback_session()
            errors = []
        except SpineDBAPIError as e:
            errors = [e.msg]
        self._something_happened.emit(_Event.ROLLBACK_SESSION, (errors, undo_stack))

    def _rollback_session_event(self, errors, undo_stack):
        undo_stack.setClean()
        if errors:
            self._db_mngr.error_msg.emit({self._db_map: errors})
        else:
            self._db_mngr.session_rolled_back.emit({self._db_map})


def _make_iterator(query, query_chunk_size=1000, iter_chunk_size=1000):
    """Runs the given query and yields results by chunks of given size.

    Args:
        query (Query): the query

    Yields:
        list: chunk of items
    """
    it = (x._asdict() for x in query.yield_per(query_chunk_size).enable_eagerloads(False))
    while True:
        chunk = list(itertools.islice(it, iter_chunk_size))
        yield chunk
        if not chunk:
            break


class TimeOutError(Exception):
    """An exception to raise when a timeouts expire"""


class _Queue:
    """A simple queue class to pass information between QThreads."""

    def __init__(self):
        self._items = []
        self._mutex = QMutex()
        self._semafore = QSemaphore()

    def put(self, item):
        self._mutex.lock()
        self._items.append(item)
        self._mutex.unlock()
        self._semafore.release()

    def get(self, timeout=None):
        if timeout is None:
            timeout = -1
        timeout *= 1000
        if not self._semafore.tryAcquire(1, timeout):
            raise TimeOutError()
        self._mutex.lock()
        item = self._items.pop(0)
        self._mutex.unlock()
        return item


class _Future:
    """A simple future class to hold the result of an asynchronous computation."""

    def __init__(self):
        self._result_queue = _Queue()
        self._exception_queue = _Queue()

    def set_result(self, result):
        self._exception_queue.put(None)
        self._result_queue.put(result)

    def set_exception(self, exc):
        self._exception_queue.put(exc)
        self._result_queue.put(None)

    def result(self, timeout=None):
        result = self._result_queue.get(timeout=timeout)
        exc = self.exception(timeout=0)
        if exc is not None:
            raise exc
        return result

    def exception(self, timeout=None):
        return self._exception_queue.get(timeout=timeout)


class PythonLikeQThread(QThread):
    def __init__(self, target=None, args=()):
        super().__init__()
        self._target = target
        self._args = args

    def run(self):
        return self._target(*self._args)


class PythonLikeQThreadPoolExecutor:
    """A thread pool executor that always reuses - never discards - their QThreads."""

    def __init__(self, max_workers=None):
        if max_workers is None:
            max_workers = min(32, os.cpu_count() + 4)
        self._max_workers = max_workers
        self._threads = set()
        self._requests = _Queue()
        self._semafore = QSemaphore()

    def submit(self, fn, *args, **kwargs):
        future = _Future()
        self._requests.put((future, fn, args, kwargs))
        self._spawn_thread()
        return future

    def _spawn_thread(self):
        if self._semafore.tryAcquire():
            # No need to spawn a new thread
            return
        if len(self._threads) == self._max_workers:
            # Not possible to spawn a new thread
            return
        thread = PythonLikeQThread(target=self._do_work)
        self._threads.add(thread)
        thread.start()

    def _do_work(self):
        while True:
            request = self._requests.get()
            if request is None:
                break
            future, fn, args, kwargs = request
            try:
                result = fn(*args, **kwargs)
                future.set_result(result)
            except Exception as exc:  # pylint: disable=broad-except
                future.set_exception(exc)
            self._semafore.release()

    def shutdown(self):
        for _ in self._threads:
            self._requests.put(None)
        while self._threads:
            thread = self._threads.pop()
            thread.wait()
            thread.deleteLater()
