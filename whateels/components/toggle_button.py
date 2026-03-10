from panel.widgets import Button
from typing import Optional, Callable

class ToggleButton(Button):
    """
    A two-state toggle button for Panel with customizable labels, colors, and callbacks.

    Parameters
    ----------
    initial_state : bool, optional
        If True, button starts in the 'on' state, else 'off'.
    states : dict, optional
        A dictionary specifying the properties for each state. Must have keys 'on' and 'off',
        each mapping to a dict with at least:
            - 'label': str, the button label for that state
            - 'button_type': str, the Panel button_type (e.g. 'success', 'danger')
            - 'on_click': callable or None, function to call when button is clicked in that state
        Example:
            states = {
                'on': {'label': 'Stop', 'on_click': stop_fn, 'button_type': 'danger'},
                'off': {'label': 'Start', 'on_click': start_fn, 'button_type': 'success'}
            }
    kwargs :
        Additional keyword arguments passed to Panel's Button.
    """
    # State identifiers
    _ON = 'on'
    _OFF = 'off'
    
    # Dictionary keys for state properties
    _NAME = 'label'
    _ON_CLICK = 'on_click'
    _BUTTON_TYPE = 'button_type'
    
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
        button_type = states[self._ON][self._BUTTON_TYPE] if initial_state else states[self._OFF][self._BUTTON_TYPE]

        # Initialize the Button with the appropriate label and button type
        super().__init__(name=name, button_type=button_type, **kwargs)
        
        # Store state and configuration
        self._state: bool = initial_state
        self._states = states

        # Set up click event handler
        self.on_click(self._handle_click)

    def _handle_click(self, event):
        """Handle button click events to toggle state and update label and button type."""
        # Call the function for the CURRENT state (before toggling)
        current_state_key = self._ON if self._state else self._OFF
        on_click_fn = self._states[current_state_key].get(self._ON_CLICK)
        if callable(on_click_fn):
            on_click_fn()
        
        # Then toggle and update the UI
        self.toggle()
        new_state_key = self._ON if self._state else self._OFF
        self.name = self._states[new_state_key][self._NAME]
        self.button_type = self._states[new_state_key][self._BUTTON_TYPE]

    def toggle(self):
        """Toggle the button's state."""
        self._state = not self._state
        new_state_key = self._ON if self._state else self._OFF
        self.name = self._states[new_state_key][self._NAME]
        self.button_type = self._states[new_state_key][self._BUTTON_TYPE]

    def is_on(self):
        """Check if the button is in the 'on' state."""
        return self._state 

    def on_click_by_state(self, state: bool, on_click: Callable):
        """Set the on_click handler for the given state (does not update the button state or UI)."""
        state_key = self._ON if state else self._OFF
        if state_key not in [self._ON, self._OFF]:
            raise ValueError(f"Invalid state '{state}'. Use 'on' or 'off'.")
        if on_click is None:
            raise ValueError("on_click cannot be None.")
        # Set the callback for the requested state only
        self._states[state_key][self._ON_CLICK] = on_click

    def set_states(self, states):
        self._states = states
