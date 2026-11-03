<#
补全第 15 页的 Hausdorff 维数图解。
只替换该页既有文本框的文字，保留模板的布局、图形和样式。
#>

[CmdletBinding()]
param(
    [string]$Source = "fractal_ppt_outline_template.pptx",
    [string]$Output = "fractal_ppt_outline_template_hausdorff.pptx"
)

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

Copy-Item -LiteralPath $Source -Destination $Output -Force
$archive = [System.IO.Compression.ZipFile]::Open((Resolve-Path -LiteralPath $Output), [System.IO.Compression.ZipArchiveMode]::Update)

try {
    $entry = $archive.GetEntry("ppt/slides/slide15.xml")
    if ($null -eq $entry) {
        throw "未找到第 15 页的 XML 内容。"
    }

    $reader = [System.IO.StreamReader]::new($entry.Open(), [System.Text.Encoding]::UTF8)
    $xmlText = $reader.ReadToEnd()
    $reader.Dispose()

    # 将两组“数覆盖块”的图，补全为 Hausdorff 覆盖成本及其临界指数。
    $changes = [ordered]@{
        "例 1：线段" = "例 1：线段的临界指数"
        "尺度 r = 1/4&#xA;需要 N(r)=4 个小段" = "4 个直径 r=1/4 的小段覆盖"
        "N(r) ≈ r⁻¹  ⇒  dim = 1" = "4·(1/4)^s = 4^(1−s)；临界 s=1 ⇒ dim=1"
        "例 2：正方形" = "例 2：正方形的临界指数"
        "尺度 r = 1/4&#xA;需要 N(r)=16 个小方格" = "16 个边长 r=1/4 的小格覆盖"
        "N(r) ≈ r⁻²  ⇒  dim = 2" = "16·(1/4)^s = 4^(2−s)；临界 s=2 ⇒ dim=2"
        "当尺度 r 变小，若覆盖数 N(r) 大约按 r⁻ˢ 增长，&#xA;这个指数 s 就对应对象的维数。" = "s 小于临界值：覆盖成本趋于 ∞；s 大于临界值：趋于 0。&#xA;刚好稳定的临界 s，就是 Hausdorff 维数。"
        "关键：Hausdorff 维数不是推翻经典维数，而是把它推广到更不规则的集合。" = "读法：N(r)≈r⁻ˢ 时，临界指数 s 重现线段的 1 维与正方形的 2 维。"
    }

    foreach ($change in $changes.GetEnumerator()) {
        if (-not $xmlText.Contains($change.Key)) {
            throw "未在第 15 页找到预期文本：$($change.Key)"
        }
        $xmlText = $xmlText.Replace($change.Key, $change.Value)
    }

    $entry.Delete()
    $newEntry = $archive.CreateEntry("ppt/slides/slide15.xml", [System.IO.Compression.CompressionLevel]::Optimal)
    $writer = [System.IO.StreamWriter]::new($newEntry.Open(), [System.Text.UTF8Encoding]::new($false))
    $writer.Write($xmlText)
    $writer.Dispose()
}
finally {
    $archive.Dispose()
}
