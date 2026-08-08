from html import escape

import panel as pn


class SimpleDetails(pn.Column):

    _STRETCH_WIDTH = "stretch_width"
    _HEADER_HEIGHT = 38
    _EXPANDED_PREFIX = "\u25b2 "
    _COLLAPSED_PREFIX = "\u25bc "
    _LOCKED_PREFIX = "\u2715 "
    _LOCKED_COLOR = "#b9b9c6"

    _BUTTON_TYPE_COLORS = {
        "default": "#ffffff",
        "primary": "var(--bs-primary, #0d6efd)",
        "success": "var(--bs-success, #198754)",
        "warning": "var(--bs-warning, #ffc107)",
        "danger": "var(--bs-danger, #dc3545)",
        "info": "var(--bs-info, #0dcaf0)",
        "light": "var(--bs-light, #f8f9fa)",
        "dark": "var(--bs-dark, #212529)",
    }

    def __init__(
        self,
        title: str,
        content,
        expanded: bool = False,
        color_on_expand: str = "#ca4bc8",
        color_on_collapse: str = "#7373da",
        button_type_on_expand: str | None = None,
        button_type_on_collapse: str | None = None,
        text_color: str = "#ffffff",
        locked: bool = False,
        **params
    ) -> None:

        self._title = title
        self._locked = bool(locked)
        expanded = bool(expanded) and not self._locked
        self._color_on_expand = self._resolve_color(
            color_on_expand,
            button_type_on_expand,
        )
        self._color_on_collapse = self._resolve_color(
            color_on_collapse,
            button_type_on_collapse,
        )
        self._text_color = text_color

        self._apply_auto_height(content)

        self._header_pane = pn.pane.HTML(
            self._header_html(expanded, self._header_color(expanded)),
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            styles={
                "pointer-events": "none",
            },
        )

        self._button_header = pn.widgets.Button(
            name="",
            button_type="default",
            on_click=lambda _: self.toggle(),
            disabled=self._locked,
            margin=0,
            sizing_mode=self._STRETCH_WIDTH,
            height=self._HEADER_HEIGHT,
            styles={
                "position": "absolute",
                "inset": "0",
                "opacity": "0",
                "cursor": "pointer",
                "z-index": "2",
                "width": "100%",
                "height": f"{self._HEADER_HEIGHT}px",
            },
            stylesheets=[f"""
            :host button,
            :host .bk-btn,
            button,
            .bk-btn {{
                cursor: pointer !important;
                height: {self._HEADER_HEIGHT}px !important;
                min-height: {self._HEADER_HEIGHT}px !important;
                opacity: 0 !important;
                width: 100% !important;
            }}
            """],
        )

        self._header_container = header = pn.Column(
            self._header_pane,
            self._button_header,
            sizing_mode=self._STRETCH_WIDTH,
            height=self._HEADER_HEIGHT,
            margin=0,
            styles={
                "box-sizing": "border-box",
                "cursor": "not-allowed" if self._locked else "pointer",
                "height": f"{self._HEADER_HEIGHT}px",
                "max-width": "100%",
                "min-height": f"{self._HEADER_HEIGHT}px",
                "min-width": "0",
                "overflow": "hidden",
                "position": "relative",
                "width": "100%",
            },
        )

        content_body = pn.Column(
            content,
            sizing_mode=self._STRETCH_WIDTH,
            margin=0,
            styles={
                "box-sizing": "border-box",
                "height": "auto",
                "max-width": "100%",
                "min-height": "0",
                "min-width": "0",
                "overflow-x": "hidden",
            },
        )

        # Do not implement the horizontal inset with CSS padding or a margin on a
        # stretch-width layout. Panel/Bokeh measures the child before those CSS
        # decorations are applied, so the child can still receive the full card
        # width and then be shifted outside it. Fixed spacers participate in the
        # layout calculation and make the centre column exactly 20 px narrower.
        self._content = pn.Row(
            pn.Spacer(width=10, margin=0),
            content_body,
            pn.Spacer(width=10, margin=0),
            sizing_mode=self._STRETCH_WIDTH,
            margin=(10, 0),
            styles={
                "box-sizing": "border-box",
                "height": "auto",
                "max-width": "100%",
                "min-height": "0",
                "min-width": "0",
                "overflow-x": "hidden",
                "transition": "height 0.3s ease",
            },
            visible=expanded,
        )

        layout = pn.Column(
            header,
            self._content,
            sizing_mode=self._STRETCH_WIDTH,
            styles={
                "box-sizing": "border-box",
                "height": "auto",
                "max-width": "100%",
                "min-height": "0",
                "min-width": "0",
                "overflow-x": "hidden",
            },
        )

        styles = {
            "box-sizing": "border-box",
            "height": "auto",
            "max-width": "100%",
            "min-height": "0",
            "min-width": "0",
            "border-radius": "4px",
            "box-shadow": "0 0 5px #d8d8d8",
            "background-color": "#f7f7f7",
            "overflow-x": "hidden",
            "overflow-y": "visible",
        }
        styles.update(params.pop("styles", {}) or {})

        super().__init__(
            layout,
            **params,
            styles=styles,
        )

    def _resolve_color(
        self,
        color: str,
        legacy_button_type: str | None = None,
    ) -> str:
        color_or_button_type = legacy_button_type or color

        return self._BUTTON_TYPE_COLORS.get(color_or_button_type, color_or_button_type)

    def _apply_auto_height(self, content) -> None:
        if not isinstance(content, pn.Column):
            return

        content.styles = {
            **(content.styles or {}),
            "box-sizing": "border-box",
            "height": "auto",
            "max-width": "100%",
            "min-height": "0",
            "min-width": "0",
        }

        for child in content.objects:
            self._apply_auto_height(child)

    def _header_color(self, expanded: bool) -> str:
        if self._locked:
            return self._LOCKED_COLOR

        return self._color_on_expand if expanded else self._color_on_collapse

    def _header_html(self, expanded: bool, background_color: str) -> str:
        if self._locked:
            prefix = self._LOCKED_PREFIX
        else:
            prefix = self._EXPANDED_PREFIX if expanded else self._COLLAPSED_PREFIX
        cursor = "not-allowed" if self._locked else "pointer"

        return f"""
        <div style="
            align-items: center;
            background-color: {background_color};
            border: 1px solid {background_color};
            border-radius: 4px;
            box-sizing: border-box;
            color: {self._text_color};
            cursor: {cursor};
            display: flex;
            font-family: inherit;
            font-size: 14px;
            height: {self._HEADER_HEIGHT}px;
            justify-content: center;
            line-height: {self._HEADER_HEIGHT}px;
            overflow: hidden;
            padding: 0 12px;
            text-align: center;
            user-select: none;
            white-space: nowrap;
            width: 100%;
        ">{escape(prefix + self._title)}</div>
        """

    @property
    def expanded(self) -> bool:
        """Whether the content block is currently visible."""
        return bool(self._content.visible)

    @property
    def locked(self) -> bool:
        """Whether the header refuses to open or close the section."""
        return self._locked

    def toggle(self):
        if self._locked:
            return

        self.set_expanded(not self.expanded)

    def set_expanded(self, expanded: bool) -> None:
        """Set the open/closed state directly instead of flipping it.

        A locked section can only be driven closed: opening it is exactly what the
        lock forbids, so callers do not have to unlock first just to collapse it.
        """
        expanded = bool(expanded)
        if self._locked and expanded:
            return

        self._content.visible = expanded
        self._render_header()

    def set_locked(self, locked: bool) -> None:
        """Block/allow the header. Locking always collapses the section first."""
        locked = bool(locked)
        if locked == self._locked:
            return

        self._locked = locked
        self._button_header.disabled = locked
        cursor = "not-allowed" if locked else "pointer"
        self._header_container.styles = {
            **(self._header_container.styles or {}),
            "cursor": cursor,
        }
        if locked:
            self._content.visible = False
        self._render_header()

    def _render_header(self) -> None:
        expanded = self.expanded
        self._header_pane.object = self._header_html(
            expanded,
            self._header_color(expanded),
        )
