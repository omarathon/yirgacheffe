import math
import os
import tempfile

import numpy as np
import pytest

from helpers import gdal_dataset_of_region, gdal_dataset_with_data, make_vectors_with_id
from yirgacheffe import WGS_84_PROJECTION
from yirgacheffe.layers import GroupLayer, RasterLayer, TiledGroupLayer, VectorLayer
from yirgacheffe.window import Area, PixelScale, Window

def test_empty_group():
    with pytest.raises(ValueError):
        _ = GroupLayer(set())

def test_single_raster_layer_in_group():
    area = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area, 0.2))
    assert raster1.area == area
    assert raster1.window == Window(0, 0, 100, 100)
    assert raster1.sum() != 0

    group = GroupLayer([raster1])
    assert group.area == area
    assert group.window == Window(0, 0, 100, 100)
    assert group.sum() == raster1.sum()

def test_mismatched_layers():
    area1 = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area1, 0.2))
    area2 = Area(-10, 10, 10, -10)
    raster2 = RasterLayer(gdal_dataset_of_region(area2, 0.3))

    with pytest.raises(ValueError):
        _ = GroupLayer([raster1, raster2])

@pytest.mark.parametrize("klass", [GroupLayer, TiledGroupLayer])
def test_two_raster_areas_side_by_side(klass):
    area1 = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area1, 0.2))
    area2 = Area(10, 10, 30, -10)
    raster2 = RasterLayer(gdal_dataset_of_region(area2, 0.2))

    group = klass([raster1, raster2])
    assert group.area == Area(-10, 10, 30, -10)
    assert group.window == Window(0, 0, 200, 100)
    assert group.sum() == raster1.sum() + raster2.sum()

@pytest.mark.parametrize("klass", [GroupLayer, TiledGroupLayer])
def test_two_raster_areas_top_to_bottom(klass):
    area1 = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area1, 0.2))
    area2 = Area(10, 10, 30, -10)
    raster2 = RasterLayer(gdal_dataset_of_region(area2, 0.2))

    group = klass([raster1, raster2])
    assert group.area == Area(-10, 10, 30, -10)
    assert group.window == Window(0, 0, 200, 100)
    assert group.sum() == raster1.sum() + raster2.sum()

@pytest.mark.parametrize("klass,dims",
    [
        (GroupLayer, 2),
        (TiledGroupLayer, 2),
        (GroupLayer, 3),
        (TiledGroupLayer, 3),
    ]
)
def test_four_tiles(klass, dims):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            raster = RasterLayer(gdal_dataset_with_data(
                (10.0 * x, -10 * y),
                2.0,
                np.full((5, 5), (y * dims) + x)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(0, 0, 10 * dims, -10 * dims)
    assert group.window == Window(0, 0, 5 * dims, 5 * dims)
    assert group.sum() == np.array([x.sum() for x in rasters]).sum()

@pytest.mark.parametrize("klass,dims",
    [
        (GroupLayer, 2),
        (TiledGroupLayer, 2),
        (GroupLayer, 3),
        (TiledGroupLayer, 3),
    ]
)
def test_overlapping_tiles(klass, dims):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            raster = RasterLayer(gdal_dataset_with_data(
                (-2 + (10 * x), 2 + (-10 * y)),
                2.0,
                np.full((7, 7), (y * dims) + x)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(-2, 2, (10 * dims) + 2, (-10 * dims) - 2)
    assert group.window == Window(0, 0, (5 * dims) + 2, (5 * dims) + 2)
    assert group.read_array(0, 0, (5 * dims) + 2, (5 * dims) + 2).shape == ((5 * dims) + 2, (5 * dims) + 2)

def test_two_raster_read_only_from_one():
    area1 = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area1, 0.2))
    area2 = Area(-10, -10, 10, -30)
    raster2 = RasterLayer(gdal_dataset_of_region(area2, 0.2))

    group = GroupLayer([raster1, raster2])
    assert group.area == Area(-10, 10, 10, -30)
    assert group.window == Window(0, 0, 100, 200)

    data = group.read_array(0, 0, 10, 10)
    expected = raster1.read_array(0, 0, 10, 10)
    assert (data == expected).all()

def test_two_raster_read_only_from_other():
    area1 = Area(-10, 10, 10, -10)
    raster1 = RasterLayer(gdal_dataset_of_region(area1, 0.2))
    area2 = Area(-10, -10, 10, -30)
    raster2 = RasterLayer(gdal_dataset_of_region(area2, 0.2))

    group = GroupLayer([raster1, raster2])
    assert group.area == Area(-10, 10, 10, -30)
    assert group.window == Window(0, 0, 100, 200)

    data = group.read_array(0, 100, 10, 10)
    expected = raster2.read_array(0, 0, 10, 10)
    assert (data == expected).all()

def test_single_vector_layer_in_group():
    with tempfile.TemporaryDirectory() as tempdir:
        path = os.path.join(tempdir, "test.gpkg")
        area = Area(-10.0, 10.0, 10.0, -10.0)
        make_vectors_with_id(42, {area}, path)

        vector1 = VectorLayer.layer_from_file(path, None, PixelScale(0.2, -0.2), WGS_84_PROJECTION)
        assert vector1.area == area
        assert vector1.window == Window(0, 0, 100, 100)
        assert vector1.sum() == (vector1.window.xsize * vector1.window.ysize)

        group = GroupLayer([vector1])
        assert group.area == area
        assert group.window == Window(0, 0, 100, 100)
        assert group.sum() == vector1.sum()

def test_overlapping_vector_layers():
    with tempfile.TemporaryDirectory() as tempdir:
        path1 = os.path.join(tempdir, "test1.gpkg")
        area1 = Area(-10.0, 10.0, 10.0, -10.0)
        make_vectors_with_id(42, {area1}, path1)
        vector1 = VectorLayer.layer_from_file(path1, None, PixelScale(0.2, -0.2), WGS_84_PROJECTION)

        path2 = os.path.join(tempdir, "test2.gpkg")
        area2 = Area(-0.0, 10.0, 20.0, -10.0)
        make_vectors_with_id(24, {area2}, path2)
        vector2 = VectorLayer.layer_from_file(path2, None, PixelScale(0.2, -0.2), WGS_84_PROJECTION)

        group = GroupLayer([vector1, vector2])
        assert group.area == Area(-10, 10, 20, -10)
        assert group.window == Window(0, 0, 150, 100)
        assert group.sum() == vector1.sum() + (vector2.sum() / 2)

@pytest.mark.parametrize("klass", [GroupLayer, TiledGroupLayer])
def test_with_window_adjust(klass):
    with tempfile.TemporaryDirectory() as tempdir:
        layers = []
        for idx in range(1, 11):
            path = os.path.join(tempdir, f"{idx}.gpkg")
            area = Area(idx, 10, idx+1, -10)
            make_vectors_with_id(idx, {area}, path)
            vector = VectorLayer.layer_from_file(path, None, PixelScale(0.1, -0.1),
                WGS_84_PROJECTION, burn_value="id_no")
            layers.append(vector)

        group = klass(layers)
        assert group.area == Area(1, 10, 11, -10)
        assert group.window == Window(0, 0, 100, 200)

        # Test before we apply a window
        row = group.read_array(0, 0, 100, 1)[0]
        for idx in range(len(row)):
            assert row[idx] == math.ceil((idx + 1) / 10.0)

        # Test also for manual offsets that we get expected result
        for idx in range(0, 10):
            row = group.read_array(idx * 10, 0, 10, 1)[0]
            assert (row == (idx + 1)).all()

        # now apply a window over each zone and check we
        # get what we expect
        for idx in range(1, 11):
            group.reset_window()
            area = Area(idx, 10, idx+1, -10)
            group.set_window_for_intersection(area)
            row = group.read_array(0, 0, 10, 1)
            assert (row == idx).all()

@pytest.mark.parametrize("klass,dims",
    [
        (GroupLayer, 2),
        (TiledGroupLayer, 2),
        (GroupLayer, 3),
        (TiledGroupLayer, 3),
    ]
)
def test_multipe_tiles_with_window(klass, dims):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            raster = RasterLayer(gdal_dataset_with_data(
                (10.0 * x, -10 * y),
                2.0,
                np.full((5, 5), (y * dims) + x)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(0, 0, 10 * dims, -10 * dims)
    assert group.window == Window(0, 0, 5 * dims, 5 * dims)

    area = Area(group.area.left + 4.0, group.area.top - 4.0, group.area.right - 4.0, group.area.bottom + 4.0)
    group.set_window_for_intersection(area)
    assert group.window == Window(2, 2, (5 * dims) - 4, (5 * dims) - 4)
    assert group.read_array(0, 0, (5 * dims) - 4, (5 * dims) - 4).shape == ((5 * dims) - 4, (5 * dims) - 4)

@pytest.mark.parametrize("klass,dims",
    [
        (GroupLayer, 2),
        (TiledGroupLayer, 2),
        (GroupLayer, 3),
        (TiledGroupLayer, 3),
    ]
)
def test_overlapping_tiles_with_window(klass, dims):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            raster = RasterLayer(gdal_dataset_with_data(
                (-2 + (10 * x), 2 + (-10 * y)),
                2.0,
                np.full((7, 7), (y * dims) + x)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(-2, 2, (10 * dims) + 2, (-10 * dims) - 2)
    assert group.window == Window(0, 0, (5 * dims) + 2, (5 * dims) + 2)

    area = Area(group.area.left + 4.0, group.area.top - 4.0, group.area.right - 4.0, group.area.bottom + 4.0)
    group.set_window_for_intersection(area)
    assert group.window == Window(2, 2, (5 * dims) - 2, (5 * dims) - 2)
    assert group.read_array(0, 0, (5 * dims) - 4, (5 * dims) - 4).shape == ((5 * dims) - 4, (5 * dims) - 4)

@pytest.mark.parametrize("klass,dims,remove",
    [
        (GroupLayer, 3, 0),
        (TiledGroupLayer, 3, 0),
        (GroupLayer, 3, 1),
        (TiledGroupLayer, 3, 1),
        (GroupLayer, 3, 2),
        (TiledGroupLayer, 3, 2),
        (GroupLayer, 3, 3),
        (TiledGroupLayer, 3, 3),
        (GroupLayer, 3, 4),
        (TiledGroupLayer, 3, 4),
        (GroupLayer, 3, 5),
        (TiledGroupLayer, 3, 5),
        (GroupLayer, 3, 6),
        (TiledGroupLayer, 3, 6),
        (GroupLayer, 3, 7),
        (TiledGroupLayer, 3, 7),
        (GroupLayer, 3, 8),
        (TiledGroupLayer, 3, 8),
    ]
)
def test_multipe_tiles_with_missing_tile(klass, dims, remove):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            val = (y * dims) + x
            if val == remove:
                continue
            raster = RasterLayer(gdal_dataset_with_data(
                (10.0 * x, -10 * y),
                2.0,
                np.full((5, 5), val)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(0, 0, 10 * dims, -10 * dims)
    assert group.window == Window(0, 0, 5 * dims, 5 * dims)

    area = Area(group.area.left + 4.0, group.area.top - 4.0, group.area.right - 4.0, group.area.bottom + 4.0)
    group.set_window_for_intersection(area)
    assert group.window == Window(2, 2, (5 * dims) - 4, (5 * dims) - 4)
    assert group.read_array(0, 0, (5 * dims) - 4, (5 * dims) - 4).shape == ((5 * dims) - 4, (5 * dims) - 4)


@pytest.mark.parametrize("klass,dims,remove",
    [
        (GroupLayer, 3, 0),
        (TiledGroupLayer, 3, 0),
        (GroupLayer, 3, 1),
        (TiledGroupLayer, 3, 1),
        (GroupLayer, 3, 2),
        (TiledGroupLayer, 3, 2),
        (GroupLayer, 3, 3),
        (TiledGroupLayer, 3, 3),
        (GroupLayer, 3, 4),
        (TiledGroupLayer, 3, 4),
        (GroupLayer, 3, 5),
        (TiledGroupLayer, 3, 5),
        (GroupLayer, 3, 6),
        (TiledGroupLayer, 3, 6),
        (GroupLayer, 3, 7),
        (TiledGroupLayer, 3, 7),
        (GroupLayer, 3, 8),
        (TiledGroupLayer, 3, 8),
    ]
)
def test_oversized_tiles_with_missing_tile(klass, dims, remove):
    rasters = []
    for x in range(dims):
        for y in range(dims):
            val = (y * dims) + x
            if val == remove:
                continue
            raster = RasterLayer(gdal_dataset_with_data(
                (-2 + (10 * x), 2 + (-10 * y)),
                2.0,
                np.full((7, 7), val)
            ))
            rasters.append(raster)

    group = klass(rasters)
    assert group.area == Area(-2, 2, (10 * dims) + 2, (-10 * dims) - 2)
    assert group.window == Window(0, 0, (5 * dims) + 2, (5 * dims) + 2)

    area = Area(group.area.left + 4.0, group.area.top - 4.0, group.area.right - 4.0, group.area.bottom + 4.0)
    group.set_window_for_intersection(area)
    assert group.window == Window(2, 2, (5 * dims) - 2, (5 * dims) - 2)
    assert group.read_array(0, 0, (5 * dims) - 4, (5 * dims) - 4).shape == ((5 * dims) - 4, (5 * dims) - 4)
