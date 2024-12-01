import numpy as np
import cv2
import matplotlib.pyplot as plt
import math

class laplacian_blender:
    def __init__(self, SOURCE, TARGET, MASK):
        self.source = SOURCE
        self.target = TARGET
        self.mask = MASK

    #################### PART A ####################
    def Get_2D_Gaussian_kernel(self, kernel_size,sigma):
        #Kernel_size should be an odd integer
        #sigma is the standard deviation of the Gaussian
        # Generate 1D Gaussian kernel
        kernel_1d = cv2.getGaussianKernel(kernel_size, sigma)
        # Create a 2D Gaussian kernel by multiplying the 1D kernel with its transpose
        kernel_2d = kernel_1d @ kernel_1d.T
        return(kernel_2d)    


    def ComputePyr(self, input_image, num_layers):
        #check if num_layers is valid
        #find max layers from computing how many times the smallest dimension can be divided by two, add one for the base layer
        max_layers = np.log2(min(input_image.shape[:2]))+1
        max_layers = math.floor(max_layers)
        if num_layers > max_layers:
            num_layers = max_layers
        #create the guassian kernel used to create the pyramid
        kernel_size = 3
        sigma = 1
        Gaussian_Kernel = self.Get_2D_Gaussian_kernel(kernel_size,sigma)
        #initialize the gaussian pyramid  with the first layer as the original image
        gPyr = [input_image]
        #initialize conditions for the loop to create the gaussian pyramid
        current_image = input_image
        #loop to create the Gaussian Pyramid
        for layer in range(num_layers): #iterates num_layers - 1 times
            #blur the image
            blurred_image = self.conv2(current_image,Gaussian_Kernel,"zero padding")
            #use nearest neighbor downsampling
            height, width = blurred_image.shape[:2]
            current_image = cv2.resize(blurred_image, (width // 2, height // 2), interpolation=cv2.INTER_NEAREST)
            #add the downsampled image to the pyramid
            gPyr.append(current_image)

        #make laplcian pyramid
        lPyr = [] #create an empty list
        for layer in range(num_layers): #iterates max_layers - 1 times
            #upsample each layer
            upscaled_image = cv2.resize(gPyr[layer+1], (gPyr[layer].shape[1],gPyr[layer].shape[0]), interpolation=cv2.INTER_NEAREST) #doubles the dimensions and upscales using nearest neighbor method
            #subtract upsampled image from the next highest level from the current layer
            lPyr.append(gPyr[layer]-upscaled_image)
        #last level of lPyr is the last level of gPyr since there is no higher level to upsample
        lPyr.append(gPyr[num_layers])    

        return gPyr, lPyr
    
    def gaussian_pyramid(self, IMAGE, NUMLEVELS):
        G = IMAGE.copy()
        gp = [G]
        for i in range(1,NUMLEVELS):
            G = cv2.pyrDown(G)
            gp.append(G)
        return gp

    def laplacian_pyramid(self, GP):
        numLevels = len(GP)-1
        lp  = [GP[numLevels]]
        for i in range(numLevels,0,-1):
            GE = cv2.pyrUp(GP[i])
            L = cv2.subtract(GP[i-1],GE)
            lp.append(L)
        lp = lp[::-1]
        return lp

    #################### PART C ####################
    def blend(self, numLevels):
        #numLevels = numLevel-1
        # Get laplacian pyramids
        '''
        _, SOURCE_LP = self.ComputePyr(self.source, numLevels)
        _, TARGET_LP = self.ComputePyr(self.target, numLevels)
        MASK_GP, _ = self.ComputePyr(self.mask, numLevels)
        '''
        SOURCE_LP = self.laplacian_pyramid(self.gaussian_pyramid(self.source,numLevels))
        TARGET_LP = self.laplacian_pyramid(self.gaussian_pyramid(self.target,numLevels))
        MASK_GP = self.gaussian_pyramid(self.mask,numLevels)

        # Create blended pyramid
        blended_pyramid = [MASK_GP[0]*SOURCE_LP[0] + (1-MASK_GP[0])*TARGET_LP[0]]
        for i in range(1,numLevels):
            blended_pyramid.append(MASK_GP[i]*SOURCE_LP[i] + (1-MASK_GP[i])*TARGET_LP[i])
        
        # Collapse the blended pyramid
        scale = 2
        for i in range(numLevels-1,0,-1):
            level = blended_pyramid.pop()
            level = self.upsample(level,scale)
            blended_pyramid[i-1] = blended_pyramid[i-1] + level
        blended_image = blended_pyramid[0]
        
        # Normalize blended image to 0-255
        blended_image = self.normalize(blended_image, 255).astype(int)
        
        return blended_image
    
    ################ HELPER FUNCTIONS ################
    def upsample(self, IMAGE, SCALE=2):
        upsampled_image = cv2.pyrUp(IMAGE)
        return upsampled_image
    
    def normalize(self, INPUT, SCALE=1):
        # If input is a pyramid
        if isinstance(INPUT, list):
            for levelIdx, level in enumerate(INPUT):
                # Convert to float
                level = level.astype(float)
                # Work in 3D
                grey = False
                if len(level.shape) == 2:
                    grey = True
                    level = np.expand_dims(level, axis=2)
                # Iterate through channels
                for idx, channel in enumerate(level.transpose(2, 0, 1)):
                    # Edge case
                    if np.max(channel) == 0:
                        continue
                    # Normalize (max will always be 255)
                    else:
                        channel = channel / 255
                    # Assign channel to level
                    level[:,:,idx] = channel
                # Assign level to pyramid
                INPUT[levelIdx] = level
                if grey:
                    level = np.squeeze(level, -1)

        # If input is just an image
        else:
            INPUT = INPUT.astype(float)
            # Work in 3D
            grey = False
            if len(INPUT.shape) == 2:
                grey = True
                INPUT = np.expand_dims(level, axis=2)
            # Iterate through every channel
            for idx, channel in enumerate(INPUT.transpose(2, 0, 1)):
                # Edge case
                if np.max(channel) == 0:
                    continue
                # Normalize
                else:
                    channel = ((channel - np.min(channel)) / (np.max(channel) - np.min(channel))) * SCALE
                INPUT[:,:,idx] = channel
            if grey:
                INPUT = np.squeeze(INPUT, -1)
        return INPUT
        
    def conv2(self,f,w,pad): #f = input image, w = 2-D kernel filter, pad = the 4 padding types 

        def pad_gray_image(f,padding_width,pad):
            #np.pad(array,pad_width,mode)
            match pad:
                case 'zero padding':
                    return np.pad(f,pad_width = padding_width,mode='constant',constant_values = 0)
                case 'wrap around':
                    return np.pad(f,pad_width = padding_width,mode='wrap')
                case 'copy edge':
                    return np.pad(f,pad_width = padding_width,mode='edge')
                case 'refelct across edge':
                    return np.pad(f,pad_width = padding_width,mode='reflect')
        
        def pad_RGB_image(f,padding_width,pad):
            #np.pad(array,pad_width,mode)
            padding = ((padding_width,padding_width),(padding_width,padding_width),(0,0))
            match pad:
                case 'zero padding':
                    return np.pad(f,padding,mode='constant',constant_values = 0)
                case 'wrap around':
                    return np.pad(f,padding,mode='wrap')
                case 'copy edge':
                    return np.pad(f,padding,mode='edge')
                case 'refelct across edge':
                    return np.pad(f,padding,mode='reflect')
            
        def convolution_range(dimension_length):
            if dimension_length % 2 == 0: #(value is even)
                convolve_min = int(-dimension_length/2 +1)
                convolve_max = int(dimension_length/2)
            else:
                convolve_min = int(-(dimension_length-1)/2)
                convolve_max = int((dimension_length-1)/2)
            return convolve_min, convolve_max
        
        #step 0 get appropriate padding size based on kernel
        padding_dimension = max(w.shape)
        padding_size = padding_dimension // 2 

        #step 1 determine if its grayscale or RGB
        #if grayscale
        if len(f.shape) == 2:
            #step2 pad the image
            padded_image = pad_gray_image(f,padding_size,pad) #since we are only using up to a 3x3 kernel we can pad all images by 1 on each side
            height,width = f.shape #get original image dimensions
            g = np.zeros((height,width)) #make an array of the same dimesions to be filled for the output image
            k_height, k_width = w.shape #get the height and width of the kernel
            height_convolve_min, height_convolve_max = convolution_range(k_height)
            width_convolve_min, width_convolve_max = convolution_range(k_width)
            kernel_height_center = int((height_convolve_max-height_convolve_min)/2 - ((height_convolve_max-height_convolve_min) % 2))
            kernel_width_center = int((width_convolve_max-width_convolve_min)/2 - ((width_convolve_max-width_convolve_min) % 2))
            for u in range(padding_size,height+padding_size): #plus one because images are padded by one on each side
                for v in range(padding_size,width+padding_size):
                    convolution_value = 0
                    for k_u in range(height_convolve_min,height_convolve_max+1):
                        for k_v in range(width_convolve_min,width_convolve_max+1):
                            convolution_value = convolution_value + padded_image[(u+k_u),(v+k_v)]*w[(kernel_height_center+k_u),(kernel_width_center+k_v)]
                    g[(u-padding_size),(v-padding_size)] = convolution_value

        #if RGB
        elif len(f.shape) == 3:
            #step 2 pad the image
            padded_image = pad_RGB_image(f,padding_size,pad)
            height,width = f.shape[:2] #get original image dimensions
            g = np.zeros((height,width,3)) #make an array of the same dimesions to be filled for the output image
            k_height, k_width = w.shape #get the height and width of the kernel
            height_convolve_min, height_convolve_max = convolution_range(k_height)
            width_convolve_min, width_convolve_max = convolution_range(k_width)
            kernel_height_center = int((height_convolve_max-height_convolve_min)/2 - ((height_convolve_max-height_convolve_min) % 2))
            kernel_width_center = int((width_convolve_max-width_convolve_min)/2 - ((width_convolve_max-width_convolve_min) % 2))
            for channel in range(0,3):
                for u in range(padding_size,height+padding_size): #plus one because images are padded by one on each side
                    for v in range(padding_size,width+padding_size):
                        convolution_value = 0
                        for k_u in range(height_convolve_min,height_convolve_max+1):
                            for k_v in range(width_convolve_min,width_convolve_max+1):
                                convolution_value = convolution_value + padded_image[(u+k_u),(v+k_v),channel]*w[(kernel_height_center+k_u),(kernel_width_center+k_v)]
                        g[(u-padding_size),(v-padding_size),channel] = convolution_value        
        #step 3 change the image values from float 64s back to uint8 
        #we need to normalize the values to 0 through 255
        max_value = np.max(g)
        min_value = np.min(g)
        g_range = max_value-min_value
        g = (g-min_value)/g_range
        g = (255*g).astype(np.uint8)

        return g