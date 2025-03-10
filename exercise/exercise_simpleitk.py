import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(sys.argv[0]), '..'))  # append the MIALab root directory to Python path

import numpy as np
import SimpleITK as sitk

import exercise.helper as helper


def load_image(img_path, is_label_img):
    # todo: load the image from the image path with the SimpleITK interface (hint: 'ReadImage')
    # todo: if 'is_label_img' is True use argument outputPixelType=sitk.sitkUInt8, else use outputPixelType=sitk.sitkFloat32
    # print(is_label_img)
    # print(img_path)
    if is_label_img:
        pixel_type = sitk.sitkUInt8
    else:
        pixel_type = sitk.sitkFloat32
    img = sitk.ReadImage(img_path,pixel_type)
    # print(img)

    return img


def to_numpy_array(img):
    # todo: transform the SimpleITK image to a numpy ndarray (hint: 'GetArrayFromImage')
    np_img = sitk.GetArrayFromImage(img)  # todo: modify here

    return np_img


def to_sitk_image(np_image, reference_img):
    # todo: transform the numpy ndarray to a SimpleITK image (hint: 'GetImageFromArray')
    # todo: do not forget to copy meta-information (e.g., spacing, origin, etc.) from the reference image (hint: 'CopyInformation')!
    #       (otherwise defaults are set)

    img = sitk.GetImageFromArray(np_image)  # todo: modify here
    # todo: ...
    img.CopyInformation(reference_img)

    return img


def register_images(img, label_img, atlas_img):
    registration_method = _get_registration_method(atlas_img, img)  # type: sitk.ImageRegistrationMethod
    # print(type(img))

    # todo: execute the registration_method to the img (hint: fixed=atlas_img, moving=img)
    # the registration returns the transformation of the moving image (parameter img) to the space
    # of the atlas image (atlas_img)

    transform = registration_method.Execute(fixed=atlas_img, moving=img)
    # print(type(transform))
    # todo: apply the obtained transform to register the image (img) to the atlas image (atlas_img)
    # hint: 'Resample' (with referenceImage=atlas_img, transform=transform, interpolator=sitk.sitkLinear,
    # defaultPixelValue=0.0, outputPixelType=label_img.GetPixelIDValue())

    # registered_img = sitk.Resample(img, atlas_img, transform, sitk.sitkLinear, 0.0, label_img.GetPixelIDValue()) # todo: modify here
    # Solution with img not label_img
    registered_img = sitk.Resample(img, atlas_img, transform, sitk.sitkLinear, 0.0, img.GetPixelIDValue())

    # todo: apply the obtained transform to register the label image (label_img) to the atlas image (atlas_img), too
    # be careful with the interpolator type for label images!
    # hint: 'Resample' (with interpolator=sitkNearestNeighbor, defaultPixelValue=0.0, outputPixelType=label_img.GetPixelIDValue())
    registered_label = sitk.Resample(label_img, atlas_img, transform, sitk.sitkNearestNeighbor, 0.0, label_img.GetPixelIDValue())  # todo: modify here

    return registered_img, registered_label


def preprocess_rescale_numpy(np_img, new_min_val, new_max_val):
    max_val = np_img.max()
    min_val = np_img.min()
    # print(np_img.shape)
    # print(max_val)
    # print(min_val)
    # print(new_max_val)
    # print(new_min_val)
    # print(np_img[1, 1, 1])
    # todo: rescale the intensities of the np_img to the range [new_min_val, new_max_val]. Use numpy arithmetics only.
    rescaled_np_img = (((new_max_val-new_min_val)/(max_val-min_val))*(np_img-max_val)) + new_max_val # todo: modify here

    return rescaled_np_img


def preprocess_rescale_sitk(img, new_min_val, new_max_val):
    # todo: rescale the intensities of the img to the range [new_min_val, new_max_val] (hint: RescaleIntensity)
    rescaled_img = sitk.RescaleIntensity(img, new_min_val, new_max_val)  # todo: modify here

    return rescaled_img


def extract_feature_median(img):
    # todo: apply median filter to image (hint: 'Median')
    median_img = sitk.Median(img)  # todo: modify here

    return median_img


def postprocess_largest_component(label_img):
    # todo: get the connected components from the label_img (hint: 'ConnectedComponent')
    connected_components = sitk.ConnectedComponent(label_img)  # todo: modify here

    # todo: order the component by ascending component size (hint: 'RelabelComponent')
    relabeled_components = sitk.RelabelComponent(connected_components)  # todo: modify here

    largest_component = relabeled_components == 1  # zero is background
    return largest_component


# --- DO NOT CHANGE
def _get_registration_method(atlas_img, img) -> sitk.ImageRegistrationMethod:
    registration_method = sitk.ImageRegistrationMethod()

    # Similarity metric settings.
    registration_method.SetMetricAsMattesMutualInformation(numberOfHistogramBins=50)
    registration_method.SetMetricSamplingStrategy(registration_method.REGULAR)
    registration_method.SetMetricSamplingPercentage(0.2)

    registration_method.SetMetricUseFixedImageGradientFilter(False)
    registration_method.SetMetricUseMovingImageGradientFilter(False)

    registration_method.SetInterpolator(sitk.sitkLinear)

    # Optimizer settings.
    registration_method.SetOptimizerAsGradientDescent(learningRate=1.0, numberOfIterations=100,
                                                      convergenceMinimumValue=1e-6, convergenceWindowSize=10)
    registration_method.SetOptimizerScalesFromPhysicalShift()

    # Setup for the multi-resolution framework.
    registration_method.SetShrinkFactorsPerLevel(shrinkFactors=[4, 2, 1])
    registration_method.SetSmoothingSigmasPerLevel(smoothingSigmas=[2, 1, 0])
    registration_method.SmoothingSigmasAreSpecifiedInPhysicalUnitsOn()

    # Set initial transform
    initial_transform = sitk.CenteredTransformInitializer(atlas_img, img,
                                                          sitk.Euler3DTransform(),
                                                          sitk.CenteredTransformInitializerFilter.GEOMETRY)
    registration_method.SetInitialTransform(initial_transform, inPlace=False)
    return registration_method


# --- DO NOT CHANGE
if __name__ == '__main__':
    callback = helper.TestCallback()
    callback.start('SimpleITK')

    callback.start_test('load_image')
    img = load_image('../data/exercise/subjectX/T1native.nii.gz', False)
    load_ok = isinstance(img, sitk.Image) and img.GetPixelID() == 8 and img.GetSize() == (181, 217, 181) and \
              img.GetPixel(100, 100, 100) == 12175 and img.GetPixel(100, 100, 101) == 11972

    callback.end_test(load_ok)

    callback.start_test('to_numpy_array')
    np_img = to_numpy_array(img)
    to_numpy_ok = isinstance(np_img, np.ndarray) and np_img.dtype.name == 'float32' and np_img.shape == (181, 217, 181) \
                  and np_img[100, 100, 100] == 12175 and np_img[101, 100, 100] == 11972
    callback.end_test(to_numpy_ok)

    callback.start_test('to_sitk_image')
    rev_img = to_sitk_image(np_img, img)
    to_sitk_ok = isinstance(rev_img, sitk.Image) and rev_img.GetOrigin() == img.GetOrigin() and \
                 rev_img.GetSpacing() == img.GetSpacing() and \
                 rev_img.GetDirection() == img.GetDirection() and rev_img.GetPixel(100, 100, 100) == 12175 and \
                 rev_img.GetPixel(100, 100, 101) == 11972
    callback.end_test(to_sitk_ok)

    callback.start_test('register_images')
    atlas_img = load_image('../data/exercise/mni_icbm152_t1_tal_nlin_sym_09a.nii.gz', False)
    label_img = load_image('../data/exercise/subjectX/labels_native.nii.gz', True)
    if isinstance(atlas_img, sitk.Image) and isinstance(label_img, sitk.Image):
        registered_img, registered_label = register_images(img, label_img, atlas_img)
        if isinstance(registered_img, sitk.Image) and isinstance(registered_label, sitk.Image):
            stats = sitk.LabelStatisticsImageFilter()
            stats.Execute(registered_img, registered_label)
            labels = stats.GetLabels()
            register_ok = registered_img.GetSize() == registered_label.GetSize() == (197, 233, 189) and \
                          labels == tuple(range(6))
        else:
            register_ok = False
    else:
        register_ok = False
    callback.end_test(register_ok)

    callback.start_test('preprocss_rescale_numpy')
    if isinstance(np_img, np.ndarray):
        pre_np = preprocess_rescale_numpy(np_img, -3, 101)
        if isinstance(pre_np, np.ndarray):
            pre_np_ok = pre_np.min() == -3 and pre_np.max() == 101
        else:
            pre_np_ok = False
    else:
        pre_np_ok = False
    callback.end_test(pre_np_ok)

    callback.start_test('preprocss_rescale_sitk')
    pre_sitk = preprocess_rescale_sitk(img, -3, 101)
    if isinstance(pre_sitk, sitk.Image):
        min_max = sitk.MinimumMaximumImageFilter()
        min_max.Execute(pre_sitk)
        pre_sitk_ok = min_max.GetMinimum() == -3 and min_max.GetMaximum() == 101
    else:
        pre_sitk_ok = False
    callback.end_test(pre_sitk_ok)

    callback.start_test('extract_feature_median')
    median_img = extract_feature_median(img)
    if isinstance(median_img, sitk.Image):
        median_ref = load_image('../data/exercise/subjectX/T1med.nii.gz', False)
        if isinstance(median_ref, sitk.Image):
            min_max = sitk.MinimumMaximumImageFilter()
            min_max.Execute(median_img - median_ref)
            median_ok = min_max.GetMinimum() == 0 and min_max.GetMaximum() == 0
        else:
            median_ok = False
    else:
        median_ok = False
    callback.end_test(median_ok)

    callback.start_test('postprocess_largest_component')
    largest_hippocampus = postprocess_largest_component(label_img == 3)  # 3: hippocampus
    if isinstance(largest_hippocampus, sitk.Image):
        largest_ref = load_image('../data/exercise/subjectX/hippocampus_largest.nii.gz', True)
        if isinstance(largest_ref, sitk.Image):
            min_max = sitk.MinimumMaximumImageFilter()
            min_max.Execute(largest_hippocampus - largest_ref)
            post_ok = min_max.GetMinimum() == 0 and min_max.GetMaximum() == 0
        else:
            post_ok = False
    else:
        post_ok = False
    callback.end_test(post_ok)

    callback.end()
