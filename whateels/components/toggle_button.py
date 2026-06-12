from panel.widgets import Button
from typing import Optional, Callable

class ToggleButton(Button):
    """
    Two-state toggle button for Panel with customizable labels, colors, and callbacks.

    Parameters
    ----------
    initial_state : bool, optional
        Initial state of the button (True = 'on', False = 'off').
    states : dict, optional
        Dictionary with properties for each state ('on' and 'off'). Each must include:
            - 'label': str, button label for that state
            - 'button_type': str, Panel button_type ('success', 'danger', etc.)
            - 'on_click': callable or None, function to execute on click in that state
        Example:
            states = {
                'on': {'label': 'Stop', 'on_click': stop_fn, 'button_type': 'danger'},
                'off': {'label': 'Start', 'on_click': start_fn, 'button_type': 'success'}
            }
    kwargs :
        Additional keyword arguments for Panel Button.
    """
    # State identifiers
    _ON = 'on'
    _OFF = 'off'
    
    # Dictionary keys for state properties
    _NAME = 'label'
    _ON_CLICK = 'on_click'
    _BUTTON_TYPE = 'button_type'
    _COLOR = 'color'
    _TEXT_COLOR = 'text_color'

    _BUTTON_TYPES = {
        "default",
        "primary",
        "success",
        "warning",
        "danger",
        "info",
        "light",
        "dark",
    }
    
    def __init__(
        self, 
        initial_state: bool = False, 
        states: Optional[dict[str, dict[str, str | Optional[Callable[..., None]]]]] = None,
        **kwargs
    ):
        # Default states if none provided
        if states is None:
            states = {
                self._ON: {self._NAME: 'On', self._ON_CLICK: (lambda: print("On clicked")), self._BUTTON_TYPE: 'success'},
                self._OFF: {self._NAME: 'Off', self._ON_CLICK: (lambda: print("Off clicked")), self._BUTTON_TYPE: 'danger'}
            }
        # Set initial state
        name = states[self._ON][self._NAME] if initial_state else states[self._OFF][self._NAME]
        button_type, color, text_color = self._resolve_state_style(
            states[self._ON] if initial_state else states[self._OFF]
        )

        # Initialize the Button with the appropriate label and button type
        super().__init__(
            name=name,
            button_type=button_type,
            stylesheets=self._button_styles(color, text_color),
            **kwargs
        )
        
        # Store state and configuration
        self._state: bool = initial_state
        self._states = states

        # Set up click event handler
        self.on_click(self._handle_click)

    def _handle_click(self, event):
        """
        Handles click: executes the callback for the current state, then toggles and updates the UI.
        """
        # Call the function for the CURRENT state (before toggling)
        current_state_key = self._ON if self._state else self._OFF
        on_click_fn = self._states[current_state_key].get(self._ON_CLICK)
        if callable(on_click_fn):
            on_click_fn()
        
        # Then toggle and update the UI
        self.toggle()
        new_state_key = self._ON if self._state else self._OFF
        self.name = self._states[new_state_key][self._NAME]
        self._apply_state_style(self._states[new_state_key])

    def toggle(self):
        """
        Toggle the button's state and update label and color.
        """
        self._state = not self._state
        new_state_key = self._ON if self._state else self._OFF
        self.name = self._states[new_state_key][self._NAME]
        self._apply_state_style(self._states[new_state_key])

    def is_on(self):
        """
        Returns True if the button is in the 'on' state.
        """
        return self._state 

    def on_click_by_state(self, state: bool, on_click: Callable):
        """
        Assigns the callback for the given state ('on' or 'off'). Does not change state or UI.
        """
        state_key = self._ON if state else self._OFF
        if state_key not in [self._ON, self._OFF]:
            raise ValueError(f"Invalid state '{state}'. Use 'on' or 'off'.")
        if on_click is None:
            raise ValueError("on_click cannot be None.")
        # Set the callback for the requested state only
        self._states[state_key][self._ON_CLICK] = on_click

    def set_states(self, states):
        """
        Update the button's state dictionary.
        """
        self._states = states

    def _resolve_state_style(self, state: dict) -> tuple[str, str | None, str]:
        color = state.get(self._COLOR)
        button_type = state.get(self._BUTTON_TYPE, "default")
        text_color = state.get(self._TEXT_COLOR, "#ffffff")

        if color is not None:
            fallback_type = button_type if button_type in self._BUTTON_TYPES else "default"
            return fallback_type, color, text_color

        if button_type in self._BUTTON_TYPES:
            return button_type, None, text_color

        return "default", button_type, text_color

    def _apply_state_style(self, state: dict) -> None:
        button_type, color, text_color = self._resolve_state_style(state)
        self.button_type = button_type
        self.stylesheets = self._button_styles(color, text_color)

    def _button_styles(self, background_color: str | None, text_color: str):
        if background_color is None:
            return []

        return [f"""
        button, .bk-btn {{
            background-color: {background_color} !important;
            border-color: {background_color} !important;
            color: {text_color} !important;
            width: 100%;
        }}

        button:hover, .bk-btn:hover {{
            filter: brightness(0.92);
        }}

        button:active, .bk-btn:active {{
            filter: brightness(0.85);
        }}
        """]
