# -*- coding: utf-8 -*-

"""
ArithmeBricks

Copyright (c) 2014 Jan Kaliszewski (zuo). All rights reserved.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division

import operator
import random

import kivy
kivy.require('1.8.0')  ##

from kivy.app import App
from kivy.clock import Clock
from kivy.config import Config
from kivy.properties import (
    AliasProperty,
    NumericProperty,
    ListProperty,
    OptionProperty,
    ReferenceListProperty,
)
from kivy.uix.behaviors import DragBehavior
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import QueryDict, platform, interpolate
from kivy.vector import Vector


#
# Constants

SYMBOL_TO_BRICK_TEXT = {
    '==': u'=',
    '+': u'+',
    '-': u'\u2212',
    '*': u'\xd7',
    '/': u'\xf7',
}
BRICK_TEXT_TO_SYMBOL = {
    text: symbol for symbol, text in SYMBOL_TO_BRICK_TEXT.items()}

DIFFICULTY_TO_LIMITS = [
    # 0
    QueryDict(
        ops='+',
        min_number=1,
        max_number=4,
        max_total_number=8,
        max_equalities=1,
        max_symbols_per_equality=6,
    ),
    # 1
    QueryDict(
        ops='+-',
        min_number=1,
        max_number=4,
        max_total_number=9,
        max_equalities=1,
        max_symbols_per_equality=6,
    ),
    # 2
    QueryDict(
        ops='+-',
        min_number=1,
        max_number=4,
        max_total_number=10,
        max_equalities=2,
        max_symbols_per_equality=6,
    ),
    # 3
    QueryDict(
        ops='+-',
        min_number=0,
        max_number=10,
        max_total_number=20,
        max_equalities=2,
        max_symbols_per_equality=8,
    ),
    # 4
    QueryDict(
        ops='+-*',
        min_number=0,
        max_number=10,
        max_total_number=40,
        max_equalities=2,
        max_symbols_per_equality=9,
    ),
    # 5
    QueryDict(
        ops='+-*',
        min_number=0,
        max_number=10,
        max_total_number=100,
        max_equalities=2,
        max_symbols_per_equality=10,
    ),
    # 6
    QueryDict(
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=100,
        max_equalities=2,
        max_symbols_per_equality=10,
    ),
    # 7
    QueryDict(
        ops='+-*/',
        min_number=0,
        max_number=20,
        max_total_number=400,
        max_equalities=2,
        max_symbols_per_equality=12,
    ),
    # 8
    QueryDict(
        ops='+-*/',
        min_number=0,
        max_number=40,
        max_total_number=2000,
        max_equalities=3,
        max_symbols_per_equality=14,
    ),
    # 9
    QueryDict(
        ops='/*+-',
        min_number=0,
        max_number=100,
        max_total_number=5000,
        max_equalities=3,
        max_symbols_per_equality=16,
    ),
]

MAX_RETRY = 40


#
# UI classes

class ArithmeBricksApp(App):

    def build(self):
        game = ArithmeBricksGame()
        Clock.schedule_once(lambda dt: game.new_game(5))
        return game


class ArithmeBricksGame(Widget):

    brick_width_div = NumericProperty(21.)
    brick_height_div = NumericProperty(16.)

    def new_game(self, difficulty):
        self.clear_widgets()
        self.provide_bricks(difficulty)

    def provide_bricks(self, difficulty):
        for symbol in SymbolGenerator(difficulty):
            self.new_brick(symbol)

    def new_brick(self, symbol):
        target_pos = self.new_pos()
        if symbol in SYMBOL_TO_BRICK_TEXT:
            if symbol == '==':
                brick = EqualityBrick(parent=self)
            else:
                brick = OperatorBrick(parent=self)
            text = SYMBOL_TO_BRICK_TEXT[symbol]
        else:
            assert symbol in '0123456789'
            brick = DigitBrick(parent=self)
            text = symbol
        brick.parent = None
        self.add_widget(brick)
        brick.text = text
        brick.pos = self.center
        brick.target_pos = target_pos
        return brick

    def new_pos(self):
        for i in range(MAX_RETRY):
            x = random.randint(5, self.width - 5 - (self.width //
                                                    self.brick_width_div))
            y = random.randint(5, self.height - 5 - (self.width //
                                                     self.brick_height_div))
            min_distance = self.width / self.brick_width_div
            _distance = Vector(x, y).distance
            if all(_distance(brick.target_pos) >= min_distance
                   for brick in self.iter_all_bricks()):
                break
        return x, y

    def iter_all_bricks(self):
        return (obj for obj in self.children
                if isinstance(obj, Brick))


class Brick(DragBehavior, Label):

    # NOTE: values of properties without defaults
    # shall be set in the .kv file

    background_color = ListProperty()
    border_color = ListProperty()

    # (declaring the following class-wide constants as properties makes it
    # easier to specify/inherit/overridde their values just in the .kv file)
    detached_border_color = ListProperty()
    move_border_color = ListProperty()
    attached_border_color = ListProperty()
    equal_border_color = ListProperty()
    final_border_color = ListProperty()

    target_x = NumericProperty(0)
    target_y = NumericProperty(0)
    target_pos = ReferenceListProperty(target_x, target_y)

    def get_target_right(self):
        return self.target_x + self.width
    def set_target_right(self, value):
        self.target_x = value - self.width
    target_right = AliasProperty(
        get_target_right, set_target_right, bind=('target_x', 'width'))

    target_right_pos = ReferenceListProperty(target_right, target_y)

    max_snap_x_distance = NumericProperty()
    max_snap_y_distance = NumericProperty()

    state = OptionProperty('detached', options=[
        'detached',
        'move',
        'attached',
        'equal',
        'final',
    ])

    left_attached_brick = None
    right_attached_brick = None

    @property
    def symbol(self):
        return self.text

    #def on_state(self, instance, state):
    #    print self.text, 'STATE:', state, self.target_pos

    def on_touch_down(self, touch):
        if super(Brick, self).on_touch_down(touch):
            self.move_started()
            return True
        return False

    def on_touch_up(self, touch):
        self.target_pos = self.pos
        if super(Brick, self).on_touch_up(touch):
            self.move_stopped()
            return True
        return False

    def move_started(self):
        if self.state == 'final':
            return
        self.detach()
        self.state = 'move'

    def move_stopped(self):
        if self.state == 'final':
            return
        assert self.state == 'move'
        if not self.try_to_attach():
            self.state = 'detached'

    def detach(self):
        self.update_states_before_detach()
        left_brick = self.left_attached_brick
        if left_brick is not None:
            left_brick.right_attached_brick = None
            self.left_attached_brick = None
        right_brick = self.right_attached_brick
        if right_brick is not None:
            right_brick.left_attached_brick = None
            self.right_attached_brick = None

    def update_states_before_detach(self):
        for brick_seq in (self.collect_all_left(),
                          self.collect_all_right()):
            if brick_seq:
                if len(brick_seq) == 1:
                    brick_seq[0].state = 'detached'
                elif self.is_brick_seq_equal(brick_seq):
                    for brick in brick_seq:
                        brick.state = 'equal'
                else:
                    for brick in brick_seq:
                        brick.state = 'attached'

    def try_to_attach(self):
        left_brick = self.choose_for_left()
        right_brick = self.choose_for_right()
        if left_brick is None and right_brick is None:
            return False
        self.attach(left_brick, right_brick)
        self.update_states_after_attach()
        return True

    def attach(self, left_brick, right_brick):
        if left_brick is not None:
            left_brick.right_attached_brick = self.proxy_ref
            self.left_attached_brick = left_brick.proxy_ref
            self.target_pos = left_brick.target_right_pos
        if right_brick is not None:
            right_brick.left_attached_brick = self.proxy_ref
            self.right_attached_brick = right_brick.proxy_ref
            target_pos = (right_brick.target_x - self.width,
                          right_brick.target_y)
            if left_brick is None:
                self.target_pos = target_pos
            else:
                self.target_pos = interpolate(tuple(left_brick.target_right_pos),
                                              target_pos,
                                              step=2)

    def update_states_after_attach(self):
        brick_seq = self.collect_all_left()
        brick_seq.append(self)
        self.collect_all_right(brick_seq)
        if self.is_brick_seq_equal(brick_seq):
            for brick in brick_seq:
                brick.state = 'equal'
            all_bricks = list(self.iter_all_bricks())
            if all(brick.state == 'equal' for brick in all_bricks):
                for brick in all_bricks:
                    brick.state = 'final'
                "TODO: final"
        else:
            for brick in brick_seq:
                brick.state = 'attached'

    def collect_all_left(self, brick_seq=None):
        if brick_seq is None:
            brick_seq = []
        left_attached_brick = self.left_attached_brick
        if left_attached_brick is not None:
            left_attached_brick.collect_all_left(brick_seq)
            brick_seq.append(left_attached_brick)
        return brick_seq

    def collect_all_right(self, brick_seq=None):
        if brick_seq is None:
            brick_seq = []
        right_attached_brick = self.right_attached_brick
        if right_attached_brick is not None:
            brick_seq.append(right_attached_brick)
            right_attached_brick.collect_all_right(brick_seq)
        return brick_seq

    def is_brick_seq_equal(self, brick_seq):
        expr_str = ''.join(brick.symbol for brick in brick_seq)
        if '==' not in expr_str:
            return False
        try:
            return eval(expr_str)
        except (SyntaxError, ArithmeticError):
            return False

    def choose_for_left(self):
        _distance = Vector(self.target_pos).distance
        bricks_and_distances = [
            (brick,
             _distance(brick.target_right_pos),
             abs(self.target_x - brick.target_right))
            for brick in self.iter_all_bricks()
            if brick.right_attached_brick is None]
        return self.get_attachable_brick(bricks_and_distances)

    def choose_for_right(self):
        _distance = Vector(self.target_right_pos).distance
        bricks_and_distances = [
            (brick,
             _distance(brick.target_pos),
             abs(self.target_right - brick.target_x))
            for brick in self.iter_all_bricks()
            if brick.left_attached_brick is None]
        return self.get_attachable_brick(bricks_and_distances)

    def get_attachable_brick(self, bricks_and_distances):
        bricks_and_distances.sort(key=operator.itemgetter(1))
        for brick, _, x_distance in bricks_and_distances:
            if brick == self:
                continue
            # (for checking snap limits, using x and y separately
            # plays better than using real x*y distance)
            y_distance = abs(self.target_y - brick.target_y)
            if (x_distance > self.max_snap_x_distance or
                  y_distance > self.max_snap_y_distance):
                return None
            if self.can_be_attached_to(brick):
                return brick

    def iter_all_bricks(self):
        return self.parent.iter_all_bricks()

    def can_be_attached_to(self, brick):
        return brick.state != 'move'


class DigitBrick(Brick):
    pass


class OperatorBrick(Brick):

    @property
    def symbol(self):
        return BRICK_TEXT_TO_SYMBOL[self.text]

    def can_be_attached_to(self, obj):
        return (super(OperatorBrick, self).can_be_attached_to(obj) and
                isinstance(obj, DigitBrick))


class EqualityBrick(OperatorBrick):
    pass


#
# Helper classes

class SymbolGenerator(object):

    class _FailedToMakeEquality(Exception):
        pass

    def __init__(self, difficulty):
        self.difficulty = difficulty
        vars(self).update(DIFFICULTY_TO_LIMITS[difficulty])

    def __iter__(self):
        max_equalities = self.max_equalities
        while True:
            left_max_symbols = random.randint(
                  self.max_symbols_per_equality // 3,
                  self.max_symbols_per_equality - 2)
            right_max_symbols = (
                  self.max_symbols_per_equality -
                  left_max_symbols -
                  1)
            try:
                equality, total_num = self.make_left_side(left_max_symbols)
                equality.append('==')
                equality.extend(self.make_right_side(total_num,
                                                     right_max_symbols))
            except self._FailedToMakeEquality:
                continue
            assert self.eval_expression(equality)
            for symbol in equality:
                yield symbol
            max_equalities -= 1
            if max_equalities < 1 or random.randint(1, 7) == 7:
                break

    @staticmethod
    def eval_expression(symbols):
        expr_str = ''.join(symbols)
        try:
            return eval(expr_str)
        except ArithmeticError:
            return None

    def make_left_side(self, cur_max_symbols):
        max_number_digits = len(str(self.max_number))
        total_num = random.randint(self.min_number, self.max_number)
        symbols = list(str(total_num))
        for i in range(MAX_RETRY):
            op = random.choice(self.ops)
            if op == '/':
                number = self._random_divisor(total_num,
                                              self.min_number,
                                              self.max_number)
            elif op == '*':
                number = self._random_multiplier(total_num,
                                                 self.min_number,
                                                 self.max_number,
                                                 self.max_total_number)
            else:
                number = random.randint(self.min_number,
                                        self.max_number)
            draft = symbols[:]
            draft.append(op)
            draft.extend(str(number))
            total_num = self.eval_expression(draft)
            if (total_num is None or
                  total_num != int(total_num) or
                  total_num < self.min_number or
                  total_num > self.max_total_number or
                  len(draft) > cur_max_symbols):
                continue
            symbols = draft
            if len(symbols) > (cur_max_symbols -
                              max_number_digits -
                              random.randint(1, max_number_digits + 2)):
                break
        else:
            raise self._FailedToMakeEquality
        return symbols, int(total_num)

    def make_right_side(self, total_num, cur_max_symbols):
        assert total_num <= self.max_total_number
        max_number_digits = len(str(self.max_number))
        symbols = list(str(total_num))
        if len(symbols) > cur_max_symbols:
            raise self._FailedToMakeEquality
        if len(symbols) > (cur_max_symbols -
                          max_number_digits -
                          1):
            return symbols
        for i in range(MAX_RETRY):
            op = random.choice(self.ops)
            if op == '+':
                number2 = random.randint(self.min_number, self.max_number)
                number1 = total_num - number2
            elif op == '-':
                number2 = random.randint(self.min_number, self.max_number)
                number1 = total_num + number2
            elif op == '*':
                number2 = self._random_divisor(total_num,
                                               self.min_number,
                                               self.max_number)
                number1 = total_num // number2
                assert number1 == total_num / number2
            elif op == '/':
                number2 = self._random_multiplier(total_num,
                                                  max(1, self.min_number),
                                                  self.max_number,
                                                  self.max_total_number)
                number1 = total_num * number2
            num1_str = str(number1)
            num2_str = str(number2)
            if (self.min_number <= number1 <= self.max_total_number and
                  self.min_number <= number2 <= self.max_number and
                  len(num1_str + op + num2_str) <= cur_max_symbols):
                symbols = list(num1_str)
                symbols.append(op)
                symbols.extend(num2_str)
                return symbols
        raise self._FailedToMakeEquality

    @classmethod
    def _random_divisor(cls, dividend, min_num, max_num):
        assert dividend is not None
        min_num = max(1, min_num)
        if random.randint(0, 10) != 10:
            min_num = max(min_num, random.randint(1, 4))
        max_num = min(dividend // 2 + 1, max_num)
        if max_num < min_num:
            raise cls._FailedToMakeEquality
        for i in range(MAX_RETRY):
            number = random.randint(min_num, max_num)
            if dividend % number == 0:
                break
        else:
            max_num = min(10, max_num)
            if max_num < min_num:
                raise cls._FailedToMakeEquality
            for i in range(MAX_RETRY):
                number = random.randint(min_num, max_num)
                if dividend % number == 0:
                    break
            else:
                raise cls._FailedToMakeEquality
        return number

    @classmethod
    def _random_multiplier(cls, multiplicand, min_num, max_num,
                           max_total_number):
        assert multiplicand is not None
        if multiplicand != 0:
            max_num = max_total_number // multiplicand
        if random.randint(0, 10) != 10:
            min_num = max(min_num, random.randint(1, 4))
        if max_num < min_num:
            raise cls._FailedToMakeEquality
        return random.randint(min_num, max_num)


#
# Helper functions

def config_tweaks():
    mouse_opt_str = Config.getdefault('input', 'mouse', None)
    if mouse_opt_str:
        mouse_options = mouse_opt_str.split(',')

        # disable mouse-based multitouch emulation
        if 'disable_multitouch' not in mouse_options:
            mouse_options.append('disable_multitouch')

        # on linux: disable mouse when another multitouch device is used
        # (see: http://kivy.org/docs/api-kivy.input.providers.mouse.html)
        if platform == 'linux' and 'disable_on_activity' not in mouse_options:
            mouse_options.append('disable_on_activity')

        Config.set('input', 'mouse', ', '.join(mouse_options))


if __name__ in ('__main__', '__android__'):
    config_tweaks()
    ArithmeBricksApp().run()