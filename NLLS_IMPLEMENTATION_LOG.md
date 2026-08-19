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

### T25 — Overlay de áreas y filtros científicos de resultados

Estado: completada la parte interactiva de la Fase 5; exportaciones aplazadas por decisión de producto hasta el bloque final.

- El mapa de cada run superpone opcionalmente un relleno categórico semitransparente de `AreaLabel` y límites explícitos de doble trazo. Los límites incluyen el perímetro exterior, las fronteras área/no seleccionada y las fronteras entre clusters, y permanecen visibles sobre cualquier mapa continuo.
- La información de área deja de mostrar únicamente el entero: recupera `area_ids_by_label` del propio `xr.Dataset` y presenta el identificador estable (`cluster_0`, etc.), con fallback seguro para datasets antiguos.
- Añadido filtro multiselección por `FitStatus`. Se muestran inicialmente todos los estados presentes para no ocultar fallos de forma implícita.
- Añadidos umbral máximo de `ReducedChiSquare` y umbral máximo de error relativo `abs(stderr/value)`. El segundo sólo se habilita cuando el mapa activo es un parámetro o su `stderr` y existe la pareja de variables.
- Mapa, marcador, clic y espectro comparten exactamente la misma máscara. Un píxel filtrado se vuelve `NaN` en el mapa, no se puede seleccionar y no alimenta las curvas; si la selección activa deja de ser válida se elige el primer éxito visible y, si no queda ninguno, se muestra un estado vacío explícito.
- El mapa de χ² usa límites robustos percentiles 2–98 y permite representación `log10` sin alterar los datos persistidos. Los mapas categóricos conservan sus escalas discretas.
- Los controles siguen viviendo en `Results > Elemental NLLS`, mientras relleno, límites y máscara se aplican a los plots aditivos del área principal.
- Cobertura añadida para overlay/retiro de overlay, segmentos de frontera, nombres de cluster, máscara por status, χ² y error relativo, rechazo de clics ocultos, estado sin coincidencias y χ² log/robusto.
- La descarga NetCDF/CSV de esta fase queda intencionadamente pendiente y se implementará junto con todas las exportaciones de referencias, resultados y herramientas derivadas al final de las fases funcionales.

### T26 — Modelo modificado y rerun por píxel

Estado: completada la Fase 6 funcional; sus futuras descargas permanecen en el bloque final.

- Cada resultado completo recibe `run_id`, `run_kind`, `run_version` y `parent_run_id`. Un rerun produce un dataset nuevo y aditivo (`modified vN`), nunca sobrescribe el bloque visual del padre y muestra su versión en el selector/resumen de runs.
- Añadidos `PixelParameterSnapshot` y `pixel_parameter_snapshot()`: reconstruyen valores y `stderr` de un píxel directamente desde las variables numéricas 2D, sin `ModelResult`, pickle ni objetos lmfit persistidos.
- El dataset guarda además `parameter_schema_by_area` con nombre, valor base, límites, `vary`, expresión y `brute_step`; el contrato queda recuperable después de un round-trip xarray/NetCDF.
- `ElementalMultifitService` acepta ahora un padre completo y valida estrictamente `run_id`, identidad/revisión de fuente, forma y eje `Eloss`. En un rerun, cada píxel parte sólo de sus propios mapas anteriores; los parámetros añadidos parten de los defaults del modelo modificado y los locks/límites proceden del `AreaModelSpec` actual.
- `NLLSResultsAccumulator.from_dataset()` clona el padre y `prepare_rerun_area()` limpia exclusivamente las máscaras elegidas. Todas las variables y píxeles de áreas no seleccionadas se preservan exactamente, incluidas componentes antiguas, parámetros, errores, curvas, status y χ².
- Añadido modo explícito `Begin Modified Model` en `Results > Elemental NLLS`. Permite seleccionar las áreas a modificar, `Lock All`, `Unlock All` o cancelar el borrador recuperando el workspace y resultado padre.
- Durante el modo modificado, `Add Edge`, composición y `Build Elemental Model` actúan sólo sobre las áreas seleccionadas; el resultado padre se mantiene vivo para propagación/rollback. El botón inferior cambia a `Run Modified Fit`, exige rebuild vigente y vuelve a `Run Elemental NLLS` tras un commit correcto.
- Los inputs congelados del worker incluyen una copia profunda del padre. La revalidación atómica distingue primera ejecución y rerun; cancelación/error conservan el padre y permiten corregir/reintentar, mientras un éxito sale del modo de edición y publica la nueva versión aditiva.
- Pruebas añadidas: recuperación pública del snapshot de píxel, iniciales exactas por píxel, componente nueva con defaults propios, locks limitados a un área, conservación exacta del área no modificada, versión/parentesco, editor de sidebar, rebuild y ejecución completa asíncrona del rerun.

### T27 — Multifit paralelo con paridad serial

Estado: completada la Fase 7 funcional en la ruta Python/Windows; queda pendiente repetir el smoke dentro del ejecutable congelado cuando se genere el siguiente build.

- Añadido `fit_chunk_worker` como función de módulo importable por `spawn`. Recibe únicamente arrays NumPy, coordenadas, `Eloss`, dataclasses de dominio, parámetros serializados y snapshots OOS muestreados; no recibe `CompositeModel`, `Parameters`, closures ni `ModelResult`.
- Cada proceso construye su propio `_SampledOOSProvider`, `NLLSModelBuilder` y modelo compuesto una vez por chunk. Devuelve sólo diccionarios de números/strings/arrays y códigos `FitStatus`, que el proceso padre fusiona en el mismo acumulador denso de la ruta serial.
- `ElementalMultifitService.fit_area_parallel()` mantiene un número acotado de futures: sólo envía hasta `workers` chunks simultáneos y deja de enviar nuevos chunks al recibir cancelación. Los no ejecutados terminan como `cancelled`; un fallo de proceso/chunk se aísla como `fit_error` sin romper el dataset.
- Workers por defecto en GUI: `max(1, cpu_count - 1)`, limitados internamente por píxeles/chunks. El chunk automático queda entre 8 y 128 píxeles; el tamaño puede inyectarse en tests/benchmarks mediante `parallel_chunk_size`.
- Cada dataset registra `execution_mode`, workers solicitados/efectivos y un `parallel_plan` por área con píxeles, chunks, chunk size y estimación de bytes de payload simultáneo. No se crea una matriz de resultados lmfit, por lo que la memoria de salida sigue siendo únicamente la de los arrays densos.
- Añadidos `Execution mode: Serial/Parallel` y `Parallel workers` en `Model Setup`. Workers sólo se habilita en modo paralelo; ambos valores se congelan en `NLLSRunRequest`, bloquean durante el run y forman parte de la revalidación atómica.
- Verificada paridad numérica serial/paralela, con tolerancia `rtol=1e-10/atol=1e-12`, tanto para primera ejecución como para rerun. También se prueba cancelación por chunks y el flujo real `Panel controller thread -> ProcessPoolExecutor -> Windows spawn -> commit` con dos workers.
- `main.py` ya llama `multiprocessing.freeze_support()` antes de imports pesados y el worker no importa MVC/Panel. La prueba efectiva del `.exe` PyInstaller queda marcada como smoke de empaquetado, no como lógica pendiente: requiere construir/arrancar el artefacto fuera de la suite unitaria.

### T28 — Center Analysis y White Lines como resultados derivados

Estado: completada la Fase 8 de Fitting con el alcance corregido por producto. **No se implementa una segunda Egerton Quantification**: esa función ya existe en la página `Quantification` y duplicarla aquí produciría dos fuentes de verdad.

- Añadido `CenterAnalysisService`, puro y sin Panel. Descubre únicamente mapas de parámetros `*center`, exige dos distintos, calcula `abs(center_a - center_b)`, enmascara por `FitStatus.SUCCESS` y devuelve un `xr.Dataset` con `Distances`, status, áreas, unidades e identidad del run padre.
- Añadidos `WhiteLineRequest` y `WhiteLineService`. Trabajan sobre componentes ELNES densas ya ajustadas o sobre el espectro raw, soportan ventanas automáticas/manuales, ratio directo/invertido y resta opcional de componentes en modo raw.
- El modo automático calcula el FWHM espacial y usa la anchura total histórica `2.5625 × max(FWHM)` centrada por píxel en cada componente. Todas las integraciones usan explícitamente `scipy.integrate.simpson(..., x=Eloss)`; no se usa `simps` ni integración por índice.
- Los datasets White Lines contienen intensidades A/B, ratio, ventanas efectivas por píxel, `FitStatus`, `AreaLabel`, unidades, request serializado, algoritmo de integración y relación con el run padre.
- Añadido bloque `Derived analyses` a los controles del run seleccionado en `Results > Elemental NLLS`: selectores Center A/B, `Get Distances`, White line A/B, fuente fitted/raw, auto/manual, ventanas manuales e inversión de ratio. Los controles permanecen deshabilitados si el run no contiene los mapas/componentes necesarios.
- Añadido `NLLSDerivedResultsPlot`: mapa grande con escala robusta, máscara de status y límites de áreas. Cada cálculo se inserta arriba del stack principal de forma aditiva, por encima de analyses/runs anteriores y de la fuente; sus selectores de mapa permanecen en la pestaña Results.
- `LayoutManager` registra, limpia y ejecuta `cleanup()` de resultados derivados junto a los runs al cambiar de fuente. Los callbacks del controlador sólo calculan/publican datasets, y un fallo visual no introduce `ModelResult` ni muta el resultado NLLS padre.
- Cobertura añadida para distancias/unidades/máscara, White Lines manual y automática con Simpson, controles habilitados según contenido, render HoloViews, orden `analysis → run → source`, limpieza y callbacks de publicación aditiva.
- Decisión explícita: cualquier enlace futuro desde Fitting hacia cuantificación deberá navegar/reutilizar la página `Quantification`; no se añadirá `EgertonQuantificationService` bajo `whateels.nlls`.

### T29 — Cierre de alcance funcional sin descargas

Estado: decisión de producto confirmada; no requiere cambios de código de exportación.

- Se retira del alcance la descarga NetCDF/CSV y cualquier serialización o botón de exportación nuevo para referencias, runs NLLS o análisis derivados. No se llegó a modificar ningún fichero para ese bloque.
- Se mantiene fuera de alcance el analizador Bethe/GOS independiente, de acuerdo con la arquitectura OOS-only de `NLLS_TODO.md`.
- Se mantiene fuera de Fitting la Egerton Quantification: la implementación existente en la página `Quantification` continúa siendo la única fuente de verdad.
- Con estas exclusiones, T25–T28 completan las fases funcionales restantes: visualización y filtros, rerun de modelo modificado, paralelización y herramientas derivadas Center/White Lines.
- Verificación final: 71 pruebas correctas mediante `unittest discover`; `compileall` y `git diff --check` correctos. La revisión de alcance no encuentra `FileDownload`/`InMemoryFile` nuevos en NLLS/Fitting ni símbolos de cuantificación Egerton duplicados.

### T30 — Corrección del overlay Area Boundaries

Estado: completada.

- El cálculo de fronteras era correcto, pero la tupla de segmentos con orientación por filas se entregaba directamente a `hv.Segments`. HoloViews interpreta una tupla como cuatro columnas (`x0`, `y0`, `x1`, `y1`), por lo que consumía las cuatro primeras filas como columnas deformadas y descartaba visualmente el resto.
- Los límites se convierten ahora de forma explícita a un array NumPy `(n_segmentos, 4)`. El botón `Area boundaries` añade y retira los dos trazos completos de cada frontera independientemente de `Area fill`.
- La misma corrección se aplica a los límites de los mapas derivados Center/White Lines.
- La regresión valida el número real de segmentos tanto en los elementos HoloViews como en los `GlyphRenderer` de Bokeh; ya no basta con comprobar que existía un objeto `Segments` vacío o mal orientado.

### T31 — Modal de filtros y geometría estable de plots aditivos

Estado: completada.

- Los controles de filtrado por `FitStatus`, χ² reducido máximo, error relativo máximo y escala logarítmica dejan de ocupar el bloque `Results > Elemental NLLS`. Un botón de ajustes junto a `Result map` abre el modal `Elemental NLLS result filters`.
- El modal monta los widgets reales del run seleccionado, sin copiar valores. Cambiar de run sustituye inmediatamente el conjunto montado y conserva el estado independiente de filtros de cada resultado.
- `Area label` se elimina de `Result map`, tanto de los mapas base como del descubrimiento automático de variables 2D y de su rama específica de render. `AreaLabel` se conserva exclusivamente como dato interno para el resumen de píxel y los overlays `Area fill`/`Area boundaries`.
- Los runs NLLS fijan altura mínima/máxima de 620 px y los análisis derivados 560 px; ambos se marcan como elementos flex no encogibles. Añadir nuevos resultados ya no comprime verticalmente plots anteriores ni reposiciona sus títulos/ejes.
- El stack reserva desde su creación el carril de la barra vertical mediante `overflow-y: scroll` y `scrollbar-gutter: stable`. La aparición del primer overflow deja de estrechar los plots responsive de Reference Fit y de runs existentes.
- La regresión renderiza primero el stack en Bokeh y después inserta dos análisis. Verifica que los objetos, títulos, escalas/opciones y geometría de Reference Fit y Run 1 permanecen intactos, además de comprobar el modal real registrado en Fitting.

### T32 — Controles de resultados derivados en modal

Estado: completada.

- Los bloques aditivos `Analysis N` y sus selectores `Derived result map` dejan de acumularse dentro del `SimpleDetails` de Elemental NLLS.
- Añadido el modal `Derived results control`, con scroll propio y los widgets reales de todos los plots derivados. Los selectores siguen actualizando inmediatamente el plot que los posee; no se duplica estado.
- Los controles para calcular Center Analysis y White Lines permanecen en el `SimpleDetails`. Tras publicar el primer resultado aparece un único botón `Derived results control`; al retirar el último resultado el botón se deshabilita y vuelve a ocultarse.
- El modal se registra en el `ModalManager` de Fitting, por lo que abrirlo oculta cualquier otro modal activo, incluido el modal de filtros del run.
- Cobertura de regresión para registro/apertura real, ausencia de selectores derivados en el `SimpleDetails`, montaje de los controles vivos, limpieza y estado visible/deshabilitado del botón.

### T33 — Contención real de mapas en el stack aditivo

Estado: completada.

- Corregido el bucle de tamaño observado en mapas altos: `SplitJs` ya no mide la altura de un hijo cuyo canvas Bokeh puede estar desbordado, sino la altura estable del viewport del split.
- Las dos columnas del split tienen `min-width/min-height: 0` y `overflow: hidden`; un canvas ya no puede agrandar el flex item que debe contenerlo.
- El mapa del run arranca dimensionado por altura y, al recibir el tamaño real del navegador, calcula un tamaño fijo que cabe simultáneamente en ancho y alto conservando `x/y`. Se fijan también mínimos y máximos para impedir que Bokeh reabra la caja.
- Los mapas derivados eligen `scale_height` para geometrías altas/cuadradas y `scale_width` para geometrías anchas. Título, ejes y barra de color permanecen dentro del mismo modelo Bokeh y de los bloques fijos de 560 px.
- La regresión usa mapas artificiales `3×20` y `20×2`, simula el mensaje de resize y comprueba dimensiones del `figure`, relación de aspecto, título y barra de color; no se limita a comprobar que el objeto Python no cambió.

### T34 — Retirada completa de Modified model / rerun

Estado: completada por decisión de producto. Esta tarea sustituye y deja sin efecto T26 y las referencias a rerun de T27/T29.

- Eliminados del sidebar el bloque `Modified model / rerun`, `Begin/Cancel Modified Model`, selección de áreas, `Lock All` y `Unlock All`.
- Eliminado del controlador todo el estado de borrador/padre, callbacks, rollback, rebuild por áreas modificadas, nombres de thread específicos y revalidación de parentesco. `Fit`/`Run Elemental NLLS` siempre congela una ejecución normal nueva.
- Eliminado `rerun_from` de `NLLSRunRequest`, junto con `PixelParameterSnapshot`, `pixel_parameter_snapshot()`, `NLLSResultsAccumulator.from_dataset()`, `prepare_rerun_area()` y el helper global de locks del workspace.
- `ElementalMultifitService` exige de nuevo una referencia vigente por área en toda ejecución. Serial y paralelo inicializan cada píxel desde una copia independiente de esa referencia y nunca reciben un dataset previo.
- Los datasets conservan un `run_id` único para el apilado y la procedencia de análisis derivados (`source_run_id` en el derivado), pero ya no publican `modified_areas`, `parent_run_id`, `run_kind` ni `run_version`. Las etiquetas de Results dejan de mostrar `first/modified vN`.
- `NLLS_TODO.md` se actualiza para que otro agente no vuelva a implementar la fase retirada: la Fase 6 documenta ahora explícitamente la ausencia de rerun y el carácter independiente/aditivo de ejecuciones sucesivas.
- Pruebas del flujo retirado sustituidas por regresiones de ausencia de controles/campos y por dos ejecuciones normales consecutivas con `run_id` distintos. Verificación actual: 71 pruebas correctas; la validación final de toda la suite se repite al cerrar esta tarea.

### T35 — Acceso a filtros integrado en Area overlay

Estado: completada.

- El acceso al modal de filtros deja de ser un icono estrecho situado junto a `Result map`.
- Se sustituye por un botón `Filters` de tipo visual `default`, colocado inmediatamente debajo de `Area fill / Area boundaries` y con `stretch_width`, por lo que ocupa el ancho combinado de ambos botones.
- El botón sigue montando los controles vivos del run seleccionado y abre el mismo modal `Elemental NLLS result filters`; sólo cambia su posición y presentación.
- La regresión comprueba el orden exacto `Result map → Run → Area overlay → botones de área → Filters → Curves`, su estilo y su actualización al cambiar de run.

### T36 — Toggles de área separados y Derived analyses en modal

Estado: completada.

- El antiguo `CheckButtonGroup` de área se sustituye por dos `Toggle` independientes, `Fill` y `Boundaries`. Cada uno conserva su estado propio y puede activar/desactivar únicamente su capa.
- Ambos toggles se presentan en una fila con separación real y altura fija de 32 px. El botón `Filters` adopta exactamente esa misma altura y continúa ocupando el ancho completo bajo la fila.
- Los formularios de Center Analysis y White Lines dejan de formar parte del contenido del `SimpleDetails`. Se montan como controles vivos en el nuevo modal `Derived analyses`, con scroll interno y cierre propio.
- Se añade un botón `Derived analyses` neutro y de ancho completo. Mide 42 px, igual que `Derived results control`; este último continúa abriendo el modal separado que gobierna los mapas derivados ya publicados.
- Los tres modales de resultados —filtros, cálculo derivado y control de resultados derivados— se registran en el mismo `ModalManager`, por lo que abrir uno cierra visualmente los otros.
- Cobertura de regresión para independencia/nombres de toggles, alturas, orden de montaje, ausencia del formulario derivado en el sidebar, contenido vivo del nuevo modal y exclusión mutua entre modales.

### T37 — Geometría aditiva aislada y Boundaries global

Estado: completada.

- El stack de Fitting adopta el patrón de actualización de Adv. Clustering: al publicar un resultado se reasigna una única vez el orden de hijos conservando los modelos Bokeh existentes, en vez de insertar sobre la columna ya renderizada.
- El plot fuente ocupa exactamente un viewport (`flex: 0 0 100%`) y deja de crecer cuando el stack cambia. Fuente, runs y derivados crean contextos de layout/pintado aislados y no pueden recalcular la geometría de sus hermanos.
- Los mapas derivados sustituyen el tamaño exterior `scale_height/scale_width` descrito en T33 por una caja estable `stretch_both`; `aspect="equal"` conserva la proporción dentro de esa caja. Así título, ejes, toolbar y colorbar permanecen dentro del bloque fijo de 560 px sin desplazar plots inferiores.
- `Boundaries` pasa a ser un estado compartido. Cambiarlo desde cualquier run se propaga a todos los runs, a todos los mapas derivados ya creados y a los que se publiquen después. `Fill` continúa siendo independiente por run.
- El mapa fuente de Current Clustering queda deliberadamente fuera de ese estado global: nunca dibuja boundaries. Al reconstruir datasets se limpia además la lista histórica de visualizadores del layout.
- La regresión renderiza el stack antes de añadir dos derivados y comprueba que los identificadores de los modelos Bokeh de Reference Fit y Run 1 permanecen idénticos, además de validar geometría fija, títulos, escalas y colorbars. Otra regresión cubre el ciclo global `Boundaries on → off → on`, incluida la herencia por un resultado derivado posterior.
- Verificación: 72 pruebas correctas, compilación en memoria de los seis módulos Python modificados y `git diff --check` correcto. `compileall` global no se fuerza porque tres `.pyc` preexistentes de `helpers/nlls_library/cross_sections/__pycache__` están bloqueados por otro proceso; no se borran ni se sobrescriben.

### T38 — Retirada de la tarjeta resumen del run

Estado: completada.

- Eliminada del `SimpleDetails` de Elemental NLLS la tarjeta informativa `Run N · processed/selected pixels · method=...`.
- Eliminadas también su construcción y su función de formateo; no queda un panel oculto ni lógica muerta asociada.
- Se conserva el resumen contextual del píxel seleccionado, que sí cambia con la interacción del mapa y sigue mostrando status, área y χ² reducido.
- Verificación: 15 regresiones específicas y suite completa de 72 pruebas correctas.

### T39 — Current Clustering siempre sin boundaries

Estado: completada.

- El plot fuente `Current Clustering` vuelve a ser siempre una única `hv.Image`, sin capas `Segments` ni lógica para reaccionar al toggle `Boundaries`.
- El toggle global conserva su alcance sobre los mapas de runs NLLS y los mapas derivados, pero nunca modifica el clustering usado como referencia.
- Verificación: 16 pruebas específicas de plots/controles y suite completa de 72 pruebas correctas.

### T40 — Aislamiento real del stack primario frente a derived analyses

Estado: sustituida por T41. Esta tarea identificó correctamente que conservar los modelos individuales no bastaba, pero el aislamiento en dos sub-stacks todavía dejaba `Elemental NLLS + Reference` bajo un mismo padre mutable y alteraba innecesariamente el tamaño original de Reference.

- El viewport aditivo contiene ahora dos sub-stacks hermanos: uno exclusivo para `Derived analyses` y otro exclusivo para `Elemental NLLS + Reference`.
- Publicar un derived sólo modifica la lista de hijos del sub-stack derivado. El sub-stack primario conserva simultáneamente su objeto padre, su lista de hijos y sus modelos Bokeh, por lo que sus ejes, títulos, escalas y colorbars no vuelven a entrar en el solver de layout.
- La caja fija de 620 px aplicada aquí a Reference se revierte en T41: Reference conserva su maquetación original ajustada al viewport.
- `SplitJs` memoriza su última geometría real. Un `ResizeObserver` despertado por el movimiento vertical del bloque no envía mensajes a Python ni dispara un `window.resize` global si ancho y alto no han cambiado al menos 0.5 px.
- La regresión renderiza el árbol completo antes de publicar dos derived analyses y comprueba que el sub-stack primario conserva exactamente los mismos hijos y el mismo modelo de layout, además de los modelos/opciones de cada plot.
- Verificación: 15 pruebas específicas de resultados y suite completa de 72 pruebas correctas.

### T41 — Árboles Bokeh persistentes y resize estrictamente local

Estado: completada. Corrige el desplazamiento residual de ejes/títulos y la desaparición del plot Elemental NLLS al interactuar después de publicar análisis derivados.

- El viewport mantiene desde su creación tres regiones hermanas permanentes: `Derived analyses`, runs `Elemental NLLS` y `Reference/source`. Publicar un derived sólo cambia los hijos del primer stack; publicar NLLS sólo cambia los del segundo; el wrapper de Reference nunca cambia de padre y recupera su `stretch_both` original, sin altura artificial de 620 px.
- Los stacks Derived y NLLS calculan una altura exterior exacta a partir de sus hijos fijos y márgenes. Vacíos quedan invisibles y a 0 px; con resultados son cajas flex no encogibles. El crecimiento se absorbe exclusivamente como scroll del viewport exterior.
- Los mapas y espectros de `NLLSMultifitResultsPlot` dejan de asignar un nuevo objeto a `HoloViews.pane.object` ante cada selector, filtro o tap. Ahora conservan un `hv.DynamicMap` estable y envían cada frame mediante `holoviews.streams.Pipe`; también se estabiliza la capa del marcador, incluso cuando el píxel queda filtrado.
- Los mapas de `NLLSDerivedResultsPlot` usan la misma actualización por `Pipe`. Sólo una transición estructural real de capas —por ejemplo activar/desactivar `Boundaries`— requiere construir un renderer distinto; cambiar el mapa derivado no reemplaza su figura.
- `SplitJs` deduplica notificaciones de `ResizeObserver` cuando las dimensiones reales no cambian y deja de emitir por completo `window.resize` sintéticos. Bokeh/Panel ya observan cada hijo local; el evento global hacía recalcular ejes, títulos y colorbars de todos los plots no relacionados cuando se añadía un resultado.
- La regresión renderiza el árbol antes de publicar dos derivados y comprueba identidad de los hijos exteriores, del sub-stack NLLS, de sus modelos de layout y de los modelos Bokeh de mapa, espectro y Reference. Otra regresión cambia `Result map` y selecciona un píxel después del render y exige que permanezcan idénticos tanto los panes como sus modelos Bokeh.
- Verificación: 16 regresiones específicas de resultados y suite completa de 73 pruebas correctas.

### T42 — Restauración de interacción en Reference Fit y Elemental NLLS

Estado: completada. La estabilidad geométrica de T41 no debe convertir los resultados en plots estáticos.

- El `Tap` de Elemental NLLS estaba enlazado a unos `Points` devueltos dentro de un `DynamicMap` alimentado por `Pipe`. HoloViews mostraba la herramienta, pero no registraba ningún callback Bokeh `tap`; llamar directamente al método Python ocultaba este fallo en las pruebas.
- `Tap` pasa a ser un stream de entrada del propio `DynamicMap`. Su callback devuelve el frame que incorpora el nuevo marcador sin reenviar recursivamente el mismo `Pipe`; el clic real actualiza píxel, resumen y espectro manteniendo el renderer estable.
- El spectrum pane compartido por Reference Fit conservaba siempre el `DynamicMap` inicial aunque los botones cambiasen el número o tipo de curvas. Bokeh no puede materializar renderers nuevos desde un overlay cuya estructura inicial era distinta.
- El `Pipe` base registra ahora una firma de renderer. Los cambios de datos con la misma composición actualizan en sitio; los cambios `Reference / Best fit / Components / Residual` reconstruyen atómicamente únicamente el renderer del espectro y vuelven a enlazar `RangeXY`.
- La regresión de Elemental exige que el figure Bokeh renderizado tenga un callback `tap` y emite el evento por el stream, sin invocar el handler directamente. La regresión de Reference renderiza primero el pane, comprueba reutilización con la misma firma y exige un renderer nuevo cuando se añade `Best fit`.
- Verificación: 16 regresiones específicas de resultados y suite completa de 73 pruebas correctas.

### T43 — Desplazamiento de ejes y colorbar al publicar análisis derivados

Estado: revertida como estrategia por T47 y cerrada definitivamente por T48. No debe recuperarse la recomposición forzada del layout de raíz.

- Diagnóstico. `LayoutDOMView.build_child_views()` hace que cada vista observe también el elemento de **cada uno de sus hijos**. Al publicar un bloque en el stack aditivo se redimensionan sus hermanos, de modo que la notificación llega primero a la vista **padre**; su `update_bbox()` refresca de forma silenciosa la caja cacheada de todos los descendientes y devuelve únicamente si cambió la caja *propia*. Como la del padre no cambia, no se llama a `compute_layout()`; y cuando después llega la notificación del propio plot, su bbox ya está actualizada, `update_bbox()` devuelve `false` y `after_resize()` tampoco ejecuta `compute_layout()`. El elemento queda con la geometría nueva mientras el canvas conserva la pintura resuelta para la anterior: ejes, títulos y barras de color dibujados fuera de su marco. `CanvasView.after_resize()` se auto-inhibe cuando el canvas pertenece a un plot, así que nada lo corrige por su cuenta.
- `SplitJs` recibe ahora `view` en su `render` ESM, sube hasta la raíz de layout de Bokeh y llama a `compute_layout()` sobre ella. Se dispara al entrar en el DOM, en cada notificación real del `ResizeObserver` —incluso cuando esta división conservó su caja exacta, que es justo el caso que Bokeh olvida— y ante un mensaje `relayout` enviado desde Python.
- `SplitJs.refresh_layout()` expone ese recálculo al servidor. `LayoutManager` lo invoca tras publicar un run o un análisis derivado sobre la división de cada run y sobre la del plot fuente, por lo que Reference Fit y todos los Elemental NLLS vuelven a resolver su layout en una única pasada. Es una operación idempotente: no hace nada en los plots ya consistentes.
- El orden de publicación se invierte: `_sync_isolated_stack_height` aplica la geometría final del sub-stack **antes** de montar el bloque. Antes se insertaba primero, por lo que las vistas Bokeh del bloque nuevo se construían dentro de un padre invisible o de altura cero y se medían como 0x0. El método acepta un parámetro `pending` para contabilizar el bloque que aún no está en `objects`.
- Se conserva la deduplicación de mensajes del `ResizeObserver`: seguir sin molestar a Python cuando la caja no cambia es correcto; lo que faltaba era recomponer el layout local de todos modos.
- Regresiones: una comprueba que al publicar un run y un derivado el sub-stack ya está visible y con su altura exacta en el instante del montaje, y que se pide recomposición a la división del run y a la del plot fuente; otra exige que el ESM de `SplitJs` recomponga desde la raíz y que `refresh_layout()` funcione tanto antes como después del render. Verificación: suite completa de 75 pruebas correctas y comprobación de que la nueva regresión falla con el orden y sin la recomposición anteriores.

### T44 — Píxeles cuadrados sin comprimir el título, la toolbar ni el colorbar

Estado: revertida como estrategia por T47 y T48. El seguimiento reactivo del tamaño del frame no forma parte de la solución estable.

- Diagnóstico. `aspect='equal'` + `responsive=True` hace que HoloViews escriba `plot.aspect_ratio = nx/ny` sobre la **caja exterior** de la figura Bokeh (`_update_layout` la emite como CSS `aspect-ratio` en `:host`), y esa caja también contiene el título, la toolbar y la barra de color. Lo que consumen se resta por tanto del marco de datos: la imagen sale estirada y cualquier cambio en la métrica de ese mobiliario —etiquetas del colorbar más largas, un título que envuelve— lo absorbe el marco y desplaza visiblemente el mapa. `match_aspect` de Bokeh no lo compensa: `RangeManager._update_dataranges` sólo reequilibra `DataRange1d` y HoloViews emite siempre `Range1d`, de modo que la propiedad quedaba activa pero inerte.
- Nuevo helper `whateels/helpers/square_pixels.py`. `square_pixel_limits()` calcula el `xlim`/`ylim` que dan píxeles exactamente cuadrados dentro de un marco conocido: reparte el excedente sobre el eje que tiene holgura y mantiene la imagen centrada, sin recortar nunca datos. `FrameSizeTracker` sigue el tamaño real del marco mediante `holoviews.streams.PlotSize`, que transporta `inner_width`/`inner_height`, es decir lo que Bokeh concedió *después* de repartir el mobiliario.
- Los mapas de `NLLSMultifitResultsPlot` y `NLLSDerivedResultsPlot` dejan de usar `aspect="equal"`. Su figura pasa a ser `stretch_both` sin `aspect_ratio`, así que el título, la toolbar y la barra de color reciben siempre su espacio medido y no pueden ser desplazados; los píxeles cuadrados salen del rebajado de rangos. Como cambiar rangos no cambia el tamaño del marco —ambos mapas ocultan sus ejes—, la reacción no se realimenta: reenviar el mismo tamaño no reconstruye el renderer.
- `clear_outer_aspect()` retira el `aspect_ratio` que HoloViews escribe únicamente en el primer dibujo, necesario porque la figura nace antes del primer informe de tamaño del navegador.
- `SplitJs` deja de forzar la caja de un pane que no declara `_splitjs_xy_ratio`. El mapa del run NLLS ya no lo declara, por lo que la división no vuelve a fijarle `sizing_mode='fixed'` con una caja de proporción de datos. El plot fuente lo conserva: su imagen integrada no lleva colorbar ni título, así que su caja exterior coincide con su marco y la proporción exterior sigue siendo correcta ahí.
- Alcance deliberado. No se tocan `plot_image`, `plot_energy_map` ni el mapa de `Current Clustering` de `paneA`, ni las páginas Home/Clustering/Demo, que comparten `BaseSpectrumImagePlot`. El defecto sólo se manifiesta cuando la figura lleva mobiliario dentro de la caja con proporción fijada; extenderlo a `paneA` exige además decidir su interacción dinámica con `SplitJs` en los estados con colorbar.
- Regresiones: la de mapas altos/anchos exige ahora caja exterior responsive sin `aspect_ratio`, colorbar presente en el panel derecho, y píxeles cuadrados con delta 0.01 para run tall, derivado tall y derivado wide tras informar un marco de 400x300, comprobando además que el rebajado nunca recorta el extremo de los datos. Otra prueba unitaria cubre `square_pixel_limits` (marco desconocido, marco más ancho, marco más alto, marco ya proporcionado). Verificado también que la inversión del eje Y se conserva y que repetir el mismo tamaño no reconstruye el renderer. Suite completa: 76 pruebas correctas.

### T45 — Píxeles cuadrados también en el plot fuente (paneA)

Estado: revertida como estrategia por T47 y T48. Se conservan únicamente puntos de extensión inocuos de la clase base; no se usa el seguimiento reactivo de T44/T45.

- `paneA` no es siempre una imagen desnuda: `Energy Map` y `Current Clustering` añaden título y barra de color. En esos estados `aspect='equal'` sobre la caja exterior restaba su espacio al marco de datos exactamente igual que en los mapas de resultados. La imagen integrada, en cambio, no lleva ninguno de los dos: ahí caja exterior y marco coinciden y fijar la caja es correcto.
- `BaseSpectrumImagePlot` gana dos puntos de extensión y ninguna otra página cambia de comportamiento: `_paneA_aspect_options(nx, ny)`, que por defecto devuelve `{'aspect': 'equal'}`, y `_SPLITJS_SIZES_PANEA`, que por defecto sigue siendo `True`. `_setup_plots` y `_update_selection_overlay` pasan a construir sus opciones a través de ellos en vez de repetir literales, y se guarda `self._ny` junto al `self._nx` que ya existía.
- `SpectrumImageVisualizer` de Fitting declara `_SPLITJS_SIZES_PANEA = False` y sobrescribe `_paneA_aspect_options` para rebajar rangos con `square_pixel_limits`. Al no declarar `_splitjs_xy_ratio`, la división deja de fijarle `sizing_mode='fixed'`: `paneA` conserva una caja responsive en los tres estados, sin alternancia dinámica que mantener.
- Los tres estados se re-rebajan cuando el navegador informa un marco nuevo. La imagen integrada y el mapa de energía reutilizan `_update_selection_overlay`; el mapa de clustering se guarda sin límites y se reaplica clonado, porque devolver el mismo objeto al pane no lo volvería a renderizar.
- Verificación medida sobre el modelo Bokeh renderizado: en los tres estados `aspect_ratio` es `None`, `sizing_mode` es `stretch_both`, el píxel es cuadrado con delta 0.01 tras informar un marco de 400x300, se conserva la inversión del eje Y y la barra de color aparece en el panel derecho en los dos estados que la llevan. Repetir el mismo tamaño no reconstruye el renderer. Comprobado además que `BaseSpectrumImagePlot` sigue produciendo `_splitjs_xy_ratio=1.5`, `aspect_ratio=1.5` y `scale_height`, es decir que Home, Clustering y Demo quedan intactas.
- Regresiones nuevas: una recorre los tres estados de `paneA` y exige lo anterior; otra fija los valores por defecto de la clase base frente al opt-out de Fitting. Comprobado que la primera falla al restaurar el comportamiento previo. Suite completa: 78 pruebas correctas.

### T46 — paneA en blanco tras el rebajado de rangos

Estado: revertida junto con T45. T48 mantiene el comportamiento compartido y estable de `paneA` sin recuperar el rebajado de rangos.

- Síntoma: la mitad izquierda del plot fuente aparecía vacía, sólo con su toolbar.
- Causa: `BaseSpectrumImagePlot` crea `paneA` con `styles={'margin': 'auto'}`, un estilo pensado para la caja **encogida por proporción** que `SplitJs` le imponía (`scale_height` + `aspect_ratio`), donde servía para centrarla. Al pasar `paneA` a rebajar rangos con caja `stretch_both`, ese `margin: auto` deja de tener sentido y, al ser una regla *inline*, gana sobre el `margin` que Bokeh calcula para la caja en `:host`.
- El visualizador de Fitting normaliza ahora `paneA` tras `super().__init__` a exactamente la misma geometría que `paneB`, que renderiza correctamente: `sizing_mode='stretch_both'` y `styles={'min-width': '0', 'min-height': '0'}`, sin `margin`. Los cuatro panes de mapa —`paneA`, mapa de run, mapa derivado— y `paneB` comparten desde ahora la misma caja, verificado sobre el modelo Bokeh embebido.
- Las demás páginas no cambian: la base conserva `margin: auto` junto a `scale_height`, que es la combinación coherente mientras `SplitJs` sí dimensiona el pane.
- La regresión de los tres estados de `paneA` exige además `stretch_both` y ausencia de `margin` en sus estilos. Suite completa: 78 pruebas correctas.

### T47 — Geometría estática al publicar, siguiendo Adv. Clustering

Estado: revertida por T48. Esta revisión introdujo el solapamiento severo de plots al asumir incorrectamente que Panel/Bokeh reservaría mediante CSS la suma vertical de hijos con altura fija.

- Diagnóstico corregido. La comparación con Adv. Clustering, que es estable, muestra la diferencia real: allí publicar un bloque **no escribe geometría en absoluto**. El controlador mete el plot en un wrapper permanente y reordena la columna con `move_to_top`; los wrappers tienen su tamaño en CSS (`width: 100%`, `aspect-ratio: 1`) y las figuras son `responsive=True` sin `aspect` ni tamaño fijo. Fitting, en cambio, escribía en cada publicación `visible`, `height`, `min_height`, `max_height` y `styles` sobre la sub-pila: las cuatro primeras disparan cada una un `invalidate_layout()` que llega hasta la raíz del documento y obliga a **re-resolver el layout de todos los plots**; la quinta cambia la caja sin invalidar nada. Eso, no un canvas obsoleto, es lo que movía ejes y colorbars.
- Retirado `_sync_isolated_stack_height` por completo, junto con `_vertical_margin`. Las sub-pilas `Derived` y `Elemental NLLS` pasan a dimensionarse por CSS a partir de sus hijos, que ya llevan altura fija propia (620 px y 560 px): vacías miden 0 px y con resultados miden exactamente lo que suman, sin altura en Python, sin alternar `visible` y sin reescribir `styles`.
- Retirada la recomposición forzada de T43: `refresh_layout()` en `SplitJs`, el mensaje `relayout`, el paseo hasta la raíz de layout en el ESM y las llamadas del `LayoutManager`. Adv. Clustering no necesita ninguna porque allí nada se redimensiona al publicar; forzar un `compute_layout()` de raíz sólo añadía otra pasada de layout al momento exacto en que el usuario ve el salto.
- Retirado el rebajado de rangos por `PlotSize` de T44/T45 y el módulo `whateels/helpers/square_pixels.py`. Reaccionar desde Python al tamaño del marco volvía a renderizar el pane en cada evento de tamaño, es decir añadía movimiento en vez de quitarlo.
- Los mapas de run y derivados quedan como los de Adv. Clustering: `responsive=True`, sin `aspect`, sin `aspect_ratio` y sin tamaño fijo, llenando su bloque. Bokeh reparte siempre título, toolbar y colorbar en sus propios paneles medidos, y la geometría del bloque es función pura de una caja que publicar no altera. `SplitJs` tampoco los toca, porque no declaran `_splitjs_xy_ratio`.
- `paneA` vuelve exactamente a su comportamiento compartido con Home, Clustering y Demo: `_splitjs_xy_ratio`, `aspect='equal'` y dimensionado por `SplitJs`. Se conservan en la clase base los puntos de extensión `_paneA_aspect_options`/`_paneA_overlay_options` y `self._ny`, con los valores por defecto de siempre, verificados idénticos.
- Corregido además el `TypeError: FrameSizeTracker._handle() got an unexpected keyword argument 'scale'` que aparecía en consola; el código que lo provocaba ya no existe.
- Coste asumido y consciente: los mapas de resultados se estiran hasta su bloque en vez de conservar píxeles exactamente cuadrados, igual que el mapa HDBSCAN de Adv. Clustering. Se prioriza la estabilidad, que es lo reportado.
- Verificación: publicar un run y dos análisis derivados produce **cero** escrituras de geometría sobre las sub-pilas y sobre la pila exterior, medido observando `height`, `min_height`, `max_height`, `width`, `visible`, `styles` y `sizing_mode`. Suite completa: 72 pruebas correctas.

### T48 — Recuperación de la geometría estable de resultados aditivos

Estado: completada para el aislamiento y las alturas de los stacks. La geometría interna de mapas restaurada inicialmente desde T42 queda corregida y sustituida por T49.

- Causa confirmada del caos visual: los `pn.Column` interiores de `Derived analyses` y `Elemental NLLS` tenían `height/min_height/max_height=None`. El modelo padre de Panel/Bokeh no reserva de forma fiable la suma vertical de sus hijos fijos; los canvas de 560/620 px desbordaban una región exterior sin altura y se pintaban sobre Reference, otros mapas, ejes y colorbars.
- Restaurada `_sync_isolated_stack_height()`: cada sub-stack reserva exactamente la altura de sus hijos más sus márgenes (`632 px` por run y `572 px` por análisis derivado), queda como caja flex no encogible y vuelve a `0 px`/invisible al vaciarse. El viewport exterior sigue siendo el único elemento con scroll.
- Se mantienen las tres regiones hermanas permanentes de T41: `Derived analyses`, `Elemental NLLS` y `Reference/source`. Publicar derivados sólo cambia el primer árbol; añadir NLLS sólo cambia el segundo; Reference no cambia de padre ni se sustituye.
- La primera versión de T48 restauró la relación espacial de `SplitJs` y `aspect='equal'` en mapas NLLS/derived. La captura real posterior demostró que esta parte seguía comprimiendo o recortando título, toolbar y colorbar; T49 la revierte de forma selectiva sin retirar las alturas exactas de los stacks.
- Se conservan intactos el resize local y deduplicado de `SplitJs`, los `Pipe`/`DynamicMap` persistentes, el `Tap` como entrada real del mapa NLLS y la reconstrucción por firma estructural de Reference Fit. No se recuperan `compute_layout()` global, mensajes sintéticos de resize ni seguimiento reactivo de frames de T43–T46.
- Regresiones actualizadas: verifican alturas exactas y estado vacío, identidad de árboles/modelos Bokeh al publicar dos derivados, contención de mapas altos/anchos, colorbar/títulos y, tras publicar derivados, cambio de `Result map` y clic real sobre NLLS sin perder el espectro.
- Verificación: 15 pruebas específicas de resultados y suite completa de 72 pruebas correctas.

### T49 — Eje de energía y colorbar realmente visibles

Estado: completada. Corrige el clipping interno que las pruebas de identidad de modelos de T48 no detectaban.

- Evidencia visual: el eje `Energy loss (eV)` visible arriba pertenecía al bloque anterior; el espectro actual no mostraba su eje inferior. En `paneA` aparecían los ticks categóricos, pero la barra de color estaba recortada. Los modelos Bokeh conservaban tanto `LinearAxis` como `ColorBar`, por lo que no era un fallo de construcción del plot sino de geometría CSS/DOM.
- Eliminadas las pinzas acumuladas: `SplitJs` recupera `overflow: auto` vertical y sólo oculta el overflow horizontal durante el drag; deja de escribir `overflow:hidden` directamente sobre el pane izquierdo. El wrapper fuente conserva `contain: layout` para aislar el layout, pero ya no usa `contain: layout paint` ni recorta la pintura de los paneles Bokeh.
- `paneA` de Fitting deja de imponer la relación cruda `nx/ny` sobre la caja exterior cuando puede contener título y colorbar. Usa `stretch_both`, sin `margin:auto`, sin min/max fijos y sin `_splitjs_xy_ratio`. Esto es específico de Fitting; las demás páginas conservan el comportamiento de la clase base.
- Los mapas de runs NLLS y análisis derivados usan también una caja exterior `stretch_both` sin `aspect='equal'`. La proporción de datos ya no comprime el mobiliario del plot; título, toolbar y colorbar reciben espacio dentro del bloque fijo de 620/560 px.
- Corregido el orden de montaje: `_sync_isolated_stack_height(..., pending=view)` reserva los 632/572 px finales antes de insertar el hijo. Ningún renderer nuevo nace dentro de un padre invisible de 0 px. Se mantienen las alturas exactas de T48 y los tres árboles persistentes de T41.
- Regresiones: comprueban que la geometría final existe antes del mount, que Fitting no hereda ratio/margen/clipping, que `ColorBar` está visible en el panel derecho, que el eje de energía está visible en `below`, y que `SplitJs` no vuelve a ocultar el mobiliario vertical.
- Verificación visual en navegador sobre un stack con Reference Fit, un run NLLS y dos derived: colorbar completo junto al mapa y eje `Energy loss (eV)` bajo el espectro, ambos dentro de sus paneles. Verificación automatizada: 17 pruebas focalizadas y suite completa de 73 pruebas correctas.

### T50 — Publicación dinámica append-only sin desplazar plots existentes

Estado: completada. Sustituye la arquitectura de sub-stacks de T48/T49; se conservan sus correcciones de clipping, `Pipe`/`DynamicMap`, interacción y tamaño fijo de cada bloque individual.

- La captura dinámica real demostró que el estado final correcto de T49 no bastaba: al publicar cada derived, `_sync_isolated_stack_height()` todavía escribía `visible`, `height`, `min_height`, `max_height` y `styles`, y después se anteponía el hijo. Panel/Bokeh invalidaba repetidamente la raíz y volvía a montar o recolocar canvas ya renderizados; de ahí el salto del eje de energía de paneB y del colorbar de paneA.
- Eliminados los sub-stacks `Derived`/`NLLS`, `_sync_isolated_stack_height()`, `_vertical_margin()` y la recomposición por prepend. Source, cada run NLLS y cada derived son ahora hijos directos de una única columna de scroll.
- La lista física de hijos es estrictamente append-only. El nuevo plot se añade al final, por lo que los modelos y nodos DOM anteriores permanecen como prefijo idéntico. El orden visual se obtiene sin moverlos mediante `order` CSS: derived nuevos, derived anteriores, runs nuevos, runs anteriores y source.
- `_StableAdditiveColumn` impide que la inferencia interna de Panel sume los hijos fijos en `min_height` y convierta el viewport en una caja creciente. El viewport conserva `stretch_both`, `min_height=0`, scrollbar estable y `overflow-anchor: none`; el contenido aditivo se resuelve exclusivamente con scroll.
- El estado global de `Boundaries` se aplica antes de montar el nuevo plot. El modal oculto `Derived results control` ya no reconstruye sus hijos durante la publicación: se rellena sólo al abrirlo. Su botón permanece maquetado y pasa de deshabilitado a habilitado sin cambiar la geometría del sidebar.
- Regresión documental: tras renderizar Source + Run 1 y añadir dos derived, la raíz emite únicamente dos cambios `children`; no cambia `height`, `min_height`, `max_height`, `styles`, `visible` ni `sizing_mode`. El prefijo de hijos Bokeh y los modelos de mapa, espectro y Reference siguen siendo exactamente los mismos; los controles continúan respondiendo después.
- Verificación dinámica en Chromium/Edge: capturas del mismo Run antes, después de un derived y después de dos derived, compensando únicamente el nuevo scroll. En la región de plots sólo variaron 30 píxeles de antialiasing; eje de energía, títulos, frames y colorbar permanecieron en las mismas coordenadas. Verificación automatizada: 16 regresiones focalizadas y suite completa de 73 pruebas correctas.

### T51 — Eliminación del reparentado DOM que desplazaba ejes y colorbars

Estado: completada. Sustituye la parte interna de T50 que todavía mantenía `SplitJs` en los plots de Fitting; el stack físico continúa siendo append-only.

- La reproducción con la página real —`FastListTemplate`, pestañas, sidebar, viewport con scroll, Reference Fit, Elemental NLLS y publicaciones derivadas sucesivas— confirmó que el problema no estaba en los datos ni en la construcción de los ejes. Al añadir un derived, Panel/Bokeh invalida el layout de la raíz aunque sólo cambie la lista `children` del stack.
- La causa decisiva era `SplitJs`: después de que Panel/Bokeh creara sus vistas, el componente movía manualmente los nodos DOM de `paneA` y `paneB` dentro de contenedores propios. Bokeh seguía calculando la geometría con su jerarquía original, mientras el navegador pintaba otra jerarquía. Una invalidación posterior separaba visualmente el canvas de sus paneles laterales/inferiores: colorbar, título y eje de energía parecían desplazarse o desaparecer.
- Los plots fuente/Reference y cada resultado Elemental NLLS usan ahora una `pn.Row` nativa con dos columnas `stretch_both` y un separador gris fijo de 10 px. Todo el plot permanece dentro del árbol de layout que conoce Bokeh; el separador conserva la maquetación 50/50, pero deja de ser arrastrable para eliminar el reparentado no determinista.
- No se modifica `SplitJs` globalmente: otras páginas que lo usan conservan su contrato. La sustitución se limita a Fitting, que es donde conviven los plots dinámicos y el stack aditivo.
- Se mantiene la publicación física append-only y el orden visual mediante CSS de T50. Los plots existentes no se reemplazan, sus `DynamicMap`, `Pipe`, `Tap`, suscriptores y modelos Bokeh conservan identidad, y Reference/NLLS siguen reaccionando a clics después de añadir uno, dos y tres resultados derivados.
- Verificación visual real en Edge tras dos publicaciones derivadas y desplazamiento del viewport: el colorbar queda completo a la derecha del mapa; título, eje Y, ticks, eje X y `Energy loss (eV)` quedan dentro del espectro. Verificación automatizada: 17 regresiones focalizadas de resultados, 12 de Fitting manual y suite completa de 74 pruebas correctas.

### T52 — Ratio espacial conservado sin volver a fijar la caja exterior

Estado: completada. Complementa T51: los layouts nativos permanecen estables y los mapas recuperan píxeles X/Y cuadrados.

- No se recupera `aspect='equal'` ni `data_aspect=1`. En HoloViews 1.20.2 ambas opciones convierten la figura responsive en `scale_both` y aplican `aspect_ratio` a la caja Bokeh completa, incluida la reserva de título, toolbar, ejes y colorbar; eso reintroduciría el defecto corregido en T51.
- Añadido `square_pixel_plot_hook()`. Mantiene la figura exterior en `stretch_both` y `aspect_ratio=None`, pero sustituye una sola vez los `Range1d` espaciales por `DataRange1d` y activa `match_aspect` con escala 1:1. Bokeh calcula el letterboxing dentro del frame real, después de descontar todo el mobiliario del plot.
- El hook se aplica al mapa integrado, `Energy Map`, `Current Clustering`, mapas Elemental NLLS y mapas derived. Los espectros no lo usan. Para mapas cuyo ratio difiere de su hueco aparecen bandas blancas centradas; no hay deformación de píxeles ni compresión de paneles laterales/inferiores.
- `BoxZoomTool` conserva el aspecto y `WheelZoomTool` actúa sobre ambos ejes. Los clics sobre bandas de letterboxing se rechazan antes de redondear coordenadas, evitando que seleccionen falsamente un píxel del borde.
- Verificación real en Edge: en un clustering `46×80`, un run `3×2` y derived `2×2`, se cumple `x_span / y_span = inner_width / inner_height`; los mapas quedan centrados con unidades cuadradas. Tras publicar dos derived siguen visibles y alineados los títulos, ejes de energía y colorbars de los plots inferiores.
- La regresión exige ahora `DataRange1d` en ambos ejes, Y invertido, padding cero, `match_aspect=True`, caja `stretch_both`, ausencia de `aspect_ratio`, colorbar intacto y rechazo de taps fuera del mapa. Suite completa: 74 pruebas correctas.

### T53 — Topología estable y ratio verificado en Current Clustering

Estado: completada. Endurece el único mapa espacial de Fitting que todavía sustituía la raíz montada por un tipo diferente.

- `Current Clustering` deja de montar un `hv.Image` directo y usa un `hv.Overlay` de una sola imagen, igual que el mapa integrado, los mapas Elemental NLLS y los resultados derived. El hook `square_pixel_plot_hook` vive en esa raíz estable.
- El overlay contiene exactamente una imagen categórica: no incorpora `Segments` ni boundaries, de acuerdo con la decisión de que el clustering de referencia nunca muestre fronteras NLLS.
- No se fija la relación `nx/ny` en la caja exterior. La caja sigue siendo `stretch_both` para que título, toolbar y colorbar tengan espacio propio; el ratio se conserva en el raster mediante `DataRange1d`, `match_aspect=True` y letterboxing interno.
- Medición sobre el caso real mostrado: SI `96×141`, ratio esperado `96/141 = 0.68085`; región coloreada aproximada `577×847`, ratio observado `0.68123`. La diferencia relativa es inferior a 0.1 %, por lo que el raster ya conserva el ratio y la apariencia distinta corresponde únicamente a la caja responsive exterior.
- La regresión inspecciona ahora el modelo Bokeh ya montado antes del cambio dinámico, no una raíz nueva creada después. Comprueba raíz `Overlay`, una única imagen, matriz sin transposición, bounds espaciales exactos, ausencia de boundaries, `DataRange1d`, Y invertido, colorbar visible y `match_aspect` activo.
- Verificación: prueba focalizada correcta y suite completa de 74 pruebas correctas.

### T54 — Divisor arrastrable recuperado sin reparentado DOM

Estado: completada. Devuelve a Fitting la única capacidad que se perdió en T51 —mover la frontera entre mapa y espectro— sin recuperar el mecanismo que la hacía inestable.

- Precisión sobre la causa. Lo que rompía ejes y colorbars no era que el `paneA` de Fitting fuese complejo, sino que `SplitJs` saca los nodos DOM de sus dos paneles del árbol que Bokeh maqueta: `model.get_child()` seguido de `container.appendChild()`. Eso ocurre igual con una imagen desnuda; en Adv. Clustering no se nota porque allí nada invalida la raíz, mientras que en Fitting el stack aditivo la invalida en cada publicación. Restringir `SplitJs` al bloque fuente habría retirado el disparador, no la causa.
- Nuevo componente `DragGutter` (`whateels/components/drag_gutter.py`). No declara ningún parámetro `Child`, así que estructuralmente no puede llegar a ser el padre de un panel: dibuja únicamente la barra separadora. Los dos paneles siguen siendo hijos directos de la `pn.Row` nativa introducida en T51.
- El arrastre se resuelve entero en el navegador. `pointermove` escribe `flex` en línea sobre los dos hermanos y nada más: no hay `send_msg`, ni `ResizeObserver`, ni `window.dispatchEvent`, ni escritura de geometría desde Python. Publicar un run o un análisis derivado sigue costando exactamente lo mismo que antes.
- Se usa `flex-grow` proporcional sobre base cero en vez de porcentajes o píxeles, de modo que la proporción arrastrada se conserva al redimensionar la ventana sin volver a medir nada. La declaración en línea gana sobre la regla `:host` que `FlexBoxView._update_layout()` escribe en el `parent_style` de cada panel (`flex: 1 0 0px` para `stretch_both`), por lo que Bokeh puede recomponer su layout sin deshacer el arrastre. Doble clic retira las declaraciones y devuelve el reparto original.
- La fila y sus dos paneles se localizan por clases marcadoras (`whateels-split-row`, `whateels-split-pane`). Panel monta cada hijo de layout dentro de su propio shadow root, así que ni `closest()` ni una consulta a nivel de documento llegan a la fila: el recorrido sale de cada shadow root por su `host`. Si la búsqueda falla, el separador simplemente no arrastra; nada se rompe.
- El elemento interno se llama `whateels-drag-gutter` y no `drag-gutter`: Panel ya bautiza su propio contenedor con el nombre de la clase Python convertido a kebab-case, y ese contenedor es el que recibe la caja de 10 px × 100 % de `set_size()`.
- Alcance: las dos filas de dos paneles que existen en Fitting, es decir el bloque fuente/Reference (`SpectrumImageVisualizer.create_plots`) y cada run de `NLLSMultifitResultsPlot`. Los análisis derivados no entran porque su bloque es un único mapa sin espectro. `SplitJs` no se toca: Home, Clustering, Demo, Multifitting y Quantification mantienen su contrato intacto.
- Cada run monta su propia fila marcada y su propio `DragGutter`. La resolución sube al ancestro `.whateels-split-row` más cercano y busca los paneles dentro de esa fila, de modo que en un stack de varios runs ningún separador alcanza los paneles de otro run ni los del plot fuente.
- Regresiones: la del panel fuente y la de los bloques de run exigen `DragGutter` en la fila, clases marcadoras en fila y paneles, `min-width: 0` en ambos y ausencia de `SplitJs`; la de publicación de dos runs comprueba que cada uno tiene un gutter distinto y su fila marcada; una nueva prueba focalizada prohíbe en el ESM `get_child`, `appendChild`, `removeChild`, `insertBefore`, `send_msg`, `dispatchEvent` y `ResizeObserver`, exige el recorrido por `host` y comprueba sobre el modelo renderizado que `min_pane_size` viaja en el modelo `data` que lee el proxy ESM.
- Verificación: suite completa de 75 pruebas correctas. Falta la comprobación visual del arrastre en navegador, que corresponde ejecutar en la aplicación real.
