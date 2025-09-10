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

    // Function to recalculate and update column sizes
    const recalculateColumns = () => {
        const containerWidth = container.offsetWidth;
        const gutterWidth = 12;
        const gapWidth = 10;
        const availableWidth = containerWidth - gutterWidth - gapWidth;
        
        // Get current percentage split to maintain proportions
        const currentLeftWidth = left_column.offsetWidth;
        const currentRightWidth = right_column.offsetWidth;
        const currentTotalWidth = currentLeftWidth + currentRightWidth;
        
        let leftPercentage, rightPercentage;
        
        if (currentTotalWidth > 0) {
            // Maintain current proportions
            leftPercentage = currentLeftWidth / currentTotalWidth;
            rightPercentage = currentRightWidth / currentTotalWidth;
        } else {
            // Default to 50/50 if no current sizes
            leftPercentage = 0.5;
            rightPercentage = 0.5;
        }
        
        // Apply minimum size constraints (20% each)
        const minPercentage = 0.2;
        const maxPercentage = 0.8;
        
        if (leftPercentage < minPercentage) {
            leftPercentage = minPercentage;
            rightPercentage = 1 - leftPercentage;
        } else if (leftPercentage > maxPercentage) {
            leftPercentage = maxPercentage;
            rightPercentage = 1 - leftPercentage;
        }
        
        // Calculate new pixel widths
        const newLeftWidth = availableWidth * leftPercentage;
        const newRightWidth = availableWidth * rightPercentage;
        
        // Apply new widths
        left_column.style.width = newLeftWidth + 'px';
        right_column.style.width = newRightWidth + 'px';
        
        console.log('Columns recalculated:', {
            containerWidth,
            availableWidth,
            leftWidth: newLeftWidth,
            rightWidth: newRightWidth,
            leftPercentage: Math.round(leftPercentage * 100) + '%',
            rightPercentage: Math.round(rightPercentage * 100) + '%'
        });
    };

    // Initialize column widths after container is built
    setTimeout(() => {
        recalculateColumns();
    }, 100);

    // Set up ResizeObserver to detect container size changes
    if (window.ResizeObserver) {
        const resizeObserver = new ResizeObserver((entries) => {
            for (const entry of entries) {
                // Debounce resize events to avoid excessive recalculations
                clearTimeout(container._resizeTimeout);
                container._resizeTimeout = setTimeout(() => {
                    console.log('Container resized, recalculating columns...');
                    recalculateColumns();
                }, 50);
            }
        });
        
        // Observe the container for size changes
        resizeObserver.observe(container);
        
        // Store reference for cleanup if needed
        container._resizeObserver = resizeObserver;
    } else {
        // Fallback for older browsers - use window resize event
        const handleWindowResize = () => {
            clearTimeout(container._resizeTimeout);
            container._resizeTimeout = setTimeout(() => {
                console.log('Window resized, recalculating columns...');
                recalculateColumns();
            }, 100);
        };
        
        window.addEventListener('resize', handleWindowResize);
        container._windowResizeHandler = handleWindowResize;
    }

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
        
        // Add dragging class for animations
        gutter.classList.add('dragging');
        
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
        const gapWidth = 10; // Account for 5px gaps on each side
        const availableWidth = containerWidth - gutterWidth - gapWidth;
        
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
            
            // Remove dragging class to stop animations
            gutter.classList.remove('dragging');
            
            console.log('Drag ended');
        }
    });
    
    return gutter;
}

// Cleanup function for when component is removed
const cleanup = (container) => {
    if (container._resizeObserver) {
        container._resizeObserver.disconnect();
        container._resizeObserver = null;
    }
    
    if (container._windowResizeHandler) {
        window.removeEventListener('resize', container._windowResizeHandler);
        container._windowResizeHandler = null;
    }
    
    if (container._resizeTimeout) {
        clearTimeout(container._resizeTimeout);
        container._resizeTimeout = null;
    }
};