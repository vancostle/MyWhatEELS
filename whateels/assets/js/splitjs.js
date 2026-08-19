const LEFT_COLUMN = 'left_column';
const RIGHT_COLUMN = 'right_column';
const ID = 'id';
export function render({ model }) {
    const MILISECONDS_TO_RESIZE = 200;
    // Get Panel children
    const left = get_model_child(model, LEFT_COLUMN);
    const right = get_model_child(model, RIGHT_COLUMN);
    // Prevent horizontal scrollbars while dragging without clipping vertical
    // plot furniture on pages that still use the draggable splitter.
    left.style.overflowX = 'hidden';
    right.style.overflowX = 'hidden';
    left.style.minWidth = '0';
    right.style.minWidth = '0';
    left.style.minHeight = '0';
    right.style.minHeight = '0';

    const container = document.createElement('div');
    container.className = 'split';
    container.appendChild(left);
    container.appendChild(right);
    let dragIntervalId = null;
    let resizeTimeoutId = null;
    let lastGeometry = null;
    const syncResize = (event) => {
        lastGeometry = resizing(left, right, model, event, lastGeometry);
    };

    // Apply Split.js using direct element references (not selectors)
    const splitInstance = Split([left, right], {
        sizes: [50, 50],
        minSize: 200,
        dragInterval: 2,
        gutterSize: 10,
        direction: 'horizontal',
        onDragStart: (_) => {
            syncResize('drag_start');
        },
        onDrag: (_) => {
            // Start calling resizing every second
            if (dragIntervalId === null) {
                dragIntervalId = setInterval(() => {
                    syncResize('dragging');
                }, MILISECONDS_TO_RESIZE);
            }
        },
        onDragEnd: (_) => {
            syncResize('drag_end');
            if (dragIntervalId !== null) {
                clearInterval(dragIntervalId);
                dragIntervalId = null;
            }
        }
    });

    // Watch for external resizing (browser window, parent container, etc.)
    const resizeObserver = new ResizeObserver((entries) => {
        // Debounce the resize events to avoid excessive calls
        if (resizeTimeoutId !== null) {
            clearTimeout(resizeTimeoutId);
        }
        
        resizeTimeoutId = setTimeout(() => {
            // Only trigger if we're not currently dragging
            if (dragIntervalId === null) {
                syncResize('external_resize');
            }
            resizeTimeoutId = null;
        }, MILISECONDS_TO_RESIZE);
    });

    // Observe both split panels
    resizeObserver.observe(left);
    resizeObserver.observe(right);

    // Store observer for cleanup if needed
    container._resizeObserver = resizeObserver;
    container._splitInstance = splitInstance;

    // Initial sync after the split has entered the DOM. ResizeObserver remains
    // responsible for later container/window/stack changes.
    requestAnimationFrame(() => syncResize('external_resize'));

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}
const resizing = (left, right, model, event, previousGeometry) => {
    // Get actual pixel dimensions using getBoundingClientRect (more accurate)
    const leftRect = left.getBoundingClientRect();
    const rightRect = right.getBoundingClientRect();

    const leftWidth = leftRect.width;
    const rightWidth = rightRect.width;
    // Measure height from the split viewport, never from a child whose Bokeh
    // canvas may already be overflowing. This breaks the resize feedback loop.
    const containerRect = left.parentElement?.getBoundingClientRect();
    const viewportHeight = containerRect?.height || Math.min(leftRect.height, rightRect.height);
    const leftHeight = viewportHeight;
    const rightHeight = viewportHeight;

    const geometry = {
        leftWidth,
        rightWidth,
        leftHeight,
        rightHeight,
    };
    const isValid = Object.values(geometry).every(
        (value) => Number.isFinite(value) && value > 0
    );
    if (!isValid) {
        return previousGeometry;
    }
    // Moving a SplitJs block further down the additive result stack may wake
    // ResizeObserver without changing its actual box. Do not emit a Python
    // message or a global window resize in that case: either one makes every
    // responsive Bokeh figure solve its axes and color bars again.
    const unchanged = previousGeometry && Object.keys(geometry).every(
        (key) => Math.abs(geometry[key] - previousGeometry[key]) < 0.5
    );
    if (event === 'external_resize' && unchanged) {
        return previousGeometry;
    }

    // Send drag end event to Python using Panel's messaging API
    model.send_msg({
        event,
        widths: {
            left: leftWidth,
            right: rightWidth
        },
        heights: {
            left: leftHeight,
            right: rightHeight,
        }
    });
    
    // Bokeh/Panel already observe the two local split children.  A synthetic
    // window resize here also wakes every *other* responsive plot in the page;
    // prepending an additive result then makes unrelated axes, titles and
    // colorbars solve their layout again.  Keep resizing local to this split.
    return geometry;
}
