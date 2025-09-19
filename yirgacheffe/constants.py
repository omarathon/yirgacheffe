YSTEP = 2048
MINIMUM_CHUNKS_PER_THREAD = 1

Y_SUBCHUNKS_STEP = 1

# 0 = full read, 1 = split over Y_SUBCHUNKS_STEP with benchmarking of full overhead, 2 = split with benchmarking of just GDAL calls
SUBCHUNK_READ_METHOD = 0

# I don't really want this here, but it's just too useful having it exposed
WGS_84_PROJECTION = 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,'\
	'AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],'\
	'UNIT["degree",0.0174532925199433,AUTHORITY["EPSG","9122"]],AXIS["Latitude",NORTH],'\
	'AXIS["Longitude",EAST],AUTHORITY["EPSG","4326"]]'
