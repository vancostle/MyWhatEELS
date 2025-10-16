# Project Folder Structure Documentation

## Overview
The project is organized to support a scalable, maintainable, and modular Python application, using the Panel library for web-based interfaces. The structure follows best practices for separation of concerns, feature modularity, and future extensibility. The app is designed for deployment as a real web application, supporting file uploads to a server, and can be integrated with backend frameworks like FastAPI or Flask for advanced workflows.

## Structure Breakdown

- **main.py**  
  The entry point of the application. This script is responsible for initializing and serving the main Panel app. It supports both local development and production deployment. For deployment, use `panel serve main.py --port 8000` or similar, and configure a reverse proxy (e.g., Nginx) for production.

- **readme.md**  
  Provides setup instructions and documentation for users and developers, improving onboarding and collaboration.

- **requirements.txt**  
  Lists all Python dependencies, ensuring reproducibility and easy environment setup.

- **whateels/**  
  The main application package. This encapsulates all core logic, features, and assets, keeping the root directory clean.

  - **__init__.py**  
    Marks the directory as a Python package and exposes high-level app components and routing logic. Handles Panel multi-page routing and shared state.

  - **assets/**  
    Contains static files such as CSS and images. This separation allows for easy management of styling and media resources.
    - **css/**: Stores all CSS files for custom styling.
    - **img/**: Stores image assets used in the application.

  - **components/**  
    Contains reusable UI components (e.g., file_dropper.py for file uploads, top_menu.py for navigation).

  - **errors/**  
    Custom exception classes and error handling logic.

  - **helpers/**  
    Utility functions, file readers, decoders, and parsers for domain-specific logic (e.g., DM3/DM4 file reading).

  - **pages/**  
    Contains page modules for multi-page Panel routing (e.g., home, about, clustering, nlls). Each page can use a Panel Template (like FastListTemplate) for consistent layout and navigation.

  - **tests/**  
    Keeps test code separate from production code, supporting best practices in software development.

- **uploads/**  
  Stores user-uploaded files. For large files, consider using a dedicated backend (FastAPI, Flask) for chunked uploads and processing.

## Deployment Notes

- **Production Deployment:**  
  Use `panel serve main.py --address 0.0.0.0 --port 8000` for production. Place behind a reverse proxy (Nginx/Apache) for HTTPS and static file serving. Increase Tornado's buffer limits for large file uploads if needed.

- **Backend Integration:**  
  For advanced workflows (e.g., very large file uploads, authentication, database), integrate with a backend like FastAPI or Flask. Communicate between Panel and the backend via HTTP APIs.

- **Multi-Page Support:**  
  Panel supports multi-page apps using the `routes` argument in `pn.serve` or by using templates with navigation. Shared state can be managed via global variables or `pn.state.cache`.

## Why This Structure?

- **Modularity:**  
  Each feature or component is isolated, making it easy to add, remove, or update features without affecting others.

- **Separation of Concerns:**  
  By dividing code into components, helpers, pages, and assets, the project is easier to understand, maintain, and extend.

- **Scalability:**  
  As the project grows, new features can be added as new subfolders under `whateels/`, and new assets can be added under `assets/`.

- **Reusability:**  
  Common logic and components can be shared across features, reducing code duplication.

- **Clarity:**  
  The structure is intuitive for new developers, with clear entry points and logical grouping of files.

- **Best Practices:**  
  Follows Python and web app conventions, making it compatible with tooling, testing, and deployment workflows.

---

This structure is well-suited for a scalable Panel application with multiple features, real-world deployment, and backend integration. It’s easy to navigate and extend, and supports best practices for professional Python development.
