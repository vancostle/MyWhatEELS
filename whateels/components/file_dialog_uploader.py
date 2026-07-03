import os
import param
from panel.custom import JSComponent
from .native_dialogs import open_native_file_dialog

class FileDialogUploader(JSComponent):

    default_message = param.String("Click to select a file", doc="Default message shown in the uploader area.")
    reading_message = param.String("Loading...", doc="Message shown while a file is being read.")
    error_message = param.String("Error reading file!", doc="Message shown if there is an error during file reading.")
    accepted_file_types = param.List(default=['.dm3', '.dm4'], doc="List of accepted file extensions for upload.")
    opening_dialog_message = param.String("Opening dialog...", doc="Message shown while the file dialog is open.")
    # When non-empty the component renders already in success state (back-navigation).
    initial_filepath = param.String("", doc="Full path of a pre-loaded file. Shows success state on initial render.")
    disabled = param.Boolean(False, doc="Whether file selection is disabled.")

    def __init__(self, *args, on_file_uploaded_callback=None, on_file_removed_callback=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.on_file_uploaded_callback = on_file_uploaded_callback
        self.on_file_removed_callback = on_file_removed_callback
        # Restore tracked path from initial_filepath (back-navigation scenario).
        self._current_selected_path: str | None = self.initial_filepath or None # type: ignore

    _stylesheets = [
        """
            * {
                box-sizing: border-box;
            }
            
            :host {
                width: 100%;
                display: flex;
            }

            h2, p {
                font-size: .9rem;
                font-weight: normal;
            }
            
            .file-dialog-uploader {
                flex: 1;
                min-width: 0;
            }

            .component-wrapper {
                display: flex;
                flex-direction: column;
                align-items: center;
                width: 100%;
            }

            .wrapper {
                width: 100%;
                height: 70px;

                position: relative;
                display: flex;

                overflow: clip;
                position: relative;

                border-radius: 9px;

                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;

                box-shadow: 0px 0px 5px rgba(0, 0, 0, 0.2);
            }

            .path-option-wrapper {
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                padding: 0 .5rem 0 .5rem;
                gap: .25rem;
                width: 100%;
            }

            .path-option-wrapper > form {
                padding: .5rem;
                width: 100%;
                display: flex;
                flex-direction: row;
                justify-content: center;
                align-items: center;
                background-color: #f8f8f8;
                overflow: clip;
                border-radius: 0 0 8px 8px;
                box-shadow: 0px 0px 5px rgba(0, 0, 0, 0.1);
                gap: .5rem;
            }

            .path-option-wrapper > form input {
                flex: 1;
                border-radius: 4px;
                border: 1px solid #ccc;
                width: 100%;
                
                &:focus {
                    outline: none;
                    border-color: #3182ce;
                }
            }

            .path-option-wrapper > form input:disabled {
                cursor: not-allowed;
            }

            .path-option-wrapper > form button{
                width: 1.3rem;
                height: 1.3rem;
                min-width: 1.3rem;
                min-height: 1.3rem;
                background-color: transparent;
                border: none;
                padding: 0;
                cursor: pointer;
                border-radius: 4px;
                display: grid;
                place-items: center;
            }

            .path-option-wrapper > form button svg {
                width: 100%;
                height: 100%;
                fill: #6b7280;
            }

            .path-option-wrapper > form button:not(:disabled):hover svg {
                fill: #b946b8;
            }

            .path-option-wrapper > form button:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }

            #file-zone {
                flex: 1;

                display: flex;
                justify-content: center;
                align-items: center;

                padding: 0;
                width: inherit;

                background-color: #f1f1f1;

                & > h2 {
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    color: #35373b;

                    max-width: 100%;
                    padding: 0 12px;

                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                &:hover {
                    cursor: pointer;

                    & h2 {
                        color: rgb(43, 43, 43);
                        text-decoration: underline;
                    }
                }
            }

            #file-zone.disabled {
                opacity: 0.6;
                cursor: not-allowed;

                & > h2 {
                    color: #6b7280;
                    text-decoration: none;
                }

                &:hover {
                    cursor: not-allowed;

                    & h2 {
                        color: #6b7280;
                        text-decoration: none;
                    }
                }
            }

            .path-option-wrapper.disabled {
                opacity: 0.7;
            }

            section.state {
                position: absolute;
                z-index: 1;

                transition: transform 0.7s cubic-bezier(.68,-0.55,.27,1.55);
                
                display: flex;
                align-items: center;
                justify-content: center;
                flex: 1;

                width: 100%;
                height: 100%;
                padding: 7px;
                
                z-index: 1;

                & > div {
                    display: flex;
                    flex: 1;
                    width: inherit;
                    height: inherit;
                    align-items: center;
                    justify-content: space-between;
                    border-radius: 8px;
                    padding: .5rem 1rem;
                    gap: .5rem;

                    box-shadow: 0px 0px 4px rgba(0, 0, 0, 0.2);
                    color: white;
                    width: inherit;

                    & > p {
                        flex: 1;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        max-width: 100%;
                        padding: 0;

                        white-space: nowrap;
                        overflow: hidden;
                        text-overflow: ellipsis;
                    }
                }
            }
            
            section.state.opening {
                top: 150%;
                left: 50%;
                transform: translate(-50%, -50%);

                & > div {
                    background-color: #a0aec0;
                }

                & .spinner {
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top: 4px solid white;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    animation: spin 1s linear infinite;
                }
            }

            section.state.loading {
                top: -50%;
                left: 50%;
                transform: translate(-50%, -50%);

                & > div {
                    background-color: #3182ce;
                }

                & .spinner {
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top: 4px solid white;
                    border-radius: 50%;
                    width: 24px;
                    height: 24px;
                    animation: spin 1s linear infinite;
                }
            }

            section.state.success {
                top: 50%;
                left: 100%;
                transform: translate(0%, -50%);

                & > div {
                    background-color: #38a170;
                }

                & .remove-file {
                    background-color: #1b650c;
                }
                
                & p:hover {
                    text-decoration: underline;
                    cursor: pointer;
                }
            }

            section.state.failed {
                top: 50%;
                right: 100%;
                transform: translate(0%, -50%);

                & > div {
                    background-color: rgb(170, 19, 19);
                }

                & .remove-file {
                    background-color: rgb(80, 13, 13);
                }
            }

            .remove-file {
                width: 24.5px;
                height: 24.5px;

                min-width: 24.5px;
                min-height: 24.5px;

                border: 0;
                border-radius: 50%;
                box-shadow: none;

                display: grid;
                place-items: center;

                position: relative;

                rotate: 45deg;
                transition: scale 0.2s ease-in-out, background-color 0.2s ease-in-out;

                &::before, &::after {
                    content: '';
                    position: absolute;
                    width: 4px;
                    height: calc(100% - 8px);
                    background-color: white;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    border-radius: 2px;
                    transition: background-color 0.2s ease-in-out;
                }

                &::after {
                    /* Centered horizontally, vertical bar */
                    transform: translate(-50%, -50%) rotate(90deg);
                }

                &:hover {
                    cursor: pointer;
                    scale: 1.2;
                    background-color: white;
                }
            }
            
            section.state.opening.actived-opening-dialog-state {
                transform: translate(-50%, -150%);
            }

            section.state.loading.actived-reading-file-state {
                transform: translate(-50%, 50%);
            }

            section.state.success.actived-success-state {
                transform: translate(-100%, -50%);
            }

            section.state.failed.actived-failed-state {
                transform: translate(100%, -50%);
            }

            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        """
    ]
    
    _esm = """
        const createCustomFileUploader = model => {
            const acceptedExtensions = Array.isArray(model.accepted_file_types)
                ? model.accepted_file_types.filter(ext => !!ext)
                : [];
            const extensionsLabel = acceptedExtensions.length
                ? acceptedExtensions.join(' or ')
                : 'file';

            // Get messages from model (Panel param values)
            const defaultMessage = model.default_message || `Click to select a ${extensionsLabel}`;
            const openingDialogMessage = model.opening_dialog_message || 'Opening dialog...';
            const readingMessage = model.reading_message || 'Loading...';
            const errorMessage = model.error_message || 'Error reading file!';

            const componentWrapper = document.createElement('div');
            componentWrapper.className = 'component-wrapper';

            const wrapper = document.createElement('div');
            wrapper.className = 'wrapper';

            // File zone
            const fileZone = document.createElement('section');
            fileZone.id = 'file-zone';
            fileZone.title = defaultMessage;
            const fileZoneH2 = document.createElement('h2');
            fileZoneH2.textContent = defaultMessage;
            fileZone.appendChild(fileZoneH2);

            // Opening state
            const openingSection = document.createElement('section');
            openingSection.className = 'opening state';
            const openingDiv = document.createElement('div');
            const openingP = document.createElement('p');
            openingP.textContent = openingDialogMessage;
            const openingSpinner = document.createElement('div');
            openingSpinner.className = 'spinner';
            openingDiv.appendChild(openingP);
            openingDiv.appendChild(openingSpinner);
            openingSection.appendChild(openingDiv);

            // Loading state
            const loadingSection = document.createElement('section');
            loadingSection.className = 'loading state';
            const loadingDiv = document.createElement('div');
            const loadingP = document.createElement('p');
            loadingP.textContent = readingMessage;
            const spinner = document.createElement('div');
            spinner.className = 'spinner';
            loadingDiv.appendChild(loadingP);
            loadingDiv.appendChild(spinner);
            loadingSection.appendChild(loadingDiv);

            // Success state
            const successSection = document.createElement('section');
            successSection.className = 'success state';
            const successDiv = document.createElement('div');
            const successP = document.createElement('p');
            // Will be set dynamically when file is selected
            successP.textContent = '';
            // Add click-to-copy functionality
            successP.style.cursor = 'pointer';
            let lastCopiedTimeout = null;
            successP.addEventListener('click', () => {
                const fullpath = successP.getAttribute('title');
                if (fullpath) {
                    navigator.clipboard.writeText(fullpath).then(() => {
                        // Visual feedback: temporarily change text or show a tooltip
                        const original = successP.textContent;
                        successP.textContent = 'Copied on clipboard!';
                        clearTimeout(lastCopiedTimeout);
                        lastCopiedTimeout = setTimeout(() => {
                            successP.textContent = original;
                        }, 1000);
                    });
                }
            });
            const removeSuccessBtn = document.createElement('button');
            removeSuccessBtn.className = 'remove-file success';
            successDiv.appendChild(successP);
            successDiv.appendChild(removeSuccessBtn);
            successSection.appendChild(successDiv);

            // Failed state
            const failedSection = document.createElement('section');
            failedSection.className = 'failed state';
            const failedDiv = document.createElement('div');
            const failedP = document.createElement('p');
            failedP.textContent = errorMessage;
            const removeFailedBtn = document.createElement('button');
            removeFailedBtn.className = 'remove-file failed';
            failedDiv.appendChild(failedP);
            failedDiv.appendChild(removeFailedBtn);
            failedSection.appendChild(failedDiv);

            const activateOpeningDialogState = () => {
                openingSection.classList.add('actived-opening-dialog-state');
                loadingSection.classList.remove('actived-reading-file-state');
                successSection.classList.remove('actived-success-state');
                failedSection.classList.remove('actived-failed-state');
            };

            const activateReadingFileState = () => {
                loadingSection.classList.add('actived-reading-file-state');
                openingSection.classList.remove('actived-opening-dialog-state');
                successSection.classList.remove('actived-success-state');
                failedSection.classList.remove('actived-failed-state');
                inputText.disabled = true;
                inputSubmit.disabled = true;
            };

            const activateSuccessState = (filename, fullpath) => {
                successP.textContent = filename || '';
                if (fullpath) {
                    successP.setAttribute('title', fullpath);
                } else {
                    successP.removeAttribute('title');
                }
                successSection.classList.add('actived-success-state');
                openingSection.classList.remove('actived-opening-dialog-state');
                loadingSection.classList.remove('actived-reading-file-state');
                failedSection.classList.remove('actived-failed-state');
                inputText.disabled = true;
                inputSubmit.disabled = true;
            };

            const activateFailedState = () => {
                failedSection.classList.add('actived-failed-state');
                openingSection.classList.remove('actived-opening-dialog-state');
                loadingSection.classList.remove('actived-reading-file-state');
                successSection.classList.remove('actived-success-state');
            };

            // Listen for backend -> frontend custom messages
            model.on('msg:custom', msg => {
                if (msg?.type === 'activate_failed_state') {
                    activateFailedState();
                }
                if (msg?.type === 'remove_all_state') {
                    removeAllStates();
                }
                if (msg?.type === 'activate_reading_file_state') {
                    activateReadingFileState();
                }
                if (msg?.type === 'file_selected' && msg?.path) {
                    activateSuccessState(msg.filename, msg.path);
                }
                if (msg?.type === 'set_disabled') {
                    setDisabledState(!!msg.disabled);
                }
            });

            removeSuccessBtn.addEventListener('click', _ => {
                const selectedPath = successP.getAttribute('title') || '';
                model.send_msg({ type: 'remove_selected_file', path: selectedPath });
                removeAllStates();
            });

            removeFailedBtn.addEventListener('click', _ => {
                removeAllStates();
            });

            fileZone.addEventListener('click', _ => {
                if (uploaderDisabled) {
                    return;
                }
                activateOpeningDialogState();
                model.send_event('file_selected_clicked', {});
            });

            // Append uploader states
            wrapper.appendChild(fileZone);
            wrapper.appendChild(openingSection);
            wrapper.appendChild(loadingSection);
            wrapper.appendChild(successSection);
            wrapper.appendChild(failedSection);

            // Manual path option
            const pathOptionWrapper = document.createElement('div');
            pathOptionWrapper.className = 'path-option-wrapper';
            const form = document.createElement('form');
            const inputText = document.createElement('input');
            inputText.type = 'text';
            inputText.placeholder = 'Or paste the file path here';
            const inputSubmit = document.createElement('button');
            inputSubmit.type = 'submit';
            inputSubmit.title = 'Submit file path';
            inputSubmit.ariaLabel = 'Submit file path';
            inputSubmit.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 640 640" aria-hidden="true"><path d="M416 160L480 160C497.7 160 512 174.3 512 192L512 448C512 465.7 497.7 480 480 480L416 480C398.3 480 384 494.3 384 512C384 529.7 398.3 544 416 544L480 544C533 544 576 501 576 448L576 192C576 139 533 96 480 96L416 96C398.3 96 384 110.3 384 128C384 145.7 398.3 160 416 160zM406.6 342.6C419.1 330.1 419.1 309.8 406.6 297.3L278.6 169.3C266.1 156.8 245.8 156.8 233.3 169.3C220.8 181.8 220.8 202.1 233.3 214.6L306.7 288L96 288C78.3 288 64 302.3 64 320C64 337.7 78.3 352 96 352L306.7 352L233.3 425.4C220.8 437.9 220.8 458.2 233.3 470.7C245.8 483.2 266.1 483.2 278.6 470.7L406.6 342.7z"/></svg>';

            let uploaderDisabled = !!model.disabled;

            const syncSubmitState = () => {
                inputSubmit.disabled = uploaderDisabled || !inputText.value.trim();
            };

            const setDisabledState = disabled => {
                uploaderDisabled = !!disabled;
                fileZone.classList.toggle('disabled', uploaderDisabled);
                pathOptionWrapper.classList.toggle('disabled', uploaderDisabled);

                if (uploaderDisabled) {
                    inputText.disabled = true;
                    inputSubmit.disabled = true;
                    return;
                }

                const lockedState =
                    openingSection.classList.contains('actived-opening-dialog-state') ||
                    loadingSection.classList.contains('actived-reading-file-state') ||
                    successSection.classList.contains('actived-success-state');

                if (!lockedState) {
                    inputText.disabled = false;
                }
                syncSubmitState();
            };

            inputText.addEventListener('input', syncSubmitState);
            syncSubmitState();

            form.addEventListener('submit', event => {
                event.preventDefault();
                if (uploaderDisabled) {
                    return;
                }

                const filePath = inputText.value.trim();
                if (!filePath) {
                    syncSubmitState();
                    return;
                }
                console.log("Submitting file path from manual input:", filePath);
                model.send_msg({ type: 'file_path_submitted', path: filePath });

                inputText.disabled = true;
                inputSubmit.disabled = true;
                activateReadingFileState();
            });

            form.appendChild(inputText);
            form.appendChild(inputSubmit);
            pathOptionWrapper.appendChild(form);

            const removeAllStates = () => {
                openingSection.classList.remove('actived-opening-dialog-state');
                loadingSection.classList.remove('actived-reading-file-state');
                successSection.classList.remove('actived-success-state');
                failedSection.classList.remove('actived-failed-state');
                inputText.disabled = uploaderDisabled;
                syncSubmitState();
            };

            componentWrapper.appendChild(wrapper);
            componentWrapper.appendChild(pathOptionWrapper);

            // Restore success state when navigating back to a page that already
            // has a file loaded (equivalent to FileUploader's force_success).
            if (model.initial_filepath) {
                const fp = model.initial_filepath;
                const fname = fp.split(/[\\/]/).pop();
                activateSuccessState(fname, fp);
            }
            setDisabledState(uploaderDisabled);

            return componentWrapper;
        };

        export function render({ model }) {
            const fileDialogUploader = createCustomFileUploader(model);
            return fileDialogUploader;
        }
    """

    @staticmethod
    def _normalize_extensions(extensions: object) -> list[str]:
        normalized: list[str] = []
        if not isinstance(extensions, (list, tuple, set)):
            return normalized

        for ext in extensions:
            candidate = str(ext).strip().lower()
            if not candidate:
                continue
            if not candidate.startswith('.'):
                candidate = f".{candidate}"
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    def _accepted_extensions(self) -> list[str]:
        return self._normalize_extensions(getattr(self, "accepted_file_types", []))

    def _is_allowed_file(self, path: str) -> bool:
        if not os.path.isfile(path):
            return False

        extensions = self._accepted_extensions()
        if not extensions:
            return True

        return os.path.splitext(path)[1].lower() in set(extensions)

    def _handle_file_selected_clicked(self, event):
        if bool(self.disabled):
            return

        path = open_native_file_dialog(self._accepted_extensions())
        if path and self._is_allowed_file(path):
            filename = os.path.basename(path)
            self._current_selected_path = path
            # Show reading state briefly while callback runs, then success.
            # Mirrors FileUploader: store → show UI → call callback.
            self._send_msg({'type': 'activate_reading_file_state'})
            if callable(self.on_file_uploaded_callback):
                self.on_file_uploaded_callback(filename, path)
            self._send_msg({'type': 'file_selected', 'path': path, 'filename': filename})
        else:
            self._send_msg({'type': 'remove_all_state'})

    def _handle_msg(self, msg): # type: ignore
        if isinstance(msg, dict) and msg.get("type") == "file_path_submitted":
            if bool(self.disabled):
                return

            raw_path = msg.get("path")
            path = str(raw_path).strip() if raw_path is not None else ""
            if path and self._is_allowed_file(path):
                filename = os.path.basename(path)
                self._current_selected_path = path
                # JS already shows reading state on form submit.
                if callable(self.on_file_uploaded_callback):
                    self.on_file_uploaded_callback(filename, path)
                self._send_msg({'type': 'file_selected', 'path': path, 'filename': filename})
            else:
                self._send_msg({'type': 'activate_failed_state'})

        elif isinstance(msg, dict) and msg.get("type") == "remove_selected_file":
            removed_path = self._current_selected_path
            self._current_selected_path = None
            if removed_path and callable(self.on_file_removed_callback):
                self.on_file_removed_callback(os.path.basename(removed_path))

    def disable(self):
        """Disable file selection controls."""
        self.disabled = True
        self._send_msg({'type': 'set_disabled', 'disabled': True})

    def enable(self):
        """Enable file selection controls."""
        self.disabled = False
        self._send_msg({'type': 'set_disabled', 'disabled': False})
                
