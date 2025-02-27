######################################################################################################################
# Copyright (C) 2017-2022 Spine project consortium
# This file is part of Spine Toolbox.
# Spine Toolbox is free software: you can redistribute it and/or modify it under the terms of the GNU Lesser General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option)
# any later version. This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General
# Public License for more details. You should have received a copy of the GNU Lesser General Public License along with
# this program. If not, see <http://www.gnu.org/licenses/>.
######################################################################################################################

"""
Unit tests for PivotModel class.

:author: P. Vennström (VTT)
:date:   16.11.2018
"""

import unittest
from spinetoolbox.spine_db_editor.mvcmodels.pivot_model import PivotModel

INDEX_IDS = ['test1', 'test2', 'test3']
DATA = {
    ('a', 'aa', 1): 'value_a_aa_1',
    ('a', 'bb', 2): 'value_a_bb_2',
    ('b', 'cc', 3): 'value_b_cc_3',
    ('c', 'cc', 4): 'value_c_cc_4',
    ('d', 'dd', 5): 'value_d_dd_5',
    ('e', 'ee', 5): 'value_e_ee_5',
}


class TestPivotModel(unittest.TestCase):
    def test_init_model(self):
        model = PivotModel()
        self.assertEqual(model.get_pivoted_data([], []), [])
        self.assertEqual(model.rows, [])
        self.assertEqual(model.columns, [])
        self.assertEqual(model.row_key(0), tuple())
        self.assertEqual(model.column_key(0), tuple())

    def test_reset_model(self):
        """test reset model data"""
        row_headers = [('a', 'aa', 1), ('a', 'bb', 2), ('b', 'cc', 3), ('c', 'cc', 4), ('d', 'dd', 5), ('e', 'ee', 5)]
        column_headers = []
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        self.assertEqual(model._data, DATA)
        self.assertEqual(model.index_ids, tuple(INDEX_IDS))
        self.assertEqual(model.pivot_rows, tuple(INDEX_IDS))
        self.assertEqual(model.pivot_columns, ())
        self.assertEqual(model.pivot_frozen, ())
        self.assertEqual(model.frozen_value, ())
        self.assertEqual(model._row_data_header, row_headers)
        self.assertEqual(model._column_data_header, column_headers)

    def test_reset_model_with_pivot(self):
        """Test set data with pivot and tuple_index_entries"""
        column_headers = [
            ('a', 'aa', 1),
            ('a', 'bb', 2),
            ('b', 'cc', 3),
            ('c', 'cc', 4),
            ('d', 'dd', 5),
            ('e', 'ee', 5),
        ]
        row_headers = []
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS, rows=(), columns=tuple(INDEX_IDS))
        self.assertEqual(model._data, DATA)
        self.assertEqual(model.index_ids, tuple(INDEX_IDS))
        self.assertEqual(model.pivot_rows, ())
        self.assertEqual(model.pivot_columns, tuple(INDEX_IDS))
        self.assertEqual(model.pivot_frozen, ())
        self.assertEqual(model.frozen_value, ())
        self.assertEqual(model._row_data_header, row_headers)
        self.assertEqual(model._column_data_header, column_headers)

    def test_set_pivot(self):
        """Test set_pivot"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        model.set_pivot(['test1', 'test2'], ['test3'], [], ())
        row_headers = [('a', 'aa'), ('a', 'bb'), ('b', 'cc'), ('c', 'cc'), ('d', 'dd'), ('e', 'ee')]
        column_headers = [(1,), (2,), (3,), (4,), (5,)]
        self.assertEqual(model._row_data_header, row_headers)
        self.assertEqual(model._column_data_header, column_headers)

    def test_set_pivot_with_frozen(self):
        """Test set_pivot with frozen dimension"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        model.set_pivot(['test2'], ['test3'], ['test1'], ('a',))
        row_headers = [('aa',), ('bb',)]
        data = [['value_a_aa_1', None], [None, 'value_a_bb_2']]
        column_headers = [(1,), (2,)]
        data_model = [[d for d in inner] for inner in model.get_pivoted_data(range(2), range(2))]
        self.assertEqual(model._row_data_header, row_headers)
        self.assertEqual(model._column_data_header, column_headers)
        self.assertEqual(data_model, data)

    def test_get_pivoted_data1(self):
        """get data with pivot and frozen index and tuple_index_entries"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        model.set_pivot(['test2'], ['test3'], ['test1'], ('a',))
        data = [['value_a_aa_1', None], [None, 'value_a_bb_2']]
        data_model = [[d for d in inner] for inner in model.get_pivoted_data(range(2), range(2))]
        self.assertEqual(data_model, data)

    def test_get_pivoted_data2(self):
        """get data from pivoted model wiht tuple_index_entries"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        model.set_pivot(['test1', 'test2'], ['test3'], [], ())
        data = [
            ['value_a_aa_1', None, None, None, None],
            [None, 'value_a_bb_2', None, None, None],
            [None, None, 'value_b_cc_3', None, None],
            [None, None, None, 'value_c_cc_4', None],
            [None, None, None, None, 'value_d_dd_5'],
            [None, None, None, None, 'value_e_ee_5'],
        ]
        data_model = [[d for d in inner] for inner in model.get_pivoted_data(range(6), range(5))]
        self.assertEqual(data_model, data)

    def test_get_pivoted_data3(self):
        """get data from pivoted model"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        model.set_pivot(['test1', 'test2'], ['test3'], [], ())
        data = [
            ['value_a_aa_1', None, None, None, None],
            [None, 'value_a_bb_2', None, None, None],
            [None, None, 'value_b_cc_3', None, None],
            [None, None, None, 'value_c_cc_4', None],
            [None, None, None, None, 'value_d_dd_5'],
            [None, None, None, None, 'value_e_ee_5'],
        ]
        data_model = [[d for d in inner] for inner in model.get_pivoted_data(range(6), range(5))]
        self.assertEqual(data_model, data)

    def test_get_unique_index_values1(self):
        """test that _get_unique_index_values returns unique values for specified indexes"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS)
        index_set = sorted({('a', 'aa'), ('a', 'bb'), ('b', 'cc'), ('c', 'cc'), ('d', 'dd'), ('e', 'ee')})
        index_header_values = model._get_unique_index_values(('test1', 'test2'))
        self.assertEqual(index_header_values, index_set)

    def test_get_unique_index_values2(self):
        """test that _get_unique_index_values returns unique values for specified indexes with filter index and value"""
        model = PivotModel()
        model.reset_model(DATA, INDEX_IDS, ('test1', 'test2'), (), ('test3',), (5,))
        index_set = sorted({('d', 'dd'), ('e', 'ee')})
        index_header_values = model._get_unique_index_values(('test1', 'test2'))
        self.assertEqual(index_header_values, index_set)

    def test_add_to_model_replaces_none(self):
        index_ids = ["test1", "test2", "test3"]
        data = {("a", "aa", 1): None}
        model = PivotModel()
        model.reset_model(data, index_ids)
        model.set_pivot(["test1"], ["test2"], ["test3"], ["frozen value"])
        model.add_to_model({("a", "aa", 1): 23.0})
        self.assertEqual(model._data, {("a", "aa", 1): 23.0})
        self.assertEqual(model.index_ids, tuple(index_ids))
        self.assertEqual(model.pivot_rows, ("test1",))
        self.assertEqual(model.pivot_columns, ("test2",))
        self.assertEqual(model.pivot_frozen, ("test3",))
        self.assertEqual(model.frozen_value, ("frozen value",))
        self.assertEqual(model._row_data_header, [])
        self.assertEqual(model._column_data_header, [])

    def test_add_to_model_nones_do_not_overwrite_existing_values(self):
        index_ids = ["test1", "test2", "test3"]
        data = {("a", "aa", 1): 23.0}
        model = PivotModel()
        model.reset_model(data, index_ids)
        model.set_pivot(["test1"], ["test2"], ["test3"], ["frozen value"])
        model.add_to_model({("a", "aa", 1): None})
        self.assertEqual(model._data, {("a", "aa", 1): 23.0})
        self.assertEqual(model.index_ids, tuple(index_ids))
        self.assertEqual(model.pivot_rows, ("test1",))
        self.assertEqual(model.pivot_columns, ("test2",))
        self.assertEqual(model.pivot_frozen, ("test3",))
        self.assertEqual(model.frozen_value, ("frozen value",))
        self.assertEqual(model._row_data_header, [])
        self.assertEqual(model._column_data_header, [])

    def test_add_to_model_nones_can_be_inserted_to_model(self):
        index_ids = ["test1", "test2", "test3"]
        data = {("a", "aa", 1): 23.0}
        model = PivotModel()
        model.reset_model(data, index_ids)
        model.set_pivot(["test1"], ["test2"], ["test3"], ["frozen value"])
        model.add_to_model({("a", "aa", 2): None})
        self.assertEqual(model._data, {("a", "aa", 1): 23.0, ("a", "aa", 2): None})
        self.assertEqual(model.index_ids, tuple(index_ids))
        self.assertEqual(model.pivot_rows, ("test1",))
        self.assertEqual(model.pivot_columns, ("test2",))
        self.assertEqual(model.pivot_frozen, ("test3",))
        self.assertEqual(model.frozen_value, ("frozen value",))
        self.assertEqual(model._row_data_header, [])
        self.assertEqual(model._column_data_header, [])


if __name__ == '__main__':
    unittest.main()
