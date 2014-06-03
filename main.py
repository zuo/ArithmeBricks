#!/usr/bin/kivy
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

from __future__ import division, unicode_literals

import collections
import functools
import operator
import random

import kivy
kivy.require('1.8.0')

from kivy.config import Config

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.properties import (
    AliasProperty,
    BooleanProperty,
    NumericProperty,
    ListProperty,
    ObjectProperty,
    OptionProperty,
    ReferenceListProperty,
)
from kivy.uix.behaviors import DragBehavior
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.utils import interpolate, platform
from kivy.vector import Vector


#
# Constants

SYMBOL_TO_BRICK_TEXT = {
    '==': '=',
    '+': '+',
    '-': '\u2212',
    '*': '\xd7',
    '/': '\xf7',
}
BRICK_TEXT_TO_SYMBOL = {
    text: symbol for symbol, text in SYMBOL_TO_BRICK_TEXT.items()}

DIFFICULTY_LEVEL_LIMITS = [
    dict(
        equalities=1,
        ops='+',
        min_number=1,
        max_number=4,
        max_total_number=8,
        max_symbols_per_equality=6,
    ),
    dict(
        equalities=1,
        ops='-',
        min_number=1,
        max_number=8,
        max_total_number=8,
        max_symbols_per_equality=6,
    ),
    dict(
        equalities=1,
        ops='+-',
        min_number=0,
        max_number=8,
        max_total_number=10,
        max_symbols_per_equality=7,
    ),
    dict(
        equalities=1,
        ops='*',
        min_number=0,
        max_number=4,
        max_total_number=9,
        max_symbols_per_equality=6,
    ),
    dict(
        equalities=1,
        ops='/',
        min_number=0,
        max_number=9,
        max_total_number=9,
        max_symbols_per_equality=6,
    ),
    dict(
        equalities=1,
        ops='+-*',
        min_number=2,
        max_number=10,
        max_total_number=12,
        max_symbols_per_equality=8,
    ),
    dict(
        equalities=1,
        ops='+-/',
        min_number=0,
        max_number=10,
        max_total_number=12,
        max_symbols_per_equality=9,
    ),
    dict(
        equalities=1,
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=12,
        max_symbols_per_equality=10,
    ),
    dict(
        equalities=1,
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=20,
        max_symbols_per_equality=11,
    ),
    dict(
        equalities=1,
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=50,
        max_symbols_per_equality=12,
    ),
    dict(
        equalities=1,
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=100,
        max_symbols_per_equality=13,
    ),
    dict(
        equalities=2,
        ops='+-*/',
        min_number=0,
        max_number=10,
        max_total_number=40,
        max_symbols_per_equality=8,
    ),
    dict(
        equalities=2,
        ops='+-*/',
        min_number=0,
        max_number=30,
        max_total_number=100,
        max_symbols_per_equality=9,
    ),
    dict(
        equalities=3,
        ops='+-*/',
        min_number=0,
        max_number=40,
        max_total_number=1000,
        max_symbols_per_equality=10,
    ),
    dict(
        equalities=3,
        ops='+-*/',
        min_number=0,
        max_number=50,
        max_total_number=5000,
        max_symbols_per_equality=12,
    ),
]

MAX_RETRY = 40

MIN_REPEATING_SYMBOL_COMBINATION_INTERVAL = 4

SOUND_FILENAME_PATTERN = 'sounds/arithmebricks-{0}_Seq01.wav'
SOUND_ID_TO_SYMBOL = {
    'eq': '==',
    'add': '+',
    'sub': '-',
    'mul': '*',
    'div': '/',
}

HELP_TEXT = (
    'Drag and drop the bricks (digits and operators) '
    'to form valid equalities (e.g. [i]2+10=15-3[/i]).\n'
    'All given bricks must be used. '
    'There is always at least one valid solution.'
)


#
# UI classes

class ArithmeBricksApp(App):

    def build(self):
        self.icon = 'icon.png'
        self.load_sounds()
        game = ArithmeBricksGame()
        Clock.schedule_once(lambda dt: game.show_title(), 1)
        return game

    def load_sounds(self):
        self.symbol_to_sound = {}
        sound_ids = list('0123456789') + list(SOUND_ID_TO_SYMBOL)
        for sound_id in sound_ids:
            filename = SOUND_FILENAME_PATTERN.format(sound_id)
            symbol = SOUND_ID_TO_SYMBOL.get(sound_id, sound_id)
            self.symbol_to_sound[symbol] = SoundLoader.load(filename)

    def play_sound(self, symbol, delay=None, volume=0.15):
        sound = self.symbol_to_sound.get(symbol)
        if sound is not None:
            def callback(dt):
                sound.volume = volume
                sound.play()
            if delay is None:
                delay = random.randint(0, 20) / 50
            Clock.schedule_once(callback, delay)


class ArithmeBricksGame(Widget):

    difficulty_level_limits = DIFFICULTY_LEVEL_LIMITS

    playing = BooleanProperty(False)
    finished = BooleanProperty(False)

    # NOTE: values of properties without defaults
    # shall be set in the .kv file
    limits = ObjectProperty()
    width_brick_ratio = NumericProperty()
    min_width_brick_ratio = NumericProperty()
    brick_width = NumericProperty()
    brick_height = NumericProperty()
    panel_height = NumericProperty()
    aux_text_size = NumericProperty()

    title_lines = ListProperty()

    def __init__(self, *args, **kwargs):
        super(ArithmeBricksGame, self).__init__(*args, **kwargs)
        self.symbol_generator = SymbolGenerator()

    def new_game(self):
        self.playing = self.finished = False
        self.clear_bricks()
        self.provide_bricks()
        self.playing = True

    def clear_bricks(self):
        for brick in list(self.iter_all_bricks()):
            Animation.cancel_all(brick)
            self.remove_widget(brick)

    def provide_bricks(self):
        limits = self.limits
        self.width_brick_ratio = max(
            self.min_width_brick_ratio,
            limits['max_symbols_per_equality']) + limits['equalities'] - 1
        for symbol in self.symbol_generator(limits):
            self.add_new_brick(symbol)

    def add_new_brick(self, symbol):
        target_pos = self.new_pos()
        if symbol in SYMBOL_TO_BRICK_TEXT:
            if symbol == '==':
                brick = EqualityBrick()
            else:
                brick = OperatorBrick()
            brick.text = SYMBOL_TO_BRICK_TEXT[symbol]
        else:
            assert symbol in '0123456789'
            brick = DigitBrick()
            brick.text = symbol
        self.add_widget(brick)
        brick.pos = self.center
        brick.target_pos = target_pos

    def new_pos(self):
        for i in range(MAX_RETRY * 2):
            x = random.randint(5, self.width - 5 - int(self.brick_width))
            y = random.randint(5 + int(self.brick_height),
                               self.height - int(self.brick_height))
            min_distance = self.brick_width
            _distance = Vector(x, y).distance
            if all(_distance(brick.target_pos) >= min_distance
                   for brick in self.iter_all_bricks()):
                break
        return x, y

    def iter_all_bricks(self):
        return (obj for obj in self.children
                if isinstance(obj, Brick))

    def finish_game(self):
        if self.playing:
            self.finished = True
        self.playing = False

    def popup_help(self):
        HelpPopup().open()

    def popup_quit(self):
        QuitPopup().open()

    def popup_new_game(self):
        def on_dismiss(popup):
            if popup.user_decision:
                self.new_game()
        NewGamePopup(on_dismiss=on_dismiss).open()

    def show_title(self):
        mid_row = len(self.title_lines) / 2
        for row, line_text in enumerate(self.title_lines):
            Clock.schedule_once(
                functools.partial(
                    self.show_title_row,
                    mid_row,
                    row,
                    line_text,
                ),
                row * 0.3)

    def show_title_row(self, mid_row, row, line_text, dt):
        if self.playing:
            return
        mid_col = len(line_text) / 2
        for col, char in enumerate(line_text):
            if char == ' ':
                continue
            pos = self.new_pos()
            brick = TitleBrick()
            self.add_widget(brick)
            brick.text = char
            brick.pos = pos
            brick.target_pos = (
                self.center_x + (col - mid_col) * self.brick_width,
                self.center_y - (row - mid_row) * self.brick_height -
                    self.brick_height / 2)


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

    max_snap_x_distance = NumericProperty()
    max_snap_y_distance = NumericProperty()
    max_double_attach_x_distance = NumericProperty()
    max_double_attach_y_distance = NumericProperty()

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

    # event dispatch

    def on_touch_down(self, touch):
        if self.state != 'final' and super(Brick, self).on_touch_down(touch):
            self.update_states_before_detach()
            self.detach()
            self.state = 'move'
            return True
        return False

    def on_touch_up(self, touch):
        if self.state != 'final' and super(Brick, self).on_touch_up(touch):
            self.target_pos = self.pos
            assert self.state == 'move'
            if self.attach():
                self.update_states_after_attach()
            else:
                self.state = 'detached'
            return True
        return False

    # detaching

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

    def detach(self):
        left_brick = self.left_attached_brick
        if left_brick is not None:
            left_brick.right_attached_brick = None
            self.left_attached_brick = None
        right_brick = self.right_attached_brick
        if right_brick is not None:
            right_brick.left_attached_brick = None
            self.right_attached_brick = None

    # attaching

    def attach(self):
        (left_brick,
         right_brick,
         target_pos) = self.get_left_right_bricks_and_target_pos()
        if left_brick is not None:
            left_brick.right_attached_brick = self.proxy_ref
            self.left_attached_brick = left_brick.proxy_ref
        if right_brick is not None:
            right_brick.left_attached_brick = self.proxy_ref
            self.right_attached_brick = right_brick.proxy_ref
        if target_pos is not None:
            self.target_pos = target_pos
        return left_brick is not None or right_brick is not None

    def get_left_right_bricks_and_target_pos(self):
        left_brick = self.choose_left_brick()
        right_brick = self.choose_right_brick()
        if right_brick is not None:
            target_pos_by_right = (right_brick.target_x - self.width,
                                   right_brick.target_y)
            if left_brick is not None:
                target_pos_by_left = tuple(left_brick.target_right_pos)
                distance_from_left = (Vector(self.target_pos)
                                      .distance(left_brick.target_right_pos))
                distance_from_right = (Vector(self.target_right_pos)
                                       .distance(right_brick.target_pos))
                if self.can_attach_to_both(
                        left_brick, right_brick,
                        target_pos_by_left, target_pos_by_right,
                        distance_from_left, distance_from_right):
                    target_pos = interpolate(target_pos_by_left,
                                             target_pos_by_right,
                                             step=2)
                elif self.should_attach_to_left(
                        left_brick, right_brick,
                        distance_from_left, distance_from_right):
                    target_pos = target_pos_by_left
                    right_brick = None
                else:
                    target_pos = target_pos_by_right
                    left_brick = None
            else:
                target_pos = target_pos_by_right
        elif left_brick is not None:
            target_pos = left_brick.target_right_pos
        else:
            target_pos = None
        return left_brick, right_brick, target_pos

    def choose_left_brick(self):
        _distance = Vector(self.target_pos).distance
        bricks_and_distances = [
            (brick,
             _distance(brick.target_right_pos),
             abs(self.target_x - brick.target_right))
            for brick in self.iter_all_bricks()
            if brick.right_attached_brick is None]
        return self.get_attachable_brick(bricks_and_distances)

    def choose_right_brick(self):
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
            # plays better than using the real x*y distance)
            y_distance = abs(self.target_y - brick.target_y)
            if (x_distance > self.max_snap_x_distance or
                  y_distance > self.max_snap_y_distance):
                return None
            if self.can_be_attached_to(brick):
                return brick

    def can_be_attached_to(self, brick):
        return brick.state != 'move'

    def can_attach_to_both(self, left_brick, right_brick,
                           target_pos_by_left, target_pos_by_right,
                           distance_from_left, distance_from_right):
        return (Vector(target_pos_by_left).distance(target_pos_by_right) <
                self.width / 3) or (
                    (distance_from_right / 3.5 <=
                     distance_from_left <=
                     3.5 * distance_from_right) and
                    # (for checking snap limits, using x and y separately
                    # plays better than using the real x*y distance)
                    (abs(self.target_x - left_brick.target_right) <=
                     self.max_double_attach_x_distance) and
                    (abs(self.target_y - left_brick.target_y) <=
                     self.max_double_attach_y_distance) and
                    (abs(self.target_right - right_brick.target_x) <=
                     self.max_double_attach_x_distance) and
                    (abs(self.target_y - right_brick.target_y) <=
                     self.max_double_attach_y_distance))

    def should_attach_to_left(self, left_brick, right_brick,
                              distance_from_left, distance_from_right):
        # (for choosing the side, comparing y distances often
        # seems to play better than comparing real x*y distances)
        from_left = abs(self.target_y - left_brick.target_y)
        from_right = abs(self.target_y - right_brick.target_y)
        if (from_left < self.height / 4 and
            from_right < self.height / 4) or (
                from_right / 1.4 <=
                from_left <=
                1.4 * from_right):
            # y distances are too small or too similar to be
            # conclusive => let's compare real x*y distances
            from_left = distance_from_left
            from_right = distance_from_right
        if from_left <= from_right:
            return True
        else:
            assert from_left > from_right
            return False

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
                self.parent.finish_game()
        else:
            for brick in brick_seq:
                brick.state = 'attached'

    # commons

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

    def iter_all_bricks(self):
        return self.parent.iter_all_bricks()


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


class TitleBrick(Brick):

    def on_touch_down(self, touch):
        return False

    def on_touch_up(self, touch):
        return False


class HelpPopup(Popup):
    help_text = HELP_TEXT


class QuitPopup(Popup):
    pass


class NewGamePopup(Popup):
    user_decision = BooleanProperty(False)


#
# Helper classes

class SymbolGenerator(object):

    class _FailedToMakeEquality(Exception):
        pass

    def __init__(self):
        self.recent_symbol_combinations = collections.deque(
            maxlen=MIN_REPEATING_SYMBOL_COMBINATION_INTERVAL)

    def __call__(self, limits):
        vars(self).update(limits)
        while True:
            generated_symbols = list(self.generate_symbols())
            if not (self.are_too_easy(generated_symbols) or
                    self.repeated_too_soon(generated_symbols)):
                return iter(generated_symbols)

    def generate_symbols(self):
        equalities = self.equalities
        max_num_digits = len(str(self.max_number))
        while True:
            left_max_symbols = random.randint(
                  self.max_symbols_per_equality // 3,
                  self.max_symbols_per_equality - 2)
            right_max_symbols = (
                  self.max_symbols_per_equality -
                  left_max_symbols -
                  1)
            try:
                equality, total_num = self.make_left_side(left_max_symbols,
                                                          max_num_digits)
                equality.append('==')
                equality.extend(self.make_right_side(total_num,
                                                     right_max_symbols,
                                                     max_num_digits))
            except self._FailedToMakeEquality:
                continue
            assert '==' in equality and eval(''.join(equality))
            for symbol in equality:
                yield symbol
            equalities -= 1
            if equalities < 1:
                break

    def are_too_easy(self, generated_symbols):
        # eliminate symbol combinations that include too few symbols
        if len(generated_symbols) < self.max_symbols_per_equality - 3:
            return True

        ones = generated_symbols.count('1')

        # eliminate boring symbol combinations that include too many '1'
        if ones > max(2, len(generated_symbols) / (3 + self.equalities)):
            return True

        # when there are few symbols: often (but not always)
        # eliminate lone multiplications/divisions by 1
        if ones and len(generated_symbols) <= 5:
            symbol_set = set(generated_symbols)
            if ((random.randint(1, 8) < 8 and
                   len(symbol_set.difference(('==', '*', '1'))) == 1) or
                (random.randint(1, 3) < 3 and
                   len(symbol_set.difference(('==', '/', '1'))) == 1)):
                return True

        muls_and_divs = (generated_symbols.count('*') +
                         generated_symbols.count('/'))

        # eliminate symbol combinations that include neither
        # '*' nor '/' when any of that operators is available
        if ('*' in self.ops or '/' in self.ops) and not muls_and_divs:
            return True

        # eliminate symbol combinations that are too easy because
        # of possibility of tricks involving '0' combined with '*'
        # or '/' and arbitrary digits (such as '2=2+0*17346348')
        zeros = generated_symbols.count('0')
        if not zeros:
            return False
        if not muls_and_divs:
            return False
        assert zeros > 0 and muls_and_divs
        if zeros == 1 and not ('+' in generated_symbols or
                               '-' in generated_symbols):
            return False
        if ((zeros == 1 or muls_and_divs == 1) and
              self.equalities == 1 and
              random.randint(1, 5) == 5):
            # sometimes we are lenient :) (but never on harder levels)
            return False
        return True

    def repeated_too_soon(self, generated_symbols):
        symbol_combination = tuple(sorted(generated_symbols))
        if symbol_combination in self.recent_symbol_combinations:
            return True
        self.recent_symbol_combinations.append(symbol_combination)
        return False

    def make_left_side(self, cur_max_symbols, max_num_digits):
        num = div_mul_operand = random.randint(self.min_number,
                                               self.max_number)
        symbols = list(str(num))
        if len(symbols) > cur_max_symbols - 2:
            raise self._FailedToMakeEquality
        for i in range(MAX_RETRY):
            op = random.choice(self.ops)
            if op == '/':
                num = self._random_divisor(div_mul_operand,
                                           self.min_number,
                                           self.max_number)
            elif op == '*':
                num = self._random_multiplier(div_mul_operand,
                                              self.min_number,
                                              self.max_number,
                                              self.max_total_number)
            else:
                num = random.randint(self.min_number, self.max_number)
            draft_symbols = symbols[:]
            draft_symbols.append(op)
            draft_symbols.extend(str(num))
            total_num = eval(''.join(draft_symbols))
            assert total_num == int(total_num)
            if (total_num < self.min_number or
                  total_num > self.max_total_number or
                  len(draft_symbols) > cur_max_symbols):
                continue
            div_mul_operand = self._new_div_mul_operand(op,
                                                        div_mul_operand,
                                                        num)
            symbols = draft_symbols
            if len(symbols) > (cur_max_symbols -
                               max_num_digits -
                               random.randint(1, (self.equalities +
                                                  max_num_digits -
                                                  1))):
                break
        else:
            raise self._FailedToMakeEquality
        return symbols, int(total_num)

    def make_right_side(self, total_num, cur_max_symbols, max_num_digits):
        assert total_num <= self.max_total_number
        symbols = list(str(total_num))
        if len(symbols) > cur_max_symbols:
            raise self._FailedToMakeEquality
        if len(symbols) > (cur_max_symbols -
                           max_num_digits -
                           1):
            return symbols
        for i in range(MAX_RETRY):
            op = random.choice(self.ops)
            if op == '+':
                num2 = random.randint(self.min_number, self.max_number)
                num1 = total_num - num2
            elif op == '-':
                num2 = random.randint(self.min_number, self.max_number)
                num1 = total_num + num2
            elif op == '*':
                num2 = self._random_divisor(total_num,
                                            self.min_number,
                                            self.max_number)
                num1 = total_num // num2
                assert num1 == total_num / num2
            elif op == '/':
                num2 = self._random_multiplier(total_num,
                                               max(1, self.min_number),
                                               self.max_number,
                                               self.max_total_number)
                num1 = total_num * num2
            symbols = list(str(num1))
            symbols.append(op)
            symbols.extend(str(num2))
            if (self.min_number <= num1 <= self.max_total_number and
                  self.min_number <= num2 <= self.max_number and
                  len(symbols) <= cur_max_symbols):
                return symbols
        raise self._FailedToMakeEquality

    @classmethod
    def _random_divisor(cls, dividend, min_num, max_num):
        min_num = max(1, min_num)
        if random.randint(0, 40) != 40:  # mostly avoid 1
            min_num = max(min_num, random.randint(2, 4))
        max_num = min(dividend // 2 + 1, max_num)
        if max_num < min_num:
            raise cls._FailedToMakeEquality
        for i in range(MAX_RETRY):
            num = random.randint(min_num, max_num)
            if dividend % num == 0:
                break
        else:
            max_num = min(10, max_num)
            if max_num < min_num:
                raise cls._FailedToMakeEquality
            for i in range(MAX_RETRY):
                num = random.randint(min_num, max_num)
                if dividend % num == 0:
                    break
            else:
                raise cls._FailedToMakeEquality
        return num

    @classmethod
    def _random_multiplier(cls, multiplicand, min_num, max_num,
                           max_total_number):
        if multiplicand != 0:
            max_num = max_total_number // multiplicand
        if random.randint(0, 40) != 40:  # mostly avoid 0, often avoid 1...
            min_num = max(min_num, random.randint(random.randint(1, 3), 4))
        if max_num < min_num:
            raise cls._FailedToMakeEquality
        return random.randint(min_num, max_num)

    @staticmethod
    def _new_div_mul_operand(op, div_mul_operand, num):
        if op == '/':
            return div_mul_operand / num
        elif op == '*':
            return div_mul_operand * num
        else:
            assert op in ('+', '-')
            return num


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
