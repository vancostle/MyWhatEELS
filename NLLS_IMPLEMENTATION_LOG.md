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
