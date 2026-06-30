"""
DM File Processing Module

This module provides a cohesive unit for processing Gatan DigitalMicrograph files (DM3/DM4).
It contains all the components needed for the complete DM file processing pipeline:

- readers: High-level file reading coordination and orchestration
- parsers: File structure parsing and metadata extraction  
- decoders: Low-level binary data decoding functions

The components work together in a pipeline:
1. Readers coordinate the overall process and use parsers
2. Parsers extract file structure and use decoders for binary data
3. Decoders provide low-level functions for reading different data types

This organization keeps all DM file processing logic together, making it easier
to understand, test, and maintain the file format support.
"""

# Import main classes for external use
from .readers import DM_EELS_Reader
from .parsers import DM_InfoParser, DM_EELS_data
