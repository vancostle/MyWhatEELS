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
            gap: 5px; /* Add 5px gap between all flex items */
            
            & #left_column, #right_column {
                height: 100%;
                overflow: auto;
                box-sizing: border-box;
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                /* Remove flex: 1 and percentage widths - let JS control */
            }
            
            & #gutter {
                width: 12px;
                height: 100%;
                background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 50%, #f8f9fa 100%);
                cursor: col-resize;
                border: none;
                border-radius: 6px;
                transition: all 0.3s ease;
                flex-shrink: 0;
                position: relative;
                box-shadow: 
                    inset 0 1px 0 rgba(255,255,255,0.8),
                    inset 0 -1px 0 rgba(0,0,0,0.1),
                    0 2px 4px rgba(0,0,0,0.1);
            }
            
            & #gutter:hover {
                background: linear-gradient(135deg, #007bff 0%, #0056b3 50%, #007bff 100%);
                box-shadow: 
                    inset 0 1px 0 rgba(255,255,255,0.3),
                    inset 0 -1px 0 rgba(0,0,0,0.2),
                    0 4px 8px rgba(0,123,255,0.3);
                transform: scale(1.01);
            }
            
            & #gutter:active {
                background: linear-gradient(135deg, #0056b3 0%, #003d82 50%, #0056b3 100%);
                transform: scale(0.98);
                box-shadow: 
                    inset 0 2px 4px rgba(0,0,0,0.3),
                    0 1px 2px rgba(0,0,0,0.2);
            }
            
            /* Dragging state - active while user drags */
            & #gutter.dragging {
                background: linear-gradient(135deg, #28a745 0%, #1e7e34 50%, #28a745 100%);
                transform: scale(1.03);
                box-shadow: 
                    inset 0 1px 0 rgba(255,255,255,0.4),
                    inset 0 -1px 0 rgba(0,0,0,0.3),
                    0 6px 12px rgba(40,167,69,0.4),
                    0 0 20px rgba(40,167,69,0.2);
                animation: pulse-glow 0.8s ease-in-out infinite alternate;
            }
            
            @keyframes pulse-glow {
                0% {
                    box-shadow: 
                        inset 0 1px 0 rgba(255,255,255,0.4),
                        inset 0 -1px 0 rgba(0,0,0,0.3),
                        0 6px 12px rgba(40,167,69,0.4),
                        0 0 20px rgba(40,167,69,0.2);
                }
                100% {
                    box-shadow: 
                        inset 0 1px 0 rgba(255,255,255,0.6),
                        inset 0 -1px 0 rgba(0,0,0,0.2),
                        0 8px 16px rgba(40,167,69,0.6),
                        0 0 30px rgba(40,167,69,0.4);
                }
            }
            
            & #gutter::before {
                content: '';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                width: 3px;
                height: 40px;
                background: repeating-linear-gradient(
                    to bottom,
                    #6c757d 0px,
                    #6c757d 3px,
                    transparent 3px,
                    transparent 6px
                );
                border-radius: 2px;
                opacity: 0.6;
                transition: opacity 0.3s ease;
            }
            
            & #gutter:hover::before {
                background: repeating-linear-gradient(
                    to bottom,
                    rgba(255,255,255,0.9) 0px,
                    rgba(255,255,255,0.9) 3px,
                    transparent 3px,
                    transparent 6px
                );
                opacity: 1;
            }
            
            & #gutter.dragging::before {
                background: repeating-linear-gradient(
                    to bottom,
                    rgba(255,255,255,1) 0px,
                    rgba(255,255,255,1) 3px,
                    transparent 3px,
                    transparent 6px
                );
                opacity: 1;
                animation: grip-pulse 0.6s ease-in-out infinite alternate;
            }
            
            @keyframes grip-pulse {
                0% { opacity: 0.8; }
                100% { opacity: 1; }
            }
            
            & #gutter {
                width: 8px;
                background-color: #666;
                cursor: col-resize;
                border-radius: 5px;
            }
        }

    """]       
