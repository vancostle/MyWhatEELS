const LEFT_COLUMN = 'left_column';
const RIGHT_COLUMN = 'right_column';
const ID = 'id';

export function render({ model }) {
    // Get Panel children
    const left = get_model_child(model, LEFT_COLUMN);
    const right = get_model_child(model, RIGHT_COLUMN);

    const container = document.createElement('div');
    container.className = 'split';
    container.appendChild(left);
    container.appendChild(right);

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
            resizing(left, right, model, 'dragging');
        },
        onDragEnd: (_) => {
            resizing(left, right, model, 'drag_end');
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

    const leftWidth = Math.trunc(leftRect.width);
    const rightWidth = Math.trunc(rightRect.width);

    console.log(`Event: ${event} Resizing: Left Width = ${leftWidth}px, Right Width = ${rightWidth}px`);

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