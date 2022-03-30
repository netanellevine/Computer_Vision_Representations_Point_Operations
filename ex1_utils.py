"""
        '########:'##::::'##::::'##:::
         ##.....::. ##::'##:::'####:::
         ##::::::::. ##'##::::.. ##:::
         ######:::::. ###::::::: ##:::
         ##...:::::: ## ##:::::: ##:::
         ##:::::::: ##:. ##::::: ##:::
         ########: ##:::. ##::'######:
        ........::..:::::..:::......::
"""
import math
import sys
from typing import List
from cv2 import cv2 as cv
import numpy as np
from matplotlib import pyplot as plt
from cv2 import IMREAD_COLOR, IMREAD_GRAYSCALE

LOAD_GRAY_SCALE = 1
LOAD_RGB = 2
RGB2YIQ_mat = np.array([0.299, 0.587, 0.114, 0.596, -0.275, -0.321, 0.212, -0.523, 0.311]).reshape(3, 3)


def myID() -> np.int:
    """
    Return my ID (not the friend's ID I copied from)
    :return: int
    """
    return 312512619


def imReadAndConvert(filename: str, representation: int) -> np.ndarray:
    """
    Reads an image, and returns the image converted as requested
    :param filename: The path to the image
    :param representation: GRAY_SCALE or RGB
    :return: The image object
    """
    img = cv.imread(filename)
    if img is None:
        sys.exit("Could not read the image.")
    if representation == 1:
        img = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
    elif representation == 2:
        img = cv.cvtColor(img, cv.COLOR_BGR2RGB)
    img = img.astype(np.float)
    norm_img = normalizeData(img)
    return norm_img


def imDisplay(filename: str, representation: int):
    """
    Reads an image as RGB or GRAY_SCALE and displays it
    :param filename: The path to the image
    :param representation: GRAY_SCALE or RGB
    :return: None
    """
    img = imReadAndConvert(filename, representation)
    # cv.imshow(filename, img)
    # cv.waitKey(0)
    if representation == 1:
        plt.imshow(img, cmap='gray')
        plt.show()
    else:
        plt.imshow(img)
        plt.show()


def transformRGB2YIQ(imgRGB: np.ndarray) -> np.ndarray:
    """
    Converts an RGB image to YIQ color space
    :param imgRGB: An Image in RGB
    :return: A YIQ in image color space
    """
    orig_shape = imgRGB.shape
    imgRGB = imgRGB.reshape(-1, 3)
    YIQ_img = imgRGB.dot(RGB2YIQ_mat).reshape(orig_shape)
    return YIQ_img


def transformYIQ2RGB(imgYIQ: np.ndarray) -> np.ndarray:
    """
    Converts an YIQ image to RGB color space
    :param imgYIQ: An Image in YIQ
    :return: A RGB in image color space
    """
    orig_shape = imgYIQ.shape
    imgYIQ = imgYIQ.reshape(-1, 3)
    YIQ2RGB_mat = np.linalg.inv(RGB2YIQ_mat)
    RGB_img = imgYIQ.dot(YIQ2RGB_mat).reshape(orig_shape)
    return RGB_img


def hsitogramEqualize(imgOrig: np.ndarray) -> (np.ndarray, np.ndarray, np.ndarray):
    """
        Equalizes the histogram of an image
        :param imgOrig: Original Histogram
        :ret
    """
    isColored = False
    YIQimg = 0
    tmpMat = imgOrig
    if len(imgOrig.shape) == 3:  # it's RGB convert to YIQ and take the Y dimension
        YIQimg = transformRGB2YIQ(imgOrig)
        tmpMat = YIQimg[:, :, 0]
        isColored = True
    tmpMat = cv.normalize(tmpMat, None, 0, 255, cv.NORM_MINMAX)
    tmpMat = tmpMat.astype('uint8')
    histOrg = np.histogram(tmpMat.flatten(), bins=256)[0]  # original image histogram
    cumSum = np.cumsum(histOrg)  # image cumSum

    LUT = np.ceil((cumSum / cumSum.max()) * 255)  # calculate the LUT table
    imEqualized = tmpMat.copy()
    for i in range(256):  # give the right value for each pixel according to the LUT table
        imEqualized[tmpMat == i] = int(LUT[i])

    histEq = np.histogram(imEqualized.flatten().astype('uint8'), bins=256)[0]  # equalized image histogram

    imEqualized = imEqualized / 255
    if isColored:  # RGB img -> convert back to RGB color space
        YIQimg[:, :, 0] = imEqualized
        imEqualized = transformYIQ2RGB(YIQimg)

    return imEqualized, histOrg, histEq


def quantizeImage(imOrig: np.ndarray, nQuant: int, nIter: int) -> (List[np.ndarray], List[float]):
    """
        Quantized an image in to **nQuant** colors
        :param imOrig: The original image (RGB or Gray scale)
        :param nQuant: Number of colors to quantize the image to
        :param nIter: Number of optimization loops
        :return: (List[qImage_i],List[error_i])
    """
    isColored = False
    YIQimg = 0
    tmpMat = imOrig
    if len(imOrig.shape) == 3:  # it's RGB convert to YIQ and take the Y dimension
        YIQimg = transformRGB2YIQ(imOrig)
        tmpMat = YIQimg[:, :, 0]
        isColored = True
    tmpMat = cv.normalize(tmpMat, None, 0, 255, cv.NORM_MINMAX).astype('uint8')
    histOrg = np.histogram(tmpMat.flatten(), bins=256)[0]
    cumSum = np.cumsum(histOrg)  # image cumSum
    each_slice = cumSum.max() / nQuant
    slices = [0]
    k = 1
    for i in range(255):  # divide it to slices for the first time.
        if cumSum[i] <= each_slice * k <= cumSum[i + 1]:
            slices.append(i)
            k += 1
    slices.pop()
    slices.insert(nQuant, 255)
    iterImages = []
    MSE = []
    for i in range(nIter):
        temp_img = np.zeros(tmpMat.shape)
        Qi = []
        for j in range(nQuant):  # calculate the Qi avg for each slice.
            Si = np.array(range(slices[j], slices[j+1]))
            Pi = histOrg[slices[j]:slices[j + 1]]
            avg = int((Si * Pi).sum() / Pi.sum())
            Qi.append(avg)

        for k in range(nQuant):  # update the image.
            temp_img[tmpMat > (slices[k])] = Qi[k]

        slices.clear()
        for k in range(1, nQuant):  # update the slices.
            slices.append(int((Qi[k - 1] + Qi[k]) / 2))

        slices.insert(0, 0)
        slices.insert(nQuant, 255)
        # print(slices)
        MSE.append((np.sqrt((tmpMat - temp_img) ** 2)).mean())  # add the MSE to the list
        tmpMat = temp_img
        iterImages.append(temp_img / 255)  # add the updated image to the list
    if isColored:
        for i in range(nIter):
            YIQimg[:, :, 0] = iterImages[i]
            iterImages[i] = transformYIQ2RGB(YIQimg)

    return iterImages, MSE





    # print(slices)
    # plt.hist(cumSum, 256, [0, 256])
    # plt.show()
    # print(cumSum.shape)
    # print(cumSum[209])
    # print(cumSum[237])
    # print(cumSum[254])
    # print(cumSum)
    pass


def normalizeData(data):
    return (data - np.min(data)) / (np.max(data) - np.min(data))




