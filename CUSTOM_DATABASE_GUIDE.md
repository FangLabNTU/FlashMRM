# Custom Interference Database Usage Guide

This guide explains how to prepare and use custom interference databases.

## Feature Description

The program supports users uploading their own interference database files or folders for MRM transition optimization calculations. Uploaded interference databases are automatically validated to ensure all required columns are present.

## Interference Database Format Requirements

### NIST Method Interference Database

**Required columns:**
- `InChIKey`: Compound InChIKey identifier
- `PrecursorMZ`: Precursor ion m/z value
- `RT`: Retention time (minutes)
- `MSMS`: Fragment ion m/z value
- `NCE`: Normalized collision energy
- `CE`: Collision energy
- `Ion_mode`: Ion mode (e.g., 'P' for positive ion mode)
- `Precursor_type`: Precursor type (e.g., '[M+H]+')

**Example CSV format:**
```csv
InChIKey,PrecursorMZ,RT,MSMS,NCE,CE,Ion_mode,Precursor_type
YASYVMFAVPKPKE-UHFFFAOYSA-N,202.0433,10.5,175.0320,30.0,30.0,P,[M+H]+
```

### QE Method Interference Database

**Required columns:**
- `Alignment ID`: Alignment ID
- `Average Mz`: Average m/z value
- `Average Rt(min)`: Average retention time (minutes)
- `CE`: Collision energy
- `MS/MS spectrum`: MS/MS spectrum string (format: mz1:intensity1 mz2:intensity2 ...)

**Example CSV format:**
```csv
Alignment ID,Average Mz,Average Rt(min),CE,MS/MS spectrum
ID001,202.0433,10.5,30.0,175.0320:1000 131.0600:500
```

## Usage

### 1. Prepare Interference Database File

Ensure your interference database file or folder contains all required columns and is saved in CSV format.

### 2. Use Command-Line Arguments

```bash
# Use a single CSV file as interference database
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db.csv

# Use a folder containing multiple CSV files as interference database
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db_folder

# Use relative path
python main.py --intf-db nist --custom-intf-db ./my_interference_db.csv
```

### 3. Validation Process

The program automatically validates the interference database format:
- Checks if path exists
- Checks file format (must be CSV)
- Checks if all required columns are present
- Displays basic information about the interference database (file count, row count, etc.)

If validation fails, the program will display detailed error messages to help you correct the format.

### 4. Skip Validation (Not Recommended)

Only use `--skip-validation` when you are certain the interference database format is completely correct:

```bash
python main.py --intf-db nist --custom-intf-db /path/to/db --skip-validation
```

## Notes

1. **File Encoding**: Ensure CSV files use UTF-8 encoding
2. **Column Name Case**: Column names must exactly match requirements (including case)
3. **Data Types**: Numeric columns (such as PrecursorMZ, RT, etc.) should be numeric type
4. **File Size**: Large files will be read in chunks and not loaded into memory all at once
5. **Folder Structure**: If using a folder, all CSV files should have the same column structure

## Examples

### Example 1: Using a Single File

```bash
python main.py \
    --intf-db nist \
    --custom-intf-db ./my_custom_interference.csv \
    --max-compounds 100 \
    --output results_with_custom_db.csv
```

### Example 2: Using a Folder

```bash
python main.py \
    --intf-db nist \
    --custom-intf-db ./interference_databases/my_db_folder \
    --max-compounds 50
```

### Example 3: QE Method Custom Interference Database

```bash
python main.py \
    --intf-db qe \
    --custom-intf-db ./qe_interference_db.csv \
    --single-compound \
    --inchikey "YOUR_INCHIKEY"
```

## Troubleshooting

### Error: Interference database path does not exist
- Check if the path is correct
- Use absolute path or ensure relative path is correct

### Error: Missing required columns
- Check if CSV file contains all required columns
- Ensure column names are spelled correctly (including case)

### Error: Incorrect file format
- Ensure file is in CSV format
- Check if file encoding is UTF-8

### Performance Issues
- Large files will be automatically processed in chunks
- If folder contains many files, first run may take longer to build index

## Technical Support

If you encounter problems, please check:
1. Whether interference database format meets requirements
2. Whether file path is correct
3. Whether file encoding is UTF-8
4. Check detailed error messages in log output
