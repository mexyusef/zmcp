# ZMCP - High Performance PyQt6 MCP Client/Server

ZMCP is a desktop application implementing the Model Context Protocol (MCP).
It provides both server and client capabilities in a modern, modular interface.

## Features

### Server Features
- **Flexible Server Configuration**: Dynamically load and configure multiple MCP tool providers with visual configuration interface
- **Tool Management**: Predefined tools with easy-to-use interfaces
- **Protocol Support**: Full MCP specification compliance with support for tools, resources, and prompts
- **Performance Monitoring**: Track server activity and performance metrics

### Client Features
- **Server Connection Management**: Connect to multiple MCP servers with secure authentication
- **Tool Discovery and Usage**: Automatically discover and use tools from connected servers
- **Interactive Session Management**: Create, save, and manage interaction sessions
- **Response Visualization**: Display various content types in rich text format

## Installation

### Requirements
- Python 3.8 or higher
- PyQt6
- aiohttp

### Setup

1. Clone the repository:
```bash
git clone https://github.com/mexyusef/zmcp.git
cd zmcp
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application

Run the application using the provided startup script:
```bash
python run.py
```

### Server Mode

1. Go to the "Server" tab
2. Configure the server settings
3. Add and configure tools
4. Click "Start Server" to begin hosting

### Client Mode

1. Go to the "Client" tab
2. Enter the server URL (e.g., http://localhost:8000)
3. Click "Connect" to connect to the server
4. Browse available tools, resources, and prompts
5. Select and use tools with the provided interface

## Predefined Tools

ZMCP comes with several predefined tools:

- **Web Fetch**: Fetch content from web URLs
- **System Info**: Get information about the system
- **File Manager**: Read, write, and list files
- **Process Manager**: Execute and manage processes
- **Memory Tool**: Store and retrieve memories

## Customization

ZMCP can be customized in various ways:

- **Theme**: Choose between light and dark themes
- **Layout**: Adjust panel positions and visibility
- **Server Configuration**: Configure server settings through the visual interface
- **Tool Configuration**: Enable/disable and configure individual tools

## License

[MIT License](LICENSE)
