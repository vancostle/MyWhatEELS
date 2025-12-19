const LEFT_COLUMN = 'left_column';
const RIGHT_COLUMN = 'right_column';
const ID = 'id';

export function render({ model }) {
    const MILISECONDS_TO_RESIZE = 150;
    // Get Panel children
    const left = get_model_child(model, LEFT_COLUMN);
    const right = get_model_child(model, RIGHT_COLUMN);

    const container = document.createElement('div');
    container.className = 'split';
    container.appendChild(left);
    container.appendChild(right);
    let dragIntervalId = null;

    // Apply Split.js using direct element references (not selectors)
    Split([left, right], {
        sizes: [50, 50],
        minSize: 200,
        dragInterval: 2,
        gutterSize: 10,
        direction: 'horizontal',
        onDragStart: (_) => {
            resizing(left, right, model, 'drag_start');
        },
        onDrag: (_) => {
            // Start calling resizing every second
            if (dragIntervalId === null) {
                dragIntervalId = setInterval(() => {
                    resizing(left, right, model, 'dragging');
                }, MILISECONDS_TO_RESIZE);
            }
        },
        onDragEnd: (_) => {
            resizing(left, right, model, 'drag_end');
            if (dragIntervalId !== null) {
                clearInterval(dragIntervalId);
                dragIntervalId = null;
            }
        }
    });

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}
const resizing = (left, right, model, event) => {
    // Get actual pixel widths using getBoundingClientRect (more accurate)
    const leftRect = left.getBoundingClientRect();
    const rightRect = right.getBoundingClientRect();

    const leftWidth = leftRect.width;
    const rightWidth = rightRect.width;

    // Send drag end event to Python using Panel's messaging API
    model.send_msg({
        event,
        widths: {
            left: leftWidth,
            right: rightWidth
        }
    });
    
    // Dispatch window resize event for Plotly plots
    window.dispatchEvent(new Event('resize'));
}

