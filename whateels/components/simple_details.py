from html import escape

import panel as pn


class SimpleDetails(pn.Column):

    _STRETCH_WIDTH = "stretch_width"
    _HEADER_HEIGHT = 38
    _EXPANDED_PREFIX = "\u25b2 "
    _COLLAPSED_PREFIX = "\u25bc "

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
        **params
    ) -> None:

        self._title = title
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

        initial_color = self._color_on_expand if expanded else self._color_on_collapse

        self._header_pane = pn.pane.HTML(
            self._header_html(expanded, initial_color),
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

        header = pn.Column(
            self._header_pane,
            self._button_header,
            sizing_mode=self._STRETCH_WIDTH,
            height=self._HEADER_HEIGHT,
            margin=0,
            styles={
                "cursor": "pointer",
                "height": f"{self._HEADER_HEIGHT}px",
                "min-height": f"{self._HEADER_HEIGHT}px",
                "overflow": "hidden",
                "position": "relative",
                "width": "100%",
            },
        )

        self._content = pn.Column(
            content,
            sizing_mode=self._STRETCH_WIDTH,
            styles={
                "height": "auto",
                "min-height": "0",
                "padding": "10px",
                "transition": "height 0.3s ease",
            },
            visible=expanded,
        )

        layout = pn.Column(
            header,
            self._content,
            sizing_mode=self._STRETCH_WIDTH,
            styles={
                "height": "auto",
                "min-height": "0",
            },
        )

        styles = {
            "height": "auto",
            "min-height": "0",
            "border-radius": "4px",
            "box-shadow": "0 0 5px #d8d8d8",
            "background-color": "#f7f7f7",
            "overflow": "visible",
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
            "height": "auto",
            "min-height": "0",
        }

        for child in content.objects:
            self._apply_auto_height(child)

    def _header_html(self, expanded: bool, background_color: str) -> str:
        prefix = self._EXPANDED_PREFIX if expanded else self._COLLAPSED_PREFIX

        return f"""
        <div style="
            align-items: center;
            background-color: {background_color};
            border: 1px solid {background_color};
            border-radius: 4px;
            box-sizing: border-box;
            color: {self._text_color};
            cursor: pointer;
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

    def toggle(self):
        self._content.visible = not bool(self._content.visible)

        expanded = self._content.visible
        color = self._color_on_expand if expanded else self._color_on_collapse

        self._header_pane.object = self._header_html(expanded, color)
