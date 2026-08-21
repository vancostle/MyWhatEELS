const ROW_SELECTOR = '.whateels-split-row';
const PANE_SELECTOR = '.whateels-split-pane';
const DEFAULT_MIN_PANE = 160;
// Mirrors the cadence SplitJs reports at while a drag is in progress.
const REPORT_INTERVAL_MS = 200;
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
        request_relayout();
    };

    // Changing flex is a pure CSS change, and a plot that sizes its own box
    // (any scale_* mode) keeps the geometry of its first solve: its observed
    // element never changed, only the parent that clips it. The map then stays
    // frozen at the old size - visibly wrong once it holds an aspect ratio -
    // until an unrelated window resize happens to wake the whole page.
    //
    // So the two panes are asked to solve again, and only those two. A global
    // resize event would do it as well, which is exactly why it is not used
    // here: it relayouts every responsive plot in the page, including the ones
    // stacked above this split.
    let relayout_frame = null;
    const request_relayout = () => {
        if (relayout_frame !== null || context === null) {
            return;
        }
        relayout_frame = requestAnimationFrame(() => {
            relayout_frame = null;
            for (const pane of [context.left, context.right]) {
                for (const view of views_inside(pane)) {
                    solve_again(view);
                }
            }
        });
    };

    // Report the left pane's box so Python can size the ratio pane from it.
    //
    // The fit deliberately does NOT happen here. The pane is a Bokeh-managed
    // element, so under any responsive sizing mode Bokeh rewrites its inline
    // width/height on the next layout solve and any size written from here is
    // lost. Setting the model in Python is the only instruction Bokeh keeps.
    //
    // This has to run DURING the drag, not only on release. The ratio pane is
    // sized 'fixed', so between two reports it keeps the width it was given
    // while the pane around it shrinks - it then spills past the gutter and
    // shows through wherever the right pane does not paint. SplitJs reports on
    // an interval through the drag for the same reason; the throttle below
    // keeps that to a handful of messages per gesture instead of one per frame.
    let last_report = 0;
    const report_geometry = (force) => {
        if (context === null || !model.pane_ratio) {
            return;
        }
        const now = performance.now();
        if (!force && now - last_report < REPORT_INTERVAL_MS) {
            return;
        }
        last_report = now;
        const rect = context.left.getBoundingClientRect();
        if (!(rect.width > 0) || !(rect.height > 0)) {
            return;
        }
        model.send_msg({ width: rect.width, height: rect.height });
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
            // Once the flex has settled: re-measure for the ratio pane, and
            // solve again so neither pane keeps the last intermediate frame.
            report_geometry(true);
            request_relayout();
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
        // Throttled: keeps the fixed-size ratio pane following the shrinking
        // pane instead of overflowing it until the pointer is released.
        report_geometry();
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
        report_geometry(true);
        request_relayout();
    });

    // render() returns before this element is in the document, so the panes
    // cannot be measured yet. Retry for a bounded number of frames rather than
    // spinning forever on a gutter that never gets mounted.
    let attempts = 0;
    const initial_fit = () => {
        if (resolve_context() === null) {
            if (++attempts < 120) {
                requestAnimationFrame(initial_fit);
            }
            return;
        }
        report_geometry(true);
        request_relayout();
    };
    requestAnimationFrame(initial_fit);

    // A window resize changes the panes without ever touching the gutter, so
    // the ratio pane has to be re-measured for it too.
    window.addEventListener('resize', () => {
        report_geometry(true);
        request_relayout();
    });

    return gutter;
}

// Bokeh keeps its view tree in `Bokeh.index`. Its exact shape has changed
// across 3.x releases, so every known form is accepted and an unknown one
// simply yields no roots: the drag still resizes, it just stops correcting the
// plots instead of throwing on every pointer move.
const root_views = () => {
    const bokeh = window.Bokeh;
    const index = bokeh && bokeh.index;
    if (!index) {
        return [];
    }
    if (typeof index[Symbol.iterator] === 'function') {
        return Array.from(index);
    }
    if (Array.isArray(index.roots)) {
        return index.roots;
    }
    if (typeof index.get_all === 'function') {
        return Array.from(index.get_all());
    }
    return Object.keys(index).map((key) => index[key]);
}

// The outermost view that already sits inside the pane is the one to solve:
// solving it cascades to its children, and stopping there keeps every plot
// outside this split untouched. Roots themselves are usually template-level and
// contain both panes, so they are descended into rather than solved.
const views_inside = (pane) => {
    const found = [];
    const visit = (view) => {
        if (!view) {
            return;
        }
        const el = view.el;
        if (el && is_inside(el, pane)) {
            found.push(view);
            return;
        }
        const children = view.child_views;
        if (children) {
            for (const child of children) {
                visit(child);
            }
        }
    };
    for (const root of root_views()) {
        visit(root);
    }
    return found;
}

const solve_again = (view) => {
    try {
        if (typeof view.invalidate_layout === 'function') {
            view.invalidate_layout();
        } else if (typeof view.compute_layout === 'function') {
            view.compute_layout();
        }
    } catch (error) {
        // A view detached between the frame request and this callback. The next
        // drag frame picks up whatever replaced it.
    }
}

// `contains` does not cross shadow boundaries, and Panel puts every layout
// child in its own shadow root.
const is_inside = (node, ancestor) => {
    let current = node;
    while (current) {
        if (current === ancestor) {
            return true;
        }
        current = current.parentNode || current.host || null;
    }
    return false;
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
