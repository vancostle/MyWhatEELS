import panel as pn
import param

from panel.custom import JSComponent, Child
from whateels.helpers.constants import JS_ROOT

class ResizableColumns(JSComponent):
    
    value = param.Integer()
        
    left_column = Child(class_=pn.Column)
    right_column = Child(class_=pn.Column)
    
    _JS_FILE = JS_ROOT / "resizable_columns.js"

    _esm = str(_JS_FILE)
    _stylesheets = ["""
        .resizable-columns-container {
            display: flex;
            width: 100%;
            height: 100%;
            
            & #left_column, #right_column {
                height: 100%;
                overflow: auto;
                box-sizing: border-box;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                /* Remove flex: 1 and percentage widths - let JS control */
            }
            
            & #gutter {
                width: 8px;
                height: 100%;
                background-color: #dee2e6;
                cursor: col-resize;
                border: 1px solid #adb5bd;
                transition: background-color 0.2s;
                flex-shrink: 0; /* Prevent gutter from shrinking */
            }
            
            & #gutter:hover {
                background-color: #6c757d;
            }
            
            & #gutter:active {
                background-color: #495057;
            }
            
            & #gutter {
                width: 8px;
                background-color: #666;
                cursor: col-resize;
                border-radius: 5px;
            }
        }

    """]       
