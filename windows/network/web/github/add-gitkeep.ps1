#This file go through all dir and find empty folder, then add a .gitkeep file to that.
Get-ChildItem -Directory -Recurse | 
    Where-Object { (Get-ChildItem $_.FullName -Force | Measure-Object).Count -eq 0 } |
    ForEach-Object { New-Item -Path ($_.FullName + "\.gitkeep") -ItemType File -Force }
