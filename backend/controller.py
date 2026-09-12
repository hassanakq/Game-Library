"""
Native controller layer.

The controller is managed on the Python side through pygame/SDL2.  The
frontend polls GameLibraryAPI.get_controller_state() several times per second.

Important: controllers may be plugged in or unplugged while the application is
running.  SDL invalidates a Joystick object when its device disappears, so this
module never keeps using an invalid object and never calls
pygame.joystick.quit()/init() on every poll.
"""

import time

try:
    import pygame
except Exception:
    pygame = None


# Standard SDL2 button layout for Xbox-style pads.
BUTTON_MAP = {
    0: "a",
    1: "b",
    2: "x",
    3: "y",
    4: "lb",
    5: "rb",
    6: "select",
    7: "start",
}

AXIS_DEADZONE = 0.5
NAV_REPEAT_DELAY = 0.35
NAV_REPEAT_INTERVAL = 0.14


class ControllerManager:
    def __init__(self):
        self._ready = False
        self._joystick = None
        self._joystick_instance_id = None
        self._prev_buttons = {}
        self._nav_direction = None
        self._nav_since = 0.0
        self._next_repeat = 0.0

        if pygame is not None:
            try:
                # Initialize only the subsystems we actually use (display +
                # joystick), instead of pygame.init(), which also brings up
                # audio/font/etc. In a frozen PyInstaller build those extra
                # subsystems can fail to initialize (e.g. no audio device
                # available), and since that failure was previously caught
                # here it silently disabled the *entire* controller instead
                # of just the unused subsystem.
                #
                # The joystick subsystem needs an SDL video subsystem to be
                # initialized first in order to receive hotplug events, so
                # display.init() must run before joystick.init().
                #
                # Do NOT repeatedly quit/init the joystick module in poll();
                # doing so invalidates joystick objects and causes
                # "Joystick not initialized" errors.
                pygame.display.init()
                pygame.joystick.init()
                self._ready = True
            except Exception:
                self._ready = False

    # ------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------

    def _reset_joystick(self):
        """Forget the current device and reset all edge/repeat state."""
        joystick = self._joystick
        self._joystick = None
        self._joystick_instance_id = None
        self._prev_buttons.clear()
        self._update_nav(None)

        if joystick is not None:
            try:
                joystick.quit()
            except Exception:
                # The device may already have disappeared.
                pass

    def _connect_first_joystick(self):
        """Connect to the first currently available joystick, if any."""
        if not self._ready:
            return None

        try:
            count = pygame.joystick.get_count()
        except pygame.error:
            try:
                pygame.joystick.init()
                count = pygame.joystick.get_count()
            except Exception:
                return None

        if count <= 0:
            self._reset_joystick()
            return None

        try:
            joystick = pygame.joystick.Joystick(0)
            joystick.init()

            self._joystick = joystick

            try:
                self._joystick_instance_id = joystick.get_instance_id()
            except Exception:
                self._joystick_instance_id = None

            self._prev_buttons.clear()
            self._update_nav(None)
            return joystick

        except Exception:
            self._reset_joystick()
            return None

    def _process_device_events(self):
        """Process SDL device add/remove events and keep our object valid."""
        if not self._ready:
            return

        try:
            events = pygame.event.get()
        except Exception:
            try:
                pygame.event.pump()
            except Exception:
                pass
            return

        removed_current = False
        added = False

        for event in events:
            if event.type == pygame.JOYDEVICEADDED:
                added = True

            elif event.type == pygame.JOYDEVICEREMOVED:
                removed_id = getattr(event, "instance_id", None)
                if (
                    self._joystick_instance_id is None
                    or removed_id == self._joystick_instance_id
                ):
                    removed_current = True

        if removed_current:
            self._reset_joystick()

        # If the current joystick vanished, or a new controller appeared while
        # no controller was connected, try to connect again.
        if self._joystick is None and (added or removed_current):
            self._connect_first_joystick()

    def _ensure_joystick(self):
        """Return a valid joystick, reconnecting when necessary."""
        if not self._ready:
            return None

        # No object yet: this covers startup and hot-plugging.
        if self._joystick is None:
            return self._connect_first_joystick()

        # Check whether the stored object is still valid.  SDL raises
        # pygame.error after a device has been unplugged.
        try:
            self._joystick.get_numbuttons()
            self._joystick.get_numaxes()
            self._joystick.get_numhats()
            return self._joystick
        except (pygame.error, AttributeError):
            self._reset_joystick()
            return self._connect_first_joystick()
        except Exception:
            self._reset_joystick()
            return self._connect_first_joystick()

    def _safe_name(self, joystick):
        try:
            return joystick.get_name()
        except Exception:
            return "Controller"

    def _hat_direction(self, joystick):
        try:
            if joystick.get_numhats() == 0:
                return None

            hx, hy = joystick.get_hat(0)

            if hy == 1:
                return "up"
            if hy == -1:
                return "down"
            if hx == -1:
                return "left"
            if hx == 1:
                return "right"
        except (pygame.error, AttributeError):
            return None
        except Exception:
            return None

        return None

    def _stick_direction(self, joystick):
        try:
            if joystick.get_numaxes() < 2:
                return None

            lx = joystick.get_axis(0)
            ly = joystick.get_axis(1)

            if abs(lx) < AXIS_DEADZONE and abs(ly) < AXIS_DEADZONE:
                return None

            if abs(lx) >= abs(ly):
                return "right" if lx > 0 else "left"

            return "down" if ly > 0 else "up"
        except (pygame.error, AttributeError):
            return None
        except Exception:
            return None

    def _update_nav(self, direction):
        now = time.monotonic()

        if direction is None:
            self._nav_direction = None
            self._nav_since = 0.0
            self._next_repeat = 0.0
            return None

        if direction != self._nav_direction:
            self._nav_direction = direction
            self._nav_since = now
            self._next_repeat = now + NAV_REPEAT_DELAY
            return direction

        if now >= self._next_repeat:
            self._next_repeat = now + NAV_REPEAT_INTERVAL
            return direction

        return None

    # ------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------

    def poll(self):
        if not self._ready:
            return {
                "connected": False,
                "name": None,
                "pressed": [],
                "nav": None,
            }

        try:
            # event.get() both pumps SDL and lets us detect hot-plug events.
            self._process_device_events()
        except Exception:
            try:
                pygame.event.pump()
            except Exception:
                pass

        joystick = self._ensure_joystick()

        if joystick is None:
            self._update_nav(None)
            return {
                "connected": False,
                "name": None,
                "pressed": [],
                "nav": None,
            }

        try:
            pressed = []

            # ---- one-shot (edge-triggered) buttons ----
            button_count = joystick.get_numbuttons()

            for index, action in BUTTON_MAP.items():
                if index >= button_count:
                    continue

                is_down = bool(joystick.get_button(index))
                was_down = self._prev_buttons.get(index, False)

                if is_down and not was_down:
                    pressed.append(action)

                self._prev_buttons[index] = is_down

            # ---- continuous navigation ----
            direction = (
                self._hat_direction(joystick)
                or self._stick_direction(joystick)
            )

            nav = self._update_nav(direction)

            return {
                "connected": True,
                "name": self._safe_name(joystick),
                "pressed": pressed,
                "nav": nav,
            }

        except (pygame.error, AttributeError):
            # The controller can disappear between any two SDL calls.  Treat
            # that as a normal hot-unplug instead of allowing the pywebview
            # callback to throw a traceback.
            self._reset_joystick()
            return {
                "connected": False,
                "name": None,
                "pressed": [],
                "nav": None,
            }
        except Exception:
            # Keep controller polling from ever breaking the webview API.
            self._reset_joystick()
            return {
                "connected": False,
                "name": None,
                "pressed": [],
                "nav": None,
            }


controller = ControllerManager()
