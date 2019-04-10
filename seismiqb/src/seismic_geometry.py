""" SeismicGeometry-class containing geometrical info about seismic-cube."""

import numpy as np
import segyio
import logging
from tqdm import tqdm_notebook

from .utils import get_linear

class SeismicGeometry():
    """ Class to hold information about .sgy-file. """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, **kwargs):
        self.il_xl_trace = {}
        self.x_to_xline, self.y_to_iline = {}, {}
        self.ilines, self.xlines = set(), set()
        self.cdp_x, self.cdp_y = set(), set()
        self.value_min, self.value_max = np.inf, -np.inf
        self.log_path = kwargs.get('log')

        # this logging should be within load:
        #if isinstance(kwargs.get('log'), str):
            #self._log(path, path_log=kwargs.get('log'))

    def absolute_to_line(self, order=('iline', 'xline', 'h')):
        """ Get range-transforms: absolute coordinates into xline/iline/height-coords.
        """
        return [self._absolute_to_line(axis) for axis in order]

    def _absolute_to_line(self, axis):
        if axis in ['xline', 'iline']:
            from_attr, to_attr = ('cdp_x', 'xlines') if axis == 'xline' else ('cdp_y', 'ilines')
            transform = get_linear(list(getattr(self, from_attr)), list(getattr(self, to_attr)))
        elif axis == 'h':
            transform = lambda x: ((x + 280) / 4).astype(np.int64)  # fetch coords from header rather than use fixed constants!
        else:
            raise ValueError('Unknown axis!')
        return transform

    def load(self, path, **kwargs):
        """ Actual parsing of .sgy-file.
        Does one full path through the file for collecting all the
        necessary information, including:
            `il_xl_trace` dictionary for map from (iline, xline) point
                to trace number
            `ilines`, `xlines` lists with possible values of respective coordinate
            `depth` contains length of each trace
        """
        if not isinstance(path, str):
            raise ValueError('Path to a segy-cube should be supplied!')

        # init all the containers
        with segyio.open(path, 'r', strict=False) as segyfile:
            segyfile.mmap() # makes operation faster

            self.depth = len(segyfile.trace[0])

            for i in tqdm_notebook(range(len(segyfile.header))):
                header_ = segyfile.header[i]
                iline_ = header_.get(segyio.TraceField.INLINE_3D)
                xline_ = header_.get(segyio.TraceField.CROSSLINE_3D)
                cdp_x_ = header_.get(segyio.TraceField.CDP_X)
                cdp_y_ = header_.get(segyio.TraceField.CDP_Y)

                # Map:  (iline, xline) -> index of trace
                self.il_xl_trace[(iline_, xline_)] = i

                # Set: all possible values for ilines/xlines
                self.ilines.add(iline_)
                self.xlines.add(xline_)
                self.cdp_x.add(cdp_x_)
                self.cdp_y.add(cdp_y_)

                # Map:  cdp_x -> xline
                # Map:  cdp_y -> iline
                self.y_to_iline[cdp_y_] = iline_
                self.x_to_xline[cdp_x_] = xline_

                trace_ = segyfile.trace[i]
                if np.min(trace_) < self.value_min:
                    self.value_min = np.min(trace_)

                if np.max(trace_) > self.value_max:
                    self.value_max = np.max(trace_)

            # More useful variables
            self.ilines = sorted(list(self.ilines))
            self.xlines = sorted(list(self.xlines))
            self.ilines_offset = min(self.ilines)
            self.xlines_offset = min(self.xlines)
            self.ilines_len = len(self.ilines)
            self.xlines_len = len(self.xlines)
            self.cube_shape = [self.ilines_len, self.xlines_len, self.depth]


    def _log(self, path, path_log):
        """ Log some info. """
        logging.basicConfig(level=logging.INFO,
                            format=' %(message)s',
                            filename=path_log, filemode='w')
        logger = logging.getLogger('geometry_logger')

        with segyio.open(path, 'r', strict=False) as segyfile:
            header_file = segyfile.bin
            header_trace = segyfile.header[0]
            logger.info("\nFILE HEADER:")
            _ = [logger.info('{}: {}'.format(k, v))
                 for k, v in header_file.items()]

            logger.info("\nTRACE HEADER:")
            _ = [logger.info('{}: {}'.format(k, v))
                 for k, v in header_trace.items()]

        logger.info('\nSHAPES INFO:')
        logger.info('Depth of one trace is: {}'.format(self.depth))

        logger.info('Number of ILINES: '.format(self.ilines_len))
        logger.info('Number of XLINES: '.format(self.xlines_len))

        logger.info('ILINES range from {} to {}'.format(min(self.ilines), max(self.ilines)))
        logger.info('ILINES range from {} to {}'.format(min(self.xlines), max(self.xlines)))

        logger.info('CDP_X range from {} to {}'.format(min(self.cdp_x),
                                                       max(self.cdp_x)))
        logger.info('CDP_X range from {} to {}'.format(min(self.cdp_y),
                                                       max(self.cdp_y)))
