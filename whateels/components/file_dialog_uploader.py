import panel as pn, param, os, ctypes
from ctypes import wintypes
from panel.custom import JSComponent

class FileDialogUploader(JSComponent):

    class _OPENFILENAMEW(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", wintypes.LPVOID),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", wintypes.LPVOID),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    @staticmethod
    def _open_windows_file_dialog() -> str:
        OFN_FILEMUSTEXIST = 0x00001000
        OFN_PATHMUSTEXIST = 0x00000800
        OFN_EXPLORER = 0x00080000
        OFN_HIDEREADONLY = 0x00000004

        file_buffer = ctypes.create_unicode_buffer(65536)
        filter_value = "DigitalMicrograph (*.dm3;*.dm4)\0*.dm3;*.dm4\0All files (*.*)\0*.*\0\0"

        ofn = FileDialogUploader._OPENFILENAMEW()
        ofn.lStructSize = ctypes.sizeof(FileDialogUploader._OPENFILENAMEW)
        ofn.hwndOwner = ctypes.windll.user32.GetForegroundWindow()
        ofn.lpstrFilter = filter_value
        ofn.nFilterIndex = 1
        ofn.lpstrFile = ctypes.cast(file_buffer, wintypes.LPWSTR)
        ofn.nMaxFile = len(file_buffer)
        ofn.lpstrTitle = "Select a DigitalMicrograph file"
        ofn.Flags = OFN_EXPLORER | OFN_FILEMUSTEXIST | OFN_PATHMUSTEXIST | OFN_HIDEREADONLY

        selected = ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(ofn))
        if selected:
            return file_buffer.value.strip()

        error_code = ctypes.windll.comdlg32.CommDlgExtendedError()
        if error_code != 0:
            print(f"Win32 dialog error code: {error_code}")
        return ""
    
    default_message = param.String("Click to select a file", doc="Default message shown in the uploader area.")
    reading_message = param.String("Loading...", doc="Message shown while a file is being read.")
    error_message = param.String("Error reading file!", doc="Message shown if there is an error during file reading.")
    accepted_file_types = param.List(default=['.dm3', '.dm4'], doc="List of accepted file extensions for upload.")
    
    file_selected_callback = param.Parameter(doc="Callback function to be called when a file is selected.")

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
                
                &:hover {
                    cursor: pointer;
                    & h2 {
                        text-decoration: underline;
                    }    
                }
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
            // Wrapper
            const wrapper = document.createElement('div');
            wrapper.className = 'wrapper';

            // File zone
            const fileZone = document.createElement('section');
            fileZone.id = 'file-zone';
            fileZone.title = 'Click to select a dm3 or dm4 file';
            fileZone.addEventListener('click', event => {
                openingSection.classList.add('actived-opening-dialog-state');
                loadingSection.classList.remove('actived-reading-file-state');
                successSection.classList.remove('actived-success-state');
                failedSection.classList.remove('actived-failed-state');

                model.send_event('file_selected_clicked', {}); 
            });
            const fileZoneH2 = document.createElement('h2');
            fileZoneH2.textContent = 'Click to select a dm3 or dm4 file';
            fileZone.appendChild(fileZoneH2);
            
            // Opening state
            const openingSection = document.createElement('section');
            openingSection.className = 'opening state';
            const openingDiv = document.createElement('div');
            const openingP = document.createElement('p');
            openingP.textContent = 'Opening dialog...';
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
            loadingP.textContent = 'Reading file...';
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
            successP.textContent = 'STEM SI_HL.dm4';
            const removeSuccessBtn = document.createElement('button');
            removeSuccessBtn.className = 'remove-file success';
            removeSuccessBtn.addEventListener('click', _ => {
                successSection.classList.remove('actived-success-state');
                loadingSection.classList.remove('actived-reading-file-state');
                failedSection.classList.remove('actived-failed-state');
            });
            successDiv.appendChild(successP);
            successDiv.appendChild(removeSuccessBtn);
            successSection.appendChild(successDiv);

            // Failed state
            const failedSection = document.createElement('section');
            failedSection.className = 'failed state';
            const failedDiv = document.createElement('div');
            const failedP = document.createElement('p');
            failedP.textContent = 'Failed to upload file!';
            const removeFailedBtn = document.createElement('button');
            removeFailedBtn.className = 'remove-file failed';
            removeFailedBtn.addEventListener('click', _ => {
                failedSection.classList.remove('actived-failed-state');
                loadingSection.classList.remove('actived-reading-file-state');
                successSection.classList.remove('actived-success-state');
            });
            failedDiv.appendChild(failedP);
            failedDiv.appendChild(removeFailedBtn);
            failedSection.appendChild(failedDiv);

            // Append all sections to wrapper
            wrapper.appendChild(fileZone);
            wrapper.appendChild(openingSection);
            wrapper.appendChild(loadingSection);
            wrapper.appendChild(successSection);
            wrapper.appendChild(failedSection);

            return wrapper;
        }

        export function render({ model }) {
            const fileDialogUploader = createCustomFileUploader(model);
            return fileDialogUploader;
        }        
    """
    
    def _handle_file_selected_clicked(self, _):
        print("File selection triggered in JS, opening file dialog in Python...")
        path = self._open_windows_file_dialog()

        if path and os.path.isfile(path):
            print(f"Selected file: {path}")
            # Here you could trigger a JS event or update a param to notify the frontend
        else:
            self._send_event(_)
            print("No file selected.")
        
        print("File selection process completed.")