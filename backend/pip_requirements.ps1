# Define input and output file paths
$inputFile = "requirements.txt"
$outputFile = "pip_requirements.txt"

# Read the content of the input file
$content = Get-Content -Path $inputFile

# Initialize an empty array to store modified lines
$modifiedLines = @()

# Process each line in the file
foreach ($line in $content) {
    # Replace '=' with '==' if found in the line
    if ($line -match "=") {
        $modifiedLines += $line -replace "=", "=="
    } else {
        $modifiedLines += $line
    }
}

# Write the modified lines to the output file
$modifiedLines | Out-File -FilePath $outputFile -Encoding UTF8

Write-Host "Conversion complete. Output saved to $outputFile"
