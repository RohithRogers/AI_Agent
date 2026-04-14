"""
GUI/components.py  –  Async-friendly Flet 0.84 controls
"""
from __future__ import annotations
import re
import asyncio
import flet as ft
from GUI.theme import (
    ACCENT, ACCENT_ALT, ACCENT_GLOW,
    USER_BUBBLE, AGENT_BUBBLE, TERMINAL_BG, TERMINAL_FG,
    SURFACE, SURFACE_CARD, SURFACE_HOVER, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    SUCCESS, WARNING, ERROR, INFO,
    FONT_MONO, FONT_UI,
    RADIUS_SM, RADIUS_MD, RADIUS_LG, RADIUS_XL,
)

# ─────────────────────────────────────────────────────────
#  ANSI stripper
# ─────────────────────────────────────────────────────────
_ANSI_RE = re.compile(r"\x1B\[[0-9;]*m")

def strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


# ─────────────────────────────────────────────────────────
#  Logo
# ─────────────────────────────────────────────────────────
def build_logo() -> ft.Container:
    return ft.Container(
        content=ft.Column(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME, color=ACCENT_GLOW, size=22),
                        ft.Text(
                            " FREE CODE",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=TEXT_PRIMARY,
                            font_family=FONT_UI,
                        ),
                    ],
                    tight=True,
                    spacing=4,
                ),
                ft.Text(
                    "AI Agent",
                    size=11,
                    color=TEXT_DIM,
                    font_family=FONT_UI,
                    italic=True,
                ),
            ],
            spacing=2,
            tight=True,
        ),
        padding=ft.Padding.symmetric(horizontal=16, vertical=14),
    )


# ─────────────────────────────────────────────────────────
#  StatusChip
# ─────────────────────────────────────────────────────────
class StatusChip:
    IDLE  = ("Idle",        ft.Icons.CIRCLE,          SUCCESS)
    THINK = ("Thinking",    ft.Icons.PSYCHOLOGY,       ACCENT)
    TOOL  = ("Tool Running",ft.Icons.BUILD_CIRCLE,     WARNING)
    ERR   = ("Error",       ft.Icons.ERROR_OUTLINE,    ERROR)

    def __init__(self):
        self._dot   = ft.Icon(self.IDLE[1], color=self.IDLE[2], size=14)
        self._dot.animate_opacity = 500
        self._label = ft.Text(self.IDLE[0], size=12, color=self.IDLE[2])
        self.control = ft.Container(
            content=ft.Row([self._dot, self._label], spacing=6, tight=True),
            bgcolor=SURFACE_CARD,
            border_radius=RADIUS_SM,
            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            border=ft.Border.all(1, BORDER),
        )

    def update_state(self, state: tuple, page: ft.Page):
        """Note: Caller should handle page.update_async() if in async mode."""
        self._dot.name    = state[1]
        self._dot.color   = state[2]
        self._label.value = state[0]
        self._label.color = state[2]
        
        # Start pulse if not idle
        if state[0] != "Idle":
            self._dot.opacity = 0.3
        else:
            self._dot.opacity = 1.0


# ─────────────────────────────────────────────────────────
#  Sidebar helpers
# ─────────────────────────────────────────────────────────
def nav_button(icon, label, on_click=None, active=False) -> ft.Container:
    color = ACCENT_GLOW if active else TEXT_SECONDARY
    return ft.Container(
        content=ft.Row(
            [
                ft.Icon(icon, color=color, size=16),
                ft.Text(label, size=13, color=color, font_family=FONT_UI),
            ],
            spacing=10,
            tight=True,
        ),
        bgcolor=SURFACE_HOVER if active else "transparent",
        border_radius=RADIUS_SM,
        padding=ft.Padding.symmetric(horizontal=12, vertical=9),
        on_click=on_click,
        ink=True,
    )


def sidebar_divider() -> ft.Container:
    return ft.Container(
        height=1,
        bgcolor=BORDER,
        margin=ft.Margin.symmetric(vertical=6, horizontal=8),
    )


# ─────────────────────────────────────────────────────────
#  ChatMessage
# ─────────────────────────────────────────────────────────
class ChatMessage:
    def __init__(self, role: str, content: str = "", is_thought: bool = False):
        self.role       = role
        self.content    = content
        self.is_thought = is_thought
        self._md:  ft.Markdown | None  = None
        self.control: ft.Container | None = None
        self._build()

    def set_content(self, text: str, page: ft.Page):
        self.content = text
        if self._md:
            self._md.value = text or " "

    def _build(self):
        if self.role == "tool_call":
            self._build_tool()
            return
        if self.is_thought:
            self._build_thought()
            return

        is_user = (self.role == "user")
        avatar  = ft.Container(
            content=ft.Icon(
                ft.Icons.PERSON if is_user else ft.Icons.AUTO_AWESOME,
                color=ACCENT_ALT if is_user else ACCENT,
                size=16,
            ),
            width=32, height=32,
            bgcolor=SURFACE_CARD,
            border_radius=16,
            border=ft.Border.all(1, BORDER),
            alignment=ft.Alignment(0, 0),
        )

        self._md = ft.Markdown(
            value=self.content or " ",
            selectable=True,
            extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
            code_theme="atom-one-dark",
        )

        bubble = ft.Container(
            content=self._md,
            bgcolor=USER_BUBBLE if is_user else AGENT_BUBBLE,
            border_radius=ft.BorderRadius.only(
                top_left=RADIUS_MD,
                top_right=RADIUS_MD,
                bottom_left=2 if is_user else RADIUS_MD,
                bottom_right=RADIUS_MD if is_user else 2,
            ),
            border=ft.Border.all(1, BORDER),
            padding=14,
            expand=True,
        )

        name = ft.Text(
            "You" if is_user else "Agent",
            size=11, color=TEXT_DIM,
        )
        col  = ft.Column([name, bubble], spacing=4, tight=True, expand=True)
        row  = ft.Row(
            [col, avatar] if is_user else [avatar, col],
            alignment=ft.MainAxisAlignment.END if is_user else ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.START,
            spacing=10,
        )
        self.control = ft.Container(
            content=row,
            padding=ft.Padding.symmetric(horizontal=16, vertical=6),
        )

    def _build_tool(self):
        self._md = ft.Markdown(
            value=f"```json\n{self.content}\n```",
            selectable=True,
            code_theme="atom-one-dark",
        )
        inner = ft.Container(
            content=self._md,
            padding=ft.Padding.only(left=16, right=8, top=4, bottom=8),
        )
        self.control = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.BUILD_OUTLINED, color=WARNING, size=14),
                                ft.Text("Tool Call", size=12, color=WARNING, weight=ft.FontWeight.BOLD),
                            ],
                            spacing=6, tight=True,
                        ),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                    inner,
                ],
                spacing=0,
            ),
            margin=ft.Margin.symmetric(horizontal=16, vertical=4),
            border_radius=RADIUS_SM,
            border=ft.Border.all(1, WARNING),
            bgcolor=SURFACE_CARD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )

    def _build_thought(self):
        self._md = ft.Markdown(
            value=self.content or " ",
            selectable=True,
            code_theme="atom-one-dark",
        )
        inner = ft.Container(
            content=self._md,
            padding=ft.Padding.only(left=16, right=8, top=4, bottom=8),
        )
        self.control = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(ft.Icons.PSYCHOLOGY_ALT, color=ACCENT, size=14),
                                ft.Text("Reasoning", size=12, color=ACCENT, italic=True),
                            ],
                            spacing=6, tight=True,
                        ),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                    inner,
                ],
                spacing=0,
            ),
            margin=ft.Margin.symmetric(horizontal=16, vertical=4),
            border_radius=RADIUS_SM,
            border=ft.Border.all(1, ACCENT),
            bgcolor=SURFACE_CARD,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )


# ─────────────────────────────────────────────────────────
#  TerminalView
# ─────────────────────────────────────────────────────────
class TerminalView:
    MAX_LINES = 300

    def __init__(self):
        self._lines: list[str]       = []
        self._text:  ft.Text | None  = None
        self._cmd:   ft.Text | None  = None
        self.control = self._build()

    def _build(self) -> ft.Container:
        self._cmd  = ft.Text("Ready", color=TEXT_DIM, size=12, font_family=FONT_MONO, weight=ft.FontWeight.BOLD)
        self._text = ft.Text("",      color=TERMINAL_FG, size=12, font_family=FONT_MONO, selectable=True, no_wrap=False)

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Row(
                                    [
                                        ft.Container(width=12, height=12, bgcolor="#FF5F57", border_radius=6),
                                        ft.Container(width=12, height=12, bgcolor="#FEBC2E", border_radius=6),
                                        ft.Container(width=12, height=12, bgcolor="#28C840", border_radius=6),
                                    ],
                                    spacing=6,
                                ),
                                ft.Text("  PowerShell", size=12, color=TEXT_DIM, font_family=FONT_MONO),
                                ft.Container(expand=True),
                                self._cmd,
                            ],
                        ),
                        bgcolor="#0F1218",
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                    ),
                    ft.Divider(height=1, color=BORDER),
                    ft.Container(
                        content=ft.Column(
                            [self._text],
                            scroll=ft.ScrollMode.AUTO,
                        ),
                        expand=True,
                        padding=ft.Padding.symmetric(horizontal=14, vertical=8),
                    ),
                ],
                spacing=0,
                expand=True,
            ),
            bgcolor=TERMINAL_BG,
            border=ft.Border.all(1, BORDER),
            border_radius=ft.BorderRadius.only(top_left=RADIUS_SM, top_right=RADIUS_SM),
            expand=True,
        )

    def set_command(self, cmd: str, page: ft.Page):
        self._lines = []
        self._cmd.value  = f"❯ {cmd}"
        self._cmd.color  = ACCENT
        self._text.value = ""

    def append_output(self, chunk: str, page: ft.Page):
        chunk = strip_ansi(chunk)
        for line in chunk.splitlines(keepends=True):
            self._lines.append(line.rstrip("\n"))
        if len(self._lines) > self.MAX_LINES:
            self._lines = self._lines[-self.MAX_LINES:]
        self._text.value = "\n".join(self._lines)

    def clear(self, page: ft.Page):
        self._lines = []
        self._cmd.value  = "Ready"
        self._cmd.color  = TEXT_DIM
        self._text.value = ""


# ─────────────────────────────────────────────────────────
#  PillToggle
# ─────────────────────────────────────────────────────────
class PillToggle:
    def __init__(self, options: list[str], on_change=None, initial: int = 0):
        self.options   = options
        self.on_change = on_change
        self.selected  = initial
        self._btns: list[ft.Container] = []
        self.control   = self._build()

    def _build(self) -> ft.Container:
        self._btns = []
        for i, opt in enumerate(self.options):
            active = (i == self.selected)
            btn = ft.Container(
                content=ft.Text(opt, size=12, color=TEXT_PRIMARY if active else TEXT_DIM),
                bgcolor=ACCENT if active else "transparent",
                border_radius=RADIUS_LG,
                padding=ft.Padding.symmetric(horizontal=14, vertical=6),
                on_click=self._on_btn_click,
                data=i,
                ink=True,
            )
            self._btns.append(btn)

        return ft.Container(
            content=ft.Row(self._btns, spacing=2, tight=True),
            bgcolor=SURFACE_CARD,
            border_radius=RADIUS_LG,
            border=ft.Border.all(1, BORDER),
            padding=3,
        )

    async def _on_btn_click(self, e):
        await self._select(e.control.data)

    async def _select(self, idx: int):
        old = self.selected
        self.selected = idx
        self._btns[old].bgcolor         = "transparent"
        self._btns[old].content.color   = TEXT_DIM
        self._btns[idx].bgcolor         = ACCENT
        self._btns[idx].content.color   = TEXT_PRIMARY
        
        # In async flet, the container must be updated manually or by the parent
        page = self.control.page
        if page:
            page.update()

        if self.on_change:
            if asyncio.iscoroutinefunction(self.on_change):
                await self.on_change(self.options[idx])
            else:
                self.on_change(self.options[idx])


# ─────────────────────────────────────────────────────────
#  Permission dialog
# ─────────────────────────────────────────────────────────
def build_permission_dialog(tool_name: str, params: str, on_approve, on_deny) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        title=ft.Row(
            [
                ft.Icon(ft.Icons.SHIELD_OUTLINED, color=WARNING, size=20),
                ft.Text(" Permission Required", color=TEXT_PRIMARY, size=16, weight=ft.FontWeight.BOLD),
            ],
        ),
        content=ft.Column(
            [
                ft.Text(f"Tool:  {tool_name}", color=ACCENT, size=13, weight=ft.FontWeight.BOLD),
                ft.Container(height=6),
                ft.Text("Parameters:", color=TEXT_SECONDARY, size=12),
                ft.Container(
                    content=ft.Text(
                        params[:400], color=TERMINAL_FG, size=12,
                        font_family=FONT_MONO, selectable=True,
                    ),
                    bgcolor=TERMINAL_BG,
                    border_radius=RADIUS_SM,
                    padding=10,
                ),
            ],
            tight=True,
            spacing=6,
            width=420,
        ),
        bgcolor=SURFACE,
        actions=[
            ft.TextButton("Deny",   on_click=on_deny,    style=ft.ButtonStyle(color=ERROR)),
            ft.FilledButton("Allow", on_click=on_approve, style=ft.ButtonStyle(bgcolor=ACCENT)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        shape=ft.RoundedRectangleBorder(radius=RADIUS_MD),
    )


# ─────────────────────────────────────────────────────────
#  Input area factory
# ─────────────────────────────────────────────────────────
def build_input_area(
    text_field: ft.TextField,
    on_send,
    on_attach,
    on_voice,
    attached_files: list[str],
    page: ft.Page | None = None,
) -> ft.Container:
    chips = [
        ft.Chip(
            label=ft.Text(p.split("\\")[-1], size=11),
            delete_icon_color=ERROR,
            bgcolor=SURFACE_CARD,
            label_style=ft.TextStyle(color=TEXT_SECONDARY),
        )
        for p in attached_files
    ]

    return ft.Container(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Row(chips, wrap=True, spacing=4),
                    padding=ft.Padding.only(left=12, top=6) if attached_files else ft.Padding.all(0),
                    visible=bool(attached_files),
                ),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.ATTACH_FILE,
                                tooltip="Attach file",
                                on_click=on_attach,
                                icon_color=TEXT_SECONDARY,
                                icon_size=20,
                            ),
                            ft.IconButton(
                                ft.Icons.MIC_NONE,
                                tooltip="Voice input",
                                on_click=on_voice,
                                icon_color=TEXT_SECONDARY,
                                icon_size=20,
                            ),
                            text_field,
                            ft.IconButton(
                                ft.Icons.SEND_ROUNDED,
                                tooltip="Send  (Ctrl+Enter)",
                                on_click=on_send,
                                icon_color=ACCENT,
                                icon_size=22,
                            ),
                        ],
                        spacing=4,
                        vertical_alignment=ft.CrossAxisAlignment.END,
                    ),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=8),
                ),
            ],
            spacing=0,
        ),
        bgcolor=SURFACE,
        border=ft.Border.only(top=ft.BorderSide(1, BORDER)),
    )
