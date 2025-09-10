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

    // Track if this is the initial setup
    let isInitialSetup = true;

    // Function to recalculate and update column sizes
    const recalculateColumns = () => {
        const containerWidth = container.offsetWidth;
        
        // Get actual gutter width (including any borders/margins)
        const gutterWidth = gutter.offsetWidth;
        const gapWidth = 10; // 5px gap on each side of gutter
        
        // Calculate available width for content
        const availableWidth = containerWidth - gutterWidth - gapWidth;
        
        // Get current column content widths (excluding borders since we use border-box)
        const currentLeftWidth = left_column.offsetWidth;
        const currentRightWidth = right_column.offsetWidth;
        const currentTotalWidth = currentLeftWidth + currentRightWidth;
        
        let leftPercentage, rightPercentage;
        
        if (isInitialSetup || currentTotalWidth === 0) {
            // Force 50/50 on initial setup
            leftPercentage = 0.5;
            rightPercentage = 0.5;
            isInitialSetup = false; // Mark as no longer initial setup
        } else {
            // Maintain current proportions for resize events
            leftPercentage = currentLeftWidth / currentTotalWidth;
            rightPercentage = currentRightWidth / currentTotalWidth;
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
        
        // Calculate new pixel widths with precise rounding for equal distribution
        const newLeftWidth = Math.round(availableWidth * leftPercentage);
        const newRightWidth = availableWidth - newLeftWidth; // Ensure exact fit
        
        // Apply new widths (border-box means this includes borders)
        left_column.style.width = newLeftWidth + 'px';
        right_column.style.width = newRightWidth + 'px';
        
        // Force layout recalculation
        left_column.offsetHeight;
        right_column.offsetHeight;

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
                recalculateColumns();
            }, 100);
        };
        
        window.addEventListener('resize', handleWindowResize);
        container._windowResizeHandler = handleWindowResize;
    }

    // Perform initial sizing with proper calculations
    setTimeout(() => {
        recalculateColumns();
    }, 10); // Small delay to ensure DOM is ready

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
            newRightWidth = availableWidth - newLeftWidth; // Ensure exact fit
        } else if (newLeftWidth > maxWidth) {
            newLeftWidth = maxWidth;
            newRightWidth = availableWidth - newLeftWidth; // Ensure exact fit
        } else {
            newRightWidth = availableWidth - newLeftWidth; // Always calculate right from left
        }
        
        // Round to avoid sub-pixel issues - use Math.round for equal distribution
        newLeftWidth = Math.round(newLeftWidth);
        newRightWidth = availableWidth - newLeftWidth;
        
        // Apply new widths using passed column references
        left_column.style.width = newLeftWidth + 'px';
        right_column.style.width = newRightWidth + 'px';
        
        // Update startX for next move
        startX = currentX;
        
        e.preventDefault();
    });
    
    document.addEventListener('mouseup', () => {
        if (isDragging) {
            isDragging = false;
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            
            // Remove dragging class to stop animations
            gutter.classList.remove('dragging');
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