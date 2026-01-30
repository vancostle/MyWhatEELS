import panel as pn
import threading

pane = pn.pane.Markdown("Initial value")

def update():
    def set_value():
        pane.object = "Updated!"
    pn.io.state.curdoc.add_next_tick_callback(set_value)

threading.Thread(target=update).start()

pane.servable()