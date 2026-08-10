# Diario de implementación — Elemental NLLS

Este documento registra el trabajo realizado a partir de `NLLS_TODO.md` para que otra sesión pueda continuar sin reconstruir el contexto desde cero.

## Estado general

- Rama/checkout revisado: la página **Fitting** ya contiene la maquetación de las pestañas `Manual`, `Elemental` y `Results`.
- Alcance del primer incremento: lógica pura OOS y de dominio, procedencia verificable del background, estado NLLS separado y conexión inicial de `Add Edge`, `Build Elemental Model` y ajustes de referencia.
- Invariante: no modificar el modelo manual (`ComponentItem`, `FittingModel.dictionary`, `AppState.fitting_results`) para almacenar artefactos NLLS.

## Tareas

### T01 — Auditoría del TODO y del checkout

Estado: completada para el modelo manual; quedan snapshots visuales/UI de una fase posterior.

- Leído `NLLS_TODO.md` completo (1422 líneas).
- Confirmado que el backend será exclusivamente OOS/FSalvat y que sólo existen las composiciones `continuum_only` y `continuum_plus_elnes`.
- Confirmado que la maquetación Elemental ya expone controles, estados y botones, pero `FittingController` todavía no los conecta.
- Localizada la publicación real del cubo power-law sustraído en `SpectrumImageVisualizer._run_multifitting_thread`.
- Localizados los JSON OOS en `whateels/data/oos/Hartree_Xsections_FSalvat` (99 ficheros).
- Añadidas pruebas de caracterización del contrato manual: Add Component + fit, borrado, reset de fuente y definición numérica actual de Energy Map.

### T02 — Procedencia pública del preprocesado power-law

Estado: completada para la ruta Home `MultiFit(...).run(mode="subtracted")`.

- Añadido `whateels/nlls/provenance.py`.
- Home publica ahora `background_subtracted=True`, historial JSON con operación, implementación, rango, identidad de origen, hash del cubo resultante y revisión estable.
- La revisión cambia si cambian los valores preprocesados aunque coincidan fichero, forma y rango.
- `validate_background_subtracted` exige simultáneamente el flag y la operación power-law; PCA/smoothing/preprocessed genérico no desbloquean NLLS.

### T03 — Proveedor OOS puro y probado

Estado: completada para el constructor y ajuste de referencias; pendiente la comparación dorada con la cuantificación antigua.

- Añadido `whateels/nlls/cross_sections/oos_continuum_provider.py`.
- Lee el formato FSalvat real, valida arrays/onset, ordena el eje y resuelve duplicados.
- Calcula Salvat RPWBA sobre `eaxis` canal a canal, con corrección vectorial de alpha finito.
- Rechaza dominio cinemático inválido, NaN/Inf, curva nula, tabla ausente/corrupta y fit range sin solapamiento.
- Suma las curvas físicas reales de los dobletes, aplica broadening en eV, interpola con cero fuera de dominio y conserva `normalization_factor` reversible.
- `integrate` usa `scipy.integrate.trapezoid(..., x=energy_eV)`.
- Smoke real: C K1, E0=200 keV, alpha=10 mrad, beta=20 mrad, 99 tablas localizadas; curva finita y máximo normalizado 1.0.
- Verificado que los tres spec (`mywhateels.spec`, `mywhateels_linux.spec`, `mywhateels_van.spec`) ya incluyen los JSON FSalvat en la ruta que resuelve el proveedor; no se añadieron tablas GOS.

### T04 — Contratos, workspace y builder lmfit

Estado: parcialmente completada.

- Añadidos `contracts.py`, `defaults.py`, `workspace.py`, `model_builder.py`, `references.py` y excepciones de dominio.
- Implementados `DatasetIdentity`, geometría, rangos, parámetros, specs de edge/continuo/ELNES/área, snapshots y request.
- Workspace independiente por área con deep-copy, revisión, invalidación selectiva, build revision y snapshots de referencia.
- Builder con continuo obligatorio y exactamente las composiciones `continuum_only` / `continuum_plus_elnes`.
- Convención implementada y probada: `table(x + chemical_shift)` desplaza el continuo hacia menor energía cuando el shift es positivo.
- Ajuste de referencia usa `method="leastsq"`, muestras finitas, rango explícito y devuelve arrays/parámetros ligeros; no persiste `ModelResult`.
- Pendiente: serialización JSON versionada, edición de ParameterSpec desde tarjetas y máscaras/áreas de clustering.

### T05 — Conexión con la maquetación Fitting Elemental

Estado: parcialmente completada.

- Añadido `NLLSController` y conectado desde `FittingController` después de registrar los callbacks manuales.
- El controlador rellena subcapas desde las tablas reales y actualiza estados de background, geometría, onset, checksum y cobertura.
- `Add Edge` completa L2/L3 y M4/M5 cuando existen, crea continuo y ELNES serializables y marca el área dirty.
- `Build Elemental Model`, cambio de composición, reset, Fit Current y Fit All ya operan sobre el workspace.
- El fit de referencia usa la media de la ROI comprometida; sin ROI usa la media de la ventana central 2/5–3/5.
- El cambio raw/preprocessed invalida el workspace NLLS además del reset manual existente.
- `Run Elemental NLLS` y `Cancel` permanecen deshabilitados intencionadamente hasta implementar propagación y resultados densos.
- Pendiente: tarjetas de specs/preview gráfico, clustering en memoria/JSON, multifit y Results.

### T06 — Verificación

Estado: completada para este incremento.

- Suite total: 19 pruebas, todas correctas (`15` NLLS + `4` de no regresión manual/estado).
- Cubierto: catálogo, shell ausente, JSON corrupto, eaxis canal a canal, alpha finito, doblete, integración irregular, rango sin soporte, escala reversible, signo, dos composiciones, procedencia, revisión de fuente, workspace y snapshot de referencia.
- `compileall` correcto con Python 3.13.4 para módulos nuevos y conectores editados.
- `git diff --check` correcto.
- Smoke aislado de `NLLSController`: fuente válida -> selección -> Add Edge -> Build, sin escribir `AppState.fitting_results`.

## Decisiones de esta sesión

- El primer incremento no implementará todavía el multifit multipíxel, cancelación ni la pestaña de resultados; esos botones permanecerán deshabilitados hasta que existan resultados y propagación correctos.
- Los objetos vivos de lmfit sólo existirán en memoria dentro del builder/controlador; `AppState` recibirá workspace y snapshots serializables, nunca `ModelResult` por píxel.
- `DatasetIdentity` derivará la validez de background del historial público, no de `AppState.is_multifit` ni de `_preprocessed_source`.

## Bloqueos o limitaciones detectadas

- El `python.exe` global es el alias de Microsoft Store y no puede ejecutarse en este entorno.
- `temporal_venv` contiene Python 3.13.4, pero comenzó sin las dependencias científicas. La sintaxis se verificó allí; las pruebas se ejecutaron con `C:\Users\Vanessa\anaconda3\envs\MyWhatEELS\python.exe`, que contiene las versiones fijadas del proyecto.
- Importar `whateels.pages` carga todas las páginas de forma eager y supera un smoke de 60 s en este entorno. Para aislar el nuevo controlador se comprobó su import y flujo con los paquetes padre preregistrados, evitando atribuir ese coste global previo a NLLS.

## Comandos de recuperación/verificación

```powershell
& C:\Users\Vanessa\anaconda3\envs\MyWhatEELS\python.exe -m unittest discover -s tests -v
& .\temporal_venv\Scripts\python.exe -m compileall -q whateels/nlls whateels/pages/fitting/MVC/controller tests
git diff --check
```

## Siguiente bloque recomendado al cerrar el primer incremento

Nota de recuperación: el punto 3 de esta lista quedó completado en T07-T09; usar la lista final del documento para continuar.

1. Añadir `serialization.py` y round-trip JSON estricto de modelo/workspace sin arrays/objetos lmfit.
2. Crear tarjetas Elemental para mostrar/editar cada `ContinuumSpec` y `FineStructureSpec`, con preview que no use `AppState.fitting_results`.
3. Implementar `ClusteringAreaAdapter`, máscaras y referencias medias por cluster.
4. Sólo después, implementar propagación serial por píxel y `NLLSResultsAccumulator`/`xr.Dataset`.

## Continuación — clustering y ajustes de interfaz

### T07 — Adaptador de clustering y áreas NLLS

Estado: completada para el clustering actual en memoria; la carga de JSON permanece deshabilitada.

- Añadido `whateels/nlls/areas.py` con `ClusteringAreaAdapter` y `AreaDefinition`.
- El adaptador valida estructura, matriz 2D, forma espacial exacta, etiquetas finitas/enteras/no negativas, `n_clusters`, identidad de fichero e imagen, cobertura completa y exclusividad.
- Cada etiqueta genera un identificador estable (`cluster_<label>`), una máscara booleana inmutable y un fingerprint SHA-256.
- `AreaModelSpec` conserva máscara, fingerprint y etiqueta de clustering sin incluir el array en comparaciones del contrato.
- `NLLSWorkspace.apply_clustering` mantiene `default` como plantilla interna y sustituye las áreas segmentadas por deep-copies independientes. Cuando existen clusters, sólo ellos son áreas ejecutables para referencias y futuros runs.
- Reaplicar clustering elimina referencias segmentadas obsoletas; resetear un cluster conserva su máscara e identidad espacial.
- Las referencias de cluster se recalculan como la media de los píxeles de su máscara sobre `ElectronCount` activo. Los `centres` guardados por Clustering no se usan.
- `Use Current Clustering` ya aplica las áreas, actualiza el selector y respeta los estados de Build/Fit Current/Fit All.
- `ClusteringOrchestrator.save_clustering_result` publica el resultado en `AppState` al terminar el algoritmo; ya no es necesario descargar primero el JSON para que Fitting pueda verlo.

### T08 — Ajustes visuales solicitados en Fitting

Estado: completada.

- `Load Clustering JSON` y su `FileInput` se eliminaron completamente de la vista por petición posterior del usuario.
- Todos los iconos `?` de la barra lateral de Fitting crean un `bokeh.models.Tooltip(position="left")`, incluido el control compartido de datos preprocesados.
- `OOS Status` ya no usa `SimpleDetails`: método/versión y estado quedan en un bloque informativo siempre visible.

### T09 — Verificación de la continuación

Estado: completada.

- Suite total actual: 26 pruebas, todas correctas (`20` de dominio NLLS y `6` de regresión/manual/layout).
- Nuevas coberturas: máscaras estables y excluyentes, shape/identidad inválidos, etiquetas no enteras/negativas, deep-copy por cluster, conservación de máscara en reset, referencia media real, tooltips izquierdos, FileInput deshabilitado y ausencia de `SimpleDetails` para OOS Status.
- Smoke MVC real correcto: clustering compatible habilita el botón, crea `cluster_0`/`cluster_1` y la referencia activa coincide con la media exacta de su máscara sobre el cubo preprocesado.
- `compileall` correcto para dominio NLLS, controladores/layouts de Fitting, orquestador de Clustering y pruebas.
- `git diff --check` correcto.

## Siguiente bloque recomendado tras T09

1. Implementar tarjetas Elemental editables para `ContinuumSpec` y `FineStructureSpec`, con invalidación por área.
2. Añadir preview del modelo/curvas OOS sin reutilizar los resultados manuales.
3. Diseñar la serialización JSON versionada para modelos/resultados; no reintroducir `Load Clustering JSON` salvo petición explícita futura.
4. Implementar propagación NLLS serial por píxel y acumulación densa en `xarray`, manteniendo `Run Elemental NLLS` deshabilitado hasta que esa ruta esté completa y probada.

## Continuación — build, reset y referencias completas

### T10 — Limpieza definitiva de OOS/JSON en la vista

Estado: completada.

- Eliminados por completo el campo `OOS method / version`, el Markdown `OOS status`, su tooltip, propiedades y aliases de la vista/controlador.
- Eliminados el texto `Load Clustering JSON`, el `FileInput` y todas sus propiedades; ya no existe un control deshabilitado residual.
- La validación física OOS sigue activa internamente para Add Edge/Build/Fit y comunica errores mediante notificaciones, sin mostrar el bloque informativo retirado.

### T11 — Build Elemental Model y Reset Area

Estado: completada para modelos y previews portables.

- Añadido `ModelBuildSnapshot`: área/revisión/fuente/composición, componentes, parámetros iniciales, preview, curvas por componente y metadata OOS necesaria para reproducibilidad.
- `Build Elemental Model` reconstruye el modelo desde specs, evalúa un preview finito sobre Eloss y hace commit sólo si área, revisión, composición y DatasetIdentity siguen vigentes.
- El workspace guarda snapshots ligeros, nunca `Model`, `CompositeModel`, `Parameters` ni `ModelResult` vivos.
- Cambiar specs/rango/geometría invalida build y referencia del área afectada.
- `Reset Area` elimina build y referencia. En clusters restaura la configuración desde `default` conservando máscara/fingerprint; en `default` vuelve al modelo vacío y a referencia ROI.
- Al aplicar clustering después de construir `default`, cada cluster recibe una copia independiente y válida del snapshot de build; así no hay que reconstruir manualmente el mismo modelo para todos los clusters recién creados.

### T12 — ROI default, Fit Current y Fit All References

Estado: completada.

- Añadido selector `Default reference source` con `Current ROI` (predeterminado) y `Central window`.
- `Current ROI` exige una ROI comprometida y usa la media, no la suma mostrada por la gráfica. `Central window` conserva el fallback 2/5–3/5.
- Cada referencia registra estrategia, número de píxeles y fingerprint de máscara. Cambiar o borrar la ROI invalida sólo la referencia `default`, conservando su build.
- `Fit Current Reference` exige un build vigente, reconstruye lmfit desde specs, ajusta con `method="leastsq"`, persiste espectro/reference metadata, parámetros completos, stderr, redchi, best fit, residual y componentes.
- Añadido `ReferenceFitService.fit_many` con aislamiento por área y resultado tipado de éxitos/fallos.
- Tras aplicar clustering, `default` se conserva como plantilla/fit ROI, pero `runnable_area_ids` contiene sólo los clusters. Por tanto, `Fit All References` ajusta exactamente todos los clusters y no vuelve a incluir el área solapada `default`.
- Un fallo de cluster no detiene los demás; su snapshot se elimina para impedir que se considere válido en futuros runs, mientras se conservan los clusters convergidos.
- Los botones verifican build, disponibilidad de máscara/ROI, revisión, fuente, composición, fit range, estrategia y fingerprint antes de habilitarse.

### T13 — Verificación de build y referencias

Estado: completada.

- Suite total actual: 31 pruebas, todas correctas.
- Integración MVC cubierta: build de `default`, fit ROI con amplitud esperada, invalidación al cambiar ROI, fallback central, reset, clonación a clusters, Fit All con amplitudes distintas y fallo parcial aislado.
- Dominio cubierto: snapshot portable/inmutable de build, snapshot de referencia inmutable y `fit_many` con una referencia inválida.
- `compileall` y `git diff --check` correctos.

## Continuación — visualización de resultados de referencia

### T14 — Maquetación reactiva de Results

Estado: completada para `ReferenceFitSnapshot`.

- Sustituido el placeholder de la pestaña `Results` por `NLLSResultsView`, un componente aislado en `view/components/nlls_results_view.py` que consume únicamente snapshots portables; no conserva objetos `ModelResult` ni estado vivo de lmfit.
- Tras `Fit Current Reference` y `Fit All References`, la barra lateral abre automáticamente `Results` y selecciona el área recién ajustada.
- La vista muestra referencia original, best fit, componentes individuales y límites del fit range sobre Eloss; debajo muestra el residual `data - best fit` y su línea de cero.
- Añadido selector de curvas `Reference / Best fit / Components` y selector reactivo de área. Después de clustering se puede recorrer el fit ROI conservado y todos los clusters convergidos sin recalcular.
- El resumen informa área, `Reduced χ²`, número de píxeles, origen de la referencia, composición, método, rango y mensaje del optimizador.
- Añadida tabla de parámetros con valor, error estándar, cotas y estado libre/fijo.
- La maquetación reutiliza la paleta de Fitting (`#ca4bc8` / `#7373da`), tarjetas, sombras, radios y espaciado existentes, y mantiene scroll vertical/contención horizontal en la barra lateral.
- Cualquier cambio de ROI, fuente, rango, composición, build/reset o clustering vuelve a filtrar los snapshots contra revisión, fuente, máscara y fit range; un resultado stale desaparece de la vista inmediatamente.

### T15 — Verificación de Results

Estado: completada.

- Cobertura MVC añadida para placeholder inicial, apertura automática de la pestaña, overlays de fit/residual, resumen ROI, tabla de parámetros, selector ROI/clusters y retirada visual de clusters fallidos o referencias invalidadas.
- Suite total actual: 32 pruebas, todas correctas.
- Smoke de render Panel/Bokeh correcto: tanto el sidebar completo como `NLLSResultsView` generan un root de documento y el gráfico publicado es un `holoviews.Overlay`.

## Continuación — resultados en los paneles principales

### T16 — Clustering y resultados a tamaño completo

Estado: completada.

- `Use Current Clustering` sustituye el mapa integrado original del panel izquierdo por un mapa categórico de etiquetas, con la misma paleta discreta `tab20b` usada por Clustering y colorbar de clusters.
- El panel espectral derecho pasa a mostrar las referencias medias reales de todos los clusters. Se recalculan sobre `ElectronCount` de la fuente NLLS activa; los `centres` normalizados del JSON/memoria de Clustering siguen sin usarse.
- `Fit Current Reference` y `Fit All References` conservan la navegación automática a `Results`, pero el overlay `Reference / Best fit / Components` se publica ahora en el panel espectral principal, usando todo el ancho y alto disponibles.
- Eliminados del cuerpo visible de la barra lateral los dos gráficos pequeños de fit/residual. `Results` conserva selector de área, resumen y parámetros, y añade `Main plot: Fit curves / Residual`; ambas opciones reutilizan el panel principal a tamaño completo.
- Los controles `Reference / Best fit / Components` actualizan en vivo el gráfico principal. Se deshabilitan mientras se visualiza el residual.
- Mientras el mapa de clustering está activo, hover/click no sustituyen accidentalmente las referencias de cluster o el resultado NLLS por un espectro de píxel.
- Al invalidar un resultado por ROI, reset, rango o modelo, el panel principal restaura las referencias de clusters si hay clustering; en caso contrario recupera el espectro ROI/hover.
- Cambiar a un cluster todavía no ajustado restaura sus referencias de clustering en vez de enseñar silenciosamente el fit ROI/default conservado.

### T17 — Verificación del intercambio de paneles

Estado: completada.

- Añadida cobertura del visualizador real para la secuencia imagen/ROI → labels/referencias de clustering → resultado NLLS → referencias de clustering.
- Añadida cobertura del controlador para publicación del overlay principal, conmutación a residual, bloqueo de capas y payload de clustering con dos medias espectrales.
- Suite total actual: 33 pruebas, todas correctas; `compileall`, render Panel/Bokeh y `git diff --check` correctos.

### T18 — Residual como capa del gráfico principal

Estado: completada.

- Eliminado el selector separado `Fit curves / Residual`.
- `Residual` pasa a ser la cuarta capa conmutable junto a `Reference`, `Best fit` y `Components`; puede visualizarse simultáneamente con cualquiera de ellas.
- Los cuatro botones conservan su tamaño y estilo, organizados como una cuadrícula 2×2 en `Results`.
- El residual se dibuja en rojo sobre el mismo eje de cuentas e incluye una línea horizontal discontinua en cero.
- Se conserva internamente el plot de residual aislado para inspección/compatibilidad, pero la interfaz publica siempre la combinación de capas en el panel principal grande.

### T19 — Flujo Fit unificado y selección de áreas en modal

Estado: completada.

- Eliminada por completo la tarjeta `Fitted parameters` de `Results`; los snapshots siguen conservando sus parámetros para cálculo, trazabilidad y futuras exportaciones, pero la interfaz ya no los muestra.
- Normalizada la cuadrícula 2×2 de `Reference / Best fit / Components / Residual`: las cuatro celdas fuerzan la misma altura, margen, radio y ancho.
- Eliminados `Reset Area`, `Fit Current Reference`, `Fit All References`, el `SimpleDetails` de `Areas` y el `SimpleDetails` de `Run Setup`.
- `Use Current Clustering` vive ahora en `Model Setup` y funciona como acción reversible: al activarlo muestra etiquetas/espectros de clusters y pasa a `Use Preprocessed Data`; al pulsarlo de nuevo elimina las áreas segmentadas y restaura el ROI preprocesado conservando el modelo y fit válidos de `default`.
- Añadido un único botón `Fit`. En modo ROI ajusta automáticamente `default`; en modo clustering ajusta exactamente los clusters elegidos.
- `Model Setup` conserva un modelo compartido en `default`: si se activa clustering antes de añadir aristas o construir, los cambios se vuelven a clonar sobre todas las máscaras. Así no quedan clusters imposibles de construir después de retirar el antiguo selector `Active Area`.
- Añadido junto a `Fit` el mismo icono SVG de ajustes empleado por UMAP. Abre el modal `Select Area to run fit`, con `Areas to fit`, `Select all` y cierre `Okay.`.
- El modal permanece deshabilitado en modo ROI y se habilita solamente cuando se ha aplicado un clustering. Al entrar en clustering inicializa la selección con todos los clusters; el usuario puede reducirla y `Select all` la repone completa.
- Eliminado el slider `Fit Range` y todos sus watchers/configuración. Build, validación y fit derivan ahora un único rango automático del mínimo y máximo finitos del eje `Eloss` activo.
- Añadido `NLLSWorkspace.clear_clustering()` para volver de forma explícita y comprobable al área ROI `default`, descartando áreas/builds/fits de clusters sin tocar los artefactos válidos del ROI.
- Verificación actual: 34 pruebas correctas para MVC/manual y dominio NLLS, incluida selección parcial/completa, configuración compartida posterior al clustering, fallo aislado de cluster, retorno a ROI, rango automático y ausencia de controles retirados; `git diff --check` correcto.

### T20 — Clustering dentro del modal y acciones ancladas

Estado: completada.

- El icono de ajustes permanece junto a `Fit` y `Use Current Clustering / Use Preprocessed Data` se ha trasladado al interior del modal `Select Area to run fit`.
- El modal puede abrirse en modo ROI siempre que exista un resultado de clustering compatible. Sus clusters se cargan antes de activar el modo y la selección se conserva al pulsar `Use Current Clustering` desde el propio modal.
- El icono, el botón de clustering, `Areas to fit` y `Select all` sólo se deshabilitan cuando no existe un clustering compatible ni hay áreas de clustering activas.
- Rehecha la cadena de altura del sidebar (`FittingRightSidebarLayout` → contenedor raíz → `Tabs` → pestaña Elemental) con `stretch_both`, altura completa y `min-height: 0`.
- El bloque central de estados/secciones absorbe el espacio libre y dispone de scroll propio; el bloque de acciones no encoge y queda anclado al fondo con padding completo. Se sustituyó el margen superior externo de la pestaña por padding interno para que no sume altura y corte la última fila.
- El `right-sidebar` exterior oculta su overflow: el único scroll vertical del contenido Elemental queda ahora en el contenedor central, no alrededor de los botones de acción.
- Verificación actual: 36 pruebas correctas, incluidas disponibilidad previa del modal, ausencia de clustering compatible, composición interna del modal, vecindad del icono con `Fit` y contrato de altura/scroll; `git diff --check` correcto.

### T21 — Edge Definition y Model Setup bloqueados por los estados de validación

Estado: completada.

- `SimpleDetails` acepta ahora `locked` y expone `expanded`, `locked`, `set_expanded()` y `set_locked()`. Una sección bloqueada se cierra, deshabilita su cabecera, ignora `toggle()`, se pinta en gris (`#b9b9c6`) con prefijo `✕` y usa `cursor: not-allowed`. `set_expanded(False)` sigue permitido con la sección bloqueada; abrirla es exactamente lo que el bloqueo impide.
- Las secciones `Edge Definition` y `Model Setup` de la pestaña Elemental se crean con `locked=True`: sin un controlador que valide la fuente no pueden abrirse ni exponer `Add Edge` / `Build Elemental Model`.
- `NLLSController._update_validation_status` calcula por separado la validez de background y de geometría y añade `_apply_section_availability`:
  - Si **cualquiera** de los dos estados es inválido, ambas secciones quedan bloqueadas y cerradas.
  - Cada aviso sólo es visible cuando su propio estado bloquea. Con los dos válidos no se muestra ningún `Alert`, de modo que las dos secciones pasan a ocupar la posición superior de la pestaña sin reordenar la maquetación.
  - La apertura automática ocurre sólo en la transición inválido → válido (`_sections_unlocked`), así una sección plegada a mano por el usuario sigue plegada en refrescos posteriores con la misma fuente.
- Añadido un watcher de `AppState.all_datasets`: la tarjeta compartida `Dataset Information` escribe E0/alpha/beta en `dataset.attrs` y republica esa lista, que era la única señal disponible. Sin él, corregir la geometría desde la tarjeta dejaba las secciones bloqueadas hasta conmutar la fuente raw/preprocessed.
- Nuevas propiedades `elemental_edge_section` / `elemental_model_section` en `FittingRightSidebarLayout` y en `FittingView`, con el mismo patrón de alias ya usado por el resto de widgets Elemental.
- Verificación: 38 pruebas correctas. Nueva cobertura de layout (secciones bloqueadas y cerradas de inicio, cabecera deshabilitada, `toggle()` sin efecto y orden `background → geometry → edge → model` en el contenedor) y de controlador (fuente válida sin avisos y con ambas secciones abiertas, plegado manual conservado, geometría bloqueada vía `all_datasets`, recuperación de la geometría y pérdida de la procedencia power-law). Smoke de render Panel/Bokeh correcto con secciones bloqueadas, desbloqueadas y con los avisos ocultos; `compileall` y `git diff --check` correctos.

### T22 — Run Elemental NLLS: propagación y multifit serial

Estado: completada para la primera ejecución multipíxel serial (Fase 4 del TODO).

- Ampliado `NLLSRunRequest` como contrato inmutable y cerrado: áreas seleccionadas, rango/método, composición por área, revisión de fuente/workspace/áreas, modo serial, workers y futuro origen de rerun. Rechaza áreas duplicadas, `default` combinado con clusters, configuraciones incompletas o sobrantes, revisiones inválidas y solicitudes stale.
- Añadido `ElementalMultifitService` sin dependencias de Panel. Reconstruye el modelo exactamente una vez por área y cada píxel recibe una copia nueva de los parámetros convergidos de `ReferenceFitSnapshot`; nunca hereda el resultado del píxel anterior. Cada cluster usa exclusivamente su propia referencia.
- La selección espacial sigue las máscaras congeladas del workspace. En modo clustering se ajustan únicamente los clusters seleccionados en el modal; las máscaras solapadas fallan antes del primer fit. En modo `default`, conforme al contrato actual de `NLLS_TODO.md`, la ROI define el espectro de referencia y la máscara de ejecución cubre la imagen completa.
- El bucle usa `method="leastsq"`, aplica el rango finito, aísla errores por píxel y distingue `not_selected`, `pending`, `success`, `insufficient_data`, `fit_error` y `cancelled`. Un píxel inválido no detiene el resto.
- Añadidos `NLLSResultsAccumulator` y `NLLSResultsAssembler`. El resultado es un `xr.Dataset` numérico denso con `OriginalData`, `AreaLabel`, `FitStatus`, `ReducedChiSquare`, `BestFit`, `Residuals`, curvas por componente y mapas de valor/stderr por parámetro. Los esquemas de componentes/parámetros se materializan aunque todos sus píxeles fallen; no se guarda ningún `ModelResult` ni array `dtype=object`.
- El dataset persiste identidad/revisión de fuente, geometría, método, composiciones, procedencia de background, convención de chemical shift, metadatos/checksums OOS, configuración/áreas, timestamp, estado complete/cancelled, conteos y versiones. Se verificó round-trip NetCDF.
- `Run Elemental NLLS` se habilita sólo si todas las áreas seleccionadas conservan build y referencia vigentes. Al arrancar congela dataset/specs/referencias, bloquea los controles mutables y ejecuta el servicio serial en un hilo daemon; el worker sólo publica eventos en una cola y nunca escribe Panel/AppState.
- Añadido indicador de progreso por chunks al bloque inferior de acciones. El hilo del documento drena la cola mediante callback periódico, actualiza el progreso y realiza el único commit de `app_state.nlls_results`.
- Añadida cancelación cooperativa entre píxeles. Si se cancela, los pendientes quedan marcados y el resultado parcial sólo se conserva cuando no existía uno completo; un resultado completo anterior permanece intacto. Cambiar ROI, fuente o geometría durante un run solicita cancelación.
- El commit es atómico y revalida fuente, workspace, selección, rango, composición, revisiones y referencias. Un resultado de worker stale se descarta sin reemplazar el último resultado completo.
- Cobertura nueva: iniciales independientes frente a convergencias extremas, referencias distintas por área, invariancia al orden de áreas/píxeles, selección parcial de clusters, errores aislados, máscaras solapadas, cancelación, preservación del resultado anterior, descarte stale, arrays numéricos y round-trip NetCDF.
- Verificación actual: 48 pruebas correctas; `compileall` y `git diff --check` correctos.

Pendiente según el orden del TODO:

- Fase 5: visualización de mapas `ReducedChiSquare`/`FitStatus`, selección de píxel, mapas de parámetros/stderr, overlays/filtros y descarga NetCDF/CSV.
- El rerun desde los parámetros previos del mismo píxel, `Lock All` y componentes modificadas pertenecen a la Fase 6; la ruta inicial los rechaza explícitamente para no mezclar semánticas.
- La paralelización y `fit_chunk_worker` pertenecen a la Fase 7 y permanecen desactivados hasta validar paridad con esta ruta serial.

### T23 — Plots multipíxel aditivos en el área principal

Estado: completada la primera parte visual de la Fase 5.

- Añadido `NLLSMultifitResultsPlot`, un bloque principal interactivo que consume directamente el `xr.Dataset` portable del run y no reconstruye ni conserva objetos lmfit.
- El panel izquierdo permite visualizar `ReducedChiSquare`, `FitStatus`, `AreaLabel`, todos los mapas de parámetros y sus mapas `stderr`. Los estados usan colores discretos y una colorbar con sus nombres; el píxel activo queda marcado sobre el mapa.
- Al pulsar un píxel del mapa, el panel derecho actualiza sus curvas `Original`, `Best fit`, componentes y `Residual`. Las cuatro capas son combinables mediante el mismo grid 2×2 empleado en los resultados de referencia. También se muestran área, status y χ² reducido del píxel.
- `LayoutManager` envuelve el plot fuente de Fitting en un stack vertical con scroll. Cada nuevo run se inserta en la posición superior, conservando debajo todos los runs anteriores y, al final, el mapa/espectro original. Es el mismo patrón aditivo y `move-to-top` conceptual de Adv. Clustering; ningún resultado nuevo sustituye los plots ya visibles.
- Cada resultado se presenta en una tarjeta plegable titulada con número de run, áreas y estado complete/incomplete. Al añadirlo, el scroll vuelve arriba para que sea visible inmediatamente.
- El commit numérico continúa siendo atómico y ocurre antes del render. Si la construcción del plot falla, `app_state.nlls_results` permanece guardado y sólo se muestra un aviso. Los resultados existentes de la fuente activa se restauran al volver a crear el controlador/página.
- Cambiar la fuente raw/preprocessed elimina los bloques visuales derivados y ejecuta `cleanup()` sobre watchers/streams; editar el modelo o lanzar otro run no elimina el histórico visual de la misma fuente.
- Nueva cobertura para selector de mapas, selección de píxel, capas espectrales, render Panel/Bokeh, inserción de dos runs en orden `nuevo → anterior → fuente`, limpieza y publicación desde el commit.
- Verificación actual: 50 pruebas correctas; el nuevo componente y el stack aditivo renderizan correctamente con Panel/Bokeh.

Pendiente de la Fase 5:

- Overlay explícito de límites/áreas y filtros de status.
- Descarga de resultados completos en NetCDF y exportación tabular CSV.

### T24 — Todos los controles de resultados en la pestaña Results

Estado: completada.

- La pestaña `Results` deja de ser un único bloque y pasa a contener exactamente dos `SimpleDetails` abiertos: `Reference Fit` y `Elemental NLLS`. Ambos son sólo controles; sus figuras viven siempre en el área principal, así que el menú y los gráficos ya no se mezclan.
- La tarjeta de resumen de `Reference Fit` pierde la banda magenta con el nombre del área (`Cluster #`). El área ya se elige en el selector inmediatamente superior, de modo que el título sólo repetía información. El resto de la tarjeta (métricas, método, rango y mensaje) se conserva intacto.
- `NLLSMultifitResultsPlot` deja de ser un `pn.Card`: es un `pn.Column` que sólo contiene el `SplitJs` mapa/espectro. Se eliminan cabecera plegable, título de tarjeta y colores de cabecera. Los runs se apilan directamente en el área de plots, igual que los bloques de Adv. Clustering.
- Sus widgets siguen creándose en el propio run pero se exponen como `controls` (tupla en orden de presentación) y los monta la barra lateral. Un run no renderiza nunca sus propios widgets.
- Añadido `NLLSMultifitControls`, el bloque de la sección `Elemental NLLS`. Monta un único conjunto de widgets cada vez y coloca el selector `Run` **debajo** de `Result map`, para que el control superior sea el mapa igual que `Reference area` lo es en el bloque de referencia. El selector `Run` sólo es visible y editable con dos o más runs; con uno solo repetiría el título del gráfico.
- Se conserva el apilado aditivo de T23: registrar un run lo inserta arriba en el stack y lo selecciona en el menú, sin retirar los anteriores. `clear_nlls_result_plots` desregistra además los controles, de modo que cambiar de fuente raw/preprocessed vacía menú y plots a la vez.
- Como ya no hay cabecera de tarjeta, cada figura lleva el número de run en su propio título (`Run 2 · Reduced χ²`, `Run 2 · Pixel y=1, x=2 — success`); en un stack de varios runs seguían siendo indistinguibles.
- Un run recién publicado trae la pestaña `Results` al frente, igual que ya hacía un ajuste de referencia. Restaurar un resultado previo al reconstruir la página no roba la pestaña (`activate=False`).
- Ambos bloques pierden su padding horizontal propio: el `SimpleDetails` anfitrión ya inserta 10 px por lado y se duplicaba.
- Verificación actual: 55 pruebas correctas. Nueva cobertura de las dos secciones del tab y su contenido, ausencia del título de área en el resumen de referencia, widgets fuera del bloque de plots, orden `Result map → Run → capas` al montar, conmutación entre runs, visibilidad del selector según el número de runs y registro/desregistro desde `LayoutManager`. Smoke de render Panel/Bokeh correcto para sidebar, stack de dos runs y conmutación de run/píxel/mapa; `compileall` y `git diff --check` correctos.
