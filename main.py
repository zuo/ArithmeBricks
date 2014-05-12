# -*- coding: utf-8 -*-

import kivy
kivy.require('1.8.0')  ##

from kivy.app import App
from kivy.config import Config
from kivy.properties import (
    ListProperty,
    OptionProperty,
)
from kivy.uix.behaviors import DragBehavior
from kivy.uix.label import Label
from kivy.uix.widget import Widget
from kivy.utils import platform
from kivy.vector import Vector


class ArithmeBricksGame(Widget):
    pass


class Brick(DragBehavior, Label):

    left_neighbor = None
    right_neighbor = None

    state = OptionProperty('detached', options=[
        'detached',
        'move',
        'attached',
        'equal',
        'final',
    ])

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

    def on_state(self, instance, state):
        print 'STATE:', state, Vector(self.pos).distance((50, 50))

    def on_touch_down(self, touch):
        if super(Brick, self).on_touch_down(touch):
            self.move_started(touch)
            return True
        return False

    def on_touch_up(self, touch):
        if super(Brick, self).on_touch_up(touch):
            self.mode_stopped(touch)
            return True
        return False

    def move_started(self, touch):
        if self.state == 'final':
            return
        elif self.state in ('attached', 'equal'):
            "detach from the row of bricks... (especially re-eval the row(s) on left and/or right)"
        self.state = 'move'

    def mode_stopped(self, touch):
        if self.state == 'final':
            return
        assert self.state == 'move'
        if "becomes attached..." and (((False))):
            if "becomes part of equality...":
                if "all bricks are parts of an equality...":
                    "set state to 'final' for *all* bricks"
                else:
                    "set state='equal' for the bricks the equality consist of"
            else:
                "set state='attached' for this and the other brick"
        else:
            self.state = 'detached'


class DigitBrick(Brick):
    pass


class ArithmeBricksApp(App):
    def build(self):
        return ArithmeBricksGame()


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
