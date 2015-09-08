"""Find plasmodesmata."""

import os.path
import argparse

import numpy as np
import skimage.measure

from jicbioimage.core.io import FileBackend
from jicbioimage.core.image import DataManager, SegmentedImage, Image
from jicbioimage.core.transform import transformation
from jicbioimage.core.util.array import (
    dtype_contract,
    normalise,
    _pretty_color
)

from jicbioimage.transform import (
    max_intensity_projection,
    threshold_otsu,
    remove_small_objects,
)

HERE = os.path.dirname(os.path.realpath(__file__))


def get_microscopy_collection(input_file):
    """Return microscopy collection from input file."""
    data_dir = os.path.abspath(os.path.join(HERE, "..", "data"))
    if not os.path.isdir(data_dir):
        raise(OSError("Data directory does not exist: {}".format(data_dir)))
    backend_dir = os.path.join(data_dir, 'unpacked')
    file_backend = FileBackend(backend_dir)
    data_manager = DataManager(file_backend)
    microscopy_collection = data_manager.load(input_file)
    return microscopy_collection


def connected_components(image, neighbors=8, background=None):
    """Return a segmented image."""
    connected_components, n_cc = skimage.measure.label(image,
                                                       neighbors=8,
                                                       background=background,
                                                       return_num=True)
    return connected_components.view(SegmentedImage)


@transformation
@dtype_contract(input_dtype=bool, output_dtype=bool)
def remove_large_objects(image, max_size):
    """Remove objects larger than max_size."""
    segmented_image = connected_components(image)
    for i in segmented_image.identifiers:
        region = segmented_image.region_by_identifier(i)
        if region.area > max_size:
            segmented_image[region.index_arrays] = 0
    return segmented_image.astype(bool)


def create_annotated_image(image, max_intensity):
    """Write an annotated image to disk."""
    segmented_image = connected_components(image)
    gray_intensity = normalise(max_intensity) * 255
    rgb_intensity = np.dstack([gray_intensity, gray_intensity, gray_intensity])
    annotated = Image.from_array(rgb_intensity)
    for i in segmented_image.identifiers:
        border = segmented_image.region_by_identifier(i).dilate(1).border
        annotated[border.index_arrays] = _pretty_color()
    with open("annotated.png", "wb") as fh:
        fh.write(annotated.png())


def find_plasmoesmata(zstack, max_size, min_size):
    """Return segmented image.

    :param zstack: numpy.ndarray
    :param max_size: maximum size allowed
                     for a region to be classified as a plasmodesmata
    :param min_size: minimum size allowed
                     for a region to be classified as a plasmodesmata
    :returns: :class:`jicbioimage.core.image.SegmentedImage`
    """
    max_intensity = max_intensity_projection(zstack)

    im = threshold_otsu(max_intensity)
    im = remove_large_objects(im, max_size=max_size)
    im = remove_small_objects(im, min_size=min_size)

    create_annotated_image(im, max_intensity)

    return connected_components(im)


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("input_file", help="path to raw microscopy data")
    parser.add_argument("series", type=int,
        help="zero based index of microscopy image series to analyse")
    parser.add_argument("-l", "--max_size",
        default=100, type=int, help="maximum number of pixels (default=100)")
    parser.add_argument("-s", "--min_size",
        default=2, type=int, help="minimum number of pixels (default=2)")
    args = parser.parse_args()
    if not os.path.isfile(args.input_file):
        parser.error("No such microscopy file: {}".format(args.input_file))

    microscopy_collection = get_microscopy_collection(args.input_file)
    zstack = microscopy_collection.zstack_array(s=args.series)
    find_plasmoesmata(zstack, args.max_size, args.min_size)

if __name__ == "__main__":
    main()