const ROW_SELECTOR = '.whateels-split-row';
const PANE_SELECTOR = '.whateels-split-pane';
const DEFAULT_MIN_PANE = 160;
const DIV = 'div';

export const render = ({ model }) => {
    // Deliberately not `drag-gutter`: Panel already gives its own container
    // div that class, derived from the Python class name.
    const gutter = document.createElement(DIV);
    gutter.classList.add('whateels-drag-gutter');

    // Resolved lazily. At render time this element is not in the document yet,
    // so neither the surrounding row nor its panes can be located.
    let context = null;
    let dragging = false;
    let row_rect = null;

    const resolve_context = () => {
        if (context !== null) {
            return context;
        }
        const row = closest_across_shadow(gutter, ROW_SELECTOR);
        if (row === null) {
            return null;
        }
        const panes = find_panes(row);
        if (panes === null) {
            return null;
        }
        context = { row: row, left: panes[0], right: panes[1] };
        return context;
    };

    const apply_ratio = (ratio) => {
        // Proportional flex-grow over a zero basis. The panes keep the dragged
        // ratio when the window or the surrounding stack changes size, and no
        // percentage has to be resolved against a box this component does not
        // own. Inline declarations also outrank the ``:host`` rule Bokeh writes
        // inside each pane's own shadow root, so nothing has to be re-applied.
        context.left.style.flex = ratio + ' 1 0px';
        context.right.style.flex = (1 - ratio) + ' 1 0px';
        context.left.style.minWidth = '0';
        context.right.style.minWidth = '0';
    };

    const stop_drag = (event) => {
        if (!dragging) {
            return;
        }
        dragging = false;
        gutter.classList.remove('dragging');
        try {
            gutter.releasePointerCapture(event.pointerId);
        } catch (error) {
            // The capture is already gone; nothing left to release.
        }
        if (context !== null) {
            context.row.style.userSelect = '';
        }
    };

    gutter.addEventListener('pointerdown', (event) => {
        if (event.button !== 0) {
            return;
        }
        const ctx = resolve_context();
        if (ctx === null) {
            return;
        }
        row_rect = ctx.row.getBoundingClientRect();
        if (!(row_rect.width > 0)) {
            return;
        }
        dragging = true;
        gutter.classList.add('dragging');
        ctx.row.style.userSelect = 'none';
        // Pointer capture keeps the drag alive over the Bokeh canvases, whose
        // own tools would otherwise swallow every move event.
        try {
            gutter.setPointerCapture(event.pointerId);
        } catch (error) {
            // Without capture the drag still works while the pointer stays
            // over the gutter, which is better than refusing to start.
        }
        event.preventDefault();
    });

    gutter.addEventListener('pointermove', (event) => {
        if (!dragging || context === null) {
            return;
        }
        const gutter_width = gutter.getBoundingClientRect().width || 0;
        const available = row_rect.width - gutter_width;
        if (!(available > 0)) {
            return;
        }
        const min_pane = Math.min(min_pane_size(model), available / 2);
        const raw = event.clientX - row_rect.left - gutter_width / 2;
        const left_px = Math.max(min_pane, Math.min(available - min_pane, raw));
        apply_ratio(left_px / available);
    });

    gutter.addEventListener('pointerup', stop_drag);
    gutter.addEventListener('pointercancel', stop_drag);

    // Restore the even split. Dropping the inline declarations hands the panes
    // back to the sizing Panel/Bokeh gave them, without a server round trip.
    gutter.addEventListener('dblclick', () => {
        const ctx = resolve_context();
        if (ctx === null) {
            return;
        }
        ctx.left.style.flex = '';
        ctx.right.style.flex = '';
    });

    return gutter;
}

const min_pane_size = (model) => {
    const value = Number(model.min_pane_size);
    return Number.isFinite(value) && value > 0 ? value : DEFAULT_MIN_PANE;
}

// Panel renders every layout child inside its own shadow root, so neither
// `closest()` nor a document-level query reaches the surrounding Panel Row.
const closest_across_shadow = (node, selector) => {
    let current = node;
    while (current) {
        if (current.nodeType === Node.ELEMENT_NODE && current.matches(selector)) {
            return current;
        }
        // A ShadowRoot has no parentNode; step out through its host instead.
        current = current.parentNode || current.host || null;
    }
    return null;
}

// The panes are direct children of the row's shadow root. The row element
// itself is only searched as a fallback for a row rendered without one.
const find_panes = (row) => {
    const roots = [row.shadowRoot, row];
    for (const root of roots) {
        if (!root) {
            continue;
        }
        const found = root.querySelectorAll(PANE_SELECTOR);
        if (found.length >= 2) {
            return [found[0], found[1]];
        }
    }
    return null;
}
