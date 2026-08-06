# TODO de integración del NLLS elemental en MyWhatEELS

Estado: propuesta técnica; no implementa ni modifica todavía el código de la aplicación.

Fuente funcional: ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md.

Destino estudiado: MyWhatEELS, rama vanessa_new, con entrada main.py y GUI Panel/HoloViews/Bokeh organizada por páginas MVC.

Decisión de alcance confirmada: MyWhatEELS dispondrá únicamente de la base OOS/FSalvat. No se añadirán tablas GOS ni se portará el cálculo de superficies de Bethe. El NLLS elemental siempre incluirá un continuo físico OOS y ofrecerá exactamente dos composiciones: `continuum_only` y `continuum_plus_elnes`. Ambas se ajustarán sobre la fuente preprocesada cuya sustracción power-law del background pre-edge esté acreditada.

## 0. Conclusión previa: incompatibilidades directas

Sí existen incompatibilidades directas con una copia literal del NLLS antiguo. No bloquean una migración, pero obligan a introducir una capa de adaptación.

| Incompatibilidad | Evidencia en MyWhatEELS | Decisión de integración |
|---|---|---|
| main.py no es el lugar donde vive la GUI de fitting. Sólo prepara multiprocessing, splash y arranca App. | main.py:2-8 y main.py:52-74. Las rutas se registran en whateels/__init__.py:47-63. | No añadir lógica NLLS a main.py. Mantenerlo sin cambios salvo una futura necesidad de empaquetado/imports. Integrar el flujo en la ruta /fitting y en servicios independientes de Panel. |
| El nombre multifit ya significa ajuste power-law del fondo y datos con fondo sustraído. | whateels/state/app_state.py:27-30; whateels/pages/multifitting/MVC/model/__init__.py:16-17 y 51-80. | Usar siempre nombres elemental_nlls o nlls_pixel_fit. No reutilizar AppState.multifit, AppState.is_multifit, MultifittingModel ni MultiFit para el resultado elemental. |
| El fitting actual sólo mantiene un modelo manual y un único resultado de referencia. | whateels/pages/fitting/MVC/model/__init__.py:34-37, 150-191 y 305-336. | Añadir NLLSWorkspace por dataset, fuente y área. No convertir dictionary ni ref_results actuales en estructuras incompatibles. |
| ComponentItem no contiene elemento, subcapa, área, tipo continuum/ELNES ni identificador estable. | whateels/pages/fitting/MVC/model/component_item.py:1-40. | Mantener ComponentItem para el modo manual y crear DTOs nuevos para el NLLS elemental. |
| Los watchers actuales reconstruyen y ajustan inmediatamente al editar cada tarjeta. | whateels/pages/fitting/MVC/view/components/component_item_view.py:189-196 y 227-269. | Conservar esta reacción en modo manual. En NLLS elemental, marcar el workspace como dirty y ajustar sólo al pulsar Fit References. |
| La segmentación nueva es un diccionario en memoria/JSON, no el Dataset NetCDF antiguo con labs. | whateels/pages/clustering/MVC/model/__init__.py:19-37; whateels/pages/clustering/utils/orchestrator.py:108-129; whateels/pages/clustering/MVC/view/layouts/right_sidebar_layout.py:175-213. | Crear ClusteringAreaAdapter para outputs.labels y recalcular las referencias desde el cubo activo. Ofrecer además carga del JSON que ya exporta la GUI nueva. |
| Los centres guardados no siempre tienen la escala espectral original: K-Means ajusta el array pre-normalizado. | whateels/pages/clustering/utils/preprocessing.py:37-70; whateels/pages/clustering/utils/clustering.py:138-156. | No usar centres como referencia NLLS. Calcular siempre la media de los píxeles de cada máscara sobre la fuente preprocesada y validada que se ajustará. |
| La copia actual de la librería GOS está incompleta: importa bethe_surface_calculations, pero el fichero no está en el árbol. | whateels/helpers/nlls_library/cross_sections/__init__.py:7-11. | Ya no es un bloqueo: el nuevo NLLS no importará ese paquete ni portará Bethe. El código OOS se extraerá a un módulo independiente. |
| Las 322 tablas Hartree JSON no forman parte de los builds; sólo se empaqueta la base OOS/FSalvat. | mywhateels.spec:153-160; patrón equivalente en mywhateels_linux.spec y mywhateels_van.spec. | Es coherente con el nuevo alcance. No mover, empaquetar ni depender de las tablas Hartree. |
| El Bethe antiguo usa scipy.integrate.simps/trapz, incompatible con el stack nuevo. | ../whatEELS/Library/cross_sections/bethe_surface_calculations.py:8,304,315 frente a scipy==1.16.2 en requirements.txt:4-7. | No portar ese módulo. Usar scipy.integrate.simpson/trapezoid únicamente donde lo necesiten OOS, white lines o cuantificación. |
| El multifit elemental antiguo devuelve una matriz de ModelResult y es serial. | ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:335-362. | No persistir ModelResult por píxel. Devolver arrays densos en xarray y DTOs ligeros. Añadir paralelización sólo después de validar la ruta serial. |
| ProcessPoolExecutor ya existe, pero la página de fondo llama al modo serial por defecto. | whateels/helpers/fitting/multifitting.py:154-236 y 388-422; whateels/pages/multifitting/MVC/model/__init__.py:69-77. | Reutilizar el patrón de workers reconstruyendo el modelo dentro del proceso; nunca enviar CompositeModel, closures, Parameters o ModelResult al worker. |
| AppState persiste entre páginas y pestañas, y clear_all no limpia varios campos derivados actuales. | whateels/state/cache.py:11-52; whateels/state/app_state.py:148-156. | Añadir invalidación explícita del workspace/resultados NLLS por identidad de dataset y fuente, y limpiar el estado nuevo en clear_all. No aprovechar este trabajo para cambiar la semántica de campos existentes sin tests. |
| Energy Map actual no es un mapa de parámetros NLLS. Suma la curva de referencia común a cada píxel y luego integra. | whateels/pages/fitting/MVC/model/__init__.py:338-397. | Preservar el botón actual y añadir mapas NLLS con nombres y paneles distintos. |
| El continuo antiguo depende de GOS, pero MyWhatEELS sólo puede usar Salvat OOS/Egerton. | whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:266-384; las tablas OOS ya se incluyen en mywhateels.spec:153-160. | Implementar OOSContinuumProvider como único backend del continuo. El resultado no será numéricamente idéntico al continuo GOS antiguo. Tanto `continuum_only` como `continuum_plus_elnes` requieren una curva OOS válida y datos con background pre-edge sustraído. |

### 0.1. Bethe/GOS no es un requisito matemático del NLLS

El optimizador NLLS sólo necesita una función de modelo evaluable sobre Eloss. Las superficies de Bethe/GOS eran el mecanismo del WhatEELS antiguo para derivar una forma física del continuo con dependencia completa en transferencia de momento q; no son un requisito de lmfit ni de mínimos cuadrados.

Con OOS se usarán dos composiciones explícitas del mismo modelo NLLS:

    # model_composition == "continuum_only"
    I(E) = suma_i A_i * sigma_OOS_i(E + chem_i; E0, alpha, beta)

    # model_composition == "continuum_plus_elnes"
    I(E) = suma_i A_i * sigma_OOS_i(E + chem_i; E0, alpha, beta)
           + suma_j ELNES_j(E)

Por tanto, con OOS se conservan constructor, ajuste por áreas, referencias, propagación, multifit, chi-cuadrado, mapas de parámetros, análisis de centros, white lines y cuantificación. No se implementarán ni se prometerán:

- dependencia GOS completa en q;
- superficies theoretical, beta-cut, F-factor o beta-F;
- compatibilidad numérica exacta con el continuo del WhatEELS antiguo;
- analizador independiente Bethe/GOS.

La sustracción power-law elimina el background pre-edge, pero no elimina el continuo de ionización del borde. Por eso OOS forma parte de las dos composiciones: `continuum_only` ajusta sólo las amplitudes y, opcionalmente, los onsets de las secciones OOS; `continuum_plus_elnes` optimiza simultáneamente esos continuos y los picos Gaussian/Lorentzian/PseudoVoigt/SplitLorentzian. `lmfit` es el único motor de ajuste en ambos casos; la diferencia está únicamente en la lista de componentes. Las dos rutas y sus validaciones se especifican en 5.4.3-5.4.5.

#### 0.1.1. Compatibilidad funcional de las composiciones

| Composición | WhatEELS original | MyWhatEELS | Componentes entregados a lmfit |
|---|---:|---:|---|
| `continuum_only` | Sí, eliminando/desactivando las ELNES | Sí, opción explícita | Uno o varios continuos físicos; GOS en el original y OOS en MyWhatEELS |
| `continuum_plus_elnes` | Sí, funcionamiento normal | Sí, opción predeterminada | Continuos físicos + picos ELNES |

No llamar «lmfit-only» a ninguna de ellas: `lmfit` construye y optimiza los dos modelos. Tampoco confundir el continuo físico del borde con el background pre-edge que se sustrae durante el preprocesado.

### 0.2. Corrección imprescindible del servicio OOS actual

El servicio OOS existente no debe reutilizarse literalmente como continuo. oos_reader devuelve energy, oos y onset en whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:148-193. Sin embargo, df_cross_section descarta energy mediante:

    _, oos, eloss = self.oos_reader(z_number, subshell)

en whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:325. Desde ahí trata el onset escalar como variable de pérdida energética en las líneas 325-365. Eso puede producir un array con la longitud de oos, pero no una sección calculada canal a canal sobre su eje energético.

Hay un segundo defecto que tampoco debe copiarse: `Loader.cross_section`, en el mismo fichero `:367-384`, integra el array devuelto sin pasar `x=eaxis` a `scipy.integrate.trapezoid`. Esa operación usa separación unitaria entre índices, no la dispersión energética real de la tabla.

OOSContinuumProvider debe corregir el contrato:

    energy, oos, onset = oos_reader(...)
    cross_section = calculate_oos_cross_section(
        energy=energy,
        oscillator_strength=oos,
        beam_energy_keV=E0,
        convergence_angle_mrad=alpha,
        collection_angle_mrad=beta,
    )
    curve_on_eloss = interpolate(energy, cross_section, dataset.Eloss)

Después debe anular el continuo antes del onset, aplicar el desplazamiento químico, convolución/suavizado instrumental y amplitud ajustable. Esta corrección debe implementarse una sola vez en un servicio compartido por NLLS y, tras pruebas de regresión, por cuantificación.

## 1. Base real que debe conservarse

| Contrato actual | Código real | Implicación |
|---|---|---|
| Entrada de proceso y soporte de ejecutable congelado | main.py:2-8 y 52-74 | freeze_support ya permite añadir workers en una fase posterior. |
| Registro de páginas | whateels/__init__.py:47-63 | /fitting ya existe; no se necesita una ruta nueva para el primer incremento. |
| Construcción MVC de Fitting | whateels/pages/fitting/__init__.py:11-24 | El adaptador NLLS se inyectará desde esta página sin cambiar sus URL ni sidebars. |
| Selección de dataset por ?tab= | whateels/pages/fitting/MVC/controller/__init__.py:31-52 | La identidad NLLS debe incorporar ese índice y atributos del dataset. |
| Selector raw/preprocessed | whateels/pages/fitting/MVC/controller/__init__.py:167-227 y 241-279 | Un cambio de fuente invalida modelos, referencias y resultados NLLS igual que ya invalida el fitting manual. En Elemental NLLS, seleccionar raw deja Build/Run deshabilitados. |
| ROI seleccionada | whateels/pages/fitting/MVC/controller/__init__.py:77-94; whateels/pages/fitting/MVC/view/plots/spectrum_image_plot.py:114-126 | La GUI ya publica un espectro ROI. Para NLLS deberá calcularse la media, no reutilizar sin más la suma mostrada. |
| Componentes manuales soportados | whateels/pages/fitting/MVC/view/__init__.py:181-224; whateels/pages/fitting/MVC/model/__init__.py:158-191 | Gaussian, Lorentzian, PseudoVoigt y SplitLorentzian se conservan. |
| lmfit instalado | requirements.txt:20-23 | Versión objetivo: lmfit 1.3.4. |
| Metadatos de geometría | whateels/pages/home/MVC/controller/services/file_processor_service.py:181-187 y 242-247 | E0 está en keV; alpha y beta, en mrad. |
| Origen DM de E0, alpha y beta | whateels/pages/home/MVC/controller/dm_file_processing/parsers/dm_eels_data.py:82-132 | Un campo ausente produce 0.0, por lo que 0 no puede considerarse geometría válida para calcular la sección OOS. |
| Dimensiones del cubo | whateels/pages/home/MVC/controller/services/file_processor_service.py:207-230 | ElectronCount usa (y, x, Eloss). El contrato NLLS debe conservar nombres y orden. |
| Segmentación compartida | whateels/state/app_state.py:67-69; whateels/pages/clustering/utils/orchestrator.py:118-129 | labels y centres están disponibles sin fichero intermedio. |
| Descarga en memoria | whateels/pages/clustering/MVC/view/layouts/right_sidebar_layout.py:186-213 | Configuración y resultados NLLS deben usar FileDownload/InMemoryFile, no escribir carpetas implícitas. |
| Base OOS empaquetada | mywhateels.spec:153-160 | Los JSON FSalvat ya forman parte del build; debe verificarse el mismo patrón en los otros dos spec. |
| Navegación común | whateels/templates/general_page_template.py:133-184 | Una futura página de resultados se añadirá aquí y en App, no en main.py. |

## 2. Invariantes de no regresión

- El modo manual actual debe seguir mostrando exactamente los cuatro tipos de componente, conservar Add Component, sus tarjetas reactivas y Show Energy Map.
- AppState.multifit y AppState.is_multifit continúan reservados al preprocesado/sustracción de fondo.
- AppState.fitting_results continúa siendo la curva 1D que consume la visualización manual; no almacenará un xarray NLLS.
- El switch Use Preprocessed Data mantiene su callback actual y debe invalidar también, no reciclar, el workspace NLLS de la fuente anterior.
- La página Quantification actual y su estado quantification_elements no se usarán como almacenamiento del análisis NLLS.
- Ningún primer incremento debe cambiar las rutas existentes, los parámetros query ni el orden de dimensiones ElectronCount.
- Toda capacidad nueva queda detrás de una sección o modo Elemental NLLS. Hasta completar la fase de validación puede quedar bajo un feature flag desactivado por defecto.
- Los errores de metadatos, OOS o convergencia deben aparecer como notificaciones de Panel y dejar los resultados anteriores intactos.
- No se guardarán objetos pickle, ModelResult, splines ni closures en ficheros de usuario.

## 3. Arquitectura propuesta

Los nombres de esta sección son nuevos y propuestos; no se presentan como símbolos ya existentes.

    whateels/
    ├── nlls/
    │   ├── contracts.py
    │   ├── defaults.py
    │   ├── workspace.py
    │   ├── model_builder.py
    │   ├── references.py
    │   ├── multifit.py
    │   ├── workers.py
    │   ├── results.py
    │   ├── serialization.py
    │   ├── cross_sections/
    │   │   ├── protocol.py
    │   │   ├── oos_continuum_provider.py
    │   │   └── cache.py
    │   └── analysis/
    │       ├── centers.py
    │       ├── white_lines.py
    │       └── egerton.py
    └── pages/fitting/MVC/
        ├── controller/nlls_controller.py
        ├── view/layouts/nlls_sidebar_layout.py
        └── view/components/
            ├── elemental_edge_item_view.py
            ├── area_model_item_view.py
            └── nlls_results_view.py

Regla de dependencias:

    Panel callbacks
        -> NLLSController
        -> servicios puros de whateels.nlls
        -> lmfit / NumPy / SciPy / xarray / proveedor OOS

whateels.nlls no debe importar Panel, Bokeh, HoloViews, FittingView ni AppState. El controlador traduce widgets a comandos de dominio y traduce excepciones/estado a la GUI. Esto permite probar modelo, propagación y análisis sin arrancar el servidor.

### 3.1. Contratos de dominio

Crear dataclasses inmutables o de mutación controlada:

| Tipo propuesto | Campos mínimos | Finalidad |
|---|---|---|
| DatasetIdentity | tab_index, original_name, image_name, shape, Eloss_hash, source_kind, source_revision, preprocessing_history, background_subtracted | Evitar aplicar máscaras, referencias o resultados al dataset/fuente equivocados y verificar que el NLLS recibe la fuente con background pre-edge sustraído. |
| ExperimentalGeometry | beam_energy_keV, collection_angle_mrad, convergence_angle_mrad, provenance | Validar unidades y registrar si el usuario corrigió un 0 de metadatos. |
| ParameterSpec | value, min, max, vary, expr opcional | Un único formato serializable para iniciales, cotas y bloqueos. |
| FineStructureSpec | id, element, subshell_group, shape, center, sigma, amplitude y ParameterSpec | Describir ELNES sin depender de un objeto lmfit vivo. |
| ModelComposition | `continuum_only` o `continuum_plus_elnes` | Hacer explícitas las dos composiciones admitidas sin confundirlas con dos optimizadores diferentes. |
| ContinuumSpec | id, element, subshell_group, provider_version, onset, soften, normalization_factor, A, chemical_shift, chemical_shift_convention | Describir el continuo OOS obligatorio y cómo regenerar su curva. La convención viaja con el modelo serializado. |
| AreaModelSpec | area_id, label, mask, reference_strategy, model_composition, component_specs, deleted_component_ids | Mantener configuración independiente por área. `model_composition` sólo admite `continuum_only` o `continuum_plus_elnes`. |
| ReferenceFitSnapshot | area_id, success, message, method, params, redchi, best_fit, residual, components | Persistir el ajuste de referencia sin serializar ModelResult. |
| NLLSWorkspace | schema_version, DatasetIdentity, geometry, areas, active_area, reference_fits, dirty_revision | Estado editable y reproducible del constructor. |
| NLLSRunRequest | selected_areas, fit_range, method, model_composition_by_area, parallel, workers, rerun_from | Entrada cerrada e inmutable de una ejecución. |

### 3.2. Estado reactivo

Añadir campos con nombres exclusivos a AppState:

- nlls_workspace: workspace activo o None.
- nlls_results: xr.Dataset denso o None.
- nlls_run_state: idle, building, fitting_references, running, cancelling, complete o error.
- nlls_revision: entero que el controlador incrementa cuando cambia contenido interno.

Actualizar clear_all para llamar a clear_nlls_state. El workspace debe incluir DatasetIdentity y validarse en cada entrada a /fitting. El estado no debe contener una rejilla de ModelResult.

Motivo: CacheManager mantiene AppState entre páginas y pestañas del mismo usuario, whateels/state/cache.py:11-52, mientras el clear actual sólo cubre una parte de los parámetros, whateels/state/app_state.py:148-156.

### 3.3. Ruta real del código que debe estudiar el siguiente agente

No existe actualmente un NLLS elemental basado en OOS conectado a Fitting. Las piezas están separadas y algunas están duplicadas. Ésta es la ruta de lectura recomendada:

| Orden | Fichero/símbolo existente | Qué contiene realmente | Cómo usarlo |
|---:|---|---|---|
| 1 | whateels/pages/fitting/__init__.py:11-24 | Construye FittingModel, FittingView y FittingController. | Punto de composición de la página. Inyectar NLLSController aquí o desde FittingController, sin poner dominio en la página. |
| 2 | whateels/pages/fitting/MVC/controller/__init__.py:70-99 | Registra callbacks del fitting manual, ROI, preprocessed switch y Energy Map. | Mantener intactos esos callbacks y delegar los nuevos a NLLSController.bind(). |
| 3 | whateels/pages/fitting/MVC/view/__init__.py:150-268 | Crea los widgets y la barra lateral actual. | Añadir el selector de modo Manual/Elemental NLLS y los controles nuevos. |
| 4 | whateels/pages/fitting/MVC/model/__init__.py:84-191 | Estima componentes manuales, construye Gaussian/Lorentzian/etc. y crea Parameters. | Inspiración para prefijos, make_params y componentes ELNES. No convertir esta clase en el workspace elemental. |
| 5 | whateels/pages/fitting/MVC/model/__init__.py:305-336 | Ajusta la única referencia manual con Model.fit. | Inspiración para limpieza de NaN/Inf; el servicio nuevo debe operar por area_id. |
| 6 | whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:133-384 | Loader OOS activo, fórmula Salvat, corrección alpha/beta y total integrado. | Fuente física más completa, pero requiere corregir eaxis/onset e integración antes de extraerla del MVC. |
| 7 | whateels/pages/quantification/MVC/controller/__init__.py:31-34 y 194-214 | Instancia Loader_OOS desde OOS_ROOT, lee E0/beta/alpha y guarda curvas por subcapa. | Ruta activa que demuestra dónde están los JSON y cómo llegan los metadatos. |
| 8 | whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py:222-238 | Suma curvas de varias subcapas sobre un eje común. | Reutilizar el algoritmo de preparar/interpolar/sumar, trasladado a dominio y sin lógica visual. |
| 9 | whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py:674-761 | Consume eaxis y cross_section para una subcapa o white-line group. | Inspiración para agrupación y chemical shift; no reutilizar las clases de plot dentro del modelo. |
| 10 | whateels/pages/fitting/MVC/controller/services/oos_loader_service.py:56-245 | Segunda copia OOS, sin corrección de alpha. | No usar como backend. Está sin conectar a FittingController y debe eliminarse o delegar al proveedor compartido en una refactorización posterior. |
| 11 | whateels/helpers/nlls_library/cross_sections/oos_loader.py:39-124 | Loader OOS legado con dependencias globales de Fileinput y trapz antiguo. | No importar. Sólo sirve para localizar deuda técnica. |
| 12 | whateels/pages/home/MVC/view/plots/spectrum_image_plot.py:2616-2644 | Ejecuta PowerLawModel multipíxel, devuelve mode=subtracted y publica preprocessed_plot_dataset. | Ésta es la ruta obligatoria antes del NLLS elemental mientras éste no modele simultáneamente el background. Debe publicar procedencia verificable de la sustracción. |
| 13 | whateels/pages/multifitting/MVC/model/__init__.py:16-80 | Otra fachada del multifit power-law de fondo. | No confundir con el NLLS elemental ni reutilizar su AppState.multifit como resultado elemental. |

Comprobación importante: no hay import de Loader_OOS dentro de FittingController ni de FittingModel. La mera existencia de whateels/pages/fitting/MVC/controller/services/oos_loader_service.py no significa que Fitting lo use.

### 3.4. Ruta de inspiración exacta en WhatEELS antiguo

El siguiente agente debe leer el original en este orden. Es inspiración de responsabilidades, no código para copiar:

| Paso antiguo | Símbolo y líneas | Responsabilidad | Adaptación OOS propuesta |
|---|---|---|---|
| Inicializar SI | ../whatEELS/Library/nlls_functions.py:31-127, NLLS_fitting.__init__ | Lee Eloss, ElectronCount, E0/beta/alpha y crea la referencia central. | DatasetIdentity, ExperimentalGeometry y ReferenceSpectrumService. |
| Registrar edge | ../whatEELS/Library/nlls_functions.py:128-150, add_element | Completa parejas 4/5 y 2/3 y crea bethe_surface. | Workspace.add_edge completa grupos, pero sólo registra OOS shells; no crea Bethe. |
| Preparar sección | ../whatEELS/Library/nlls_functions.py:153-242, ready_elements | Calcula curvas GOS, extensión y splines. | OOSContinuumProvider.curve calcula sigma(E), filtra dominio, interpola en Eloss y normaliza. |
| Crear specs | ../whatEELS/Library/nlls_functions.py:333-361, create_components/create_components_and_model | Crea continuo, ELNES, referencia y máscara default. | NLLSModelBuilder trabaja desde AreaModelSpec; ReferenceSpectrumService gestiona referencia/máscara. |
| Crear continuo | ../whatEELS/Library/nlls_functions.py:411-504, create_continuum_components | Construye closures A y chem, agrupa dobletes y aplica suavizado. | NLLSModelBuilder._make_oos_component crea una closure reconstruible desde OOSCurveSnapshot. |
| Suavizar | ../whatEELS/Library/nlls_functions.py:506-523, _soften_x_sections | gaussian_filter1d sobre la curva. | OOSContinuumProvider._broaden convierte eV a canales antes de gaussian_filter1d. |
| Crear ELNES | ../whatEELS/Library/nlls_functions.py:525-560, add_ELNES | Añade white-line peaks y estima center/sigma/amplitude. | NLLSModelBuilder._make_elnes_component y ParameterDefaults. |
| Defaults | ../whatEELS/Library/nlls_functions.py:619-693, initial_constraints_continuum/initial_constraints_WL | Define A, chem, vary y cotas ELNES. | defaults.py y ParameterSpec, nunca diccionarios paralelos sin tipo. |
| Componer lmfit | ../whatEELS/Library/nlls_functions.py:695-808, create_model | Envuelve continuo en Model, crea modelos ELNES, suma y hace make_params. | NLLSModelBuilder.build, con soporte explícito para `continuum_only` y `continuum_plus_elnes`. |
| Ajustar referencia | ../whatEELS/Library/nlls_functions.py:992-1008, fit_reference | Model.fit(reference, params, x=Eloss). | ReferenceFitService.fit_area. |
| Ajustar píxeles | ../whatEELS/Library/interactive_NLLS_SImages.py:2142-2223, _callback_multifit | Usa params de referencia, recorre máscara y guarda ModelResult. | ElementalMultifitService.fit_areas y NLLSResultsAccumulator. |
| Extraer resultados | ../whatEELS/Library/nlls_functions.py:1369-1481, get_full_results_data | Extrae redchi, fits, componentes y parámetros. | Extraer inmediatamente después de cada fit y producir xr.Dataset, sin rejilla de ModelResult. |

Diferencia crítica: create_model antiguo comienza en mod_cont_list[0] y después suma ELNES, ../whatEELS/Library/nlls_functions.py:784-793. MyWhatEELS mantendrá el continuo como componente obligatorio, pero construirá una lista general y validará explícitamente que exista al menos una curva OOS válida. Esto evita un `IndexError`, permite diferenciar limpiamente `continuum_only` de `continuum_plus_elnes` y produce errores de dominio comprensibles.

### 3.5. Ficheros y funciones nuevas: contrato de implementación

| Fichero nuevo | Símbolos mínimos | No debe hacer |
|---|---|---|
| whateels/nlls/contracts.py | ModelComposition, DatasetIdentity, ExperimentalGeometry, FitRange, BroadeningSpec, ParameterSpec, EdgeSpec, ContinuumSpec, FineStructureSpec, AreaModelSpec, ReferenceFitSnapshot, NLLSRunRequest | Importar Panel/lmfit.Model o guardar arrays globales. |
| whateels/nlls/workspace.py | NLLSWorkspace.add_edge, set_model_composition, clone_area, update_parameter, invalidate_area, invalidate_all | Ajustar datos o tocar widgets. |
| whateels/nlls/cross_sections/oos_continuum_provider.py | OOSRawCurve, OOSPhysicalCurve, OOSCurveSnapshot; OOSContinuumProvider.available_edges, load_raw, differential_cross_section, curve, integrate, _broaden | Leer AppState, usar onset como eje o depender de una View. |
| whateels/nlls/model_builder.py | BuiltAreaModel; NLLSModelBuilder.build, _make_oos_component, _make_elnes_component, _apply_parameter_specs | Persistir CompositeModel o decidir el área activa de GUI. |
| whateels/nlls/references.py | ReferenceSpectrumService.from_roi/from_mask/default_central; ReferenceFitService.fit_area/fit_many | Usar outputs.centres normalizados como referencia. |
| whateels/nlls/multifit.py | ElementalMultifitService.fit_areas, fit_area_serial, _initial_params_for_pixel, _fit_pixel | Actualizar Panel desde el worker o encadenar vecinos en el primer fit. |
| whateels/nlls/workers.py | fit_chunk_worker, serialize_worker_request | Recibir Model, Parameters, closure o ModelResult desde el proceso padre. |
| whateels/nlls/results.py | NLLSResultsAccumulator.create/store_success/store_error/to_dataset; NLLSResultsAssembler | Guardar objetos dtype=object. |
| whateels/nlls/serialization.py | dump/load/migrate config; dump result metadata | Usar pickle o rutas absolutas. |
| whateels/pages/fitting/MVC/controller/nlls_controller.py | bind, callbacks _on_*, _run_service, _publish_revision, cleanup | Contener fórmulas físicas o bucles de píxeles. |

El agente debe crear primero contratos y servicios puros; sólo después conectar widgets. Así cualquier fallo puede aislarse sin arrancar Panel.

## 4. Mapa del pipeline antiguo al nuevo

| Etapa del mapa antiguo | Servicio/símbolo nuevo propuesto | Entrada desde la GUI nueva | Resultado |
|---|---|---|---|
| 3. Constructor | NLLSModelBuilder, OOSContinuumProvider, ParameterDefaults | Elemental NLLS > Add Edge; Build Elemental Model | AreaModelSpec materializado y preview de componentes |
| 4. Áreas | ClusteringAreaAdapter, ReferenceSpectrumService | Use Current Clustering; Load Clustering JSON; selector de área | Máscaras y referencia media por área |
| 5. Referencias | ReferenceFitService.fit_one/fit_many | Fit Current Reference; Fit All References | ReferenceFitSnapshot por área |
| 6. Propagación | ElementalMultifitService._initial_params_for_pixel | Implícita dentro de Run Elemental NLLS | Copia de parámetros convergidos de la referencia o del mismo píxel en rerun |
| 7. Multifit | ElementalMultifitService.fit_areas; fit_chunk_worker | Run Elemental NLLS; Cancel; Run Modified Fit | xr.Dataset de resultados y estados por píxel |
| 8. Análisis | NLLSResultsAssembler, CenterAnalysisService, WhiteLineService, EgertonQuantificationService | Results; Center Analysis; White Lines; Elemental Quantification | Mapas, ratios y datasets derivados |
| 9. Bethe/GOS periférico | Fuera de alcance | Sin entrada GUI | No implementado: MyWhatEELS sólo dispone de OOS |
| 10. Guardado | NLLSConfigSerializer, NLLSResultExporter | Save Model; Save Configuration; Download References; Download Results | JSON con esquema + NetCDF, CSV e imágenes opcionales |

Referencia del comportamiento antiguo: ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:80-190 para el constructor, 192-244 para áreas, 246-286 para referencias, 288-382 para propagación/multifit, 383-472 para análisis y 474-540 para GOS/guardado.

## 5. Etapa 3: constructor del modelo

### 5.1. Encaje en la GUI

En whateels/pages/fitting/MVC/view/__init__.py:150-268, sustituir el contenido único del bloque NLLS Instructions por dos pestañas o un RadioButtonGroup:

1. Manual Components: contiene sin cambios los widgets actuales y Add Component.
2. Elemental NLLS: contiene los nuevos pasos explícitos.

Controles nuevos:

- Experimental Geometry: E0, beta y alpha, inicializados desde attrs. Si E0 <= 0 o beta <= 0, mostrar error y permitir corrección local; no modificar silenciosamente los attrs del dataset.
- Element: selector por número atómico, reutilizando sólo la lectura OOS/tabla periódica que ya usa QuantificationController en whateels/pages/quantification/MVC/controller/__init__.py:85-129.
- Subshells: opciones realmente presentes en la base OOS/FSalvat.
- OOS method/version: campo informativo y persistido; no es un selector GOS.
- Model composition: `Continuum + ELNES` por defecto o `Continuum only`. Las dos opciones usan el continuo OOS; la segunda excluye todas las componentes ELNES del modelo materializado.
- Background status: indicador de procedencia de la sustracción power-law pre-edge. `Add Edge`, `Build` y `Run` permanecen bloqueados hasta que la fuente activa acredite esa operación.
- OOS status: tabla localizada, versión/checksum, rango energético cubierto y motivo de error si el edge elegido no está disponible.
- Soften edge: activado por defecto; strength 1.5 para reproducir el código antiguo.
- ELNES shape: Gaussian por defecto; Lorentzian, PseudoVoigt y SplitLorentzian como alternativas.
- Add Edge.
- Build Elemental Model.
- Save Model y Load Model.

No conectar estos widgets a FittingController._add_component_item_button_callback, que hoy crea ComponentItem y llama inmediatamente a add_component, whateels/pages/fitting/MVC/controller/__init__.py:126-144.

### 5.2. Callbacks propuestos

| Control | Callback en NLLSController | Efecto |
|---|---|---|
| Cambio de geometría | _on_geometry_changed | Valida unidades, invalida curvas OOS, referencias y multifit; conserva la definición de edges. |
| Cambio de composición | _on_model_composition_changed | Cambia `AreaModelSpec.model_composition` entre `continuum_only` y `continuum_plus_elnes` e invalida modelo materializado, referencia y resultados del área. No cambia la fuente ni omite la validación OOS/background. |
| Cambio de elemento | _on_element_changed | Consulta subcapas realmente presentes en el catálogo OOS. |
| Add Edge | _on_add_edge | Completa parejas 4/5 y 2/3, crea siempre specs de continuo y conserva specs ELNES editables para la composición completa, marca dirty. No ejecuta lmfit. |
| Build Elemental Model | _on_build_model | Valida la sustracción de background, geometría y tablas OOS; calcula curvas OOS y añade ELNES sólo si la composición es `continuum_plus_elnes`. Después crea preview y materializa modelo/params del área activa. |
| Cambio de parámetros/cotas | _on_component_spec_changed | Modifica ParameterSpec del área activa, incrementa revisión e invalida sólo sus fits. |
| Remove ELNES | _on_remove_fine_structure | Desactiva/elimina una componente sólo en el área activa. |
| Reset Area | _on_reset_area_model | Restaura la copia heredada por esa área. |
| Save/Load Model | _on_download_model / _on_load_model | JSON portable sólo con geometría opcional, edges y defaults; sin máscaras ni resultados. |

### 5.3. Traducción de edge a componentes

Mantener la semántica demostrada por el código antiguo:

    elemento + subcapa
      -> normalizar pares 4/5 y 2/3
      -> ContinuumSpec OOS por grupo
      -> curva OOS corregida e interpolada en Eloss
      -> si model_composition=continuum_plus_elnes: FineStructureSpec habilitadas
      -> si model_composition=continuum_only: ninguna ELNES en el modelo materializado
      -> NLLSModelBuilder.build(area)
      -> Model o CompositeModel + make_params

El mapa antiguo documenta la normalización de parejas en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:98-124 y la construcción de continuo/ELNES en las líneas 126-166.

### 5.4. Continuo OOS

Implementar CrossSectionProvider como protocolo:

    available_edges(element) -> list[str]
    curve(element, subshells, geometry, Eloss) -> CrossSectionCurve
    database_info() -> versión, fuente y checksums

OOSContinuumProvider debe:

- resolver datos desde whateels/data/oos/Hartree_Xsections_FSalvat con pathlib;
- cargar y validar eaxis, counts y onset;
- calcular la sección diferencial sobre todo eaxis, no sólo en onset;
- incorporar E0 y beta, y la corrección de ángulo efectivo cuando alpha sea finito;
- interpolar la sección en el Eloss exacto del dataset;
- poner cero antes del onset y fuera del dominio no extrapolable;
- combinar dobletes usando las curvas OOS reales de cada subcapa cuando ambas existan;
- suavizar/convolucionar sólo cuando está activado;
- cachear por elemento, subcapas, geometría, Eloss_hash, fuerza y `fit_range` cuando la normalización dependa de esa ventana;
- devolver arrays serializables, no interpoladores como estado persistente;
- lanzar MissingOOSTableError o InvalidOOSDataError sin fallback GOS.

La base ya está centralizada bajo OOS_ROOT en whateels/helpers/constants.py:20-22 y el controlador actual la abre desde ese root en whateels/pages/quantification/MVC/controller/__init__.py:31-34. La nueva implementación debe extraer la física de la capa MVC y no importar el oos_loader legado de helpers, que conserva dependencias globales.

#### 5.4.1. Ruta de datos OOS que debe implementarse

El siguiente agente debe seguir esta secuencia, manteniendo separadas la tabla física, la forma normalizada usada por lmfit y el parámetro de amplitud:

    OOS14.json
      -> OOSContinuumProvider.load_raw(z, shell)
      -> OOSRawCurve(energy_eV, oscillator_strength, onset_eV)
      -> OOSContinuumProvider.differential_cross_section(raw, geometry)
      -> OOSPhysicalCurve(energy_eV, sigma, units, formula_version)
      -> combine_shells(...)              # suma física antes de normalizar
      -> broaden_in_energy_units(...)      # opcional
      -> interpolate_to_dataset_eloss(...)
      -> normalize_for_fit(...)
      -> OOSCurveSnapshot(shape, normalization_factor, metadata)
      -> NLLSModelBuilder._make_oos_component(...)
      -> A * shape(Eloss + chemical_shift)

API concreta propuesta en `whateels/nlls/cross_sections/oos_continuum_provider.py`:

    class OOSContinuumProvider:
        def available_edges(self, atomic_number: int) -> tuple[str, ...]: ...
        def load_raw(self, atomic_number: int, shell: str) -> OOSRawCurve: ...
        def differential_cross_section(
            self, raw: OOSRawCurve, geometry: ExperimentalGeometry
        ) -> OOSPhysicalCurve: ...
        def curve(
            self,
            atomic_number: int,
            shells: tuple[str, ...],
            geometry: ExperimentalGeometry,
            dataset_eloss: np.ndarray,
            broadening: BroadeningSpec,
            fit_range: FitRange | None,
        ) -> OOSCurveSnapshot: ...
        def integrate(
            self, curve: OOSPhysicalCurve, energy_min: float, energy_max: float
        ) -> float: ...

`load_raw` puede inspirarse sólo en el parseo de `Loader.oos_reader`, `whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:148-199`. Debe devolver los tres valores con nombres no ambiguos. En la base actual, `eaxis` es un eje absoluto de pérdida energética que comienza en el onset; no debe transformarse en un eje relativo sin que el formato de datos lo indique.

La fórmula Salvat/Egerton debe extraerse de `Loader.df_cross_section`, `whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:266-365`, pero reemplazando el `eloss` escalar de la línea 325 por el array `energy_eV`. En pseudocódigo de implementación:

    T = geometry.beam_energy_keV * 1000.0
    W = np.asarray(raw.energy_eV, dtype=float)
    f = np.asarray(raw.oscillator_strength, dtype=float)
    mec2 = ELECTRON_REST_ENERGY_EV
    gamma = 1.0 + T / mec2
    beta_v2 = 1.0 - 1.0 / gamma**2
    theta = effective_collection_angle(
        convergence_mrad=geometry.alpha_mrad,
        collection_mrad=geometry.beta_mrad,
        beam_energy_keV=geometry.beam_energy_keV,
        energy_loss_eV=W,
    )

    valid = (
        np.isfinite(W) & np.isfinite(f)
        & (W >= raw.onset_eV) & (W > 0.0) & (W < T)
    )
    root_argument = (
        (T * (T + 2.0 * mec2))**3
        * (T - W[valid])
        * (T - W[valid] + 2.0 * mec2)
    )
    if np.any(root_argument < 0.0):
        raise InvalidOOSDataError("invalid kinematic domain")

    Y = (
        1.0
        + 4.0
        * np.sqrt(root_argument)
        * np.sin(theta[valid] / 2.0)**2
        / (mec2**2 * W[valid]**2)
    )
    collection_term = np.log(Y) - beta_v2 * (1.0 - 1.0 / Y)
    prefactor = 8.0 * np.pi * (BOHR_RADIUS * RYDBERG_EV)**2
    prefactor /= mec2 * beta_v2 * W[valid]
    sigma = np.zeros_like(W)
    sigma[valid] = prefactor * f[valid] * collection_term

Esto es una guía de traslación del código existente, no una nueva validación científica de la fórmula. Antes de fijarla como API estable hay que crear casos dorados, comprobar unidades/radianes y contrastar límites `alpha=0` y `alpha>0`. La corrección de ángulo efectivo que ya existe en `oos_loader_service.py:71-130` recibe pérdida energética; su nueva versión debe aceptar un array o vectorizarse explícitamente.

Validaciones obligatorias antes de devolver una curva:

- `energy_eV`, `oscillator_strength` y `sigma` son unidimensionales, tienen igual longitud y contienen al menos dos muestras válidas;
- el eje se ordena de forma creciente y los duplicados se resuelven de forma determinista antes de interpolar;
- `E0 > 0`, `beta > 0`, `alpha >= 0`, y `W < E0` en el dominio calculado;
- no se silencian raíces negativas, `NaN`, `Inf` ni una curva completamente nula;
- se pone cero antes del onset y se usa `left=0, right=0`: no se extrapola fuera de la tabla;
- el intervalo de ajuste debe solaparse con el dominio OOS del edge; de lo contrario se bloquea el build con un error accionable.

La integración física debe usar el eje real:

    mask = (curve.energy_eV >= energy_min) & (curve.energy_eV <= energy_max)
    value = scipy.integrate.trapezoid(
        curve.sigma[mask], x=curve.energy_eV[mask]
    )

No copiar `Loader.cross_section`, `whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:367-384`, sin corregirlo: actualmente llama a `trapezoid(self.df_cross_section(...))` sin `x`, por lo que integra por índice de canal en vez de por eV cuando el paso no es exactamente 1 eV.

#### 5.4.2. Dobletes, desplazamiento, suavizado y escala numérica

Las parejas `L2+L3` y `M4+M5` no se representan duplicando una forma. `EdgeSpec` conserva las subcapas solicitadas; el provider carga cada JSON presente, calcula cada sección con la misma geometría, las interpola sobre un eje común y las suma. Esta intención procede de `NLLS_fitting.add_element`, `../whatEELS/Library/nlls_functions.py:128-150`, pero la forma concreta debe ser OOS, no GOS. La vista de cuantificación nueva ya muestra el patrón de sumar curvas de shells sobre un eje común en `whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py:222-238`; reutilizar la idea, no widgets ni estado de esa vista.

El suavizado debe expresarse en eV y convertirse a canales con el paso real del dataset:

    dispersion_eV = np.median(np.abs(np.diff(dataset_eloss)))
    sigma_channels = broadening.sigma_eV / dispersion_eV
    broadened = scipy.ndimage.gaussian_filter1d(curve, sigma_channels)

No copiar el suavizado antiguo como un sigma fijo en muestras (`_soften_x_sections`, `../whatEELS/Library/nlls_functions.py:506-523`). Si el selector GUI usa FWHM, convertir una sola vez mediante `sigma_eV = fwhm_eV / 2.354820045`.

La convención de desplazamiento será única:

    shifted_shape(x, chemical_shift) = interp(
        x + chemical_shift,
        oos_energy,
        oos_shape,
        left=0.0,
        right=0.0,
    )

Con esta definición, `chemical_shift > 0` desplaza el borde modelado hacia **menor** pérdida de energía: un rasgo tabulado en `E0` aparece en `E0 - chemical_shift`. Leído al revés, `chemical_shift` es cuánto por encima está la tabla respecto de donde el borde aparece realmente en los datos.

Se adopta deliberadamente la convención que ya usa MyWhatEELS. Así las tres implementaciones coinciden y no hay conversión de signo en ninguna frontera:

- Cuantificación actual: `x = eaxis - chemical_shift` en `whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py:225`, `:733` y `:1014`; la ventana de cuantificación sigue la misma regla en `whateels/pages/quantification/MVC/model/element_item.py:36-39`.
- WhatEELS antiguo: evalúa la spline en `x + chem`, `../whatEELS/Library/nlls_functions.py:444`, que produce el mismo desplazamiento observable.
- NLLS nuevo: `interp(x + chemical_shift, oos_energy, oos_shape)`.

La aparente diferencia sintáctica no es una diferencia física: desplazar las abscisas tabuladas a `eaxis - chemical_shift` y después interpolar en `x`, como hace cuantificación, equivale algebraicamente a consultar la tabla original en `x + chemical_shift`, como hacen el código antiguo y el NLLS propuesto.

Consecuencia deliberada que hay que documentar: dentro del mismo objeto `Parameters` conviven los `center` de las ELNES, cuyo aumento desplaza el pico hacia mayor energía, mientras que un `chemical_shift` positivo desplaza el continuo hacia menor energía. Los dos signos son opuestos a propósito. Debe constar en el docstring de `_make_oos_component`, en el tooltip del widget —el `FloatInput` actual no documenta ningún signo, `whateels/pages/quantification/MVC/view/components/element_item_view.py:74-80`— y en los attrs del resultado, para que los mapas `component_id__parameter` de 9.4 no se interpreten al revés.

Texto único recomendado para GUI, docstring y metadatos: `Positive chemical shift evaluates table(x + shift) and moves the modeled edge to lower energy; ELNES center uses the opposite direction.` En la vista actual, mantener `chemical_shift_input` y su watcher y envolver el control en un `pn.Row` con `pn.widgets.TooltipIcon(value=Tooltip(...))`; el repositorio ya usa ese patrón en `whateels/pages/quantification/MVC/view/__init__.py:277-283`. El nuevo widget NLLS debe reutilizar la misma constante de texto para evitar que ambas ayudas diverjan.

Pruebas obligatorias: (a) una curva sintética delta/escalón cuyo máximo se desplace exactamente `-dE` al fijar `chemical_shift = +dE`; (b) que el proveedor/componente nuevo y `calculate_shell_theoretical_data`, `whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py:728-761`, produzcan la misma curva para el mismo `chemical_shift` y la misma curva OOS de entrada.

No ajustar directamente amplitudes del orden físico de una sección eficaz. En `normalize_for_fit`:

    normalization_factor = np.nanmax(np.abs(sigma_on_dataset[fit_mask]))
    if not np.isfinite(normalization_factor) or normalization_factor <= 0:
        raise InvalidOOSDataError("zero OOS curve in fit range")
    shape = sigma_on_dataset / normalization_factor

El modelo usa `A * shape`; el coeficiente respecto de la sección física es `A / normalization_factor`. Persistir `normalization_factor`, unidades, fórmula, checksum y rango en `ContinuumSpec`/resultado. Así lmfit opera con magnitudes comparables al espectro sin perder la posibilidad de reconstruir la escala física.

#### 5.4.3. Cómo convertir la curva OOS en un componente lmfit

Implementación propuesta en `whateels/nlls/model_builder.py`; es deliberadamente una función reconstruible, no un objeto persistente:

    def _make_oos_component(
        snapshot: OOSCurveSnapshot,
        prefix: str,
    ) -> lmfit.Model:
        energy = np.asarray(snapshot.energy_eV, dtype=float)
        shape = np.asarray(snapshot.normalized_shape, dtype=float)

        def oos_continuum(x, A=1.0, chemical_shift=0.0):
            """Positive chemical_shift moves the tabulated feature to lower energy."""
            sample_x = np.asarray(x, dtype=float) + chemical_shift
            return A * np.interp(sample_x, energy, shape, left=0.0, right=0.0)

        model = lmfit.Model(
            oos_continuum,
            independent_vars=["x"],
            prefix=prefix,
            nan_policy="omit",
        )
        model.set_param_hint("A", value=1.0, min=0.0, vary=True)
        model.set_param_hint(
            "chemical_shift", value=0.0, min=-10.0, max=10.0, vary=False
        )
        return model

Los prefijos deben ser estables y únicos, por ejemplo `si_l23_cont_`, y nunca depender del orden visual de tarjetas. `ParameterSpec` aplica después los valores/cotas/vary particulares de cada área. La amplitud inicial debe estimarse con el espectro de referencia —por ejemplo, una proyección lineal no negativa de la señal local sobre `shape`— y sólo usar 1.0 como fallback documentado.

El builder completo no debe repetir el supuesto GOS del código antiguo:

    def build(self, area: AreaModelSpec, eloss: np.ndarray) -> BuiltAreaModel:
        parts: list[lmfit.Model] = []

        for continuum_spec in area.continuum_specs:
            snapshot = self.oos_provider.curve(...)
            parts.append(self._make_oos_component(snapshot, continuum_spec.prefix))

        if not parts:
            raise EmptyModelError("area has no valid OOS continuum components")

        if area.model_composition is ModelComposition.CONTINUUM_PLUS_ELNES:
            for fine_structure_spec in area.enabled_fine_structure_specs:
                parts.append(self._make_elnes_component(fine_structure_spec))
        elif area.model_composition is not ModelComposition.CONTINUUM_ONLY:
            raise UnsupportedModelCompositionError(area.model_composition)

        composite = functools.reduce(operator.add, parts)
        params = composite.make_params()
        self._apply_parameter_specs(params, area.parameter_specs)
        return BuiltAreaModel(model=composite, params=params, curve_snapshots=...)

Esta composición hace explícitos los dos usos heredados: con `CONTINUUM_ONLY`, `parts` conserva únicamente modelos OOS; con `CONTINUUM_PLUS_ELNES`, añade las estructuras finas habilitadas. No existe una ruta que construya ELNES sin continuo. `NLLS_fitting.create_model` antiguo empieza directamente con `mod_cont_list[0]`, `../whatEELS/Library/nlls_functions.py:784-793`; la nueva implementación conserva el requisito físico de al menos un continuo, pero lo valida antes de componer para devolver un error claro.

Las closures de `_make_oos_component`, `CompositeModel`, `Parameters` y `ModelResult` sólo viven durante el cálculo local. En el worker paralelo se envían specs/arrays serializables y se vuelve a llamar a `build`; no se intenta hacer pickle de esos objetos.

#### 5.4.4. Preprocesado obligatorio y separación entre background y continuum

El background pre-edge power-law y el continuo OOS del borde son contribuciones distintas:

    raw(E) = background_pre_edge(E) + continuum_OOS(E) + ELNES(E)

La sustracción power-law produce:

    background_subtracted(E) = continuum_OOS(E) + ELNES(E)

Por tanto, sustraer el background no autoriza a eliminar el continuo OOS del modelo. En `continuum_only` se ajusta ese continuo sin ELNES; en `continuum_plus_elnes` se ajustan ambos simultáneamente.

La aplicación ya puede producir una fuente con power-law sustraído desde Home: crea `MultiFit(..., model=lmfit.models.PowerLawModel)`, ejecuta `run(mode="subtracted", ...)` y publica `preprocessed_plot_dataset` en `whateels/pages/home/MVC/view/plots/spectrum_image_plot.py:2616-2644`. Ésta es la fuente requerida para las dos composiciones del NLLS elemental. Sin embargo, la marca `_preprocessed_source="multifit"` de la línea 2643 sólo vive en el visualizador y `AppState.is_multifit` no constituye hoy una procedencia fiable. Antes de habilitar Build/Run, Home/AppState debe publicar algo equivalente a:

    dataset.attrs["background_subtracted"] = True
    dataset.attrs["preprocessing_history"] = json.dumps([
        {
            "operation": "power_law_background_subtraction",
            "implementation": "whateels.helpers.fitting.multifitting.MultiFit",
            "fit_range_eV": [start, stop],
            "source_identity": raw_identity,
            "revision": revision,
        }
    ])

El nombre final puede cambiar, pero el contrato público no: `DatasetIdentity.background_subtracted` se deriva de procedencia persistida, no de que exista cualquier `preprocessed_plot_dataset`. PCA, normalización, smoothing u otro preprocesado no prueban que se haya eliminado el fondo.

Reglas de validación y UI:

| Fuente activa | Composición solicitada | Resultado |
|---|---|---|
| raw, aunque exista tabla OOS | cualquiera | Bloquear Build/Run: falta sustraer el background pre-edge. |
| preprocessed sin operación de background subtraction verificable | cualquiera | Bloquear Build/Run; mostrar la operación que falta. |
| power-law subtracted con procedencia válida y tabla OOS válida | `continuum_only` | Construir sólo los continuos OOS de los edges seleccionados. |
| power-law subtracted con procedencia válida y tabla OOS válida | `continuum_plus_elnes` | Construir continuos OOS y las ELNES habilitadas. |
| power-law subtracted con tabla OOS ausente/corrupta | cualquiera | `MissingOOSTableError`/`InvalidOOSDataError`; bloquear Build/Run sin degradar silenciosamente el modelo. |

No añadir por ahora un `PowerLawModel` dentro del modelo elemental: el background se sustrae en Home y el NLLS conserva esa procedencia. Si en el futuro se decide ajustar simultáneamente background, continuo y ELNES, debe diseñarse como una estrategia de background separada, con parámetros, cotas y pruebas de covarianza propios; nunca como sustitución silenciosa del continuo OOS.

#### 5.4.5. Dos composiciones del modelo: continuum-only y continuum + ELNES

`ModelComposition` debe tener exactamente dos valores en la primera versión:

    class ModelComposition(str, Enum):
        CONTINUUM_ONLY = "continuum_only"
        CONTINUUM_PLUS_ELNES = "continuum_plus_elnes"

Resumen matemático que debe reflejar exactamente el código del builder:

    # model_composition == "continuum_only"
    y_hat(x; p) = sum_k A_k * normalized_OOS_k(x + chemical_shift_k)

    # model_composition == "continuum_plus_elnes"
    y_hat(x; p) = sum_k A_k * normalized_OOS_k(x + chemical_shift_k)
                  + sum_j ELNES_j(x; amplitude_j, center_j, width_j, ...)

    residual(x; p) = background_subtracted_source(x) - y_hat(x; p)

Ambas composiciones usan la misma fuente con background pre-edge sustraído, las mismas llamadas `model.fit`, el mismo método `leastsq` y la misma propagación desde el snapshot de referencia. `lmfit` no define una tercera implementación: la diferencia se resuelve una vez en el builder mediante la lista de componentes.

Cambiar `continuum_only <-> continuum_plus_elnes` invalida el modelo materializado, el `ReferenceFitSnapshot` y los resultados del área. Conserva `EdgeSpec`, `ContinuumSpec` y las definiciones ELNES editables para poder reconstruir sin perder configuración.

| Salida/herramienta | `continuum_only` | `continuum_plus_elnes` |
|---|---|---|
| best-fit, residual, chi-cuadrado reducido y status | Disponible | Disponible. |
| Mapas de amplitud/shift del continuo | Disponible | Disponible. |
| Mapas de parámetros ELNES | No existen; la GUI no debe rellenarlos con cero | Disponibles para las ELNES ajustadas. |
| Center Analysis | No disponible para ELNES | Disponible para ELNES. |
| White Lines | No disponible | Disponible si las componentes requeridas existen. |
| Intensidad ajustada del edge | Continuo OOS según la definición guardada | Continuo OOS + ELNES según la definición guardada. |
| Cuantificación por sección eficaz | Usa el mismo OOSContinuumProvider para integrar sigma | Usa el mismo OOSContinuumProvider para integrar sigma; las contribuciones ELNES se tratan según la definición cuantitativa guardada. |
| Tabla OOS no disponible | El ajuste se bloquea | El ajuste se bloquea. |

Cada `NLLSResultsDataset` debe persistir `model_composition_by_area`, `background_subtracted`, `preprocessing_history`, `oos_provider_version` y checksums usados. Así un análisis posterior puede distinguir un ajuste `continuum_only` de uno `continuum_plus_elnes` y reconstruir exactamente qué componentes participaron.

#### 5.4.6. Orquestación completa desde callbacks, sin lógica científica en la vista

La secuencia propuesta para cada botón es:

    _on_add_edge(event)
      -> validar selección GUI
      -> workspace.add_edge(active_area, EdgeSpec(...))
      -> workspace.invalidate_area(active_area, reason="edge changed")
      -> view.render_area_specs(snapshot)

    _on_model_composition_changed(event)
      -> validator.validate_background_subtracted(dataset_identity)
      -> workspace.set_model_composition(active_area, requested_composition)
      -> workspace.invalidate_area(active_area, reason="model composition changed")
      -> view.update_button_states(validation)

    _on_build_model(event)
      -> source = source_service.active_dataset()
      -> workspace_validator.validate_identity(source, workspace.dataset_identity)
      -> built = model_builder.build(workspace.active_area_spec, source.Eloss.values)
      -> reference = reference_service.compute_reference(...)
      -> preview = built.model.eval(params=built.params, x=source.Eloss.values)
      -> publicar sólo DTO/arrays de preview; no guardar ModelResult

    _on_fit_current_reference(event)
      -> built = model_builder.build(area_spec, eloss)
      -> reference_fit_service.fit(area_spec, reference_spectrum, built)
      -> workspace.commit_reference_snapshot(area_id, snapshot, expected_revision)

    _on_run_elemental_nlls(event)
      -> congelar NLLSRunRequest + copia inmutable de specs/referencias
      -> validar que cada snapshot coincide con revision/dataset/fit_range/mode
      -> ElementalMultifitService.fit_areas(request, source)
      -> publicar progreso mediante scheduler de Panel
      -> commit atómico del xr.Dataset sólo si el request sigue vigente

Los callbacks pertenecen al nuevo `NLLSController` conectado desde `whateels/pages/fitting/MVC/controller/__init__.py`, cuyos callbacks manuales actuales están en `:70-99` y deben conservarse. La vista sólo lee/escribe widgets; `OOSContinuumProvider`, `NLLSModelBuilder`, referencia y multifit no importan Panel. La composición de la página sigue la ruta `whateels/pages/fitting/__init__.py:11-24`.

### 5.5. ELNES y defaults

Centralizar todos los defaults en whateels/nlls/defaults.py. No duplicarlos en widgets, tarjetas y builder.

Defaults de compatibilidad inicial:

| Parámetro | Default |
|---|---|
| Forma ELNES | Gaussian |
| FWHM | dataset.attrs.fwhm_from_0loss si es finito y positivo; si no, 4.8 eV |
| Flexibilidad inicial | Medium |
| center | onset o máximo local cercano |
| center bounds | center ± 7 eV |
| sigma min | 0.5 |
| sigma max | sigma + 1.25 sigma |
| amplitude min | 0 |
| amplitude max | +inf |
| continuum A | 1, min 0, vary True |
| continuum chemical_shift | 0 eV, vary False |
| Composición del modelo | `continuum_plus_elnes` por defecto; alternativa `continuum_only` |
| soften | True, strength 1.5 |

Estos valores reproducen el código antiguo según ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:124,139-157. La implementación manual actual tiene otros límites por flexibilidad en whateels/pages/fitting/MVC/model/__init__.py:103-143; ambos conjuntos deben coexistir y estar claramente separados.

### 5.6. API lmfit

Usar:

- lmfit.Model para cada continuo calculado;
- GaussianModel, LorentzianModel, PseudoVoigtModel y SplitLorentzianModel para ELNES;
- suma con +; con dos o más partes produce `CompositeModel`, mientras una sola componente sigue siendo un `Model` válido;
- `model.make_params` para crear `Parameters`, tanto si el agregado es `Model` como `CompositeModel`;
- `model.fit` para referencias y píxeles;
- method="leastsq" explícito para fijar el comportamiento reproducible.

No usar lmfit.minimize ni construir Parameters manualmente salvo deserialización controlada. El código actual también compone modelos con suma y make_params, whateels/pages/fitting/MVC/model/__init__.py:150-191, y llama Model.fit sin method, líneas 305-336. El antiguo tampoco seleccionaba method, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:159-170; aquí se propone hacerlo explícito.

`model.fit` minimiza el residual `reference_or_pixel_counts - model.eval(...)` sobre las muestras finitas del `fit_range`. En `continuum_only`, `model.eval` suma uno o varios `A * OOS_shape(x + chemical_shift)`. En `continuum_plus_elnes`, añade las curvas ELNES habilitadas. No debe existir un condicional de composición dentro del bucle de optimización: la diferencia se resuelve una vez al construir la lista de componentes, lo que mantiene idénticas la propagación, extracción de `redchi` y gestión de errores.

## 6. Etapa 4: áreas y referencias espaciales

### 6.1. Importar la segmentación nueva

ClusteringAreaAdapter.from_app_state debe leer:

    app_state.last_clustering_result["clustering"]["file"]
    app_state.last_clustering_result["clustering"]["spectrum_image"]
    app_state.last_clustering_result["clustering"]["type"]
    app_state.last_clustering_result["clustering"]["inputs"]
    app_state.last_clustering_result["clustering"]["outputs"]["labels"]

La estructura se crea en whateels/pages/clustering/utils/orchestrator.py:118-129 y se valida parcialmente en whateels/pages/clustering/MVC/model/__init__.py:64-93.

Validaciones obligatorias antes de Apply Areas:

- labels es 2D, entero o convertible sin pérdida, y coincide con ElectronCount.shape[:2];
- no contiene labels negativos salvo que se defina explícitamente como excluded;
- file e image_name coinciden con DatasetIdentity, o el usuario confirma una importación externa;
- el source_kind raw/preprocessed se registra al importar y sólo la fuente preprocessed con procedencia power-law válida puede alimentar referencias/fits NLLS;
- Eloss y forma espacial no han cambiado;
- cada área contiene al menos un píxel;
- las máscaras resultantes son mutuamente excluyentes.

El JSON descargado por clustering se carga con un FileInput propio y pasa por exactamente el mismo adaptador; su formato actual está en whateels/pages/clustering/MVC/view/layouts/right_sidebar_layout.py:175-213.

### 6.2. Espectro de referencia

No usar outputs.centres. Para cada label n:

    mask_n = labels == n
    reference_n = nanmean(active_cube[mask_n, :], axis=0)

`active_cube` es necesariamente la fuente preprocesada que ha superado `validate_background_subtracted`; nunca se recalcula una referencia NLLS desde raw ni desde otro preprocesado sin procedencia compatible.

Razón: la normalización se aplica antes de K-Means, whateels/pages/clustering/utils/preprocessing.py:60-68, y K-Means guarda fitted.cluster_centers_, whateels/pages/clustering/utils/clustering.py:152-156. Esos centros pueden no tener la amplitud de un espectro de píxel, necesaria para inicializar A/amplitude.

Estrategia default sin segmentación:

- crear area_id="default";
- máscara de unos sobre toda la imagen;
- si existe una ROI comprometida, usar la media de sus píxeles como referencia;
- si no existe ROI, usar la media de la ventana central 2/5–3/5 en x e y para mantener el fallback antiguo;
- registrar reference_strategy y los índices usados.

El código antiguo usa esa ventana central y una máscara completa, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:240-244. La GUI actual publica la suma de ROI en AppState.spectra, whateels/pages/fitting/MVC/view/plots/spectrum_image_plot.py:114-126; por eso el nuevo servicio debe recibir los índices de ROI y calcular la media directamente del cubo.

### 6.3. Estado independiente por área

Al aplicar clustering:

1. conservar default como plantilla;
2. deep-copy AreaModelSpec de default a cada cluster_n;
3. recalcular guesses de amplitud con reference_n;
4. mantener ParameterSpec, componentes desactivadas/borradas y bloqueos dentro de cada área;
5. marcar referencias y resultados de cada área como stale cuando cambia su propia configuración.

No compartir listas o ParameterSpec mutables entre áreas. El antiguo separaba models_components, pars, ref_spectra, ref_results, ref_matrices y results por área, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:216-238.

Regla de solapamiento: default no puede ejecutarse a la vez que cluster_n porque su máscara cubre todos los píxeles. La GUI debe hacerlo mutuamente excluyente o mostrar error.

## 7. Etapa 5: ajuste de referencias

### 7.1. Servicio

Firma propuesta:

    ReferenceFitService.fit_area(
        workspace,
        area_id,
        active_dataset,
        method="leastsq",
        fit_range=None,
    ) -> ReferenceFitSnapshot

Comportamiento de compatibilidad:

- reconstruir modelo y Parameters desde AreaModelSpec;
- ajustar la suma completa contra reference_spectrum;
- usar todos los pares Eloss/cuentas finitos;
- por defecto usar todo Eloss, sin pesos;
- pasar method="leastsq";
- calcular best_fit, residual, eval_components, redchi, success y message;
- persistir un snapshot serializable y una copia de parámetros convergidos;
- no persistir ModelResult en AppState ni en disco.

El ajuste antiguo exacto está documentado en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:246-276. El fitting actual también elimina NaN/Inf y ajusta el espectro 1D completo, whateels/pages/fitting/MVC/model/__init__.py:305-336.

Esqueleto de implementación del servicio; éste es el mismo para ambas composiciones del modelo:

    def fit_area(self, area_spec, reference, eloss, fit_range, method="leastsq"):
        built = self.model_builder.build(area_spec, eloss)
        mask = np.isfinite(eloss) & np.isfinite(reference)
        if fit_range is not None:
            mask &= (eloss >= fit_range.minimum) & (eloss <= fit_range.maximum)
        if np.count_nonzero(mask) <= built.n_varying_parameters:
            raise InsufficientReferenceDataError(...)

        result = built.model.fit(
            reference[mask],
            params=built.params.copy(),
            x=eloss[mask],
            method=method,
            nan_policy="omit",
        )
        if not result.success or not all_finite(result.params):
            raise ReferenceFitError(result.message)

        full_best_fit = built.model.eval(params=result.params, x=eloss)
        full_components = built.model.eval_components(params=result.params, x=eloss)
        return ReferenceFitSnapshot.from_result(
            params=result.params,
            best_fit=full_best_fit,
            residual=reference - full_best_fit,
            components=full_components,
            redchi=result.redchi,
            dataset_identity=...,
            area_revision=area_spec.revision,
            model_composition=area_spec.model_composition,
            fit_range=fit_range,
        )

En `continuum_only`, `result.params` contiene los `A`/`chemical_shift` OOS. En `continuum_plus_elnes`, contiene además los parámetros ELNES. `ReferenceFitSnapshot.params` debe serializar para cada parámetro `name`, `value`, `min`, `max`, `vary`, `expr`, `brute_step` y, si existe, `stderr`; no basta guardar sólo `value`, porque el multifit debe reconstruir exactamente las cotas y bloqueos que convergieron.

### 7.2. GUI y callbacks

| Control | Callback | Habilitación |
|---|---|---|
| Fit Current Reference | _on_fit_current_reference | Modelo del área construido y no vacío |
| Fit All References | _on_fit_all_references | Todas las áreas válidas y al menos una dirty |
| Area selector | _on_active_area_changed | Tras crear default; añade clusters al aplicar segmentación |
| Show raw / best fit / components | _on_reference_layer_changed | ReferenceFitSnapshot válido |
| Download References | _on_download_references | Al menos una referencia ajustada |

Fit All debe seguir ajustando las demás áreas si una falla, pero devolver un resumen y no habilitar Run Elemental NLLS para las áreas fallidas.

## 8. Etapa 6: propagación de parámetros

Éste es el contrato más importante y debe tener un test dedicado.

### 8.1. Primer ajuste multipíxel

Función objetivo propuesta:

    whateels/nlls/multifit.py
    ElementalMultifitService._initial_params_for_pixel(area_id, pixel, rerun_from)

Semántica:

    reference_snapshot = workspace.reference_fits[area_id]
    reference_params = parameters_from_snapshot(reference_snapshot.params)

    for y, x in selected_coordinates:
        pixel_params = reference_params.copy()
        result = model.fit(
            cube[y, x, :],
            params=pixel_params,
            x=eloss,
            method="leastsq",
        )
        accumulator.store(y, x, result)

La copia por píxel es obligatoria: todos los píxeles del área parten del mismo estado convergido de su referencia y ninguno hereda el resultado de su vecino.

Esto reproduce la ruta GUI antigua: ref_results[area].params se pasa a cada Model.fit y la asignación paramet = res.params está comentada, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:288-318.

### 8.2. Rerun

Para un rerun, cada píxel parte de su propio snapshot anterior:

    previous = first_run.pixel_parameters(y, x)
    pixel_params = merge(previous, new_components, area_locks)
    result = modified_model.fit(pixel, params=pixel_params, ...)

No partir de la referencia, del último píxel visitado ni de otro área. Aplicar:

    parameter.vary = not lock_spec.locked

El comportamiento antiguo equivalente está en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:320-333.

### 8.3. Pruebas obligatorias de propagación

- Dos píxeles del mismo área reciben valores iniciales idénticos aunque el primero converja a valores extremos.
- Dos áreas reciben sus propios parámetros de referencia.
- Cambiar el orden de iteración no cambia las iniciales del primer fit ni los resultados dentro de tolerancia.
- En rerun, cada píxel recibe sus parámetros previos exactos.
- Lock All fija vary=False sólo en el área indicada.
- Añadir una componente en rerun no modifica los parámetros previos de otras áreas.

## 9. Etapa 7: multifit elemental

### 9.1. Selección y exclusión

Añadir MultiChoice "Areas to fit". Tras Fit References:

- options = áreas con ReferenceFitSnapshot.success;
- value = todas las áreas válidas salvo default cuando hay clusters;
- el usuario excluye un área quitándola de la selección;
- un píxel se excluye si no está en la máscara seleccionada o no tiene datos finitos suficientes;
- labels negativos, si se admiten en el futuro, se tratan como excluded y se documentan en attrs;
- máscaras solapadas producen error antes del cómputo.

El antiguo también ajustaba sólo np.where(mask == 1) de las áreas elegidas, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:337-350.

### 9.2. Bucle serial de referencia

Implementar primero una ruta serial pura y determinista:

1. validar NLLSRunRequest y congelar una copia del workspace;
2. crear arrays de salida prellenados con NaN y status=not_selected;
3. por área, reconstruir una vez modelo y parámetros base;
4. obtener coordenadas planas de su máscara;
5. copiar parámetros de referencia por píxel;
6. ajustar y extraer inmediatamente resultados ligeros;
7. capturar excepciones por píxel como status=fit_error;
8. actualizar progreso por chunks, no por cada canal;
9. publicar nlls_results sólo al finalizar o como resultado parcial marcado incomplete;
10. conservar intacto el último resultado complete si el usuario cancela.

### 9.3. Paralelización posterior

No activar multiprocessing hasta que la ruta serial pase los tests de paridad.

fit_chunk_worker debe ser una función de módulo y recibir sólo:

- chunk de cuentas NumPy;
- coordenadas;
- Eloss;
- AreaModelSpec serializado;
- parámetros de referencia serializados;
- curvas OOS muestreadas o claves de caché reconstruibles;
- método y rango.

El worker reconstruye el CompositeModel. Devuelve arrays/dicts de números, strings y booleanos. El helper de fondo ya documenta este patrón para evitar pickling de lmfit, whateels/helpers/fitting/multifitting.py:388-422.

Controles:

- workers por defecto: max(1, cpu_count - 1), limitado por número de chunks;
- chunk_size configurable internamente y medido con benchmarks;
- Cancel marca un Event y detiene el envío de nuevos chunks;
- los callbacks de Panel se actualizan únicamente en el hilo del documento;
- Windows/PyInstaller usa el freeze_support ya presente en main.py:2-8.

### 9.4. Estructura devuelta

NLLSResultsAssembler debe producir un xr.Dataset, no results[area][y][x] de ModelResult.

Dimensiones:

    y, x, Eloss, component y parameter cuando proceda

Variables mínimas:

| Variable | Dimensiones | Contenido |
|---|---|---|
| OriginalData | y,x,Eloss | Fuente exacta ajustada |
| AreaLabel | y,x | Label; -1 para no seleccionado |
| FitStatus | y,x | Código entero con tabla en attrs |
| ReducedChiSquare | y,x | result.redchi |
| BestFit | y,x,Eloss | Curva total |
| Residuals | y,x,Eloss | datos - best fit |
| component_id__component | y,x,Eloss | eval_components por componente |
| component_id__parameter | y,x | valor convergido |
| component_id__parameter__stderr | y,x | error o NaN |

Attrs mínimos:

- schema_version;
- DatasetIdentity y source_kind;
- geometry y unidades;
- método lmfit;
- `model_composition_by_area`, `background_subtracted` y `preprocessing_history` de la fuente ajustada;
- `chemical_shift_convention="model(x)=table(x+chemical_shift); positive shifts features to lower energy"`; repetirlo también como attr de cada mapa `*_chemical_shift` exportado;
- versión/fuente/checksum de la base y fórmula OOS;
- configuración serializada;
- áreas seleccionadas;
- timestamp, complete y cancelled;
- versión de MyWhatEELS y lmfit.

## 10. Etapa 8: resultados y herramientas derivadas

### 10.1. Chi-cuadrado reducido

Copiar result.redchi al acumulador por píxel; no recalcularlo con otra definición. Los fallos y no seleccionados quedan NaN y se distinguen mediante FitStatus. El código antiguo sigue esta misma regla, ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:383-404.

La vista NLLS Results debe ofrecer:

- mapa ReducedChiSquare con escala robusta y opción log;
- overlay de AreaLabel;
- click/hover para mostrar OriginalData, BestFit, Residuals y componentes;
- selector de mapas de parámetros/stderr;
- máscara por status, umbral redchi y error relativo;
- descarga del dataset completo o variables seleccionadas.

No reutilizar Show Energy Map: su cálculo actual es distinto, whateels/pages/fitting/MVC/model/__init__.py:338-397.

### 10.2. Center Analysis

CenterAnalysisService:

- listar componentes ELNES que tengan mapa center;
- para continuo K, permitir onset sólo si se implementa y valida el detector por segunda derivada;
- calcular abs(center_a - center_b);
- propagar máscara de FitStatus;
- devolver xr.Dataset con Distances y metadatos de los componentes.

El algoritmo antiguo está resumido en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:412-426.

Callback:

    Center Analysis -> _on_open_center_analysis
    Get Distances   -> _on_compute_center_distances
    Download        -> _on_download_center_results

### 10.3. White Lines

WhiteLineService debe operar sobre componentes ya ajustadas:

- auto y advanced;
- ancho por FWHM o manual;
- fitted o raw;
- selección de componentes, resta e inclusión opcional de continuo;
- ratio directo e inverso;
- integración con scipy.integrate.simpson, nunca simps.

Para paridad, el modo auto usa una ventana total 2.5625 por el FWHM máximo espacial, según ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:428-439.

Callbacks:

    White Lines -> _on_open_white_lines
    Compute     -> _on_compute_white_lines
    Invert      -> _on_invert_white_line_ratio
    Download    -> _on_download_white_line_results

### 10.4. Cuantificación elemental

Crear EgertonQuantificationService separado de QuantificationModel actual.

Entradas:

- NLLSResultsDataset;
- elementos/edges y ventanas;
- versión de base y fórmula OOS visibles;
- E0, alpha, beta del resultado, no del dataset actualmente seleccionado;
- fitted o raw;
- corrección de solapamientos opcional.

Regla física:

- integrar la sección eficaz del edge sobre la misma ventana energética;
- para raw, restar contribuciones seleccionadas de otros elementos y recortar a cero;
- para fitted en `continuum_only`, integrar la definición guardada del continuo OOS del edge;
- para fitted en `continuum_plus_elnes`, integrar la definición guardada del continuo más las ELNES del edge;
- producir intensidades integradas, secciones integradas, ratios relativos y máscara;
- etiquetar unidades y backend;
- no afirmar concentración absoluta/densidad areal porque no aparece en el flujo antiguo.

La ruta antigua Egerton/corte beta está documentada en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:441-472.

Usar la misma OOSContinuumProvider corregida para el continuo y para integrar secciones de cuantificación. La cuantificación actual ya lee E0, beta y alpha de attrs al añadir elementos, `whateels/pages/quantification/MVC/controller/__init__.py:194-214`, y su servicio Salvat aplica beta efectiva para alpha finito, `whateels/pages/quantification/MVC/controller/services/oos_loader_service.py:266-384`. La migración al proveedor compartido conserva exactamente la convención de signo existente `x + chemical_shift`; por tanto no necesita conversión de signo en ninguna frontera. El único cambio numérico acoplado que debe aislarse en la comparación antes/después es la corrección del eje de 0.2 —usar `eaxis` canal a canal y ese mismo eje en `trapezoid`—, lo que simplifica la interpretación de la regresión.

En las dos composiciones, OOS participó en el NLLS y debe ser el mismo backend empleado después como sección eficaz de normalización. `EgertonQuantificationService` calcula `sigma_integrated` desde `OOSContinuumProvider.integrate`, con la geometría, ventana, versión y checksum guardados. En `continuum_only` no debe inventar contribuciones ELNES; en `continuum_plus_elnes` debe seguir la definición guardada para incluirlas o separarlas de forma reproducible.

## 11. Etapa 9: analizador Bethe/GOS independiente

Fuera de alcance por decisión de producto. MyWhatEELS no tendrá tablas GOS y una OOS unidimensional no permite reconstruir de forma general la superficie F(q,E). Por tanto:

- no crear /gos-analysis;
- no portar GOSAnalysisService ni bethe_surface;
- no mostrar theoretical, beta-cut, F-factor o beta-F;
- no simular una superficie a partir de OOS;
- mantener esta etapa documentada como no implementable con los datos disponibles.

La herramienta antigua se conserva únicamente como referencia histórica en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:474-498 y no forma parte de la definición de terminado de MyWhatEELS.

## 12. Etapa 10: guardado y exportación

### 12.1. Formatos

| Acción | Formato | Contenido |
|---|---|---|
| Save Model | JSON | edges, shapes, defaults, `model_composition`, `chemical_shift_convention` y versión/fórmula/checksums OOS; sin áreas |
| Save Configuration | JSON | modelo, geometría, áreas, masks opcionalmente comprimidas/RLE, ParameterSpec, bloqueos, DatasetIdentity, `chemical_shift_convention` y procedencia de sustracción de fondo |
| Download References | NetCDF + JSON attrs | espectros, best fit, residual, componentes y parámetros por área |
| Download Results | NetCDF | NLLSResultsDataset |
| Download Selected Maps | CSV o NetCDF | variables 2D elegidas |
| Download Spectra/Curves | CSV | Eloss y curvas seleccionadas |
| Download View | PNG/SVG en fase posterior | figura actualmente visible |

Usar pn.widgets.FileDownload e InMemoryFile como la descarga actual de clustering, whateels/pages/clustering/MVC/view/layouts/right_sidebar_layout.py:186-213.

### 12.2. Seguridad y reproducibilidad

- JSON con schema_version y migradores explícitos.
- NetCDF con nombres de variables seguros y attrs serializables.
- No np.save de dtype object.
- No allow_pickle=True.
- No guardar rutas absolutas internas.
- No escribir Savings-Workspace automáticamente.
- Al cargar configuración, validar elementos, subcapas, checksum de backend y compatibilidad de Eloss.
- Una configuración de modelo puede aplicarse a otro dataset sólo tras reconstruir referencias y confirmar geometría.
- Un resultado no puede reinterpretarse con otra geometría/backend sin recalcular.

Esto corrige el riesgo antiguo de gos_func.npy/gos_dict.npy con objetos y allow_pickle, documentado en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:500-540.

### 12.3. Empaquetado

Verificar conjuntamente mywhateels.spec, mywhateels_linux.spec y mywhateels_van.spec. No añadir tablas GOS. Los tres builds deben conservar la inclusión de whateels/data/oos/Hartree_Xsections_FSalvat/*.json; el spec Windows ya la declara en mywhateels.spec:153-160. Añadir sólo los módulos whateels.nlls nuevos si PyInstaller no los detecta.

Añadir un smoke test del ejecutable congelado:

1. abrir /fitting;
2. comprobar catálogo y lectura OOS;
3. crear un edge disponible;
4. ajustar una referencia pequeña;
5. ejecutar dos píxeles;
6. descargar y reabrir NetCDF.

## 13. Matriz completa de controles y callbacks

| Sección GUI | Control | Callback propuesto | Estado que lee | Estado que escribe | Invalida |
|---|---|---|---|---|---|
| Fuente | Use Preprocessed Data | callback existente + _on_nlls_source_invalidated | AppState datasets | DatasetIdentity/workspace nuevo | modelo, referencias, resultados |
| Geometría | E0/alpha/beta | _on_geometry_changed | attrs/workspace | ExperimentalGeometry | curvas, referencias, resultados |
| Modelo | Model composition | _on_model_composition_changed | DatasetIdentity/área activa/OOS status | AreaModelSpec.model_composition | modelo, referencia y resultados del área |
| Modelo | Element | _on_element_changed | catálogo OOS | opciones subshell | nada |
| Modelo | Subshell | _on_subshell_changed | catálogo OOS | selección | nada |
| Modelo | Add Edge | _on_add_edge | selección/defaults | specs área/template | referencias/resultados |
| Modelo | Build Elemental Model | _on_build_model | workspace/OOS o procedencia de fondo | preview/model cache | referencias/resultados |
| Modelo | Remove ELNES | _on_remove_fine_structure | área activa | AreaModelSpec | fit del área/resultados |
| Modelo | Reset Area | _on_reset_area_model | template | AreaModelSpec | fit del área/resultados |
| Áreas | Use Current Clustering | _on_use_current_clustering | last_clustering_result | AreaModelSpec/masks | referencias/resultados |
| Áreas | Load Clustering JSON | _on_load_clustering_json | FileInput | AreaModelSpec/masks | referencias/resultados |
| Áreas | Active Area | _on_active_area_changed | workspace | active_area/view | nada |
| Referencias | Fit Current | _on_fit_current_reference | área/modelo | ReferenceFitSnapshot | resultados de área |
| Referencias | Fit All | _on_fit_all_references | todas áreas | snapshots | resultados |
| Multifit | Areas to fit | _on_fit_areas_changed | snapshots | draft request | nada |
| Multifit | Run Elemental NLLS | _on_run_elemental_nlls | request/workspace/data | nlls_results/run_state | resultado previo sólo al commit |
| Multifit | Cancel | _on_cancel_elemental_nlls | run handle | run_state | no borra complete previo |
| Rerun | Begin Modified Model | _on_begin_rerun | primer resultado | specs rerun/locks | rerun previo |
| Rerun | Lock All/Unlock All | _on_set_all_locks | área/componente | ParameterSpec.vary | rerun |
| Rerun | Run Modified Fit | _on_run_modified_nlls | parámetros por píxel | nuevo resultado versionado | análisis derivado |
| Resultados | Results | _on_show_results | nlls_results | vista | nada |
| Resultados | Center Analysis | _on_open_center_analysis | mapas center | dataset derivado | nada |
| Resultados | White Lines | _on_open_white_lines | componentes/FWHM | dataset derivado | nada |
| Resultados | Quantification | _on_open_nlls_quantification | resultados/OOS | dataset derivado | nada |
| Guardado | Save Model/Config | callbacks download | workspace | fichero | nada |
| Guardado | Download Results | _on_download_results | nlls_results | fichero | nada |

## 14. Estados de habilitación de botones

| Botón | Debe estar habilitado cuando |
|---|---|
| Add Edge | la fuente acredita sustracción de background, y elemento/subcapa, onset, geometría y tabla OOS son válidos |
| Build Elemental Model | la fuente acredita sustracción de background, existe al menos un edge con continuo OOS válido y la composición seleccionada es coherente; `continuum_plus_elnes` puede contener una o más ELNES habilitadas |
| Use Current Clustering | last_clustering_result existe y labels coincide espacialmente |
| Fit Current Reference | área activa tiene modelo construido y referencia finita |
| Fit All References | todas las áreas seleccionadas tienen referencia y modelo |
| Run Elemental NLLS | hay áreas seleccionadas, referencias convergidas, ninguna configuración dirty y cada área conserva la validación de background, OOS y composición |
| Cancel | run_state es running o fitting_references |
| Begin Modified Model | existe un resultado complete |
| Run Modified Fit | hay componentes/bloqueos modificados y parámetros previos disponibles |
| Results | existe nlls_results complete o partial reconocido |
| Center Analysis | existen al menos dos mapas center/onset compatibles |
| White Lines | existe un doblete con componentes ajustadas |
| Quantification | hay al menos dos elementos/edges y las mismas secciones OOS válidas utilizadas por el fit; la integración respeta la composición guardada |
| Download | el artefacto correspondiente existe y pasa validación |

## 15. Fases de implementación

### Fase 0 — Línea base y protección

- [ ] Crear tests de caracterización para Add Component, edición de tarjeta, borrado y fit de referencia manual.
- [ ] Probar Show Energy Map sin cambiar su resultado actual.
- [ ] Probar cambio raw/preprocessed y su reset actual.
- [ ] Caracterizar la ruta Home `PowerLawModel -> run(mode="subtracted") -> preprocessed_plot_dataset`, whateels/pages/home/MVC/view/plots/spectrum_image_plot.py:2616-2644.
- [ ] Añadir/publicar procedencia verificable `background_subtracted` y `preprocessing_history`; no basarse en el atributo privado del visualizador ni en `AppState.is_multifit`.
- [ ] Probar clustering y descarga JSON.
- [ ] Probar Quantification actual con al menos dos elementos.
- [ ] Añadir fixture SI pequeño con metadatos E0/alpha/beta.
- [ ] Registrar snapshots de GUI/variables para detectar regresiones.

Criterio de salida: todo lo existente tiene al menos una prueba antes de editar FittingView/FittingController/AppState.

### Fase 1 — Física OOS compartida y empaquetado

- [ ] Implementar OOSContinuumProvider sin dependencias de Panel/MVC.
- [ ] Corregir el cálculo para usar eaxis canal a canal en vez de onset como Eloss.
- [ ] Corregir la integración para llamar `trapezoid(sigma, x=energy_eV)` dentro de la ventana, no integrar por índice.
- [ ] Validar unidades de E0, alpha, beta, eaxis, onset y sección resultante.
- [ ] Aplicar la corrección de ángulo efectivo para alpha finito.
- [ ] Interpolar sobre dataset.Eloss con política explícita antes del onset y fuera del dominio.
- [ ] Implementar suma física de dobletes, broadening en eV y normalización numérica reversible mediante `normalization_factor`.
- [ ] Fijar y probar la convención `shape(x + chemical_shift)`; un valor positivo desplaza el rasgo observable hacia menor energía.
- [ ] Añadir MissingOOSTableError, InvalidOOSDataError y autodiagnóstico.
- [ ] Comparar el proveedor con casos analíticos, límites alpha=0 y resultados actuales.
- [ ] Verificar los JSON OOS en los tres spec y en el ejecutable congelado.
- [ ] Documentar que el resultado es OOS-based y no equivalente numéricamente a GOS.

Criterio de salida: curvas OOS finitas, reproducibles, evaluadas sobre el eje correcto y disponibles en el build congelado.

### Fase 2 — Dominio, workspace y modelo elemental

- [ ] Implementar contracts.py, defaults.py y workspace.py.
- [ ] Implementar NLLSModelBuilder.
- [ ] Implementar `ModelComposition.CONTINUUM_ONLY/CONTINUUM_PLUS_ELNES` y el builder basado en una lista general de componentes, sin indexar directamente `mod_cont_list[0]`.
- [ ] Crear siempre `A * normalized_oos_shape`; añadir las ELNES habilitadas sólo en `continuum_plus_elnes`.
- [ ] Bloquear ambas composiciones cuando la fuente no acredita una sustracción power-law del background pre-edge o cuando OOS/geometría no son válidos.
- [ ] Implementar serialización JSON versionada.
- [ ] Añadir estado NLLS exclusivo y clear_nlls_state.
- [ ] Añadir pestaña Elemental NLLS detrás de feature flag.
- [ ] Implementar Add Edge, Build, edición por área y preview.
- [ ] Añadir al widget `chemical_shift` un tooltip que explique la convención y el signo opuesto respecto de `ELNES.center`; no dejarlo sólo en documentación interna.
- [ ] Confirmar que el modo Manual no cambia.

Criterio de salida: crear/guardar/cargar un modelo elemental sin hacer multifit.

### Fase 3 — Áreas y referencias

- [ ] Implementar DatasetIdentity.
- [ ] Implementar ClusteringAreaAdapter para estado y JSON.
- [ ] Recalcular medias desde el source activo.
- [ ] Implementar default ROI-mean/central fallback.
- [ ] Clonar configuración por área sin referencias compartidas.
- [ ] Implementar Fit Current/Fit All y snapshots.
- [ ] Añadir overlays de referencia.

Criterio de salida: referencias independientes y reproducibles para default y clusters.

### Fase 4 — Propagación y multifit serial

- [ ] Implementar NLLSRunRequest.
- [ ] Implementar inicialización exacta desde ReferenceFitSnapshot.
- [ ] Implementar bucle serial y acumulador.
- [ ] Crear xr.Dataset de resultados.
- [ ] Añadir progreso, cancelación y manejo por píxel.
- [ ] Pasar todos los tests de propagación de la sección 8.3.

Criterio de salida: dos ejecuciones con el mismo input producen parámetros/mapas iguales dentro de tolerancia.

### Fase 5 — Resultados base

- [ ] Vista ReducedChiSquare/status.
- [ ] Espectros al seleccionar píxel.
- [ ] Mapas de valores y stderr.
- [ ] Overlay de áreas y filtro de errores.
- [ ] Descarga NetCDF/CSV.

Criterio de salida: ningún análisis necesita ModelResult persistido.

### Fase 6 — Modelo modificado y rerun

- [ ] Crear snapshots por píxel recuperables desde el dataset.
- [ ] UI de nuevos componentes y locks.
- [ ] Propagación local desde el mismo píxel.
- [ ] Resultados first/modified versionados, sin sobrescribir.
- [ ] Tests de Lock All/Unlock All y áreas no modificadas.

Criterio de salida: un rerun parcial conserva exactamente los resultados de las áreas no seleccionadas.

### Fase 7 — Paralelización

- [ ] Implementar fit_chunk_worker de módulo.
- [ ] Reconstruir modelo dentro del worker.
- [ ] Comparar salida serial/paralela.
- [ ] Medir workers/chunk_size y memoria.
- [ ] Probar Windows spawn y ejecutable PyInstaller.
- [ ] Activar selector Parallel sólo después de paridad.

Criterio de salida: mismas salidas numéricas dentro de tolerancia, sin nuevas ventanas/procesos recursivos.

### Fase 8 — Herramientas derivadas

- [ ] Center Analysis.
- [ ] White Lines con scipy.integrate.simpson.
- [ ] Egerton Quantification con versión/fórmula OOS visible.
- [ ] Exportación de datasets derivados.

Criterio de salida: cada herramienta conserva provenance, unidades, máscaras y backend.

## 16. Pruebas y criterios de aceptación

### Unitarias

- OOS reader/provider: tabla válida, ausente, JSON corrupto y subcapa no disponible.
- OOS física: cálculo canal a canal, E0/beta cero, alpha cero/finito, onset, dominio `W < E0`, reinterpolación y cero fuera de tabla.
- OOS integración: eje no unitario/irregular demuestra que `trapezoid(..., x=energy_eV)` da el valor esperado.
- OOS escala: normalización y desnormalización recuperan la curva física; el fit no depende de multiplicar la tabla por una constante conocida.
- OOS desplazamiento: una delta/escalón sintética se desplaza exactamente `-dE` cuando `chemical_shift=+dE`.
- OOS compatibilidad de signo: el componente/proveedor nuevo y `calculate_shell_theoretical_data` producen la misma curva para el mismo `chemical_shift`, eje y OOS de entrada.
- Parámetros con signos opuestos: en un modelo sintético común, incrementar `ELNES.center` en `+dE` mueve el pico a mayor energía e incrementar `chemical_shift` en `+dE` mueve el continuo a menor energía.
- OOS dobletes: el resultado es la suma de las dos curvas reales interpoladas, no dos copias de una subcapa.
- Defaults: FWHM metadata/fallback y límites Medium.
- Builder `continuum_only`: prefijos únicos, parejas 4/5 y 2/3, sólo componentes OOS y Parameters con `A`/`chemical_shift`; ningún parámetro ELNES.
- Builder `continuum_plus_elnes`: las mismas componentes OOS más Gaussian/Lorentzian/PseudoVoigt/SplitLorentzian habilitadas y sus parámetros.
- Builder vacío: `EmptyModelError` si no existe ningún continuo OOS válido; nunca omitir OOS como fallback.
- Validador de fuente: raw y preprocessed sin procedencia se rechazan en ambas composiciones; power-law subtracted se acepta si geometría y OOS son válidos; una tabla ausente bloquea Build/Run.
- Workspace: deep-copy por área, invalidación y JSON round-trip.
- Áreas: labels/shape/fingerprint y media correcta.
- Referencias: NaN/Inf, fallo aislado y snapshot.
- Propagación: todos los casos de la sección 8.3.
- Resultados: redchi/status/componentes/params/stderr.
- Análisis: centros, white-line Simpson y cuantificación.

### Integración MVC

- El modo Manual conserva callbacks de whateels/pages/fitting/MVC/controller/__init__.py:70-99.
- El switch raw/preprocessed invalida sólo el workspace correspondiente.
- Cambiar `continuum_only <-> continuum_plus_elnes` invalida modelo/referencia/resultados del área, conserva EdgeSpec/ContinuumSpec/ELNES y actualiza botones.
- La GUI no habilita Build/Run por el mero hecho de que exista `preprocessed_plot_dataset`; exige procedencia verificable de la sustracción power-law.
- Un cambio de tab no restaura un workspace de otro dataset.
- Las áreas se restauran al volver de Clustering sólo si DatasetIdentity coincide.
- Los botones siguen la tabla de habilitación.
- Los widgets `chemical_shift` de NLLS y cuantificación muestran que el signo positivo mueve el continuo hacia menor energía y que `ELNES.center` tiene el sentido energético contrario.
- Cancel no elimina el último resultado completo.
- Los callbacks no escriben directamente en widgets desde workers.

### Regresión y rendimiento

- Resultado serial comparado con un caso dorado del WhatEELS antiguo.
- Paridad serial/paralela.
- Memoria máxima acotada: no hay matriz y,x de ModelResult.
- Benchmark para 32x32, 64x64 y 128x128 con número realista de componentes.
- Navegar Home -> Clustering -> Fitting -> Home no deja watchers/workers activos.
- clear_all libera workspace, resultados, caché OOS por dataset y handles de ejecución.

### Empaquetado

- Import de whateels.nlls en Python 3.13.4.
- Acceso a JSON OOS desde fuente y desde ejecutable.
- Worker spawn congelado.
- Descarga y reapertura de JSON/NetCDF.

## 17. Matriz de ficheros actuales a tocar

| Fichero actual | Cambio permitido |
|---|---|
| main.py | Ninguno inicialmente. Ya contiene freeze_support. |
| whateels/__init__.py | Sólo añadir una futura /nlls-results si se decide separarla de Fitting. |
| whateels/pages/__init__.py | Exportar nuevas páginas sólo si se crean rutas. |
| whateels/templates/general_page_template.py | Añadir link de resultados sólo si se crea la ruta, sin alterar enlaces existentes. |
| whateels/state/app_state.py | Añadir campos/clear NLLS con nombres exclusivos. |
| whateels/pages/home/MVC/view/plots/spectrum_image_plot.py | Al publicar la salida `mode="subtracted"`, adjuntar procedencia pública y serializable de sustracción power-law sin cambiar el array producido actualmente. |
| whateels/state/cache.py | Opcional: limpieza del store/cache NLLS por usuario. |
| whateels/pages/fitting/__init__.py | Construir/integrar NLLSController sin cambiar el contrato de GeneralPageTemplate. |
| whateels/pages/fitting/MVC/model/__init__.py | Mantener FittingModel manual; como máximo delegar/adaptar, no absorber todo el dominio NLLS. |
| whateels/pages/fitting/MVC/controller/__init__.py | Conectar el subcontrolador e invalidación de fuente; conservar callbacks actuales. |
| whateels/pages/fitting/MVC/view/__init__.py | Añadir el modo/accordion NLLS y panel de resultados. |
| whateels/pages/fitting/MVC/model/component_item.py | No ampliar de forma incompatible; usar nuevos DTOs. |
| whateels/pages/quantification/MVC/view/components/element_item_view.py | Conservar el cálculo; añadir al `FloatInput` de `:74-80` tooltip/ayuda explícita sobre el signo de `chemical_shift`. |
| whateels/pages/quantification/MVC/view/plots/spectrum_image_plots.py | Conservar la convención de `:225`, `:733` y `:1014`; usar `calculate_shell_theoretical_data` (`:728-761`) como caso de regresión del proveedor nuevo. |
| whateels/pages/quantification/* restante | No cambiar cálculo ni estado en la primera implementación NLLS, salvo el texto de ayuda anterior. Migrar después al proveedor OOS corregido y compartido, con tests físicos y de regresión. |
| whateels/helpers/nlls_library/* | Tratar como código legado de transición; no importarlo directamente desde GUI. |
| mywhateels*.spec | Conservar las tablas OOS; incluir módulos nuevos. No añadir GOS. |

## 18. Elementos que no deben copiarse del código antiguo

- Importaciones y búsqueda de datos mediante sys.path.
- scipy.integrate.simps o trapz.
- El motor Bethe, el loader GOS y cualquier dependencia de tablas Hartree.
- Callbacks que capturan excepciones con pass.
- Uso de listas Python results[area][y][x] de ModelResult.
- Guardado NPY de objetos y allow_pickle=True.
- Carpeta Savings-Workspace creada implícitamente.
- Propagación desde el píxel anterior en helpers alternativos.
- Inicialización directa con `mod_cont_list[0]`; debe sustituirse por validación explícita de una lista de continuos OOS no vacía y composición posterior según `ModelComposition`.
- ClustersMatrix creado con np.empty_like para default.
- Límites de centro porcentuales de las extra-components antiguas.
- Ruta soften=False defectuosa.
- Controles con disable en vez de disabled.

Estos defectos/inconsistencias están inventariados en ../whatEELS/MAPEO_DETALLADO_CALLBACKS_PUNTOS_3_A_10.md:542-563.

## 19. Decisiones confirmadas y pendientes

Decisiones confirmadas:

- OOS/FSalvat será el único backend del continuo NLLS.
- El NLLS ofrecerá exactamente `continuum_only` y `continuum_plus_elnes`; las dos composiciones incluyen continuo OOS y usan el mismo motor lmfit.
- La sustracción power-law del background pre-edge será un requisito verificable para las dos composiciones; no sustituye ni elimina el continuo OOS del borde.
- La ausencia/corrupción de una tabla OOS bloqueará el ajuste y nunca eliminará el continuo automáticamente.
- No se añadirán tablas GOS ni se portarán superficies Bethe.
- No se implementará el analizador GOS de la etapa 9.
- La compatibilidad buscada es funcional con el pipeline NLLS antiguo, no identidad numérica de sus continuos GOS.

Pendiente:

1. Definir tolerancias numéricas para el proveedor OOS corregido, parámetros y redchi.
2. Elegir si el resultado NLLS se muestra sólo dentro de /fitting en la primera versión o si se crea /nlls-results. Recomendación: integrarlo primero en /fitting para minimizar cambios.
3. Elegir si las máscaras se guardan dentro del JSON de configuración o sólo por referencia/checksum. Recomendación: incluir RLE opcional para que el workspace sea reproducible.
4. Definir tamaño máximo de resultado y política de arrays BestFit/Residuals/componentes para imágenes grandes. Recomendación: permitir un modo maps-only explícito, nunca eliminar datos silenciosamente.

## 20. No localizado en MyWhatEELS tras la revisión

- Proveedor OOS independiente de MVC que calcule la sección sobre eaxis y la interpole a Eloss.
- Procedencia pública en AppState/dataset que distinga «preprocessed» de «background subtracted»; la marca privada del visualizador no cubre este contrato.
- Constructor elemental que conecte ElementItem con FittingModel.
- Estado por área para modelos, cotas, referencias y locks.
- Multifit elemental basado en parámetros convergidos de referencias.
- Resultado NLLS multipíxel con redchi/componentes/parámetros.
- Herramientas NLLS de centers y white lines.
- Tests existentes del pipeline NLLS elemental.

Se buscaron símbolos y rutas en main.py, whateels/pages/fitting, whateels/pages/multifitting, whateels/pages/clustering, whateels/pages/quantification, whateels/state, whateels/helpers/nlls_library y los tres ficheros mywhateels*.spec. La ausencia se refiere a este checkout; no afirma que no exista en otra rama.

## 21. Definición de terminado

La migración estará terminada cuando:

- el modo manual actual pase todas sus pruebas sin cambios funcionales;
- un usuario pueda definir edges y construir explícitamente `continuum_only` o `continuum_plus_elnes` sobre una fuente con background pre-edge sustraído, y editar cada área;
- cualquier fuente sin procedencia verificable de sustracción quede bloqueada y cambiar de composición invalide los artefactos dependientes correctos;
- default funcione sin segmentación;
- clustering en memoria o JSON genere máscaras y referencias medias correctas;
- Fit References persista snapshots por área;
- el primer píxel y todos los siguientes partan de la referencia de su área;
- el rerun parta del resultado previo del mismo píxel;
- el multifit serial y paralelo produzcan resultados equivalentes;
- ReducedChiSquare, centers, white lines y cuantificación sean reproducibles;
- los resultados se descarguen y recarguen sin pickle;
- el ejecutable encuentre las tablas OOS y no genere procesos/ventanas recursivos;
- cambiar dataset, tab o raw/preprocessed no reutilice estado obsoleto;
- los fallos parciales sean visibles y no destruyan el último resultado válido.
