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

    _null_byte = chr(0).encode("utf-8")
    _encodings = {
        "keyword": "latin_1",
        "language": "ascii",
        "translatedKeyword": "utf-8",
        "text": "utf-8"
    }

    def __init__(self, chunk_data=None, keyword="", text=""):
        """Constructor

        Passing nothing will initialize a new iTXt chunk
        Passing chunk_data will parse an existing iTXt chunk
        :param chunk_data: for existing chunks, the chunk contents (string)
        :param keyword: for new chunks, the keyword (string)
        :param text: for new chunks, the text payload (string)
        """
        # If we are given chunk_data
        if chunk_data is not None and len(chunk_data) > 0:
            # Were we given a chunk tuple or just the data?
            if isinstance(chunk_data, tuple):
                d = chunk_data[1]
            else:
                d = chunk_data
            # Cut the chunk data
            t = self._split_chunkdata(d)
            # Get the keyword for the text chunk
            self._keyword = t["keyword"].decode(self._encodings["keyword"])
            # Parse "compressed" flag
            # 0 = uncompressed, 1 = compressed
            self._compressed = t["compressed"]
            # Parse compression method
            # 0 = zlib
            self._compression_method = t["compressionMethod"]
            # Parse the language tag
            self._lang = t["language"].decode(self._encodings["language"])
            # Parse the translated keyword (self.keyword translated into self.lang)
            self._translated_keyword = t["translatedKeyword"].decode(self._encodings["translatedKeyword"])
            # Parse the text
            if self._compressed:
                # zlib decompression
                assert self._compression_method == 0, "Unknown compression method."
                self._text = zlib.decompress(t["text"]).decode(self._encodings["text"])
            else:
                # text is uncompressed
                self._text = t["text"].decode(self._encodings["text"])
        # If we aren't given chunk data
        else:
            # Initialize defaults
            self._keyword = keyword
            # Compressed
            self._compressed = 1
            self._compression_method = 0
            # US English (Sorry, I'm biased)
            self._lang = "en-us"
            # Assume no translation needed
            self._translated_keyword = self._keyword
            # String payload
            self._text = text

    def pack(self):
        """Prepare the chunk data payload

        :return: Chunk data
        """
        # Generate the text to be written
        # This means either as-is or compressed
        if self._compressed:
            assert self._compression_method == 0, "Unknown compression method."
            t = zlib.compress(self._text.encode(self._encodings["text"]))
        else:
            t = self._text
        # Join all the chunk elements with null separators
        return self._null_byte.join(
            [
                self._keyword.encode(self._encodings["keyword"]),
                (chr(self._compressed) + chr(self._compression_method)).encode("utf-8") + \
                    self._lang.encode(self._encodings["language"]),
                self._translated_keyword.encode(self._encodings["translatedKeyword"]),
                t
            ]
        )

    def get_chunk(self):
        """Prepare this chunk to be written to a PNG

        :return: A chunk tuple, ready to be written with png.write_chunks()
        """
        return bytes("iTXt", "iso8859-1"), self.pack()

    def print(self):
        """Print the chunk data for debugging purposes"""
        p = self.get_chunkdata()
        print("iTXt chunk contents:")
        for k in p.keys():
            print('  ' + k + ': "' + str(p[k]) + '"')

    def get_chunkdata(self):
        """Return a dict of the decoded chunk data elements"""
        return {
            "keyword": self._keyword,
            "compressed": bool(self._compressed),
            "compressionMethod": self._compression_method,
            "language": self._lang,
            "translatedKeyword": self._translated_keyword,
            "text": self._text
        }

    @staticmethod
    def _split_chunkdata(s):
        """Split the chunk data string on null separators and byte bounds

        :param s: The binary string to cut
        :return: dict of raw chunk elements
        """
        r = {}
        # Split on \x00
        t = s.split(ChunkITXT._null_byte, maxsplit=1)
        r["keyword"] = t[0]
        r["compressed"] = t[1][0]
        r["compressionMethod"] = t[1][1]
        # Split on \x00
        t = t[1][2:].split(ChunkITXT._null_byte, maxsplit=2)
        r["language"] = t[0]
        r["translatedKeyword"] = t[1]
        r["text"] = t[2]
        # return the dict
        return r