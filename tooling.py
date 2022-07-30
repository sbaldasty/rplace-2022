#!/usr/bin/env python

from PIL import Image
from datetime import datetime

import csv
import gzip
import numpy as np

TIMESTAMP_SORTED_GZIP = 'timestamp_sorted_history.csv.gz'

CANVAS_WIDTH = 2000
CANVAS_HEIGHT = 2000

class Analysis:
    '''
    Abstraction of an analysis to be performed on the placement history.

    The analysis handles occurrences of pixel and rectangle placements as they
    are encountered in the placement history. It typically merges each
    occurrence into some aggregate data structure it maintains.
    '''

    def __init__(self):
        self._result = None

    def on_pixel(self, timestamp, redditor, x, y, color):
        '''
        Called for each pixel placement in the placement history.

        Parameters
        ----------
        timestamp : datetime
            When the placement happened (TODO find range)

        redditor : str
            An anonamized unique identifier of the redditor who made the
            placement

        x : int
            x-coordinate of the pixel, from 0 to 1999

        y : int
            y-coordinate of the pixel, from 0 to 1999

        color : str
            An HTML-style hexadecimal representation of the **color** of the
            placement

        Returns
        -------
        None
        '''
        pass

    def on_rectangle(self, timestamp, redditor, x1, y1, x2, y2, color):
        '''
        Called for each rectangle placement in the placement history.

        Parameters
        ----------
        timestamp : datetime
            When the placement happened (TODO find range)

        redditor : str
            An anonamized unique identifier of the redditor who made the
            placement

        x1 : int
            The x-coordinate of the top-left of the rectangle, from 0 to 1999

        y1 : int
            The y-coordinate of the top-left of the rectangle, from 0 to 1999

        x2 : int
            The x-coordinate of the bottom-right of the rectangle, from 0 to
            1999, with x2 >= x1

        y2 : int
            The y-coordinate of the bottom-right of the rectangle, from 0 to
            1999, with y2 >= y1

        color : str
            An HTML-style hexadecimal representation of the **color** of the
            placement

        Returns
        -------
        None
        '''
        pass

    def result(self):
        '''
        Called after the placement history.

        Returns
        -------
        Any object representing the result of the analysis
        '''
        return self._result


def perform_analysis(analysis, gzip_path):
    '''
    Performs an analysis on the placement history.

    The placement history is large. Many machines cannot load it into memory
    fully, so instead this function feeds the analysis one row at a time for
    processing.

    Parameters
    ----------
    analysis : Analysis
        The analysis to perform
    
    gzip_path : str
        Path to the gzipped placement history file

    Returns
    -------
    The result of the analysis, the type depends on the analysis that was run
    '''

    # Number of characters that cover the date and time of a timestamp
    DATETIME_CHARS = 19

    # Indexes of columns in the placement history CSV
    TIMESTAMP_COLUMN = 0
    REDDITOR_COLUMN = 1
    COLOR_COLUMN = 2
    COORDINATE_COLUMN = 3

    with gzip.open(gzip_path, 'rt') as file:
        for row in csv.reader(file):
            timestamp = datetime.fromisoformat(row[TIMESTAMP_COLUMN][0:DATETIME_CHARS])
            redditor = row[REDDITOR_COLUMN]
            color = row[COLOR_COLUMN]
            coordinates = [int(coordinate) for coordinate in row[COORDINATE_COLUMN].split(',')]

            if len(coordinates) == 4:
                x1, y1, x2, y2 = coordinates
                analysis.on_rectangle(timestamp, redditor, x1, y1, x2, y2, color)
            else:
                x, y = coordinates
                analysis.on_pixel(timestamp, redditor, x, y, color)

    return analysis.result()

class Logger(Analysis):
    '''
    Wraps an analysis in a logger using the decorator pattern.

    The logger displays periodic updates on the processed row count on the
    console. It also displays a message when the delegate's result is being
    formulated, and a final message when it is finished.
    '''

    def __init__(self, delegate, rows_between_updates=10000):
        '''
        Initializes an instance of Logger.

        Parameters
        ----------
        delegate : Analysis
            The analysis around which to wrap this logger
        '''

        self.delegate = delegate
        self.rows_between_updates = rows_between_updates
        self.rows_processed = 0

    def log(self, message):
        MESSAGE_LENGTH = 30
        print(message.ljust(MESSAGE_LENGTH), end='\r')

    def on_any_row(self):
        self.rows_processed += 1

        if self.rows_processed % self.rows_between_updates == 0:
            self.log(str(self.rows_processed) + ' rows processed')

    def on_pixel(self, timestamp, redditor, x, y, color):
        self.delegate.on_pixel(timestamp, redditor, x, y, color)
        self.on_any_row()

    def on_rectangle(self, timestamp, redditor, x1, y1, x2, y2, color):
        self.delegate.on_rectangle(timestamp, redditor, x1, y1, x2, y2, color)
        self.on_any_row()

    def result(self):
        self.log('Formulating final result')
        result = self.delegate.result()
        self.log('Done')
        return result

def generate_image(array, rgb_provider):
    rgbs = []

    for k, v in enumerate(array):
        if k % CANVAS_WIDTH == 0:
            row = []
            rgbs.append(row)

        row.append(rgb_provider(v))

    return Image.fromarray(np.array(rgbs, dtype=np.uint8))

def generate_intensity_image(array):
    MAX_COLOR_COMPONENT = 255

    offset = min(array)
    range = max(array) - offset
    scale = MAX_COLOR_COMPONENT / range

    def rgb_provider(intensity):
        value = scale * intensity - offset
        return (value, value, value)

    return generate_image(array, rgb_provider)