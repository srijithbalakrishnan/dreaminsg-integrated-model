import matlab.engine
import numpy as np
import time
from mat4py import loadmat

def dta_matlab_model(transp_folder):
    """Runs the MATLAB dynamic traffic assignment model. Refer to `Dr. Ke Han's GitHub page <https://github.com/DrKeHan/DTA>`_ for documentation of the model.

    Arguments:
        transp_folder {string} -- The local directory in which therequired MATLAB files are stored.
    """
    eng = matlab.engine.start_matlab('-nojvm')
    eng.cd(transp_folder)
    #print("Successfully set current working directory to {}".format(transp_folder))
    start = time.time()
    eng.PROCESS_OD_INFO(nargout=0)
    eng.MAIN(nargout=0)
    eng.quit()
    end = time.time()
    print("Successfully completed running the dynamic traffic assignment model in {} s.".format(round(end-start, 2)))

def read_mat_file(mat_file):
    """Reads the .mat file.

    Arguments:
        mat_file {string} -- A .mat file which has to be read.

    Returns:
        dict -- A dictionary of the matlab file content.
    """
    mat = loadmat(mat_file)
    return mat
