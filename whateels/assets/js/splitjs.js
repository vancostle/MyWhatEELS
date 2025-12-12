import Split from 'splitjs';

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
        onDragStart: () => {
            console.log('Started resizing');
        },
        onDrag: (sizes) => {
            console.log('Resizing...', sizes);
        },
        onDragEnd: (sizes) => {
            console.log('Finished resizing', sizes);
            console.log(window.Plotly.Plots)
            // Dispatch resize event so Plotly/other components can update
            // window.dispatchEvent(new Event('resize'));
            // // Find the first element with both classes 'plot-container' and 'plotly'
            // const left_shadow_root = left.shadowRoot.querySelector('.bk-panel-models-plotly-PlotlyPlot').shadowRoot.querySelector('.plot-container.plotly').querySelector('.svg-container');
        
            // if (left_shadow_root) {
            //     console.log('Found plotly plot:', left_shadow_root.children);
            // } else {
            //     console.log('No plotly plot found');
            // }
        }
    });

    return container;
}

const get_model_child = (model, value) => {
    const child = model.get_child(value);
    child.setAttribute(ID, value);
    return child
}
