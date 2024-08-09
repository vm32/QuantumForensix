# QuantumForensix

QuantumForensix is an advanced, cross-platform digital forensics toolkit designed for creating, analyzing, and investigating disk images and mobile devices. It provides a comprehensive set of features for digital investigators and cybersecurity professionals, offering capabilities for both traditional computer forensics and mobile device analysis.

## Features

### Core Features (Python-based)
- **Multi-format Disk Imaging**: Create and analyze both raw and E01 (Expert Witness Format) disk images.
- **File System Analysis**: Perform in-depth analysis of various file systems using the pytsk3 library.
- **File Type Detection**: Accurately detect file types based on content using the python-magic library.
- **Metadata Extraction**: Extract detailed metadata from files, including creation, modification, and access times.
- **File Carving**: Recover deleted files using signature-based file carving techniques.
- **Timeline Analysis**: Generate a comprehensive timeline of file system activities.
- **Hashing**: Calculate and verify file/disk hashes for integrity checks.
- **Logging**: Detailed logging for audit trails and debugging purposes.

### iOS Forensics (C-based module: iOSynthesis)
- **Device Communication**: Establish secure connections to iOS devices.
- **SMS Extraction**: Extract and encrypt SMS messages from iOS devices.
- **App Inventory**: Generate a list of installed applications with details.
- **Device Information**: Retrieve basic iOS device information.
- **iOS-specific Reporting**: Create forensic reports for iOS device analysis.
## Operating System Compatibility

QuantumForensix is designed to work across multiple platforms. The following table outlines the compatibility of different components with various operating systems:

| Operating System | Core QuantumForensix (Python) | iOSynthesis Module (C) | Target Analysis |
|------------------|-------------------------------|------------------------|-----------------|
| Windows          | ✅                            | ⚠️                     | ✅               |
| macOS            | ✅                            | ✅                     | ✅               |
| Linux            | ✅                            | ✅                     | ✅               |
| iOS              | ❌                            | ❌                     | ✅               |
| Android          | ❌                            | ❌                     | 🚧               |

Legend:
- ✅ Fully supported
- ⚠️ Partial support (may require additional setup)
- ❌ Not supported yet
- 🚧 Planned for future release

Notes:
1. The core QuantumForensix tool, written in Python, is cross-platform and runs on Windows, macOS, and Linux.
2. The iOSynthesis module, written in C, is primarily designed for macOS and Linux. Windows support is partial and may require additional setup (e.g., using WSL - Windows Subsystem for Linux).
3. Target Analysis refers to the ability to analyze data from these operating systems, not run on them.
4. iOS devices can be analyzed using the iOSynthesis module when connected to a supported host operating system.
5. Android analysis is planned for a future release.

Please ensure you have the necessary permissions and legal authority before analyzing any device or data.

## Installation

### Core QuantumForensix
```bash
# Clone the repository
git clone https://github.com/vm32/quantumforensix.git
cd quantumforensix

# Create a virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies
pip install -r requirements.txt
```

### iOSynthesis (iOS Forensics Module)
```bash
# Navigate to the iOSynthesis directory
cd iOSynthesis

# Compile the module
gcc -o iOSynthesis iOSynthesis.c -limobiledevice -lplist -lcrypto -lsqlite3
```

Note: You may need to install additional system libraries depending on your OS. Please refer to the documentation of libimobiledevice, OpenSSL, and SQLite for specific instructions.

## Usage

### Core QuantumForensix
Here's a basic example of how to use the main QuantumForensix toolkit:

```python
from quantumforensix import QuantumForensix

forensix = QuantumForensix()
forensix.create_disk_image('/path/to/source/device', 'disk_image.E01', format='E01')
forensix.load_image('disk_image.E01')
forensix.analyze_file_system()
print(f"Image hash: {forensix.calculate_hash()}")
metadata = forensix.extract_metadata('/path/to/file/of/interest')
print(f"File metadata: {metadata}")
carved_files = forensix.file_carving(b'\xFF\xD8\xFF\xE0')  # JPEG file signature
print(f"QuantumForensix carved {len(carved_files)} potential JPEG files")
timeline = forensix.timeline_analysis()
print("QuantumForensix timeline analysis complete")
```

### iOSynthesis (iOS Forensics Module)
To use the iOS forensics module:

```bash
# Ensure an iOS device is connected
./iOSynthesis
```

The tool will automatically:
1. Connect to the attached iOS device
2. Extract and encrypt SMS messages
3. Generate a list of installed applications
4. Create a basic forensic report

Output files:
- `sms_messages.csv.enc`: Encrypted file containing extracted SMS messages
- `installed_apps.csv`: List of installed applications
- `forensic_report.txt`: Basic report summarizing the extraction process

## Security Considerations

- The iOSynthesis module encrypts sensitive data (like SMS messages) using AES-256-CBC.
- Ensure proper key management in a production environment.
- Always obtain necessary permissions before analyzing any device or data.

## Roadmap

### Version 1.1 (Next Release)
- [ ] Implement a command-line interface (CLI) for easier interaction
- [ ] Add support for AFF4 image format
- [ ] Enhance file carving with support for more file types
- [ ] Implement basic reporting functionality for core module

### Version 1.2
- [ ] Develop a graphical user interface (GUI)
- [ ] Add support for network forensics (e.g., PCAP analysis)
- [ ] Implement data deduplication for efficient storage of forensic images
- [ ] Integrate basic machine learning for automated artifact detection

### Version 2.0
- [ ] Implement distributed processing for large-scale forensics
- [ ] Add support for cloud forensics (e.g., analyzing cloud storage artifacts)
- [ ] Develop a plugin system for extensibility
- [ ] Implement advanced data visualization for complex investigations
- [ ] Expand mobile forensics to include Android devices

## Contributing

We welcome contributions to QuantumForensix! Please see our [CONTRIBUTING.md](CONTRIBUTING.md) file for details on how to get started. Whether you're improving the core Python toolkit or enhancing the iOS module, your contributions are valuable.

## License

QuantumForensix is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Contact

For support, feature requests, or bug reports, please open an issue on our GitHub repository. For security-related issues, please refer to our security policy for responsible disclosure guidelines.

---

QuantumForensix - Unveiling digital evidence with quantum precision across multiple platforms and devices.
