export const render = ({model}) => {
    const container = document.createElement('article');
    container.classList.add('error-message');

    // Header
    const header = document.createElement('header');
    const icon = document.createElement('span');
    icon.classList.add('error-icon');
    icon.textContent = '⚠️';
    const text = document.createElement('span');
    text.classList.add('error-text');
    text.textContent = 'ERROR';
    header.appendChild(icon);
    header.appendChild(text);

    // Error list
    const errors = [
    "The uploaded file format is not supported. Please upload a .dm3 or .dm4 file.",
    "File size exceeds the maximum allowed limit (100 MB).",
    "Failed to parse metadata: missing required fields.",
    "Network error: unable to connect to the server. Please check your internet connection.",
    "Permission denied: you do not have access to this file.",
    "Unexpected error: please try again or contact support."
    ];
    const ol = document.createElement('ol');
    errors.forEach(msg => {
        const li = document.createElement('li');
        li.textContent = msg;
        ol.appendChild(li);
    });

    container.appendChild(header);
    container.appendChild(ol);

    return container;
}