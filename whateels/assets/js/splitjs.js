
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
        minSize: 0,
        gutterSize: 8,
        direction: 'horizontal',
        onDrag: (sizes) => {
            // Get actual pixel widths using getBoundingClientRect (more accurate)
            const leftRect = left.getBoundingClientRect();
            const rightRect = right.getBoundingClientRect();
            
            // Send drag end event to Python using Panel's messaging API
            model.send_msg({ 
                widths: {
                    left: leftRect.width - 1,
                    right: rightRect.width - 1
                }
            });
            
            // Dispatch window resize event for Plotly plots
            window.dispatchEvent(new Event('resize'));
        },
    });

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}
