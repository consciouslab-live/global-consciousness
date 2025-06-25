# ConsciousLab Live: Quantum Randomness Proxy

This is the backend proxy service for [ConsciousLab Live](https://www.youtube.com/@ConsciousLabLive), a global public experiment exploring whether human consciousness can influence quantum randomness.

> This project is a globalized continuation and modern reconstruction of the Princeton PEAR experiment.  
> It combines quantum random number generators with real-time livestream systems to explore whether human consciousness, when collectively focused, can exert statistically significant influence on random events.

## 🚀 Quick Start

### Prerequisites

- Install Python 3.8+
- Install [uv](https://docs.astral.sh/uv/)

### Steps
1. Clone repo: `git clone https://github.com/consciouslab-live/global-consciousness.git`
2. Move into repo: `cd global-consciousness`
3. Create the virtualenv using Python 3.8+: `uv venv` and activate it: `source .venv/bin/activate`
4. Install [pre-commit](https://pre-commit.com/) hooks: `pre-commit install`
5. Install dependencies: `uv pip install -r requirements.txt`
6. Create a `.env` file in the project root: `echo 'QUANTUM_API_KEY=your_api_key_here' > .env`

### Setup API Key

Get API Key from [ANU Quantum Numbers API](https://quantumnumbers.anu.edu.au/api-key)

Create a `.env` file in the project root:
```bash
echo 'QUANTUM_API_KEY=your_api_key_here' > .env
```

Replace `your_api_key_here` with your actual API key from the ANU Quantum Numbers service.

### Install VSCode Extensions

- **Ruff** (`charliermarsh.ruff`) - Fast Python linter and formatter
- **isort** (`ms-python.isort`) - Python import sorting


## 📖 Usage Examples

### Basic Quantum Cache Usage

```python
from src.core.quantum_cache import QuantumCache

# Initialize cache
cache = QuantumCache(cache_size=50, prefetch_threshold=25)
print('✅ Cache initialized successfully')

# Check status
print('Status:', cache.get_status())

# Get quantum bits
bits = cache.get_bits(10)
print('10 quantum bits:', bits)
```

### Advanced Usage

```python
from src.core.quantum_cache import QuantumCache, QuantumDataException

try:
    # Initialize with custom parameters
    cache = QuantumCache(
        cache_size=1024,
        prefetch_threshold=512,
        max_retries=3,
    )
    
    # Get single quantum bit
    bit = cache.get_bit()
    print(f"Single quantum bit: {bit}")
    
    # Get multiple bits
    random_bits = cache.get_bits(100)
    print(f"100 quantum bits: {random_bits}")
    
    # Check cache statistics
    stats = cache.get_stats()
    print(f"Cache statistics: {stats}")
    
except QuantumDataException as e:
    print(f"Quantum data error: {e}")
```

## 🔧 Features

- **Pure Quantum Data**: Uses ANU's quantum random number generator
- **Smart Caching**: Double buffering with background prefetching
- **No Fallback**: Never uses pseudo-random data to maintain purity
- **Error Handling**: Comprehensive retry mechanism with exponential backoff
- **Statistics**: Built-in performance and usage statistics
- **Environment Variables**: Secure API key management via `.env` file

## 📊 API Specifications

The service uses the new [ANU Quantum Numbers API](https://api.quantumnumbers.anu.edu.au/):
- **Endpoint**: `https://api.quantumnumbers.anu.edu.au/`
- **Authentication**: API Key via `x-api-key` header
- **Data Type**: uint8 (converted to random bits)
- **Rate Limits**: Handled automatically with retry logic

## 🔐 Security Notes

- Keep your API key secure and never commit it to version control
- The `.env` file should be added to `.gitignore`
- API keys should be rotated regularly as per security best practices

## 📝 License

MIT License

## 🔗 Related Links

- [ConsciousLab Live YouTube Channel](https://www.youtube.com/@ConsciousLabLive)
- [ANU Quantum Numbers API](https://api.quantumnumbers.anu.edu.au/)
- [Princeton PEAR Lab](https://www.princeton.edu/~pear/) (Historical reference)

