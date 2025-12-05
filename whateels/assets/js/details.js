const CONTENT = 'content';
const TITLE = 'title';
const ID = 'id';
const DIV = 'div';

export const render = ({ model }) => {
    const container = document.createElement(DIV);
    container.classList.add('details-container');

    const header = document.createElement(DIV);
    header.classList.add('details-header');

    const title = get_model_child(model, TITLE)
    
    const button = create_dropdown_button('details-dropdown-button');

    header.appendChild(title);
    header.appendChild(button);

    const content = get_model_child(model, CONTENT)
    content.classList.add('details-content');

    container.appendChild(header);
    container.appendChild(content);

    // Initialize the container with proper max-height after DOM is ready
    setTimeout(() => {
        container.style.maxHeight = container.scrollHeight + 'px';
    }, 0);

    // Toggle content visibility on header click
    header.addEventListener('click', () => {
        const isCollapsed = container.classList.toggle('collapsed');
        button.querySelector('svg').classList.toggle('rotated');
        const headerHeight = header.offsetHeight;
        
        if (isCollapsed) {
            container.style.overflow = 'hidden';
            container.style.maxHeight = headerHeight + 'px';
            
        } else {
            // Expand animation - measure full height with proper reflow
            container.style.maxHeight = 'none';
            
            // Force reflow to ensure the browser calculates scrollHeight correctly
            void container.offsetHeight;
            
            const fullHeight = container.scrollHeight;
            
            // Set to header height first to prepare for animation
            container.style.maxHeight = headerHeight + 'px';
            
            // Small timeout to ensure the transition is applied
            setTimeout(() => {
                container.style.maxHeight = fullHeight + 'px';
            }, 10);
            
            // Reset overflow after animation completes (0.4s)
            setTimeout(() => {
                container.style.overflow = 'visible';
            }, 400);
        }
    });

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}

const create_dropdown_button = (css_class) => {
    const button = document.createElement('button');
    button.classList.add('details-dropdown-button');
    
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('width', '20');
    svg.setAttribute('height', '20');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('stroke-width', '2');
    svg.setAttribute('stroke-linecap', 'round');
    svg.setAttribute('stroke-linejoin', 'round');
    svg.classList.add('dropdown-arrow-icon');
    
    const polyline = document.createElementNS('http://www.w3.org/2000/svg', 'polyline');
    polyline.setAttribute('points', '6 9 12 15 18 9');
    
    svg.appendChild(polyline);
    button.appendChild(svg);
    button.classList.add(css_class);
    
    return button;
}