const ID = 'id';
const DIV = 'div';
const RESIZABLE_COLUMNS_CONTAINER = 'resizable-columns-container';
const LEFT_COLUMN = 'left_column';
const RIGHT_COLUMN = 'right_column';
const GUTTER = 'gutter';

export const render = ({ model }) => {
    const container = document.createElement(DIV);
    container.classList.add(RESIZABLE_COLUMNS_CONTAINER);

    const left_column = get_model_child(model, LEFT_COLUMN)
    const right_column = get_model_child(model, RIGHT_COLUMN)

    const gutter = create_gutter(left_column, right_column);

    container.appendChild(left_column);
    container.appendChild(gutter);
    container.appendChild(right_column);

    // Initialize column widths after container is built
    setTimeout(() => {
        const containerWidth = container.offsetWidth;
        const gutterWidth = 8;
        const availableWidth = containerWidth - gutterWidth;
        
        left_column.style.width = (availableWidth * 0.5) + 'px';
        right_column.style.width = (availableWidth * 0.5) + 'px';
    }, 100);

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}

const create_gutter = (left_column, right_column) => {
    const gutter = document.createElement(DIV);
    gutter.setAttribute(ID, GUTTER);
    gutter.classList.add(GUTTER);
    
    // Add dragging functionality
    let isDragging = false;
    let startX = 0;
    
    gutter.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX;
        
        // Use the passed column references directly
        const container = left_column.parentElement;
        
        // Change cursor and prevent text selection
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        gutter.style.cursor = 'col-resize';
        
        console.log('Drag started at:', startX);
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        
        const currentX = e.clientX;
        const deltaX = currentX - startX;
        
        // Get current dimensions using passed column references
        const container = left_column.parentElement;
        const containerWidth = container.offsetWidth;
        const gutterWidth = gutter.offsetWidth;
        const availableWidth = containerWidth - gutterWidth;
        
        // Get current widths
        const currentLeftWidth = left_column.offsetWidth;
        const currentRightWidth = right_column.offsetWidth;
        
        // Calculate new widths
        let newLeftWidth = currentLeftWidth + deltaX;
        let newRightWidth = currentRightWidth - deltaX;
        
        // Set minimum widths (20% of available width each)
        const minWidth = availableWidth * 0.2;
        const maxWidth = availableWidth * 0.8;
        
        if (newLeftWidth < minWidth) {
            newLeftWidth = minWidth;
            newRightWidth = availableWidth - newLeftWidth;
        } else if (newLeftWidth > maxWidth) {
            newLeftWidth = maxWidth;
            newRightWidth = availableWidth - newLeftWidth;
        } else {
            newRightWidth = availableWidth - newLeftWidth;
        }
        
        // Apply new widths using passed column references
        left_column.style.width = newLeftWidth + 'px';
        right_column.style.width = newRightWidth + 'px';
        
        // Update startX for next move
        startX = currentX;
        
        console.log('Resizing:', newLeftWidth, newRightWidth);
        e.preventDefault();
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            
            console.log('Drag ended');
        }
    });
    
    return gutter;
}