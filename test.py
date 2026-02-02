import panel as pn
import threading
import time

pn.extension()

stop_event = threading.Event()
status = pn.pane.Markdown("**Status:** Not started", width=300)


def long_running_task():
    status.object = "**Status:** Running..."
    for i in range(100):
        if stop_event.is_set():
            status.object = f"**Status:** Cancelled at step {i}"
            return
        time.sleep(0.1)  # Simulate work
        status.object = f"**Status:** Step {i+1}/100"
    status.object = "**Status:** Completed!"


def start_thread(event=None):
    stop_event.clear()
    threading.Thread(target=long_running_task, daemon=True).start()

def cancel_thread(event=None):
    stop_event.set()

start_btn = pn.widgets.Button(name="Start Task", button_type="primary")
cancel_btn = pn.widgets.Button(name="Cancel Task", button_type="danger")
start_btn.on_click(start_thread)
cancel_btn.on_click(cancel_thread)

layout = pn.Column(
    pn.Row(start_btn, cancel_btn),
    status
)

layout.servable()
