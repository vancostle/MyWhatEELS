// ============================================================================
// PANEL PLOTLY RESIZE UTILS - ES MODULE
// ============================================================================

/**
 * Función recursiva para buscar y redimensionar Plotly en Shadow DOM
 * Exactamente como lo hace Panel internamente
 */
export const resizePlotlyInElement = (element) => {
    if (!element) return;
    
    // Verificar si este elemento es un plot de Plotly
    if (element._plotly_graph && window.Plotly) {
        try {
            window.Plotly.Plots.resize(element);
            return true;
        } catch (error) {
            console.warn('Error resizing Plotly plot:', error);
        }
    }
    
    // Buscar en shadow root (Panel usa shadow DOM)
    if (element.shadowRoot) {
        Array.from(element.shadowRoot.children).forEach(resizePlotlyInElement);
    }
    
    // Buscar en hijos normales
    Array.from(element.children || []).forEach(resizePlotlyInElement);
    
    return false;
};

/**
 * Función principal para redimensionar Plotly en Split.js
 * Optimizada para el rendimiento y compatibilidad con Panel
 */
export const resizePlotsInContainers = (containerElements) => {
    if (!containerElements || containerElements.length === 0) return;
    
    containerElements.forEach(container => {
        resizePlotlyInElement(container);
    });
    
    // Disparar eventos de resize como hace Panel
    window.dispatchEvent(new Event('resize'));
    
    // Timeout para asegurar actualización del DOM
    setTimeout(() => {
        window.dispatchEvent(new Event('resize'));
    }, 50);
};

/**
 * Función para crear callbacks de Split.js con redimensión de Plotly
 * Retorna objeto con onDragEnd optimizado para Panel
 */
export const createSplitCallbacks = () => {
    return {
        onDragEnd: (sizes) => {
            // Buscar containers que contienen los elementos
            const containers = document.querySelectorAll('.split > *');
            if (containers.length > 0) {
                resizePlotsInContainers(Array.from(containers));
            }
        }
    };
};

/**
 * Función helper para Split.js - redimensiona plots en elementos específicos
 */
export const resizePlotsAfterSplit = (leftElement, rightElement) => {
    resizePlotsInContainers([leftElement, rightElement]);
};