import numpy as np
from scipy.ndimage.filters import gaussian_filter, maximum_filter
import itertools as itt
import math
from math import sqrt, hypot, log
from numpy import arccos
from skimage.util import img_as_float


# This basic blob detection algorithm is based on:
# http://www.cs.utah.edu/~jfishbau/advimproc/project1/ (04.04.2013)
# Theory behind: http://en.wikipedia.org/wiki/Blob_detection (04.04.2013)

# A lot of this code is borrowed from here
# https://github.com/adonath/blob_detection/tree/master/blob_detection


def _get_local_maxima_3d(array, threshold):
    """Finds local maxima in a 3d array.

    A pixel is considered to be a maximum if it is greater than or equal to all
    its 28 neighbors in the 3d cube.

    Parameters
    ----------
    array : ndarray
        The 3d array whose local maximas are sought.
    thresh : float
        Local maximas lesser than thresh are ignored.

    Returns
    -------
    A : (n, 3) ndarray
        A 2d array in which each row contains 3 values, the indices of local
        maxima.

    """
    # computing max filter using all neighbors in cube
    fp = np.ones((3, 3, 3))
    max_array = maximum_filter(array, footprint=fp)
    peaks = (max_array == array) & (array > threshold)
    return np.argwhere(peaks)


def _blob_overlap(blob1, blob2):
    """Finds the overlapping area fraction between two blobs.

    Returns a float representing fraction of overlapped area.

    Parameters
    ----------
    blob1 : sequence
        A sequence of ``(y,x,sigma)``, where ``x,y`` are coordinates of blob
        and sigma is the standard deviation of the Gaussian kernel which
        detected the blob.
    blob2 : sequence
        A sequence of ``(y,x,sigma)``, where ``x,y`` are coordinates of blob
        and sigma is the standard deviation of the Gaussian kernel which
        detected the blob.

    Returns
    -------
    f : float
        Fraction of overlapped area.

    """
    root2 = sqrt(2)

    # extent of the blob is given by sqrt(2)*scale
    r1 = blob1[2] * root2
    r2 = blob2[2] * root2

    d = hypot(blob1[0] - blob2[0], blob1[1] - blob2[1])

    if d > r1 + r2:
        return 0

    # one blob is inside the other, the smaller blob must die
    if d <= abs(r1 - r2):
        return 1

    acos1 = arccos((d ** 2 + r1 ** 2 - r2 ** 2) / (2 * d * r1))
    acos2 = arccos((d ** 2 + r2 ** 2 - r1 ** 2) / (2 * d * r2))
    a = -d + r2 + r1
    b = d - r2 + r1
    c = d + r2 - r1
    d = d + r2 + r1
    area = r1 ** 2 * acos1 + r2 ** 2 * acos2 - 0.5 * sqrt(abs(a * b * c * d))

    return area / (math.pi * (min(r1, r2) ** 2))


def _prune_blobs(blobs_array, overlap):
    """Eliminated blobs with area overlap.

    Parameters
    ----------
    blobs_array : ndarray
        a 2d array with each row representing 3 values, the ``(y,x,sigma)``
        where ``(y,x)`` are coordinates of the blob and sigma is the standard
        deviation of the Gaussian kernel which detected the blob.
    overlap : float
        A value between 0 and 1. If the fraction of area overlapping for 2
        blobs is greater than `overlap` the smaller blob is eliminated.

    Returns
    -------
    A : ndarray
        `array` with overlapping blobs removed.

    """

    # iterating again might eliminate more blobs, but one iteration suffices
    # for most cases
    for blob1, blob2 in itt.combinations(blobs_array, 2):
        if _blob_overlap(blob1, blob2) > overlap:
            if blob1[2] > blob2[2]:
                blob2[2] = -1
            else:
                blob1[2] = -1

    # return blobs_array[blobs_array[:, 2] > 0]
    return np.array([b for b in blobs_array if b[2] > 0])


def blob_dog(image, min_sigma=1, max_sigma=25, sigma_ratio=1.6, threshold=2.0,
             overlap=.5,):
    """Finds blobs in the given grayscale image.

    Blobs are found using the Difference of Gaussian (DoG) method[1]_.
    For each blob found, its coordinates and area are returned.

    Parameters
    ----------
    image : ndarray
        Input grayscale image, blobs are assumed to be light on dark
        background (white on black).
    min_sigma : float, optional
        The minimum standard deviation for Gaussian Kernel. Keep this low to
        detect smaller blobs.
    max_sigma : float, optional
        The maximum standard deviation for Gaussian Kernel. Keep this high to
        detect larger blobs.
    sigma_ratio : float, optional
        The ratio between the standard deviation of Gaussian Kernels used for
        computing the Difference of Gaussians
        `max_sigma`
    threshold : float, optional.
        The absolute lower bound for scale space maxima. Local maxima smaller
        than thresh are ignored. Reduce this to detect blobs with less
        intensities.
    overlap : float, optional
        A value between 0 and 1. If the area of two blobs overlaps by a
        fraction greater than `thresh`, the smaller blob is eliminated.
    log_scale : boolean, optional
        If set to True, the standard deviations of Gaussian Kernels are
        interpolated using a logarithmic scale. This is useful when finding
        blobs with a large variation in size. If set, scales are interpolated
        with log to the base 10.

    Returns
    -------
    A : (n, 3) ndarray
        A 2d array with each row containing the Y-Coordinate , the
        X-Coordinate and the estimated area of the blob respectively.

    References
    ----------
    .. [1] http://en.wikipedia.org/wiki/Blob_detection#The_difference_of_Gaussians_approach

    Examples
    --------
    >>> from skimage import data,feature
    >>> feature.blob_dog(data.coins())
    array([[  46,  336, 2513],
           [  53,  156, 2035],
           [  53,  217, 1608],
           [  54,  276, 1231],
           [  55,   42, 1608],
           [  57,  100, 1231],
           [ 121,  272, 2035],
           [ 124,  337, 1413],
           [ 125,   45, 1815],
           [ 125,  207, 1608],
           [ 126,  102, 1231],
           [ 128,  154, 1231],
           [ 185,  347, 2513],
           [ 194,  213, 1815],
           [ 194,  277, 1608],
           [ 196,   42, 1231],
           [ 196,  101, 1608],
           [ 197,  155, 1231],
           [ 260,   46, 2513],
           [ 261,  174, 2035],
           [ 263,  245, 2035],
           [ 263,  302, 2035],
           [ 266,  114, 1608],
           [ 268,  358, 1608]])

    """

    if image.ndim != 2:
        raise ValueError("'image' must be a grayscale ")

    image = img_as_float(image)

    # k such that min_sigma*(sigma_ratio**k) > max_sigma
    k = int(log(float(max_sigma) / min_sigma, sigma_ratio)) + 1

    # a geometric progression of standard deviations for gaussian kernels
    sigma_list = np.array([min_sigma * (sigma_ratio ** i)
                          for i in range(k + 1)])

    gaussian_images = [gaussian_filter(image, s) for s in sigma_list]

    # computing difference between two succesive gaussian blurred images
    # multipying with square of standard deviation provides scale invariance
    dog_images = [(gaussian_images[i] - gaussian_images[i + 1])
                  * sigma_list[i] ** 2 for i in range(k)]
    image_cube = np.dstack(dog_images)

    local_maxima = _get_local_maxima_3d(image_cube, threshold)

    # Convert the last index to its corresponding scale value
    local_maxima[:, 2] = sigma_list[local_maxima[:, 2]]
    ret_val = _prune_blobs(local_maxima, overlap)

    if len(ret_val) > 0:
        ret_val[:, 2] = math.pi * \
            ((ret_val[:, 2] * math.sqrt(2)) ** 2).astype(int)
        return ret_val
    else:
        return []
