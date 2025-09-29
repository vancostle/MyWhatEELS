import numpy as np
import plotly.graph_objs as go
import os

def multifit_modified(data, model, Eloss_x=None):
    """
    data: 3D numpy array (dimx, dimy, spectrum_length) representing EEL spectra
    model: class fitting model available in lmfit.models or similar
    Eloss_x: optional 1D energy-loss axis array. If None, tries data.Eloss_x.
    """
    results = []
    # Assume data is a 3D numpy array: (dimx, dimy, spectrum_length)
    dimx, dimy, spectrum_length = data.shape

    # Determine energy loss axis
    if Eloss_x is None:
        try:
            Eloss_x = data.Eloss_x  # Custom attribute if set
        except AttributeError:
            raise ValueError("Please provide the energy loss axis (Eloss_x) as a separate argument or attribute.")

    progress_newModels = 0
    for x_i in range(dimx):
        for y_i in range(dimy):
            data_y = data[x_i, y_i, :]
            pars = model.guess(data_y, x=Eloss_x)
            res = model.fit(data=data_y, params=pars, x=Eloss_x)
            progress_newModels += 1
            results.append(res)
            if progress_newModels % 1000 == 0:
                print(progress_newModels)
    return results

def create_data_from_multifit(results, original_data):
    """
    Create a 3D numpy array from multifit results.
    
    Parameters:
    - results: List of fit result objects from multifit_modified.
    - original_data: Original 3D numpy array (dimx, dimy, spectrum_length).
    
    Returns:
    - fitted_data: 3D numpy array with fitted spectra.
    """
    dimx, dimy, spectrum_length = original_data.shape
    fitted_data = np.zeros((dimx, dimy, spectrum_length))
    
    index = 0
    for x_i in range(dimx):
        for y_i in range(dimy):
            fitted_data[x_i, y_i, :] = results[index].best_fit
            index += 1
            
    return fitted_data

def save_fitted_data(fitted_data, folder=None, filename='fitted_data'):
    """
    Guarda fitted_data como un objeto numpy en un directorio 'temp_data'.

    Parámetros:
    - fitted_data: array numpy 3D devuelto por create_data_from_multifit.
    - folder: ruta opcional donde crear 'temp_data'. Si es None, se crea junto a este archivo.
    - filename: nombre base del fichero (sin extensión). Por defecto 'fitted_data'.

    Resultado:
    - ruta del fichero creado (incluye .npy).
    """
    # Determinar carpeta base
    base_dir = folder if folder is not None else os.path.join(os.path.dirname(__file__), 'temp_data')
    # Crear carpeta si no existe
    os.makedirs(base_dir, exist_ok=True)
    # np.save añadirá .npy si no se incluye extensión
    save_path = os.path.join(base_dir, filename)
    np.save(save_path, fitted_data)
    # Devolver la ruta final (con extensión .npy)
    final_path = save_path + '.npy' if not save_path.endswith('.npy') else save_path
    return final_path

# # save the results to a file using pickle with 'wb' mode aka 'write binary' because the data is not text neither images
# with open(folder_params +'multifit_params_DNW_topinbetween.pkl', 'wb') as f:
#     pickle.dump(resultaditos, f)
    
# # load the saved results from file with 'rb' mode aka 'read binary'
# with open(folder_params +'multifit_params_DNW_topinbetween.pkl', 'rb') as f:
#     resultaditos_readen = pickle.load(f)

# m_tallat_fit = m_tallat.deepcopy()
# contador = 0
# for i in range(m_tallat_fit.data.shape[0]):
#     for j in range(m_tallat_fit.data.shape[1]):
#         m_tallat_fit.data[i][j] = resultaditos[contador].best_fit
#         contador += 1

# resultaditos[0].values

# m_tallat_extrapolated = m.deepcopy()
# contador = 0

# def powerlaw(x, A, k):
#     return A*x**k

# for i in range(m_tallat_extrapolated.data.shape[0]):
#     for j in range(m_tallat_extrapolated.data.shape[1]):
#         A = resultaditos[contador].params
#         m_tallat_extrapolated.data[i][j] = powerlaw(m_tallat_extrapolated.axes_manager[-1].axis, \
#                                                     resultaditos[contador].values['amplitude'],\
#                                                     resultaditos[contador].values['exponent'])
#         contador += 1

# Añadir clase envoltorio para crear/ejecutar/guardar un objeto multifit
class MultiFit:
    """
    Wrapper object to run multifit, access results and save fitted_data.
    Uso:
      mf = MultiFit(data, model, Eloss_x=eloss)
      mf.run()
      fitted = mf.get_fitted_data()
      mf.save()  # guarda en temp_data/fitted_data.npy por defecto
    """
    def __init__(self, data, model, Eloss_x=None, save_folder=None, filename='fitted_data'):
        self.data = data
        self.model = model
        self.Eloss_x = Eloss_x
        self.save_folder = save_folder
        self.filename = filename
        self.results = None
        self.fitted_data = None

    def run(self):
        """Ejecuta el multifit y genera fitted_data."""
        self.results = multifit_modified(self.data, self.model, Eloss_x=self.Eloss_x)
        self.fitted_data = create_data_from_multifit(self.results, self.data)
        return self

    def get_fitted_data(self):
        return self.fitted_data

    def get_results(self):
        return self.results

    def save(self, folder=None, filename=None):
        """Guarda fitted_data usando save_fitted_data. Devuelve la ruta al fichero .npy."""
        if self.fitted_data is None:
            raise RuntimeError("No fitted_data available. Call run() first.")
        folder_to_use = folder if folder is not None else self.save_folder
        filename_to_use = filename if filename is not None else self.filename
        return save_fitted_data(self.fitted_data, folder=folder_to_use, filename=filename_to_use)

    def summary(self):
        """Resumen básico del objeto multifit."""
        n_res = len(self.results) if self.results is not None else 0
        try:
            dimx, dimy, _ = self.data.shape
        except Exception:
            dimx = dimy = None
        return {"dimx": dimx, "dimy": dimy, "n_results": n_res}