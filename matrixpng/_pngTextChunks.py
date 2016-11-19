#!/usr/bin/env python3
"""Handle iTXt chunks

The canonical source for this package is https://github.com/finitemobius/matrixpng-py
This code is lifted from Rad Lexus's answer to this StackOverflow question:
http://stackoverflow.com/questions/37068414/how-to-modify-a-compressed-itxt-record-of-an-existing-file-in-python
See the PNG specification for more info:
http://www.libpng.org/pub/png/spec/1.2/PNG-Chunks.html#C.iTXt
"""

import zlib

__author__ = "Finite Mobius, LLC"
__credits__ = ["Rad Lexus", "Jason R. Miller"]
__license__ = "MIT"
__version__ = "alpha"
__maintainer__ = "Finite Mobius, LLC"
__email__ = "jason@finitemobius.com"
__status__ = "Development"


class ChunkITXT:
    """Class to handle iTXt chunks for PNG files"""
    # TODO: Validate chunk parameters

    def __init__(self, chunk_data=None, keyword='', text=''):
        """Constructor

        Passing nothing will initialize a new iTXt chunk
        Passing chunk_data will parse an existing iTXt chunk
        :param chunk_data: for existing chunks, the chunk contents (string)
        :param keyword: for new chunks, the keyword (string)
        :param text: for new chunks, the text payload (string)
        """

        # If we are given chunk_data
        if chunk_data is not None and chunk_data != '':
            # Cut the chunk data
            t = self._split_chunkdata(chunk_data)
            # Get the keyword for the text chunk
            self._keyword = t[0]
            # Parse 'compressed' flag
            # 0 = uncompressed, 1 = compressed
            self._compressed = ord(t[1][0])
            # Parse compression method
            # 0 = zlib
            self._compression_method = ord(t[1][1])
            # Parse the language tag
            self._lang = t[1][2:]
            # Parse the translated keyword (self.keyword translated into self.lang)
            self._translated_keyword = t[2]
            # Parse the text
            if self._compressed:
                # zlib decompression
                assert self._compression_method == 0, "Unknown compression method."
                self._text = zlib.decompress(t[3])
            else:
                # text is uncompressed
                self._text = t[3]
        # If we aren't given chunk data
        else:
            # Initialize defaults
            self._keyword = keyword
            # Compressed
            self._compressed = 1
            self._compression_method = 0
            # US English (Sorry, I'm biased)
            self._lang = 'en-us'
            # Assume no translation needed
            self._translated_keyword = self._keyword
            # String payload
            self._text = text

    def pack(self):
        """Prepare this chunk to be written to a PNG

        :return: A chunk, ready to be written with png.write_chunks()
        """
        # Generate the text to be written
        # This means either as-is or compressed
        if self._compressed:
            assert self._compression_method == 0, "Unknown compression method."
            t = zlib.compress(self._text.encode(encoding='utf-8'))
        else:
            t = self._text
        # Join all the chunk elements with null separators
        # Return a tuple to match png.Reader.chunk()
        return chr(0).encode('utf-8').join([
            self._keyword.encode('utf-8'),
            (chr(self._compressed) + chr(self._compression_method) + self._lang).encode('utf-8'),
            self._translated_keyword.encode('utf-8'),
            t])

    def get_chunk(self):
        return 'iTXt', self.pack()

    def show(self):
        """List the chunk data for debugging purposes"""
        print('iTXt chunk contents:')
        print('  keyword: "' + self._keyword + '"')
        print('  compressed: ' + str(self._compressed))
        print('  compression method: ' + str(self._compression_method))
        print('  language: "' + self._lang + '"')
        print('  tag translation: "' + self._translated_keyword + '"')
        print('  text: "' + self._text + '"')

    @staticmethod
    def _split_chunkdata(s):
        """Split the chunk data string on null separators

        Also validates that there are enough null separators
        :param s: The string to cut
        :return: The split string
        """
        # Split on \x00
        r = s.split(chr(0))
        # By the definition of this chunk type, there should be exactly three null separators
        assert len(r) == 4, "Invalid iTXt chunk. (Incorrect number of null separators.)"
        # return the list
        return r
