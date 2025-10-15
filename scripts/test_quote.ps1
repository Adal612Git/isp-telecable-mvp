$versionOutput = & python -c "import sys;print('.'.join(map(str, sys.version_info[:3])))" 2>$null
