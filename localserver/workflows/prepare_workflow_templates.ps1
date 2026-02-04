$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Output "[Tapnow] Scan workflows subfolders..."

function Add-Param($map, $key, $nodeId, $inputName) {
    if (-not $key -or -not $nodeId -or -not $inputName) { return }
    if (-not $map.Contains($key)) {
        $map[$key] = [ordered]@{
            node_id = $nodeId
            field   = "inputs.$inputName"
        }
    }
}

function Get-InputNames($node) {
    if ($null -eq $node -or $null -eq $node.inputs) { return @() }
    try {
        return @($node.inputs.PSObject.Properties.Name)
    } catch {
        return @()
    }
}

Get-ChildItem -Directory | ForEach-Object {
    $dir = $_.FullName
    $jsons = Get-ChildItem -Path $dir -Filter *.json -File

    if ($jsons.Count -eq 1 -and $jsons[0].Name -ne "template.json") {
        $oldPath = $jsons[0].FullName
        $newPath = Join-Path $dir "template.json"
        Write-Output "[Rename] $($_.Name)\$($jsons[0].Name) -> template.json"
        Rename-Item -Path $oldPath -NewName "template.json"
    }

    $tplPath = Join-Path $dir "template.json"
    if (Test-Path $tplPath) {
        Write-Output "[Meta] Generating meta.json in $($_.Name)"
        $tpl = Get-Content $tplPath -Raw | ConvertFrom-Json
        $params = [ordered]@{}

        $nodes = @()
        $tpl.PSObject.Properties | ForEach-Object {
            $nodes += [pscustomobject]@{
                id        = $_.Name
                node      = $_.Value
                classType = ($_.Value.class_type | ForEach-Object { $_ })
                inputs    = Get-InputNames $_.Value
            }
        }

        # Common params auto mapping (only if unique)
        $promptCandidates = @($nodes | Where-Object { $_.inputs -contains 'text' -or $_.inputs -contains 'prompt' })
        if ($promptCandidates.Count -eq 1) {
            $pNode = $promptCandidates[0]
            if ($pNode.inputs -contains 'text') {
                $pInput = 'text'
            } else {
                $pInput = 'prompt'
            }
            Add-Param $params 'prompt' $pNode.id $pInput
        }

        $samplerCandidates = @($nodes | Where-Object {
            $_.classType -eq 'KSampler' -or ($_.inputs -contains 'seed' -or $_.inputs -contains 'steps')
        })
        if ($samplerCandidates.Count -eq 1) {
            $sNode = $samplerCandidates[0]
            if ($sNode.inputs -contains 'seed') { Add-Param $params 'seed' $sNode.id 'seed' }
            if ($sNode.inputs -contains 'steps') { Add-Param $params 'steps' $sNode.id 'steps' }
            if ($sNode.inputs -contains 'sampler_name') { Add-Param $params 'sampler' $sNode.id 'sampler_name' }
            if ($sNode.inputs -contains 'scheduler') { Add-Param $params 'scheduler' $sNode.id 'scheduler' }
        }

        $latentCandidates = @($nodes | Where-Object {
            ($_.classType -match 'Empty.*Latent') -or ($_.inputs -contains 'width' -and $_.inputs -contains 'height')
        })
        if ($latentCandidates.Count -eq 1) {
            $lNode = $latentCandidates[0]
            if ($lNode.inputs -contains 'width') { Add-Param $params 'width' $lNode.id 'width' }
            if ($lNode.inputs -contains 'height') { Add-Param $params 'height' $lNode.id 'height' }
            if ($lNode.inputs -contains 'batch_size') { Add-Param $params 'batch' $lNode.id 'batch_size' }
        }

        # Full inputs map (NodeID.input)
        $nodes | ForEach-Object {
            $nodeId = $_.id
            $nodeInputs = $_.inputs
            foreach ($inputName in $nodeInputs) {
                Add-Param $params "$nodeId.$inputName" $nodeId $inputName
            }
        }

        $meta = [ordered]@{
            name         = $_.Name
            params_map   = $params
            generated_at = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        }

        $metaPath = Join-Path $dir "meta.json"
        $meta | ConvertTo-Json -Depth 6 | Set-Content -Path $metaPath -Encoding UTF8
    } else {
        Write-Output "[Skip] $($_.Name) (no template.json)"
    }
}

Write-Output "[Tapnow] Done."
