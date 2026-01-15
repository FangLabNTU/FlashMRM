# MRM Transition Optimization Tool

A tool for optimizing MRM (Multiple Reaction Monitoring) transitions for mass spectrometry analysis.

## Project Structure

```
.
├── config.py                  # Configuration class with all parameter settings
├── data_loader.py             # Data loading module
│   ├── DataLoader            # Basic data loader
│   └── LazyFileLoader        # Lazy file loader (memory optimized)
├── interference_calculator.py # Interference calculation module
│   ├── InterferenceCalculatorQE   # QE method interference calculator
│   └── InterferenceCalculatorNIST # NIST method interference calculator
├── ion_optimizer.py          # Ion pair optimization module
│   ├── IonPairOptimizerQE    # QE method ion pair optimizer
│   └── IonPairOptimizerNIST  # NIST method ion pair optimizer
├── memory_monitor.py          # Memory monitoring module
│   └── MemoryMonitor         # Memory usage monitor
├── mrm_optimizer.py          # Main optimizer module
│   └── MRMOptimizer          # Main optimizer class
├── validator.py              # Validation module
│   └── InterferenceDBValidator # Interference database format validator
├── main.py                   # Main entry point
└── __init__.py               # Package initialization file
```

## Module Description

### config.py
Contains all configuration parameters, defined using dataclass for easy management and modification.

### data_loader.py
- **DataLoader**: Basic data loader for loading CSV files
- **LazyFileLoader**: Lazy loader that queries data on-demand to reduce memory usage

### interference_calculator.py
- **InterferenceCalculatorQE**: Interference calculation for QE method
- **InterferenceCalculatorNIST**: Interference calculation for NIST method

### ion_optimizer.py
- **IonPairOptimizerQE**: Ion pair optimization for QE method
- **IonPairOptimizerNIST**: Ion pair optimization for NIST method

### memory_monitor.py
Memory usage monitoring that tracks memory consumption during program execution.

### validator.py
Interference database format validator for validating user-uploaded custom interference databases.

### mrm_optimizer.py
Main optimizer class that coordinates all modules to complete MRM transition optimization tasks.

### main.py
Command-line entry point that parses arguments and starts the optimization process.

## Usage

### Basic Usage

```bash
# Process 375 compounds using NIST method
python main.py --intf-db nist --max-compounds 375

# Process a single compound using QE method
python main.py --intf-db qe --single-compound --inchikey "YOUR_INCHIKEY"

# Specify output file
python main.py --output my_results.csv
```

### Using Custom Interference Database

Users can upload their own interference database files or folders for calculation:

```bash
# Use custom interference database (NIST format)
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db.csv

# Use custom interference database folder (contains multiple CSV files)
python main.py --intf-db nist --custom-intf-db /path/to/your/interference_db_folder

# Use custom interference database (QE format)
python main.py --intf-db qe --custom-intf-db /path/to/your/qe_interference_db.csv

# Skip validation (not recommended, use only when format is confirmed correct)
python main.py --intf-db nist --custom-intf-db /path/to/db --skip-validation
```

#### Interference Database Format Requirements

**Required columns for NIST method interference database:**
- `InChIKey`
- `PrecursorMZ`
- `RT`
- `MSMS`
- `NCE`
- `CE`
- `Ion_mode`
- `Precursor_type`

**Required columns for QE method interference database:**
- `Alignment ID`
- `Average Mz`
- `Average Rt(min)`
- `CE`
- `MS/MS spectrum`

The program will automatically validate the format of user-uploaded interference databases to ensure all required columns are present.

## Dependencies

- pandas
- numpy
- tqdm

## License

[Add license information]
