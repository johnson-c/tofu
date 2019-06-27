# -*- coding: utf-8 -*-
"""
Created on Sat Jun  8 13:45:58 2019

@author: Arpan Khandelwal
email: napraarpan@gmail.com
This subroutine requires opencv3 and higher
"""

# Built-in
import os
from sys import stdout
from time import sleep

# Standard
import numpy as np

# More special
try:
    import cv2
except ImportError:
    print("Could not find opencv package. Try pip intall opencv-contrib-python")
    
def bin_thresh(im_path, w_dir, shot_name, im_out = None, meta_data = None, verb = True):
    """
    This subroutine converts a collection of images to binary
    The images are read in grayscale form i.e., in single channel mode
    For more information consult:
    
    1. https://docs.opencv.org/2.4/doc/tutorials/imgproc/threshold/threshold.html
    2. https://docs.opencv.org/3.4.0/d7/d4d/tutorial_py_thresholding.html
    
    Among the parameters present, if used as a part of dumpro, 
    w_dir, shot_name and meta_data are provided by the image processing 
    class in the core file.
    The verb paramenter is used when this subroutine is used independently.
    Otherwise it is suppressed by the core class.
    
    Parameters
    -----------------------
    im_path:          string
     input path where the images are stored
    w_dir:            string
     A working directory where the proccesed images are stored
    shot_name:        String
     The name of the tokomak machine and the shot number. Generally
     follows the nomenclature followed by the lab
    meta_data:        dictionary
     A dictionary containing all the video meta_data. By default it is None
     But if the user inputs some keys into the dictionary, the code will use 
     the information from the dictionary and fill in the missing gaps if
     required
     meta_data has information on total number of frames, demension, fps and 
     the four character code of the video
    disp              boolean
     to display the frames set equal to True. By default is set to True
    
    Return
    -----------------------
    im_out:              String
     Path along where the proccessed images are stored  
    meta_data:        dictionary
     A dictionary containing the meta data of the video.
    """
    if verb == True:
        print('###########################################')
        print('Binary Conversion')
        print('###########################################\n')
    
    #reading the output directory
    if verb == True:
        print('Creating output directory ...')
    #default output folder name
    folder = shot_name + '_binary'
    #creating the output directory
    if im_out == None:
        im_out = os.path.join(w_dir, folder, '')
        if not os.path.exists(im_out):
            #creating output directory using w_dir and shotname
            os.mkdir(im_out)
    
    if verb == True:
        print('output directory is : ', im_out,'\n')
    
    #describing an empty list that will later contain all the frames
    #frame_array = []
    #creating a list of all the files
    files = [f for f in os.listdir(im_path) if os.path.isfile(os.path.join(im_path,f))]    
    
    #sorting files according to names using lambda function
    files.sort(key = lambda x: int(x[5:-4]))
    #looping throuah all the file names in the list and converting them to image path
    
    if verb == True:
        print('performing binary conversion...')
    
    #looping through the files
    f_count = 1
    for i in range(len(files)):
        #converting to path
        filename = im_path + files[i]
        #dynamic printing
        if verb == True:
            stdout.write("\r[%s/%s]" % (f_count, len(files)))
            stdout.flush()
        #reading each file to extract its meta_data
        img = cv2.imread(filename,cv2.IMREAD_GRAYSCALE)
        #grayscale conversion
        ret, out = cv2.threshold(img,100,255,cv2.THRESH_BINARY)
        #generic name of each image
        name = im_out + 'frame' + str(f_count) + '.jpg'
        #writting the output file
        cv2.imwrite(name, out)
        height,width = img.shape[0],img.shape[1]
        size = (height, width)
        #providing information to user
        f_count += 1
        
    #dynamic printing
    stdout.write("\n")
    stdout.flush()
    
    #frame_array.append(img)
    
    if verb == True:
        print('Reading meta_data...')
        
    if meta_data == None:
        #defining the four character code
        fourcc = cv2.VideoWriter_fourcc(*'MJPG')
        #defining the frame dimensions
        frame_width = width
        frame_height = height
        #defining the fps
        fps = 25
        #defining the total number of frames
        N_frames = len(files)
        #defining the meta_data dictionary
        meta_data = {'fps' : fps, 'frame_height' : frame_height, 
                     'frame_width' : frame_width, 'fourcc' : fourcc,
                     'N_frames' : N_frames}
    else:
        #describing the four character code      

        fourcc = meta_data.get('fourcc', cv2.VideoWriter_fourcc(*'MJPG'))
        if 'fourcc' not in meta_data:
            meta_data['fourcc'] = fourcc
        
        #describing the frame width
        frame_width = meta_data.get('frame_width', width)
        if 'frame_width' not in meta_data:
            meta_data['frame_width'] = frame_width
        
        #describing the frame height
        frame_height = meta_data.get('frame_height', height)
        if 'frame_height' not in meta_data:
            meta_data['frame_height'] = frame_height
            
        #describing the speed of the video in frames per second 
        fps = meta_data.get('fps', 25)
        if 'fps' not in meta_data:
            meta_data['fps'] = fps

        #describing the total number of frames in the video
        N_frames = meta_data.get('N_frames', len(files))
        if 'N_frames' not in meta_data:
            meta_data['N_frames'] = N_frames
    
    if verb == True:
        print('meta_data is read successfully...\n')
    
    return im_out, meta_data