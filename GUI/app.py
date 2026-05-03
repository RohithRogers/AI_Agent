"""
GUI/app.py  ─  Premium AI Agent GUI  (Async Flet 0.84)
Run:  python GUI/app.py
"""
from __future__ import annotations
import sys
import os
import re
import threading
import asyncio
import json

# ── project root on path ──────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── register tools ────────────────────────────────────────
from tools import (
    time_tool, file_tool, program_run_tool,
    python_repl_tool, git_tool, doc_tool,
    browser_tool, ppt_tool, code_tool, skill_tool,
    workspace_tool,
)

import flet as ft
from agents.chat_agent import ChatAgent
from GUI.theme import (
    ACCENT, ACCENT_ALT, ACCENT_GLOW,
    SURFACE, SURFACE_DIM, SURFACE_CARD, SURFACE_HOVER, BORDER,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_DIM,
    SUCCESS, WARNING, ERROR,
    FONT_MONO, FONT_UI,
    RADIUS_SM, RADIUS_MD, RADIUS_LG,
    build_theme,
)
from GUI.components import (
    ChatMessage, TerminalView, StatusChip, PillToggle,
    build_logo, nav_button, sidebar_divider,
    build_permission_dialog, build_input_area,
    strip_ansi,
)

# ─────────────────────────────────────────────────────────
SIDEBAR_W   = 245
TERMINAL_H  = 220

CHAT_MODE_PROMPT = (
    "You are the helpful AI assistant 'Synthic'. You are in CHAT mode and do NOT have access to tools. "
    "Focus on conversation and answering questions."
)
RUN_MODE_PROMPT = (
    "You are the powerful AI Agent 'Synthic' with full access to system tools. "
    "Use them to help the user complete their tasks."
)

# ─────────────────────────────────────────────────────────
async def main(page: ft.Page):
    # ── Page config ───────────────────────────────────────
    page.title        = "Synthic – AI Agent"
    page.theme_mode   = ft.ThemeMode.DARK
    page.theme        = build_theme()
    page.bgcolor      = SURFACE_DIM
    page.padding      = 0
    page.window_width  = 1200
    page.window_height = 780
    page.window_min_width  = 820
    page.window_min_height = 560
    page.fonts         = {}

    # ── Agent ─────────────────────────────────────────────
    agent = ChatAgent(system_prompt=CHAT_MODE_PROMPT, mode="offline", tools_enabled=False)
    agent.auto_route  = False
    agent.manual_mode = False

    attachments:          list[str] = []
    permission_event                 = threading.Event()
    permission_approved              = [False]

    # ── Shared state ──────────────────────────────────────
    agent_bubble: list[ChatMessage | None]  = [None]
    thought_bubble: list[ChatMessage | None] = [None]
    terminal_open = [False]

    # ─────────────────────────────────────────────────────
    #  Child controls (constructed once)
    # ─────────────────────────────────────────────────────
    status_chip   = StatusChip()
    terminal_view = TerminalView()

    # ── Chat list ─────────────────────────────────────────
    chat_column = ft.ListView(
        expand=True,
        spacing=0,
        auto_scroll=True,
        padding=ft.Padding.symmetric(vertical=8),
    )

    # ── Input field ───────────────────────────────────────
    input_field = ft.TextField(
        hint_text="Message the agent…  (Ctrl+Enter to send)",
        hint_style=ft.TextStyle(color=TEXT_DIM),
        bgcolor=SURFACE_CARD,
        border_color=BORDER,
        focused_border_color=ACCENT,
        border_radius=RADIUS_MD,
        color=TEXT_PRIMARY,
        multiline=True,
        min_lines=1,
        max_lines=8,
        expand=True,
        text_size=14,
        content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
        cursor_color=ACCENT,
    )

    # ── Model dropdown ────────────────────────────────────
    model_dd = ft.Dropdown(
        hint_text="Select model",
        options=[
            ft.dropdown.Option("deepseek-coder"),
            ft.dropdown.Option("functiongemma"),
        ],
        value="deepseek-coder",
        bgcolor=SURFACE_CARD,
        border_color=BORDER,
        focused_border_color=ACCENT,
        color=TEXT_PRIMARY,
        hint_style=ft.TextStyle(color=TEXT_DIM),
        text_size=13,
        content_padding=ft.Padding.symmetric(horizontal=10, vertical=6),
    )

    async def on_model_change(e):
        if model_dd.value:
            agent.set_model(model_dd.value)

    model_dd.on_change = on_model_change

    # ── Snack helper ──────────────────────────────────────
    async def show_snack(msg: str, color: str = ACCENT):
        page.snack_bar = ft.SnackBar(
            content=ft.Text(msg, color=TEXT_PRIMARY),
            bgcolor=color,
            action="OK",
        )
        page.snack_bar.open = True
        page.update()

    # ── Mode toggles ──────────────────────────────────────
    async def on_conn_change(val: str):
        if val == "Online":
            agent.set_mode("online")
            model_dd.options.clear()
            for m in agent.online_models:
                model_dd.options.append(ft.dropdown.Option(m))
            model_dd.value = agent.model
        else:
            agent.set_mode("offline")
            model_dd.options = [
                ft.dropdown.Option("deepseek-coder"),
                ft.dropdown.Option("functiongemma"),
            ]
            model_dd.value = "deepseek-coder"
        page.update()

    async def on_route_change(val: str):
        agent.auto_route  = (val == "Auto")
        agent.manual_mode = (val == "Manual")

    async def on_chat_mode_change(val: str):
        if val == "Chat":
            agent.set_tools_enabled(False)
            agent.set_system_prompt(CHAT_MODE_PROMPT)
        else:
            agent.set_tools_enabled(True)
            agent.set_system_prompt(RUN_MODE_PROMPT)

    conn_toggle      = PillToggle(["Offline", "Online"], on_change=on_conn_change,      initial=0)
    route_toggle     = PillToggle(["Manual",  "Auto"],   on_change=on_route_change,     initial=0)
    chatmode_toggle  = PillToggle(["Chat",    "Run"],    on_change=on_chat_mode_change, initial=0)

    # ── Status bar text ───────────────────────────────────
    status_bar_text = ft.Text("", size=12, color=TEXT_DIM, italic=True)

    async def set_status(msg: str):
        status_bar_text.value = f"⚡ {msg}" if msg else ""
        page.update()

    # ── Terminal toggle ───────────────────────────────────
    terminal_container = ft.Container(
        content=terminal_view.control,
        height=TERMINAL_H,
        visible=False,
    )

    terminal_icon_btn = ft.IconButton(
        ft.Icons.TERMINAL,
        tooltip="Toggle terminal",
        icon_color=TEXT_SECONDARY,
        icon_size=18,
    )

    async def toggle_terminal(e=None):
        terminal_open[0] = not terminal_open[0]
        terminal_container.visible = terminal_open[0]
        terminal_icon_btn.icon = (
            ft.Icons.KEYBOARD_ARROW_DOWN if terminal_open[0] else ft.Icons.TERMINAL
        )
        page.update()

    terminal_icon_btn.on_click = toggle_terminal

    # ── Clear chat ────────────────────────────────────────
    async def clear_chat(e=None):
        if hasattr(agent, "clear_history"):
            agent.clear_history()
        else:
            agent.messages = [{"role": "system", "content": agent.base_system_prompt + agent.tools_prompt}]
        chat_column.controls.clear()
        terminal_view.clear(page) # Assuming terminal_view.clear is still sync as it was and handles page.update internally or via return
        agent_bubble[0]  = None
        thought_bubble[0] = None
        page.update()

    # ── File picker (DISABLED) ────────────────────────────
    async def on_attach(e=None):
        await show_snack("File picker is temporarily disabled", WARNING)

    # ── Voice ─────────────────────────────────────────────
    async def on_voice(e=None):
        try:
            from tools.voice_handler import get_voice_input
            # Voice handler is still sync/threaded usually, but we can wrap it
            text = await asyncio.to_thread(get_voice_input)
            if text:
                input_field.value = text
                page.update()
        except Exception as ex:
            await show_snack(f"Voice error: {ex}", ERROR)

    # ── Input area (rebuilt on attachment change) ─────────
    input_row_ref: list[ft.Container] = [ft.Container()]

    async def rebuild_input():
        input_row_ref[0].content = build_input_area(
            input_field, on_send, on_attach, on_voice, attachments
        )

    # ── Permission dialog ─────────────────────────────────
    async def ask_permission(tool_name: str, params: str):
        async def approve(e):
            permission_approved[0] = True
            dlg.open = False
            page.update()
            permission_event.set()

        async def deny(e):
            permission_approved[0] = False
            dlg.open = False
            page.update()
            permission_event.set()

        dlg = build_permission_dialog(tool_name, params, approve, deny)
        page.overlay.append(dlg)
        dlg.open = True
        page.update()

    # ── Send ──────────────────────────────────────────────
    async def on_send(e=None):
        text = (input_field.value or "").strip()
        if not text:
            return
        input_field.value = ""
        page.update()

        attached_copy = attachments.copy()
        attachments.clear()
        await rebuild_input()

        # user bubble
        umsg = ChatMessage("user", text)
        chat_column.controls.append(umsg.control)
        page.update()

        # Run agent in thread because it's synchronous logic
        threading.Thread(
            target=run_agent_sync,
            args=(text, attached_copy),
            daemon=True,
        ).start()

    # ── Agent runner (Async main loop with threaded blocking calls) ──
    async def run_agent_async_loop(text: str, attached: list[str]):
        """Runs the agent entirely in the async event loop, offloading blocking calls to threads."""
        agent_bubble[0]   = None
        thought_bubble[0] = None
        
        await _set_busy(True)
        await _update_status_chip(StatusChip.THINK)

        is_thought_mode = False
        full_response   = ""
        thought_content = ""

        try:
            # Create the generator
            gen = await asyncio.to_thread(agent.run, text, attachments=attached)
            
            # Start the loop
            chunk = await asyncio.to_thread(next, gen)
            
            while True:
                if chunk is None:
                    try:
                        chunk = await asyncio.to_thread(next, gen)
                    except StopIteration:
                        break
                    continue

                # permission
                if isinstance(chunk, str) and chunk.startswith("__ASK_PERMISSION__"):
                    parts       = chunk.split(":", 2)
                    tool_name   = parts[1]
                    params_json = parts[2]
                    permission_event.clear()
                    await ask_permission(tool_name, params_json)
                    # Block waiting for UI interaction (offloaded to thread)
                    await asyncio.to_thread(permission_event.wait, 60)
                    # Resume generator and capture NEXT chunk
                    chunk = await asyncio.to_thread(gen.send, permission_approved[0])
                    continue

                # status
                elif isinstance(chunk, str) and chunk.startswith("__UI_STATUS__"):
                    raw = chunk.replace("__UI_STATUS__:", "")
                    if raw.startswith("EXEC_CMD:"):
                        cmd = raw.replace("EXEC_CMD:", "")
                        await _update_status_chip(StatusChip.TOOL)
                        await _open_terminal(cmd)
                    else:
                        clean = re.sub(r"\[/?[^\]]*\]", "", raw)
                        await set_status(clean)

                # tool call
                elif isinstance(chunk, str) and chunk.startswith("__TOOL_CALL__"):
                    parts = chunk.split(":", 2)
                    tool_name = parts[1]
                    params = json.loads(parts[2])
                    await _show_tool_call(tool_name, params)
                
                # tool result
                elif isinstance(chunk, str) and chunk.startswith("__TOOL_RESULT__"):
                    parts = chunk.split(":", 2)
                    tool_name = parts[1]
                    tool_result = parts[2]
                    # We can optionally show this as a separate bubble or append to current
                    full_response += f"\n\n🛠️ **Tool [{tool_name}] Result:**\n{tool_result}\n"
                    await _update_agent_bubble(full_response)

                # terminal stream
                elif isinstance(chunk, str) and chunk.startswith("__TOOL_STREAM__"):
                    out = chunk.replace("__TOOL_STREAM__:", "")
                    await _append_terminal(out)

                # regular text / thought
                else:
                    if "<thought>" in chunk:
                        is_thought_mode = True
                    
                    if is_thought_mode:
                        thought_content += chunk
                        if "</thought>" in chunk:
                            is_thought_mode = False
                        inner = re.sub(r"</?thought>", "", thought_content)
                        await _update_thought(inner.strip())
                    else:
                        full_response += chunk
                        await _update_agent_bubble(full_response)
                
                # Fetch next chunk
                try:
                    chunk = await asyncio.to_thread(next, gen)
                except StopIteration:
                    await show_snack("Response complete", SUCCESS)
                    break

        except Exception as ex:
            import traceback
            traceback.print_exc()
            await show_snack(f"Agent error: {ex}", ERROR)
        finally:
            await _update_status_chip(StatusChip.IDLE)
            await set_status("")
            await _set_busy(False)

    def run_agent_sync(text: str, attached: list[str]):
        """Legacy bridge to the new async loop."""
        page.run_task(run_agent_async_loop, text, attached)

    async def _set_busy(busy: bool):
        input_field.disabled = busy
        input_field.hint_text = "Agent is working..." if busy else "Message the agent…  (Ctrl+Enter to send)"
        await rebuild_input()
        page.update()

    async def _update_status_chip(state):
        status_chip.update_state(state, page)
        page.update()

    async def _show_tool_call(tool_name: str, params: dict):
        bbl = ChatMessage("tool_call", json.dumps({"tool": tool_name, "params": params}, indent=2))
        chat_column.controls.append(bbl.control)
        page.update()

    # ── UI Task helpers (Async) ───────────────────────────
    async def _open_terminal(cmd: str):
        terminal_view.set_command(cmd, page)
        if not terminal_open[0]:
            await toggle_terminal()

    async def _append_terminal(out: str):
        terminal_view.append_output(out, page)

    async def _update_agent_bubble(response: str):
        if agent_bubble[0] is None:
            bbl = ChatMessage("agent", response)
            agent_bubble[0] = bbl
            chat_column.controls.append(bbl.control)
        else:
            agent_bubble[0].set_content(response, page)
        page.update()

    async def _update_thought(inner: str):
        if thought_bubble[0] is None:
            bbl = ChatMessage("agent", inner, is_thought=True)
            thought_bubble[0] = bbl
            ctrl = agent_bubble[0].control if agent_bubble[0] else None
            if ctrl and ctrl in chat_column.controls:
                idx = chat_column.controls.index(ctrl)
                chat_column.controls.insert(idx, bbl.control)
            else:
                chat_column.controls.append(bbl.control)
        else:
            thought_bubble[0].set_content(inner, page)
        page.update()

    # ── Keyboard shortcut ─────────────────────────────────
    async def on_keyboard(e: ft.KeyboardEvent):
        if e.key == "Enter" and e.ctrl:
            await on_send()

    page.on_keyboard_event = on_keyboard

    # ── Save / New chat ───────────────────────────────────
    async def on_save(e=None):
        import json, time
        fname = f"chat_save_{int(time.time())}.json"
        
        msgs_to_save = []
        if hasattr(agent, "context") and hasattr(agent.context, "messages"):
            # ContextManager is being used
            msgs_to_save = [m for m in agent.context.messages if m.get("role") != "system"]
        elif hasattr(agent, "messages"):
            msgs_to_save = [m for m in agent.messages if m.get("role") != "system"]
            
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(msgs_to_save, f, indent=2, default=str)
        await show_snack(f"Saved → {fname}", SUCCESS)

    # ─────────────────────────────────────────────────────
    #  SIDEBAR
    # ─────────────────────────────────────────────────────
    sidebar = ft.Container(
        content=ft.Column(
            [
                build_logo(),
                sidebar_divider(),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Connection", size=11, color=TEXT_DIM, weight=ft.FontWeight.W_500),
                            conn_toggle.control,
                            ft.Container(height=6),
                            ft.Text("Routing", size=11, color=TEXT_DIM, weight=ft.FontWeight.W_500),
                            route_toggle.control,
                            ft.Container(height=6),
                            ft.Text("Mode", size=11, color=TEXT_DIM, weight=ft.FontWeight.W_500),
                            chatmode_toggle.control,
                            ft.Container(height=6),
                            ft.Text("Model", size=11, color=TEXT_DIM, weight=ft.FontWeight.W_500),
                            model_dd,
                        ],
                        spacing=6,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                ),
                sidebar_divider(),
                nav_button(ft.Icons.ADD_COMMENT_OUTLINED, "New Chat",  on_click=clear_chat),
                nav_button(ft.Icons.SAVE_OUTLINED,        "Save Chat", on_click=on_save),
                sidebar_divider(),
                ft.Container(expand=True),
                sidebar_divider(),
                ft.Container(
                    content=status_chip.control,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                ),
            ],
            spacing=2,
            expand=True,
        ),
        width=SIDEBAR_W,
        bgcolor=SURFACE,
        border=ft.Border.only(right=ft.BorderSide(1, BORDER)),
    )

    # ─────────────────────────────────────────────────────
    #  TOP BAR
    # ─────────────────────────────────────────────────────
    top_bar = ft.Container(
        content=ft.Row(
            [
                ft.Row(
                    [
                        ft.Icon(ft.Icons.AUTO_AWESOME, color=ACCENT_GLOW, size=16),
                        ft.Text("Synthic", size=15, weight=ft.FontWeight.BOLD, color=TEXT_PRIMARY),
                    ],
                    spacing=6, tight=True,
                ),
                ft.Container(expand=True),
                status_bar_text,
                ft.Container(width=6),
                terminal_icon_btn,
                ft.IconButton(
                    ft.Icons.DELETE_SWEEP_OUTLINED,
                    tooltip="Clear conversation",
                    icon_color=TEXT_SECONDARY,
                    icon_size=18,
                    on_click=clear_chat,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        bgcolor=SURFACE,
        border=ft.Border.only(bottom=ft.BorderSide(1, BORDER)),
        padding=ft.Padding.symmetric(horizontal=16, vertical=10),
    )

    # ─────────────────────────────────────────────────────
    #  INPUT ROW
    # ─────────────────────────────────────────────────────
    await rebuild_input()

    # ─────────────────────────────────────────────────────
    #  RIGHT PANEL
    # ─────────────────────────────────────────────────────
    right_panel = ft.Column(
        [
            top_bar,
            chat_column,
            terminal_container,
            ft.Divider(height=1, color=BORDER),
            input_row_ref[0],
        ],
        spacing=0,
        expand=True,
    )

    # ─────────────────────────────────────────────────────
    #  ROOT
    # ─────────────────────────────────────────────────────
    page.add(
        ft.Row(
            [
                sidebar,
                ft.VerticalDivider(width=1, color=BORDER),
                right_panel,
            ],
            spacing=0,
            expand=True,
            vertical_alignment=ft.CrossAxisAlignment.START,
        )
    )

    # Add overlays
    # page.overlay.append(file_picker)
    page.update()


# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    ft.run(main)
