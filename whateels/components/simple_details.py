from html import escape

import panel as pn


class SimpleDetails(pn.Column):

    _STRETCH_WIDTH = "stretch_width"
    _EXPANDED_PREFIX = "\u25b2 "
    _COLLAPSED_PREFIX = "\u25bc "

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
        self._button_type_on_expand, self._color_on_expand = self._resolve_button_style(
            button_type_on_expand, color_on_expand
        )
        self._button_type_on_collapse, self._color_on_collapse = self._resolve_button_style(
            button_type_on_collapse, color_on_collapse
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
            height=38,
            styles={
                "position": "absolute",
                "inset": "0",
                "opacity": "0",
                "cursor": "pointer",
                "z-index": "2",
                "width": "100%",
                "height": "38px",
            },
            stylesheets=["""
            :host button,
            :host .bk-btn,
            button,
            .bk-btn {
                cursor: pointer !important;
                height: 38px !important;
                min-height: 38px !important;
                opacity: 0 !important;
                width: 100% !important;
            }
            """],
        )

        header = pn.Column(
            self._header_pane,
            self._button_header,
            sizing_mode=self._STRETCH_WIDTH,
            height=38,
            margin=0,
            styles={
                "cursor": "pointer",
                "height": "38px",
                "min-height": "38px",
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

    def _resolve_button_style(
        self,
        button_type: str | None,
        color: str,
    ) -> tuple[str, str | None]:
        color_or_button_type = button_type or color

        if color_or_button_type in self._BUTTON_TYPES:
            return color_or_button_type, None

        return "default", color_or_button_type

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

    def _button_styles(self, background_color: str | None):
        if background_color is None:
            return []

        return [f"""
        :host .bk-btn,
        :host .bk-btn-default,
        :host .bk-btn.bk-btn-default,
        :host button,
        .bk-btn,
        .bk-btn-default,
        .bk-btn.bk-btn-default,
        button {{
            background-color: {background_color} !important;
            border-color: {background_color} !important;
            color: {self._text_color} !important;
            width: 100%;
        }}

        :host .bk-btn:hover,
        :host .bk-btn-default:hover,
        :host .bk-btn.bk-btn-default:hover,
        :host button:hover,
        .bk-btn:hover,
        .bk-btn-default:hover,
        .bk-btn.bk-btn-default:hover,
        button:hover {{
            filter: brightness(0.92);
        }}

        :host .bk-btn:active,
        :host .bk-btn-default:active,
        :host .bk-btn.bk-btn-default:active,
        :host button:active,
        .bk-btn:active,
        .bk-btn-default:active,
        .bk-btn.bk-btn-default:active,
        button:active {{
            filter: brightness(0.85);
        }}
        """]

    def _button_inline_styles(self, background_color: str | None):
        if background_color is None:
            return {}

        return {
            "background-color": background_color,
            "border-color": background_color,
            "color": self._text_color,
            "width": "100%",
        }

    def _header_html(self, expanded: bool, background_color: str | None) -> str:
        prefix = self._EXPANDED_PREFIX if expanded else self._COLLAPSED_PREFIX
        color = background_color or "transparent"

        return f"""
        <div style="
            align-items: center;
            background-color: {color};
            border: 1px solid {color};
            border-radius: 4px;
            box-sizing: border-box;
            color: {self._text_color};
            cursor: pointer;
            display: flex;
            font-family: inherit;
            font-size: 14px;
            height: 38px;
            justify-content: center;
            line-height: 38px;
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
