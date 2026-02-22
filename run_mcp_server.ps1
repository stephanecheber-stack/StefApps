
Write-Host "Starting MCP SQLite Server..."
$dbPath = Join-Path (Get-Location) "workflow.db"
npx -y @modelcontextprotocol/server-sqlite --db $dbPath
