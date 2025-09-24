import numpy as np
import plotly.graph_objs as go

def multifit_modified(data, model):
    """
    data: 3D numpy array (dimx, dimy, spectrum_length) representing EEL spectra
    model: class fitting model available in lmfit.models or similar
    """
    results = []
    # Assume data is a 3D numpy array: (dimx, dimy, spectrum_length)
    dimx, dimy, spectrum_length = data.shape
    # Assume energy loss axis is the same for all spectra and is provided separately
    # You may need to pass Eloss_x as an argument if not globally available
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