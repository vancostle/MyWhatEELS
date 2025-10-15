
export const render = ({model}) => {
    const upload_message = document.createElement('div');
    upload_message.classList.add('upload-message', 'animated');
    upload_message.title = model.filename;
    
    const icon = document.createElement('span');
    icon.classList.add('upload-icon');
    icon.textContent = '📁';

    const text = document.createElement('span');
    text.classList.add('upload-text');
    text.innerHTML = `<strong>${model.filename}</strong>`;

    upload_message.appendChild(icon);
    upload_message.appendChild(text);

    return upload_message;
}