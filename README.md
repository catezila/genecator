# Genecator NFT Generator

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Performance Optimized](https://img.shields.io/badge/performance-optimized-success.svg)]()
[![Production Ready](https://img.shields.io/badge/production-ready-blue.svg)]()

A **production-ready** Python-based NFT generator with advanced performance optimizations, comprehensive error handling, and robust architecture. Features layered trait composition, rarity-based selection, real-time validation, and professional-grade reliability features.

## Features

### **Core Generation Features**
- **Layered Trait Composition**: Create unique NFTs by layering multiple trait images
- **Advanced Rarity System**: Configurable rarity weights for both trait types and individual traits (1-5 scale)
- **Rule-Based Compatibility**: Define rules to prevent incompatible trait combinations
- **Uniqueness Enforcement**: Ensure generated NFTs meet configurable uniqueness criteria
- **Multiple Output Formats**: Support for PNG, JPEG, WebP, and animated GIFs
- **Resume Functionality**: Continue generation from where you left off
- **Parallel Processing**: Speed up generation with multiprocessing support
- **Metadata Generation**: OpenSea-compatible metadata with trait statistics
- **Automatic Configuration**: Auto-generate config from trait files

### **Performance & Optimization**
- **Memory-Aware Caching**: LRU cache with automatic memory management (512MB default)
- **Cache Performance Monitoring**: Real-time hit/miss ratios and memory utilization
- **Resource Management**: Context managers for automatic cleanup of file handles and memory
- **Optimized Image Processing**: Memory-efficient image loading and composition
- **Performance Statistics**: Detailed performance metrics logged during generation

### **Error Handling & Resilience**
- **Exponential Backoff Retry**: Automatic retry for I/O operations with exponential backoff
- **Circuit Breaker Pattern**: Prevents cascading failures with automatic recovery
- **Atomic File Operations**: Guaranteed data integrity for critical file writes
- **Graceful Degradation**: System continues operating even when optional features fail
- **Comprehensive Error Recovery**: Detailed error context and recovery mechanisms

### **Configuration & Validation**
- **Runtime Type Validation**: Dataclass-based validation with detailed error messages
- **Enhanced Configuration Management**: Multi-layer validation (JSON schema + runtime types)
- **Type-Safe Configuration**: Strongly-typed configuration objects throughout the application
- **Configuration Migration**: Support for configuration versioning and updates
- **Real-time Validation**: Immediate feedback on configuration errors

### **Architecture & Maintainability**
- **Dependency Injection**: Clean architecture with injectable dependencies
- **Service-Oriented Design**: Clear separation of concerns with modular components
- **Comprehensive Type Hints**: Full type coverage for better IDE support and documentation
- **Production-Grade Code**: Professional error handling and logging
- **Extensible Design**: Easy to add new features and customize behavior

### **Analysis & Utilities**
- **Collection Analysis Tools**: Utilities for checking duplicates, similarities, and validating traits
- **Performance Monitoring**: Built-in tools for monitoring system performance
- **Error Analysis**: Comprehensive error reporting and analysis tools
- **Testing Framework**: Dependency injection support for comprehensive unit testing

## Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

## Installation

1. Clone the repository:
   ```bash
    git clone https://github.com/catezila/genecator.git
   cd genecator
   ```

2. Install dependencies using uv:
   ```bash
   uv sync
   ```

   Or using pip:
   ```bash
   pip install -e .
   ```

## Quick Start

1. **Prepare Your Traits**:
   - Organize your trait images in the `traits/` directory by trait type:
   ```
   traits/
   ├── Background/
   │   ├── Blue.png
   │   ├── Blue_1.png        # Rarity 1 (rarest)
   │   ├── Red.png
   │   └── Red_Common.png    # Rarity 5 (most common)
   ├── Body/
   │   ├── Cat.png
   │   ├── Cat_Rare.png      # Rarity 1
   │   ├── Dog.png
   │   └── Dog_3.png         # Rarity 3
   ├── Eyes/
   │   ├── Normal.png
   │   ├── Blinking.gif      # Animated trait
   │   └── Laser_Eyes.png
   └── ...
   ```

2. **Generate Configuration**:
   ```bash
   uv run --no-project get_traits.py
   ```
   This will automatically scan your `traits/` directory, detect image sizes, analyze rarities from filenames, and create a `config.json` file.

3. **Create Rules (Optional)**:
   - Create a `ruler.json` file to define compatibility rules between traits.
   - Use `ruler.sample.json` as a template.
   - Rules prevent incompatible trait combinations (e.g., "Robot" body can't have "Cigar" mouth)

4. **Generate NFTs**:
   ```bash
   uv run --no-project main.py -n 1000 --max-memory 1024 --cache-size 256
   ```
   This will generate 1000 unique NFTs with enhanced performance settings (1GB memory cache, 256 image cache size).

## Usage

### Command Line Options

```bash
python main.py -h
```

Key options include:
- `-n, --num-nfts`: Number of NFTs to generate (default: 2000)
- `-c, --config`: Configuration file (default: config.json)
- `-r, --ruler`: Rules file (default: ruler.json)
- `--resume`: Resume generation by skipping existing outputs
- `--seed`: Random seed for reproducible runs
- `--workers`: Number of worker processes for generation
- `--format`: Output image format (png, jpg, jpeg, webp)
- `--quality`: Quality for lossy formats (jpg/webp)
- `--gif-duration`: Frame duration (ms) for GIF output
- `--gif-loop`: Loop count for GIF output

### Performance & Monitoring Options
- `--max-memory`: Maximum memory for image cache in MB (default: 512)
- `--cache-size`: Maximum number of cached images (default: 128)
- `--checkpoint-every`: Checkpoint frequency for resume functionality (default: 25)
- `--max-attempts`: Maximum attempts per NFT generation (default: 1000)
- `--max-trait-attempts`: Maximum attempts per trait selection (default: 100)
- `--retry-delay`: Initial delay (seconds) for exponential backoff retries (default: 1)
- `--circuit-breaker-threshold`: Failure threshold for circuit breaker (default: 5)

### Configuration

The `config.json` file defines:
- `trait_order`: Order in which traits are layered
- `priority_traits`: Traits that are prioritized for uniqueness
- `image_size`: Dimensions for generated images
- `traits`: Trait definitions with rarity weights
- `max_similar_combinations`: Controls uniqueness enforcement
- `ipfs_cid`: IPFS CID for metadata base URI

Example config.json:
```json
{
  "trait_order": ["Background", "Body", "Eyes", "Mouth"],
  "priority_traits": ["Body", "Eyes"],
  "image_size": [320, 320],
  "traits": {
    "Background": {
      "rarity": 3,
      "options": [
        {"name": "Blue", "rarity": 5},
        {"name": "Red", "rarity": 2}
      ]
    }
  },
  "max_similar_combinations": 1,
  "ipfs_cid": "your-ipfs-cid-here"
}
```

### Rarity System

Genecator uses a 1-5 rarity scale:
- 1: Rarest
- 2: Rare
- 3: Uncommon
- 4: Common
- 5: Most Common

Rarity weights can be automatically detected from filenames:
- `TraitName_1.png` (rarity 1)
- `TraitName_2.png` (rarity 2)
- `TraitName_3.png` (rarity 3)
- `TraitName_4.png` (rarity 4)
- `TraitName_5.png` (rarity 5)
- `TraitName_Rare.png` (converted to rarity 1)
- `TraitName_Legendary.png` (converted to rarity 1)
- `TraitName_Uncommon.png` (converted to rarity 3)
- `TraitName_Common.png` (converted to rarity 5)
- `TraitName_Basic.png` (converted to rarity 5)

**Note**: The `get_traits.py` script automatically analyzes filenames and assigns appropriate rarity weights based on these patterns.

### Rules

The `ruler.json` file defines compatibility rules:
```json
{
  "rules": [
    {
      "if": {
        "trait_type": "Body",
        "value": ["Robot"]
      },
      "then": {
        "trait_type": "Mouth",
        "excluded_values": ["Cigar", "Bubblegum"]
      }
    }
  ]
}
```

### Animated GIF Support

Genecator supports animated NFTs through animated GIF traits:
1. Place animated GIF files in your trait folders alongside static PNG files
2. The system will automatically detect and composite animated traits
3. All animated traits in a single NFT must have the same:
   - Frame count
   - Frame duration
   - Loop count

Example:
```
traits/
├── Background/
│   ├── Blue.png
│   └── Red.png
├── Body/
│   ├── Cat.png
│   └── AnimatedCat.gif
└── Eyes/
    ├── Normal.png
    └── Blinking.gif
```

## Output

Generated NFTs are saved in the `output/` directory:
- Images: `output/image/{id}.png` (or other format)
- Metadata: `output/metadata/{id}.json`

Additional files:
- `output/collection_stats.json`: Collection statistics
- `output/rarity_report.csv`: Trait distribution report
- `output/metadata/combined_metadata.json`: Combined metadata for all NFTs

## Utility Scripts

The `utils/` directory contains several helpful scripts for analyzing and managing your NFT collection:

### combine_metadata.py
Combines individual NFT metadata files into a single `combined_metadata.json` file for easier analysis.

```bash
uv run --no-project utils/combine_metadata.py
```

### duplicate_check.py
Checks for duplicate NFTs in your collection based on trait combinations or hash values.

```bash
uv run --no-project utils/duplicate_check.py
```

### similarity_check.py
Finds NFTs that share a specified number of identical trait values.

```bash
# Find NFTs with 3 or more identical traits
uv run --no-project utils/similarity_check.py --threshold 3

# Find NFTs with 4 or more identical traits
uv run --no-project utils/similarity_check.py --threshold 4

# Specify a custom metadata file
uv run --no-project utils/similarity_check.py --threshold 3 --file ./output/metadata/combined_metadata.json
```

### validate_traits.py
Validates your trait files and configuration against the schema.

```bash
uv run --no-project validate_traits.py
```

### Performance Monitoring

During generation, Genecator provides detailed performance metrics:

- **Cache Hit Rate**: Percentage of image cache hits vs misses
- **Memory Usage**: Current memory utilization of image cache
- **Error Statistics**: Failed attempts and recovery information
- **Generation Progress**: Real-time progress with ETA calculations
- **Circuit Breaker Status**: Real-time monitoring of error handling system
- **Retry Statistics**: Exponential backoff retry attempts and successes

Example output:
```
Image cache performance: 92.3% hit rate, 387.2MB used of 512.0MB limit
Circuit breaker: CLOSED (0 failures)
Retry statistics: 5 successful retries, 0 failures
Generation complete. Success rate: 99.8%
Failed attempts: {'trait_validation': 12, 'uniqueness': 8}
```

### Circuit Breaker Monitoring

The circuit breaker provides real-time status:

```python
from modules.resource_manager import get_circuit_breaker_status
status = get_circuit_breaker_status()
print(f"Circuit breaker state: {status['state']}")
print(f"Failure count: {status['failure_count']}")
```

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black .

# Linting
flake8

# Type checking
mypy .
```

### Architecture Overview

Genecator uses a modular, production-ready architecture with dependency injection:

#### Core Components
- **`NFTGenerator`**: Main orchestration with dependency injection
- **`ImageProcessor`**: Memory-aware image caching and processing with LRU cache
- **`ConfigManager`**: Configuration loading with runtime validation and schema enforcement
- **`ResourceManager`**: Resource management with retry logic and circuit breaker pattern
- **`Validation`**: Runtime type validation and comprehensive error reporting
- **`TraitTracker`**: Uniqueness enforcement and combination tracking
- **`MetadataManager`**: OpenSea-compatible metadata generation

#### Architecture Features
- **Dependency Injection**: Clean separation of concerns and enhanced testability
- **Service Layer**: Abstraction over external dependencies and I/O operations
- **Error Boundaries**: Isolated error handling with automatic recovery mechanisms
- **Monitoring**: Built-in performance metrics and health checks
- **Type Safety**: Comprehensive type hints throughout the codebase
- **Memory Management**: Automatic cleanup and resource management with context managers
- **Resilience Patterns**: Exponential backoff retry and circuit breaker for reliability

## Project Structure

```
genecator/
├── main.py                 # Entry point with enhanced CLI
├── get_traits.py           # Configuration generator
├── config.sample.json      # Sample configuration
├── ruler.sample.json       # Sample rules
├── pyproject.toml          # Project metadata
├── README.md               # This file
├── modules/                # Core modules
│   ├── nft_generator.py    # Main generation logic with dependency injection
│   ├── config_manager.py   # Configuration handling with runtime validation
│   ├── image_processor.py  # Memory-aware image caching and processing
│   ├── metadata_manager.py # Metadata generation
│   ├── trait_tracker.py    # Uniqueness tracking
│   ├── constants.py        # Application constants
│   ├── resource_manager.py # Resource management with retry logic and circuit breaker
│   ├── validation.py       # Runtime type validation and error reporting
│   └── dependency_container.py # Dependency injection framework
├── traits/                 # Trait images (user-provided)
├── output/                 # Generated NFTs and metadata
│   ├── image/              # Generated NFT images
│   ├── metadata/           # Individual NFT metadata files
│   ├── seen_hashes.json    # Resume functionality data
│   ├── tracker_state.json  # Uniqueness tracking state
│   ├── rng_state.json      # Random number generator state
│   └── ...                 # Collection statistics and reports
├── utils/                  # Utility scripts
└── tests/                  # Unit tests
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.