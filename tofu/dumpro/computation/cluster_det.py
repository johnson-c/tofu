#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu May 23 09:56:31 2019

@author: Arpan Khandelwal
email: napraarpan@gmail.com
"""

#nuilt in
import os
import tempfile
#standard
import numpy as np

#special
try:
    import cv2
except ImportError:
    print("Could not find opencv package. Try pip intall opencv-contrib-python")
    
def cluster_det(video_file, meta_data = None, verb = True, fw = None, fh = None, tlim = None):
    """ Thius subroutine takes the original video as input, converts it to 
    grayscale, perform background subtraction, converts the forground into 
    binary, performs contour detection and draws a bounding circle around
    the contour. It returns the center of this circle as an array
    
     Parameters
    -----------------------
    video_file:       mp4,avi,mpg
     input video along with its path passed in as argument
    meta_data:        dictionary
     A dictionary containing all the video meta_data. By default it is None
     But if the user inputs some keys into the dictionary, the code will use 
     the information from the dictionary and fill in the missing gaps if
     required
     meta_data has information on total number of frames, demension, fps and 
     the four character code of the video
    verb:             boolean
     If true, provided information to user
    fw:               tuple
     frame size for processing.
    fh:               tuple
     frame height for processing
    (fw qnd fh selects the region of interest of the image)
    tlim:             tuple
     to select the time window of inetrest. tlim should be in frame number,i.e.
     start_frame_number,stop_frame_number.
     
    """
    #getting temporary folder
    p_temp = tempfile.gettempdir()

    #reading the input video
    try:
        if not os.path.isfile(video_file):
            raise Exception
        cap = cv2.VideoCapture(video_file)
        
    except Exception:
        msg = 'the path or filename is incorrect.'
        msg += 'PLease verify the path or file name and try again'
        raise Exception(msg)
    
    #providing users for option to displaying videos for comparison
    user_choice = input('Do you want to perform a side by side comparison of the videos ? [y/n]')
    if user_choice == 'y':
        print('Which videos do you want to view?')
        print('1. Original')
        print('2. Grayscale converted')
        print('3. After background subtracted')
        print('4. After Guassian Blur operation')
        print('5. After binary operation')
        print('6. After edge detection')
        print('7. After contour detection')
        print('if you have to chose multiple options then please enter the options followed by a "," :')
        print('for example if you want option 2 and 4, enter them as 2,4')
        #taking in user input
        user_option = input('please enter your choice :')
        
    #reading the first frame and ensuring that the video is loaded
    ret, frame = cap.read()
    if verb == True:
        print('video file successfully loaded ...\n')
        
    if meta_data == None:
        #defining the four character code
        fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
        #defining the frame dimensions
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        #defining the fps
        fps = cap.get(cv2.CAP_PROP_FPS)
        #defining the total number of frames
        N_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        #defining the meta_data dictionary
        meta_data = {'fps' : fps, 'frame_height' : frame_height, 
                     'frame_width' : frame_width, 'fourcc' : fourcc,
                     'N_frames' : N_frames}
        
    else:
        #describing the four character code      
        fourcc = meta_data.get('fourcc', int(cap.get(cv2.CAP_PROP_FOURCC)))
        if 'fourcc' not in meta_data:
            meta_data['fourcc'] = fourcc
        
        #describing the frame width
        frame_width = meta_data.get('frame_width', int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)))
        if 'frame_width' not in meta_data:
            meta_data['frame_width'] = frame_width
        
        #describing the frame height
        frame_height = meta_data.get('frame_height', int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)))
        if 'frame_height' not in meta_data:
            meta_data['frame_height'] = frame_height
            
        #describing the speed of the video in frames per second 
        fps = meta_data.get('fps', int(cap.get(cv2.CAP_PROP_FPS)))
        if 'fps' not in meta_data:
            meta_data['fps'] = fps

        #describing the total number of frames in the video
        N_frames = meta_data.get('N_frames', int(cap.get(cv2.CAP_PROP_FRAME_COUNT)))
        if 'N_frames' not in meta_data:
            meta_data['N_frames'] = N_frames

    if verb == True:
        print('meta_data successfully read ...\n')
        
    #creating background subtractor method
    back = cv2.bgsegm.createBackgroundSubtractorMOG()
    
    #for cropping frames to remove unwanted information
    #size of the frame width
    if fw == None:
        lfw, ufw = 0, frame_width
    else:
        lfw, ufw = fw
    #size of the frame height    
    if fh == None:
        lfh, ufh = 0, frame_height
    else:
        lfh, ufh = fh
        
    if tlim == None:
        start,stop = 0,(N_frames - 1)
    else:
        start,stop = tlim[0],tlim[1]

    if verb == True:
        print('Looping over file ...\n')
    
    if verb == True:
        print('')
    
    if tlim == None:
        start, stop = 1, N_frames
    else:
        start,stop = tlim
    #array to store inforamtion on clusters
    #stores the number of clusters in each frame
    t_cluster = np.ndarray(( N_frames), dtype = int)
    #lists to store information on centers
    f_center = []
    t_center = []
    
    #inistailizing loop variable
    frame_counter = 1
    #looping through the entire video
    while cap.isOpened():
        
        ret, frame = cap.read()
        #to exit when the frames have been exhausted
        if not ret: break
        #cropping each frame
        frame = frame[lfw:ufw,lfh:ufh]
        
        if verb == True:
            print('processing frame :', frame_counter)
 ######################################################################      
        #displaying original video 
        if user_choice == 'y':
            if ('1' in user_option):
                cv2.imshow('original', frame)         
                #Press q on keyboard to exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
#######################################################################        
        #conversion to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        #displaying video if user wants to view it
        if user_choice == 'y':
            if ('2' in user_option):
                cv2.imshow('grayscale', gray)         
                #Press q on keyboard to exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
#######################################################################
        #denoising video
        dst = cv2.fastNlMeansDenoising(gray,None,5,21,7)
#######################################################################        
        #applying the background subtraction method
        movie = back.apply(dst)
        #displaying video depending on user choice
        if user_choice == 'y':
            if ('3' in user_option):
                cv2.imshow('background', movie)         
                # Press Q on keyboard to exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
#######################################################################
        #blurring image to remove high frequency noise
        blurred = cv2.GaussianBlur(movie,(11,11),0)
        if user_choice == 'y':
            if ('4' in user_option):
                cv2.imshow('blurred', blurred)
                # Press Q on keyboard to exit
                if cv2.waitKey(25) & 0xFF == ord('q'):
                    break
#######################################################################
        #conversion to binary image
        ret, threshed_img = cv2.threshold(blurred,
                                          127, 255, cv2.THRESH_BINARY)
        #displaying based on user choice
        if user_choice == 'y':
            if ('5' in user_option):
                cv2.imshow('binary', threshed_img)         
                # Press Q on keyboard to  exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
#######################################################################        
        edge = cv2.Canny(threshed_img,127,255)
        #displaying based on user choice
        if user_choice == 'y':
            if ('6' in user_option):
                cv2.imshow('edge', edge)         
                # Press Q on keyboard to  exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
#######################################################################        
        #finding all the contours in the video
        contours, hierarchy = cv2.findContours(threshed_img,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        print(len(contours))
        print(hierarchy)
        print(type(contours))
        print(type(hierarchy))
        for c in contours:

 
            #finally, get the min enclosing circle
            (x, y), radius = cv2.minEnclosingCircle(c)
            #convert all values to int
            center = (int(x), int(y))
            radius = int(radius)
            if ((radius**2) >1 and (radius**2)<2000):
                #and draw the circle in blue
                frame = cv2.circle(frame, center, radius, (255, 0, 0), 2)
               # print(center)
               # print('area: ', (radius**2))
            contours = np.asarray(contours)
            f_center.append(center)

        t_cluster[frame_counter] = len(contours)  
        t_center.append(f_center)
        
        #cv2.drawContours(frame, contours, -1, (255, 255, 0), 1)
        #displaying based on user choice
        if user_choice == 'y':
            if ('7' in user_option):
                cv2.imshow('contour', frame)         
                # Press Q on keyboard to  exit 
                if cv2.waitKey(25) & 0xFF == ord('q'): 
                    break
        
        frame_counter+=1
    # When everything done, release  
    # the video capture object 
    cap.release() 
                
    # Closes all the frames 
    cv2.destroyAllWindows()
    
    return t_cluster, t_center