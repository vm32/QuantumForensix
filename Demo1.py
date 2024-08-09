import os
import hashlib
import struct
import logging
from datetime import datetime
from collections import namedtuple
import magic  # for file type detection
import pyewf  # for E01 image support
import pytsk3  # for file system analysis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

FileEntry = namedtuple('FileEntry', ['name', 'path', 'size', 'created', 'modified', 'accessed', 'file_type'])

class AdvancedFTKImager:
    def __init__(self):
        self.image = None
        self.filesystem = None

    def create_disk_image(self, source_path, output_path, format='raw'):
        logger.info(f"Creating disk image of {source_path}")
        if format == 'raw':
            self._create_raw_image(source_path, output_path)
        elif format == 'E01':
            self._create_e01_image(source_path, output_path)
        else:
            raise ValueError("Unsupported image format")
        
        self.image = output_path
        logger.info(f"Disk image created: {output_path}")

    def _create_raw_image(self, source_path, output_path):
        with open(source_path, 'rb') as source, open(output_path, 'wb') as output:
            while True:
                chunk = source.read(1024 * 1024)  # Read 1MB at a time
                if not chunk:
                    break
                output.write(chunk)

    def _create_e01_image(self, source_path, output_path):
        ewf_handle = pyewf.handle()
        ewf_handle.create(output_path)
        
        with open(source_path, 'rb') as source:
            while True:
                chunk = source.read(1024 * 1024)  # Read 1MB at a time
                if not chunk:
                    break
                ewf_handle.write(chunk)
        
        ewf_handle.close()

    def load_image(self, image_path):
        logger.info(f"Loading image: {image_path}")
        self.image = pytsk3.Img_Info(image_path)
        self.filesystem = pytsk3.FS_Info(self.image)

    def analyze_file_system(self):
        if not self.filesystem:
            logger.error("No filesystem loaded. Please load an image first.")
            return

        logger.info("Analyzing file system")
        root_dir = self.filesystem.open_dir(path="/")
        self._recurse_files(root_dir, "/")

    def _recurse_files(self, directory, path):
        for entry in directory:
            try:
                file_name = entry.info.name.name.decode('utf8')
                file_path = os.path.join(path, file_name)
                
                if entry.info.meta:
                    file_type = self._get_file_type(entry)
                    created = datetime.fromtimestamp(entry.info.meta.crtime)
                    modified = datetime.fromtimestamp(entry.info.meta.mtime)
                    accessed = datetime.fromtimestamp(entry.info.meta.atime)
                    
                    file_entry = FileEntry(
                        name=file_name,
                        path=file_path,
                        size=entry.info.meta.size,
                        created=created,
                        modified=modified,
                        accessed=accessed,
                        file_type=file_type
                    )
                    
                    logger.info(f"Found: {file_entry}")
                
                if entry.info.name.type == pytsk3.TSK_FS_NAME_TYPE_DIR:
                    sub_directory = self.filesystem.open_dir(path=file_path)
                    self._recurse_files(sub_directory, file_path)
            
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")

    def _get_file_type(self, entry):
        try:
            file_data = entry.read_random(0, min(entry.info.meta.size, 1024))
            return magic.from_buffer(file_data, mime=True)
        except:
            return "unknown"

    def calculate_hash(self, algorithm='sha256'):
        if not self.image:
            logger.error("No disk image loaded. Please create or load an image first.")
            return

        logger.info(f"Calculating {algorithm} hash")
        hash_obj = hashlib.new(algorithm)
        for chunk in iter(lambda: self.image.read(1024 * 1024), b""):
            hash_obj.update(chunk)
        return hash_obj.hexdigest()

    def extract_metadata(self, file_path):
        logger.info(f"Extracting metadata for {file_path}")
        file_object = self.filesystem.open(file_path)
        meta = file_object.info.meta
        
        return FileEntry(
            name=os.path.basename(file_path),
            path=file_path,
            size=meta.size,
            created=datetime.fromtimestamp(meta.crtime),
            modified=datetime.fromtimestamp(meta.mtime),
            accessed=datetime.fromtimestamp(meta.atime),
            file_type=self._get_file_type(file_object)
        )

    def file_carving(self, file_signature):
        logger.info(f"Carving files with signature: {file_signature.hex()}")
        carved_files = []
        
        chunk_size = 512
        offset = 0
        
        while True:
            chunk = self.image.read(offset, chunk_size)
            if not chunk:
                break
            
            if file_signature in chunk:
                file_start = offset + chunk.index(file_signature)
                carved_file = self._extract_carved_file(file_start, file_signature)
                if carved_file:
                    carved_files.append(carved_file)
            
            offset += chunk_size

        return carved_files

    def _extract_carved_file(self, start_offset, signature):
        # This is a simplified carving process. In reality, you'd need to implement
        # file-specific carving techniques for each file type.
        max_file_size = 10 * 1024 * 1024  # 10 MB max file size for this example
        
        file_data = self.image.read(start_offset, max_file_size)
        end_offset = file_data.find(b'\xFF\xD9')  # Example: JPEG end marker
        
        if end_offset != -1:
            return file_data[:end_offset + 2]
        return None

    def timeline_analysis(self):
        logger.info("Performing timeline analysis")
        timeline = []
        root_dir = self.filesystem.open_dir(path="/")
        self._recurse_timeline(root_dir, "/", timeline)
        return sorted(timeline, key=lambda x: x[0])  # Sort by timestamp

    def _recurse_timeline(self, directory, path, timeline):
        for entry in directory:
            try:
                file_name = entry.info.name.name.decode('utf8')
                file_path = os.path.join(path, file_name)
                
                if entry.info.meta:
                    timeline.extend([
                        (entry.info.meta.crtime, 'Created', file_path),
                        (entry.info.meta.mtime, 'Modified', file_path),
                        (entry.info.meta.atime, 'Accessed', file_path),
                    ])
                
                if entry.info.name.type == pytsk3.TSK_FS_NAME_TYPE_DIR:
                    sub_directory = self.filesystem.open_dir(path=file_path)
                    self._recurse_timeline(sub_directory, file_path, timeline)
            
            except Exception as e:
                logger.error(f"Error processing {file_path}: {str(e)}")

# Usage example
imager = AdvancedFTKImager()
imager.create_disk_image('/path/to/source/device', 'disk_image.E01', format='E01')
imager.load_image('disk_image.E01')
imager.analyze_file_system()
print(f"Image hash: {imager.calculate_hash()}")
metadata = imager.extract_metadata('/path/to/file/of/interest')
print(f"File metadata: {metadata}")
carved_files = imager.file_carving(b'\xFF\xD8\xFF\xE0')  # JPEG file signature
print(f"Carved {len(carved_files)} potential JPEG files")
timeline = imager.timeline_analysis()
print("Timeline analysis complete")
