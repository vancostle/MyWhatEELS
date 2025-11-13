## Demo Page - Progress Display Showcase

A simple demo page to showcase and test the ProgressDisplay component with real-time feedback.

### Structure

```
whateels/pages/demo/
├── MVC/
│   ├── model/
│   │   └── __init__.py          # DemoModel - simple model with duration setting
│   ├── view/
│   │   ├── __init__.py          # DemoView - main view class
│   │   ├── main_layout.py       # DemoMainLayout - displays progress in main area
│   │   └── right_sidebar_layout.py  # DemoRightSidebarLayout - controls
│   └── controller/
│       └── __init__.py          # DemoController - orchestrates demo loading
└── __init__.py                  # Factory function
```

### Features

1. **Always-visible Progress Display**: The ProgressDisplay component is shown by default in the main content area

2. **Duration Control**: Right sidebar has a slider to control how long the demo loads (0.5 - 30 seconds)

3. **Run Button**: Button to start the demo loading sequence

4. **Multi-stage Loading**: Simulates real loading with stages:
   - Preparing data... (25%)
   - Processing... (50%)
   - Finalizing... (75%)
   - Almost done... (90%)
   - Complete! (100%)

5. **Threading**: Uses background threads to prevent UI blocking

### Usage

The demo page demonstrates:
- How to initialize and display ProgressDisplay
- Real-time progress updates with meaningful messages
- Color-coded progress (info/success)
- Completion handling
- Error handling

### Integration

To add this to the main app:

1. Import in the main pages module:
```python
from whateels.pages.demo import create_demo_page
```

2. Create a tab with:
```python
demo_view = create_demo_page()
tabs.append(("Demo", pn.Column(demo_view.main, sizing_mode='stretch_both')))
```

### Components Used

- `ProgressDisplay`: Main component showing progress with spinner, bar, and messages
- `pn.widgets.FloatSlider`: For duration selection
- `pn.widgets.Button`: For start/stop control
- Threading: For non-blocking operations

### Key Implementation Details

- Main content is always replaced with progress display (not alongside)
- Progress updates show specific actions ("Preparing data...", etc.)
- Completion shows success message for 2 seconds then shows the progress display again
- All operations run in background threads
- Button is disabled during execution
