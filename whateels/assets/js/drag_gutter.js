const ROW_SELECTOR = '.whateels-split-row';
const PANE_SELECTOR = '.whateels-split-pane';
const RATIO_PANE_CLASS = 'whateels-ratio-pane';
const DEFAULT_MIN_PANE = 160;
const FIT_MARGIN = 8;
const RELAYOUT_INTERVAL_MS = 50;
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
    let gutter_width = 0;
    let available_width = 0;
    let drag_frame = null;
    let pending_ratio = null;

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
        context.left.style.minWidth = '0';
        context.right.style.minWidth = '0';
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
    };

    // A responsive canvas still paints its previous box until Bokeh completes
    // the next solve. Elemental NLLS normally allows visible overflow so axes
    // and colour bars are not clipped after additive publication, but during a
    // drag that exposes the stale canvas as a translucent-looking strip across
    // the neighbouring pane. Clip only for the gesture and restore afterwards.
    let pane_overflow_before_drag = null;
    let restore_overflow_after_relayout = false;

    const guard_pane_overflow = () => {
        if (context === null || pane_overflow_before_drag !== null) {
            return;
        }
        pane_overflow_before_drag = [
            context.left.style.overflow,
            context.right.style.overflow,
        ];
        context.left.style.overflow = 'hidden';
        context.right.style.overflow = 'hidden';
    };

    const restore_pane_overflow = () => {
        if (context === null || pane_overflow_before_drag === null) {
            return;
        }
        context.left.style.overflow = pane_overflow_before_drag[0];
        context.right.style.overflow = pane_overflow_before_drag[1];
        pane_overflow_before_drag = null;
        restore_overflow_after_relayout = false;
    };

    // Changing flex is a pure CSS change, and a plot that sizes its own box
    // (any scale_* mode) keeps the geometry of its first solve: its observed
    // element never changed, only the parent that clips it. The map then stays
    // frozen at the old size - visibly wrong once it holds an aspect ratio -
    // until an unrelated window resize happens to wake the whole page.
    //
    // invalidate_layout() propagates to the common Bokeh root. Invalidating a
    // view in each pane therefore solved that same root twice per frame. Keep
    // one representative view cached and invalidate it at most every 50 ms.
    // On release, any pending intermediate frame is replaced by one final pass.
    // A global resize event is still avoided because it would wake other roots.
    let relayout_frame = null;
    let relayout_view = null;
    let ratio_view = null;
    let ratio_box_width = 0;
    let ratio_box_height = 0;
    let ratio_resize_pending = false;
    let last_relayout = Number.NEGATIVE_INFINITY;

    const resolve_relayout_view = () => {
        if (context === null) {
            return null;
        }
        if (
            relayout_view !== null
            && relayout_view.el
            && (
                is_inside(relayout_view.el, context.left)
                || is_inside(relayout_view.el, context.right)
            )
        ) {
            return relayout_view;
        }
        relayout_view = null;
        for (const pane of [context.left, context.right]) {
            const candidates = views_inside(pane);
            if (candidates.length > 0) {
                relayout_view = candidates[0];
                break;
            }
        }
        return relayout_view;
    };

    const resolve_ratio_view = () => {
        if (context === null || !model.pane_ratio) {
            return null;
        }
        if (
            ratio_view !== null
            && ratio_view.el
            && ratio_view.el.classList.contains(RATIO_PANE_CLASS)
            && is_inside(ratio_view.el, context.left)
        ) {
            return ratio_view;
        }
        ratio_view = view_with_class_inside(context.left, RATIO_PANE_CLASS);
        return ratio_view;
    };

    const resize_ratio_pane_locally = () => {
        if (!ratio_resize_pending) {
            return false;
        }
        ratio_resize_pending = false;
        const spatial_ratio = Number(model.pane_ratio);
        if (
            !(spatial_ratio > 0)
            || !(ratio_box_width > 0)
            || !(ratio_box_height > 0)
        ) {
            return false;
        }
        const view = resolve_ratio_view();
        const target = view && view.model;
        if (!target || typeof target.setv !== 'function') {
            return false;
        }
        const max_width = Math.max(1, ratio_box_width - FIT_MARGIN);
        const max_height = Math.max(1, ratio_box_height - FIT_MARGIN);
        const width = Math.max(
            1,
            Math.round(Math.min(max_width, max_height * spatial_ratio)),
        );
        const height = Math.max(1, Math.round(width / spatial_ratio));
        if (
            target.sizing_mode === 'fixed'
            && target.width === width
            && target.height === height
        ) {
            return false;
        }
        // One local Bokeh update replaces the Python round trip while dragging.
        // sync:false keeps these transient sizes out of the websocket; the
        // exact final box is sent to Python on pointerup.
        target.setv(
            { sizing_mode: 'fixed', width: width, height: height },
            { sync: false },
        );
        return true;
    };

    const cancel_pending_relayout = () => {
        if (relayout_frame !== null) {
            cancelAnimationFrame(relayout_frame);
            relayout_frame = null;
        }
    };

    const request_relayout = (force) => {
        if (relayout_frame !== null || context === null) {
            return;
        }
        const now = performance.now();
        if (!force && now - last_relayout < RELAYOUT_INTERVAL_MS) {
            return;
        }
        relayout_frame = requestAnimationFrame(() => {
            relayout_frame = null;
            try {
                const view = resolve_relayout_view();
                // Updating the ratio model invalidates the same root itself.
                // The ordinary path is used for Elemental NLLS and whenever
                // rounding means the ratio model did not actually change.
                if (!resize_ratio_pane_locally() && view !== null) {
                    solve_again(view);
                }
                last_relayout = performance.now();
            } finally {
                if (restore_overflow_after_relayout) {
                    restore_pane_overflow();
                }
            }
        });
    };

    // Python only needs the durable final size. Intermediate ratio sizing is a
    // local Bokeh model update, avoiding websocket patches that can arrive late
    // and make Reference Fit appear to continue moving after the pointer stops.
    let last_reported_width = null;
    let last_reported_height = null;
    const report_geometry = () => {
        if (context === null || !model.pane_ratio) {
            return null;
        }
        const rect = context.left.getBoundingClientRect();
        const width = rect.width;
        const height = rect.height;
        if (!(width > 0) || !(height > 0)) {
            return null;
        }
        if (
            last_reported_width !== null
            && Math.abs(width - last_reported_width) < 0.5
            && Math.abs(height - last_reported_height) < 0.5
        ) {
            return { width: width, height: height };
        }
        last_reported_width = width;
        last_reported_height = height;
        model.send_msg({ width: width, height: height });
        return { width: width, height: height };
    };

    // Pointer events can arrive faster than the browser can paint. Keep only
    // the newest ratio and apply it once in the next animation frame, avoiding
    // repeated style/layout work for positions the user would never see.
    const flush_drag_frame = () => {
        if (pending_ratio === null || context === null) {
            return;
        }
        const ratio = pending_ratio;
        pending_ratio = null;
        apply_ratio(ratio);
        if (model.pane_ratio) {
            ratio_box_width = available_width * ratio;
            ratio_box_height = row_rect.height;
            ratio_resize_pending = true;
        }
        if (dragging) {
            request_relayout(false);
        }
    };

    const schedule_drag = (ratio) => {
        pending_ratio = ratio;
        if (drag_frame !== null) {
            return;
        }
        drag_frame = requestAnimationFrame(() => {
            drag_frame = null;
            flush_drag_frame();
        });
    };

    const flush_pending_drag = () => {
        if (drag_frame !== null) {
            cancelAnimationFrame(drag_frame);
            drag_frame = null;
        }
        flush_drag_frame();
    };

    const stop_drag = (event) => {
        if (!dragging) {
            return;
        }
        // Stop intermediate work first. Flushing now applies only the newest
        // CSS ratio because dragging is already false.
        dragging = false;
        flush_pending_drag();
        cancel_pending_relayout();
        gutter.classList.remove('dragging');
        try {
            gutter.releasePointerCapture(event.pointerId);
        } catch (error) {
            // The capture is already gone; nothing left to release.
        }
        if (context !== null) {
            context.row.style.userSelect = '';
            // At most one final report, and exactly one gutter layout pass. No
            // intermediate animation frame survives beyond pointerup.
            const final_box = report_geometry();
            if (final_box !== null) {
                ratio_box_width = final_box.width;
                ratio_box_height = final_box.height;
                ratio_resize_pending = true;
            }
            restore_overflow_after_relayout = true;
            request_relayout(true);
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
        gutter_width = gutter.getBoundingClientRect().width || 0;
        available_width = row_rect.width - gutter_width;
        if (!(available_width > 0)) {
            return;
        }
        pending_ratio = null;
        dragging = true;
        guard_pane_overflow();
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
        const min_pane = Math.min(min_pane_size(model), available_width / 2);
        const raw = event.clientX - row_rect.left - gutter_width / 2;
        const left_px = Math.max(
            min_pane,
            Math.min(available_width - min_pane, raw),
        );
        schedule_drag(left_px / available_width);
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
        report_geometry();
        request_relayout(true);
    });

    // render() returns before this element is in the document, so the panes
    // cannot be measured yet. Retry for a bounded number of frames rather than
    // spinning forever on a gutter that never gets mounted.
    let attempts = 0;
    const initial_fit = () => {
        initial_fit_frame = null;
        if (resolve_context() === null) {
            if (++attempts < 120) {
                initial_fit_frame = requestAnimationFrame(initial_fit);
            }
            return;
        }
        report_geometry();
        request_relayout(true);
    };
    let initial_fit_frame = requestAnimationFrame(initial_fit);

    // A window resize changes the panes without ever touching the gutter, so
    // the ratio pane has to be re-measured for it too.
    const on_window_resize = () => {
        report_geometry();
        request_relayout(true);
    };
    window.addEventListener('resize', on_window_resize);

    // ReactiveESM exposes Panel's removal lifecycle through the model proxy.
    // Release global listeners and pending frames when Fitting is torn down.
    model.on('remove', () => {
        window.removeEventListener('resize', on_window_resize);
        if (initial_fit_frame !== null) {
            cancelAnimationFrame(initial_fit_frame);
            initial_fit_frame = null;
        }
        if (drag_frame !== null) {
            cancelAnimationFrame(drag_frame);
            drag_frame = null;
        }
        cancel_pending_relayout();
        pending_ratio = null;
        relayout_view = null;
        ratio_view = null;
        ratio_resize_pending = false;
        restore_pane_overflow();
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

// Find an outermost view already sitting inside the pane. Invalidating that
// view propagates to its Bokeh root, so one representative is enough for both
// panes; roots outside this split are never selected. Template-level roots
// usually contain both panes and are therefore descended into first.
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

// Locate a specifically marked descendant without making it a Child of the
// gutter. This preserves Panel's native model hierarchy while still allowing
// the browser to update the ratio plot's own Bokeh model during a gesture.
const view_with_class_inside = (pane, class_name) => {
    let found = null;
    const visit = (view) => {
        if (!view || found !== null) {
            return;
        }
        const el = view.el;
        if (
            el
            && el.classList
            && el.classList.contains(class_name)
            && is_inside(el, pane)
        ) {
            found = view;
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
